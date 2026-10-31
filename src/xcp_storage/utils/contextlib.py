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

from xcp_storage.typing import (
    Callable,
    Iterator,
    List,
    ParamSpec,
    TypeVar,
)

P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

@contextlib.contextmanager
def scoped_factory(create: Callable[P, T], destroy: Callable[[T], None]) -> Iterator[Callable[P, T]]:
    """
    Yield a factory calling `create` to instantiate objects and call `destroy` to clean them up after use.
    """

    objects: List[T] = []

    def factory(*args: P.args, **kwargs: P.kwargs) -> T:
        objects.append(create(*args, **kwargs))
        return objects[-1]

    def destroy_all() -> None:
        # Recursive so that each `destroy` runs in a `finally`: python chains its exception to the pending one.
        if objects:
            try:
                destroy(objects.pop())
            finally:
                destroy_all()

    try:
        yield factory
    finally:
        destroy_all()
