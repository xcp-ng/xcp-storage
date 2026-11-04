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

import time

# ==============================================================================

class Clock:
    """
    Measure the time elapsed since clock creation or its last `start` call using a monotonic clock.
    """

    def __init__(self) -> None:
        self._start_time = time.monotonic()

    def start(self) -> None:
        self._start_time = time.monotonic()

    @property
    def elapsed_time(self) -> float:
        return time.monotonic() - self._start_time

class Timer:
    """
    Expire once `timeout` has elapsed since timer creation or its last `start` call.
    """

    def __init__(self, timeout: float) -> None:
        self._clock = Clock()
        self._timeout = timeout

    def start(self) -> None:
        self._clock.start()

    @property
    def remaining_time(self) -> float:
        """
        Time left before the expiration, 0 once expired.
        """

        return max(self._timeout - self._clock.elapsed_time, 0.0)

    def has_expired(self) -> bool:
        return self._clock.elapsed_time >= self._timeout
