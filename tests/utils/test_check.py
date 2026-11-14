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

import re

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.check import (
    check_non_negative_int,
    check_regex_match,
    check_type,
    is_str_integer,
    is_str_unsigned_integer,
)

from xcp_storage.typing import Final

# ==============================================================================

CHECK_VALUE_DESCRIPTION: Final = "test value"

class TestCheckType:
    @pytest.mark.parametrize("value, value_type", [
        (1, int),
        (True, bool),
        ("a", str),
        (1, object),
    ])
    def test_valid(self, value: object, value_type: type) -> None:
        check_type(value, value_type, CHECK_VALUE_DESCRIPTION)

    @pytest.mark.parametrize("value, value_type, shown_value", [
        (True, int, "`True` (type `bool`)"),
        (1, bool, "`1` (type `int`)"),
        (b"a", str, "`b'a'` (type `bytes`)"),
        (None, str, "`None` (type `NoneType`)"),
    ])
    def test_invalid(self, value: object, value_type: type, shown_value: str) -> None:
        with raises_exactly(ValueError, f"Not a {CHECK_VALUE_DESCRIPTION}: {shown_value}."):
            check_type(value, value_type, CHECK_VALUE_DESCRIPTION)

class TestCheckNonNegativeInt:
    @pytest.mark.parametrize("value", [0, 1, 2**40])
    def test_valid(self, value: int) -> None:
        check_non_negative_int(value, CHECK_VALUE_DESCRIPTION)

    @pytest.mark.parametrize("value", [-1, -(2**40)])
    def test_negative(self, value: int) -> None:
        with raises_exactly(ValueError, f"Invalid {CHECK_VALUE_DESCRIPTION}: `{value}`."):
            check_non_negative_int(value, CHECK_VALUE_DESCRIPTION)

    @pytest.mark.parametrize("value, shown_value", [
        (True, "`True` (type `bool`)"),
        (False, "`False` (type `bool`)"),
        (1.0, "`1.0` (type `float`)"),
        ("1", "`'1'` (type `str`)"),
        (None, "`None` (type `NoneType`)"),
    ])
    def test_not_an_int(self, value: object, shown_value: str) -> None:
        with raises_exactly(ValueError, f"Not a {CHECK_VALUE_DESCRIPTION}: {shown_value}."):
            check_non_negative_int(value, CHECK_VALUE_DESCRIPTION) # type: ignore[arg-type]

class TestCheckRegexMatch:
    REGEX: Final = re.compile(r"[a-z]+")

    def test_valid(self) -> None:
        check_regex_match("abc", self.REGEX, CHECK_VALUE_DESCRIPTION)

    @pytest.mark.parametrize("value", ["", "abc1", "1abc", "ab c"])
    def test_no_full_match(self, value: str) -> None:
        with raises_exactly(ValueError, f"Invalid {CHECK_VALUE_DESCRIPTION}: `{value}`."):
            check_regex_match(value, self.REGEX, CHECK_VALUE_DESCRIPTION)

    def test_not_a_string(self) -> None:
        with raises_exactly(ValueError, f"Not a {CHECK_VALUE_DESCRIPTION}: `b'abc'` (type `bytes`)."):
            check_regex_match(b"abc", self.REGEX, CHECK_VALUE_DESCRIPTION) # type: ignore[arg-type]

# ------------------------------------------------------------------------------

class TestIsStrUnsignedInteger:
    @pytest.mark.parametrize("text, base", [
        ("0", 10),
        ("007", 10),
        ("1234567890", 10),
        ("2a", 16),
        ("FF", 16),
        ("0123456789abcdefABCDEF", 16),
    ])
    def test_integer(self, text: str, base: int) -> None:
        assert is_str_unsigned_integer(text, base=base)

    @pytest.mark.parametrize("text, base", [
        ("", 10),
        # Accepted by `int`.
        ("-1", 10),
        ("+1", 10),
        ("1_0", 10),
        (" 1", 10),
        ("1 ", 10),
        ("0x2a", 16),
        # Accepted by `str.isdecimal` and `int`: Arabic-Indic and fullwidth digits.
        ("\u0661\u0662", 10),
        ("\uff11\uff12", 10),
        # Accepted by `str.isdigit`, not by `int`.
        ("\u00b2", 10),
        ("1.0", 10),
        ("2a", 10),
        ("g", 16),
    ])
    def test_not_an_integer(self, text: str, base: int) -> None:
        assert not is_str_unsigned_integer(text, base=base)

    # Never raises, whatever the arguments.
    @pytest.mark.parametrize("text, base", [
        (12, 10),
        (None, 10),
        (b"12", 10),
        ("12", 8),
        ("12", "10"),
        ("12", [10]),
    ])
    def test_invalid_arguments(self, text: object, base: object) -> None:
        assert not is_str_unsigned_integer(text, base=base) # type: ignore[arg-type]

class TestIsStrInteger:
    @pytest.mark.parametrize("text, base", [
        ("0", 10),
        ("12", 10),
        ("-0", 10),
        ("-007", 10),
        ("-2a", 16),
    ])
    def test_integer(self, text: str, base: int) -> None:
        assert is_str_integer(text, base=base)

    @pytest.mark.parametrize("text, base", [
        ("", 10),
        ("-", 10),
        ("--1", 10),
        ("- 1", 10),
        ("1-", 10),
        # Accepted by `int`.
        ("+1", 10),
        (" -1", 10),
        ("-0x2a", 16),
        # Accepted by `int`: Arabic-Indic digits.
        ("-\u0661\u0662", 10),
        ("-2a", 10),
    ])
    def test_not_an_integer(self, text: str, base: int) -> None:
        assert not is_str_integer(text, base=base)

    # Never raises, whatever the arguments.
    @pytest.mark.parametrize("text, base", [
        (-12, 10),
        (None, 10),
        (b"-12", 10),
        ("-12", 8),
        ("-12", "10"),
    ])
    def test_invalid_arguments(self, text: object, base: object) -> None:
        assert not is_str_integer(text, base=base) # type: ignore[arg-type]
