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

from xcp_storage.utils.time import Clock, Timer

from xcp_storage.typing import (
    Callable,
    Tuple,
    TypeVar,
)

T = TypeVar("T")

# ==============================================================================

def wait_for_condition(function: Callable[[], T], timeout: float, interval: float) -> T:
    if timeout <= 0:
        return function()

    timer = Timer(timeout)
    while True:
        result = function()
        if result:
            return result
        remaining_time = timer.remaining_time
        if remaining_time <= 0:
            return result
        time.sleep(min(interval, remaining_time))

def wait_for_stable_value(
    function: Callable[[], T],
    timeout: float,
    interval: float,
    *,
    stable_count: int = 2,
    stable_duration: float = 0.0
) -> Tuple[bool, T]:
    """
    Call `function` every `interval` seconds until it returns equal
    values `stable_count` times in a row over at least `stable_duration` seconds,
    and return whether it happened within `timeout` and the last value.

    A change restarts the count and the duration. A `timeout <= 0` makes a single call.
    """

    if stable_count < 1:
        raise ValueError(f"Invalid stable count: `{stable_count}`.")

    if stable_count == 1 and stable_duration <= 0:
        return True, function()

    timer = Timer(timeout)
    value = function()
    stable_clock = Clock()

    stable_iteration = 1
    while stable_iteration < stable_count or stable_clock.elapsed_time < stable_duration:
        remaining_time = timer.remaining_time
        if remaining_time <= 0:
            return False, value
        time.sleep(min(interval, remaining_time))

        previous_value, value = value, function()
        if value == previous_value:
            stable_iteration += 1
        else:
            stable_iteration = 1
            stable_clock.start()

    return True, value
