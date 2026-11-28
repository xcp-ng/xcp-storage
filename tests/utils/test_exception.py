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

from xcp_storage.utils.exception import format_exception_traceback, stringify_exception

from xcp_storage.typing import Final, override

# ==============================================================================

MESSAGE: Final = "Something failed."
CAUSE_MESSAGE: Final = "Something else failed before."

class UnprintableError(Exception):
    @override
    def __str__(self) -> str:
        raise RuntimeError("Unprintable.")

# ------------------------------------------------------------------------------

class TestFormatExceptionTraceback:
    def test_raised(self) -> None:
        # The traceback as printed by the interpreter: the frames, then the type and the message.
        try:
            raise ValueError(MESSAGE)
        except ValueError as e:
            message = format_exception_traceback(e)
        assert message.startswith("Traceback (most recent call last):\n")
        assert "    raise ValueError(MESSAGE)\n" in message
        assert message.endswith(f"ValueError: {MESSAGE}\n")

    def test_chained(self) -> None:
        # The exception it was raised from comes first.
        try:
            try:
                raise ValueError(CAUSE_MESSAGE)
            except ValueError as e:
                raise RuntimeError(MESSAGE) from e
        except RuntimeError as e:
            message = format_exception_traceback(e)
        cause_end = message.index(f"ValueError: {CAUSE_MESSAGE}\n")
        assert "The above exception was the direct cause of the following exception:" in message[cause_end:]
        assert message.endswith(f"RuntimeError: {MESSAGE}\n")

    def test_not_raised(self) -> None:
        # No frame: the type and the message only.
        assert format_exception_traceback(ValueError(MESSAGE)) == f"ValueError: {MESSAGE}\n"

class TestStringifyException:
    def test_message(self) -> None:
        assert stringify_exception(ValueError(MESSAGE)) == MESSAGE

    def test_unprintable(self) -> None:
        assert stringify_exception(UnprintableError()) == "Exception of type `UnprintableError`."

    def test_no_message(self) -> None:
        assert stringify_exception(ValueError()) == "Exception of type `ValueError`."
