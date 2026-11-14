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

from tests.utils.exception import raises_exactly
from xcp_storage.utils.math import KIB, round_up

# ==============================================================================

class TestRoundUp:
    @pytest.mark.parametrize(("value", "multiple", "rounded_value"), [
        (0, 512, 0),
        (1, 512, 512),
        (512, 512, 512),
        (513, 512, 1024),
        (1000, 512, 1024),
        (5, 3, 6),
        (64 * KIB + 1, 64 * KIB, 128 * KIB),
    ])
    def test_round_up(self, value: int, multiple: int, rounded_value: int) -> None:
        assert round_up(value, multiple) == rounded_value

    @pytest.mark.parametrize(("value", "multiple", "message"), [
        (-1, 512, "Invalid value: `-1`."),
        (1, -1, "Invalid multiple: `-1`."),
        (1, 0, "Multiple must be greater than 0."),
        (True, 512, "Not a value: `True` (type `bool`)."),
    ])
    def test_invalid(self, value: int, multiple: int, message: str) -> None:
        with raises_exactly(ValueError, message):
            round_up(value, multiple)
