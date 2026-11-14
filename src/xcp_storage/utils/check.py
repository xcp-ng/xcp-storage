# Copyright (C) 2026  Vates SAS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import string

from xcp_storage.typing import (
    Final,
    Pattern,
)

# ==============================================================================

# ASCII digits of the bases accepted by `is_str_unsigned_integer`.
_ASCII_DIGITS: Final = {10: string.digits, 16: string.hexdigits}

# ------------------------------------------------------------------------------

def check_type(value: object, value_type: type, description: str) -> None:
    """
    Raise `ValueError` if `value` is not a `value_type`.
    `description` names the value in the message (e.g. "DRBD volume number").
    """

    if not isinstance(value, value_type) or (isinstance(value, bool) and value_type is not bool):
        raise ValueError(f"Not a {description}: `{value!r}` (type `{type(value).__name__}`).")

def check_non_negative_int(value: int, description: str) -> None:
    """
    Raise `ValueError` if `value` is not an `int` (see `check_type`) or is negative.
    """

    check_type(value, int, description)
    if value < 0:
        raise ValueError(f"Invalid {description}: `{value}`.")

def check_regex_match(value: str, regex: Pattern[str], description: str) -> None:
    """
    Raise `ValueError` if `value` is not a `str` fully matched by `regex`.
    """

    check_type(value, str, description)
    if not regex.fullmatch(value):
        raise ValueError(f"Invalid {description}: `{value}`.")

# ------------------------------------------------------------------------------

def is_str_unsigned_integer(text: object, *, base: int = 10) -> bool:
    """
    Return whether `text` is a `str` holding a non-negative integer written only
    with the ASCII digits of `base` (10 or 16): no sign, `_`, space, prefix (`0x`)
    nor other unicode digits, unlike `str.isdecimal`, `str.isdigit`, `str.isnumeric`
    and `int`, so `int(text, base)` then never fails.
    """

    if not isinstance(text, str) or not bool(text):
        return False

    digits = _ASCII_DIGITS.get(base) if isinstance(base, int) else None
    return digits is not None and all(digit in digits for digit in text)

def is_str_integer(text: object, *, base: int = 10) -> bool:
    """
    Return whether `text` is a `str` holding an integer: an optional `-` sign, then
    an unsigned integer (see `is_str_unsigned_integer`).
    """

    if isinstance(text, str) and text.startswith("-"):
        text = text[1:]
    return is_str_unsigned_integer(text, base=base)
