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

from xcp_storage.utils.decorator import decorate_all_methods

from xcp_storage.typing import (
    Any,
    Callable,
    cast,
    ParamSpec,
    TypeVar,
)

P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

class TestDecorateAllMethods:
    @staticmethod
    def decorator_tracker(method: Callable[P, T]) -> Callable[P, T]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            return method(*args, **kwargs)
        cast(Any, wrapped).is_decorated = True
        return wrapped

    def test_public_methods(self) -> None:
        @decorate_all_methods(TestDecorateAllMethods.decorator_tracker)
        class Class:
            def method_a(self) -> str:
                return "method_a"

            def method_b(self) -> str:
                return "method_b"

        instance = Class()

        assert getattr(instance.method_a, "is_decorated", False)
        assert getattr(instance.method_b, "is_decorated", False)

        assert instance.method_a() == "method_a"
        assert instance.method_b() == "method_b"

    def test_private_and_special_methods(self) -> None:
        @decorate_all_methods(TestDecorateAllMethods.decorator_tracker)
        class Class:
            def __init__(self) -> None:
                return

            def public_method(self) -> str:
                return "public"

            def _private_method(self) -> str:
                return "private"

        instance = Class()

        assert getattr(instance.public_method, "is_decorated", False)
        assert not hasattr(instance._private_method, "is_decorated") # noqa: SLF001
        assert not hasattr(Class.__init__, "is_decorated")

        assert instance.public_method() == "public"
        assert instance._private_method() == "private" # noqa: SLF001

    def test_non_methods(self) -> None:
        @decorate_all_methods(TestDecorateAllMethods.decorator_tracker)
        class Class:
            attribute = "i_am_an_attribute"

        instance = Class()

        assert not hasattr(instance.attribute, "is_decorated")
        assert instance.attribute == "i_am_an_attribute"
