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

from tests.utils.time import SimulatedTime
from xcp_storage.utils.time import Clock, Timer

# ==============================================================================

class TestClock:
    def test_elapsed_time(self, simulated_time: SimulatedTime) -> None:
        clock = Clock()
        simulated_time.advance(2.5)
        assert clock.elapsed_time == 2.5
        simulated_time.advance(2.5)
        assert clock.elapsed_time == 5.0

    def test_start(self, simulated_time: SimulatedTime) -> None:
        clock = Clock()
        simulated_time.advance(2.5)
        clock.start()
        simulated_time.advance(2.5)
        assert clock.elapsed_time == 2.5

class TestTimer:
    def test_remaining_time(self, simulated_time: SimulatedTime) -> None:
        timer = Timer(5.0)
        simulated_time.advance(2.5)
        assert timer.remaining_time == 2.5
        simulated_time.advance(2.5)
        assert timer.remaining_time == 0.0
        simulated_time.advance(5.0)
        assert timer.remaining_time == 0.0

    def test_has_expired(self, simulated_time: SimulatedTime) -> None:
        timer = Timer(5.0)
        simulated_time.advance(2.5)
        assert not timer.has_expired()
        simulated_time.advance(2.5)
        assert timer.has_expired()

    def test_start(self, simulated_time: SimulatedTime) -> None:
        timer = Timer(5.0)
        simulated_time.advance(6.0)
        timer.start()
        simulated_time.advance(2.0)
        assert timer.remaining_time == 3.0
