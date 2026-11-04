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

import contextlib
import threading
import time
from types import TracebackType

from xcp_storage.utils.time import Timer

from xcp_storage.typing import (
    Callable,
    cast,
    Generic,
    List,
    Optional,
    override,
    ParamSpec,
    Type,
    TypeVar,
)

P = ParamSpec("P")
T = TypeVar("T")

# ==============================================================================

class ThreadError(Exception):
    """
    Base class of thread errors. `exceptions` holds the exceptions raised by the threads, if any.
    """

    def __init__(self, message: str, exceptions: Optional[List[BaseException]] = None) -> None:
        super().__init__(message)
        self.exceptions = exceptions or []

class ThreadTimeoutError(ThreadError):
    """
    Threads did not end in time.
    """

# ------------------------------------------------------------------------------

class ThreadGroupFuture(Generic[T]):
    """
    Return value of a function run by a `ThreadGroup`, available once its thread returned.
    """

    def __init__(self) -> None:
        self._value: Optional[T] = None
        self._fullfiled = False

    @property
    def value(self) -> T:
        if not self._fullfiled:
            raise RuntimeError("Thread did not return.")
        return cast(T, self._value)

    def _set_value(self, value: T) -> None:
        self._value = value
        self._fullfiled = True

# ------------------------------------------------------------------------------

class ThreadGroup(contextlib.AbstractContextManager):
    """
    Group of threads running functions, used as a context manager: threads can only be started inside its `with`
    block, and its exit always waits for the end of all of them, so that no thread outlives the block.

    At exit, if the block itself raised, its exception is kept. Otherwise:
    - `ThreadError` is raised if threads raised exceptions (the first one being its cause),
    - `ThreadTimeoutError` if threads are still running after `join_timeout`, shared by all of them. Without
      timeout, a thread that never ends blocks the exit.
    """

    def __init__(self, *, join_timeout: Optional[float] = None, daemon: bool = False) -> None:
        self._join_timeout = join_timeout
        self._daemon = daemon
        self._threads: List[threading.Thread] = []
        self._exceptions: List[BaseException] = []
        self._active = False

    @override
    def __enter__(self) -> "ThreadGroup":
        if self._active:
            raise RuntimeError("Thread group is already entered.")
        self._active = True
        return self

    @override
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        self._join()
        self._active = False
        if exc_type is not None:
            return

        # Copy: a thread still running can add an exception.
        exceptions = list(self._exceptions)
        if exceptions:
            raise ThreadError(f"Exception raised in {len(exceptions)} thread(s).", exceptions) from exceptions[0]

        alive_count = sum(thread.is_alive() for thread in self._threads)
        if alive_count:
            raise ThreadTimeoutError(
                f"Thread(s) still running after {self._join_timeout} second(s): {alive_count}/{len(self._threads)}."
            )

    def start(self, target: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> ThreadGroupFuture[T]:
        """
        Call `target(*args, **kwargs)` in a new thread of the group, and return its future return value.
        """

        if not self._active:
            raise RuntimeError("Thread group is not entered: threads must be started inside its `with` block.")

        future: ThreadGroupFuture[T] = ThreadGroupFuture()

        def run() -> None:
            try:
                future._set_value(target(*args, **kwargs)) # noqa: SLF001
            except BaseException as e:
                self._exceptions.append(e)

        self._threads.append(threading.Thread(target=run, daemon=self._daemon))
        self._threads[-1].start()
        return future

    def defer_start(
        self, delay: float, target: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> ThreadGroupFuture[T]:
        """
        Same as `start`, `target` being called after `delay` seconds.
        """

        def run() -> T:
            time.sleep(delay)
            return target(*args, **kwargs)

        return self.start(run)

    def _join(self) -> None:
        if self._join_timeout is None:
            for thread in self._threads:
                thread.join()
            return

        timer = Timer(self._join_timeout)
        for thread in self._threads:
            thread.join(timer.remaining_time)
