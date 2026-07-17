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

import inspect

from xcp_storage.typing import (
    Callable,
    ParamSpec,
    TypeVar,
)

C = TypeVar("C", bound=type)
P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

def decorate_all_methods(decorator: Callable[[Callable[P, T]], Callable[P, T]]) -> Callable[[C], C]:
    def wrapper(cls: C) -> C:
        for name, method in inspect.getmembers(cls, inspect.isroutine):
            if not name.startswith("_"):
                setattr(cls, name, decorator(method))
        return cls
    return wrapper
