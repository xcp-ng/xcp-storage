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

from xcp_storage.utils.time import Clock, Timer

# ==============================================================================

@patch("time.monotonic", autospec=True)
class TestClock:
    def test_elapsed_time(self, mock_time: MagicMock) -> None:
        mock_time.side_effect = [10.0, 12.5, 15.0]
        clock = Clock()
        assert clock.elapsed_time == 2.5
        assert clock.elapsed_time == 5.0

    def test_start(self, mock_time: MagicMock) -> None:
        mock_time.side_effect = [10.0, 12.5, 15.0]
        clock = Clock()
        clock.start()
        assert clock.elapsed_time == 2.5

@patch("time.monotonic", autospec=True)
class TestTimer:
    def test_remaining_time(self, mock_time: MagicMock) -> None:
        mock_time.side_effect = [10.0, 12.5, 15.0, 20.0]
        timer = Timer(5.0)
        assert timer.remaining_time == 2.5
        assert timer.remaining_time == 0.0
        assert timer.remaining_time == 0.0

    def test_has_expired(self, mock_time: MagicMock) -> None:
        mock_time.side_effect = [10.0, 12.5, 15.0]
        timer = Timer(5.0)
        assert not timer.has_expired()
        assert timer.has_expired()

    def test_start(self, mock_time: MagicMock) -> None:
        mock_time.side_effect = [10.0, 16.0, 18.0]
        timer = Timer(5.0)
        timer.start()
        assert timer.remaining_time == 3.0
