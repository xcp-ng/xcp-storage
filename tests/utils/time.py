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

from unittest.mock import MagicMock, patch

import pytest

from xcp_storage.typing import Iterator

# ==============================================================================

class SimulatedTime:
    """
    Time returned by `time.monotonic` that only advances when asked: `advance`,
    or `time.sleep` with `simulated_time`.
    """

    def __init__(self) -> None:
        self._current_time = 0.0

    def monotonic(self) -> float:
        return self._current_time

    def advance(self, delay: float) -> None:
        self._current_time += delay

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_sleep() -> Iterator[MagicMock]:
    with patch("time.sleep", autospec=True) as mock_sleep:
        yield mock_sleep

@pytest.fixture
def simulated_time(mock_sleep: MagicMock) -> Iterator[SimulatedTime]:
    """
    Starts at 0 and advances by the delay of each `time.sleep` call.
    """

    simulated_time = SimulatedTime()
    mock_sleep.side_effect = simulated_time.advance
    with patch("time.monotonic", autospec=True, side_effect=simulated_time.monotonic):
        yield simulated_time
