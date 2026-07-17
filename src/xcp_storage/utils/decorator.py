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
    Any,
    Callable,
    cast,
    ParamSpec,
    TypeVar,
)

C = TypeVar("C", bound=type)
P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

def decorate_all_methods(decorator: Callable[[Callable[P, T]], Callable[P, T]]) -> Callable[[C], C]:
    """
    Decorate all public methods of a class, including the inherited ones.

    Instance, static and class methods are supported.
    Inherited methods are copied in the decorated class: the base class is not modified.
    """

    def wrapper(cls: C) -> C:
        for name in dir(cls):
            if name.startswith("_"):
                continue

            # Get the raw attribute (without the descriptor protocol) to detect
            # `staticmethod`/`classmethod` objects and wrap them back after decoration.
            attribute = inspect.getattr_static(cls, name)
            if isinstance(attribute, staticmethod):
                setattr(cls, name, staticmethod(decorator(attribute.__func__)))
            elif isinstance(attribute, classmethod):
                # The `cls` argument of the underlying function is not expressible with `P`.
                # So we must cast to make `mypy` happy.
                class_decorator = cast(Callable[[Callable[..., Any]], Callable[..., Any]], decorator)
                setattr(cls, name, classmethod(class_decorator(attribute.__func__)))
            elif inspect.isroutine(attribute):
                setattr(cls, name, decorator(attribute))
        return cls
    return wrapper
