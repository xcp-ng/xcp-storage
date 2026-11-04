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

import pytest

from xcp_storage.utils.contextlib import scoped_factory

from xcp_storage.typing import List

# ==============================================================================

class TestScopedFactory:
    def test_create(self) -> None:
        def create(name: str, *, number: int) -> str:
            return f"{name}{number}"

        with scoped_factory(create, lambda _: None) as factory:
            assert factory("a", number=1) == "a1"

    def test_destroy_in_reverse_order(self) -> None:
        destroyed_objects: List[int] = []
        with scoped_factory(int, destroyed_objects.append) as factory:
            factory(1)
            factory(2)
            assert destroyed_objects == []
        assert destroyed_objects == [2, 1]

    def test_destroy_on_error(self) -> None:
        destroyed_objects: List[int] = []
        with pytest.raises(ValueError), scoped_factory(int, destroyed_objects.append) as factory:
            factory(1)
            raise ValueError
        assert destroyed_objects == [1]

    def test_destroy_all_when_destroy_fails(self) -> None:
        destroyed_objects: List[int] = []

        class DestroyError(Exception):
            pass

        def destroy(created_object: int) -> None:
            destroyed_objects.append(created_object)
            raise DestroyError(created_object)

        with pytest.raises(DestroyError) as exc_info, scoped_factory(int, destroy) as factory:
            factory(1)
            factory(2)
        assert destroyed_objects == [2, 1]

        # The last error is raised, chained to the first one.
        assert exc_info.value.args == (1,)
        assert isinstance(exc_info.value.__context__, DestroyError)
        assert exc_info.value.__context__.args == (2,)
