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

import contextlib

import pytest

from xcp_storage.typing import Iterator, Type, TypeVar

ExceptionT = TypeVar("ExceptionT", bound=BaseException)

# ==============================================================================

@contextlib.contextmanager
def raises_exactly(exception_class: Type[ExceptionT], message: str) -> Iterator[pytest.ExceptionInfo[ExceptionT]]:
    """
    Test for an exact exception message.
    """

    with pytest.raises(exception_class) as exc_info:
        yield exc_info
    assert str(exc_info.value) == message, f"Message {str(exc_info.value)!r} is not {message!r}."
