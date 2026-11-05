# ------------------------------------------------------------------------------
# Used: called, or passed as a function.
# ------------------------------------------------------------------------------

import time
import time as t

def measure() -> None:
    # ruleid: python-enforce-time-helpers
    start_time = time.monotonic()
    # ruleid: python-enforce-time-helpers
    time.monotonic_ns()
    # ruleid: python-enforce-time-helpers
    time.perf_counter()
    # ruleid: python-enforce-time-helpers
    time.perf_counter_ns()
    # ruleid: python-enforce-time-helpers
    t.monotonic()
    # ruleid: python-enforce-time-helpers
    get_time = time.monotonic
    # ok: python-enforce-time-helpers
    time.time()
    # ok: python-enforce-time-helpers
    time.sleep(1)
    # ok: python-enforce-time-helpers
    loop.monotonic()
    # ok: python-enforce-time-helpers
    clock.elapsed_time

# ok: python-enforce-time-helpers
@patch("time.monotonic")
def test_measure(mock_monotonic) -> None:
    pass

# ------------------------------------------------------------------------------
# Used after a "from" import: the import itself is not reported.
# ------------------------------------------------------------------------------

# ok: python-enforce-time-helpers
from time import monotonic
# ok: python-enforce-time-helpers
from time import perf_counter as counter
# ok: python-enforce-time-helpers
from time import sleep

def measure_imported() -> None:
    # ruleid: python-enforce-time-helpers
    monotonic()
    # ruleid: python-enforce-time-helpers
    counter()
    # ok: python-enforce-time-helpers
    sleep(1)
