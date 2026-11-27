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

from collections import deque
import contextlib
import threading
import time
from types import TracebackType

from xcp_storage.utils.check import check_positive_int
from xcp_storage.utils.time import Timer

from xcp_storage.typing import (
    Callable,
    cast,
    Deque,
    Generic,
    List,
    Optional,
    override,
    ParamSpec,
    Tuple,
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
    block, and its exit always waits for the end of all of them, the tasks queued included, so that no thread
    outlives the block.

    `max_threads` bounds the threads running at once: like `ThreadPoolExecutor`, `start` never waits, a task in
    excess is queued and run, in the order of the starts, by a thread once it ended its own. A thread that ended
    its task waits for the next one, taken before a new thread is created, until the exit of the block.

    At exit, if the block itself raised, its exception is kept. Otherwise:
    - `ThreadError` is raised if threads raised exceptions (the first one being its cause),
    - `ThreadTimeoutError` if threads are still running after `join_timeout`, shared by all of them, the tasks not
      started yet being dropped. Without timeout, a thread that never ends blocks the exit.
    - `ValueError` is raised if `max_threads` is not positive.
    """

    def __init__(
        self,
        *,
        join_timeout: Optional[float] = None,
        daemon: bool = False,
        max_threads: Optional[int] = None
    ) -> None:
        if max_threads is not None:
            check_positive_int(max_threads, "maximum thread count")

        self._join_timeout = join_timeout
        self._daemon = daemon
        self._max_threads = max_threads

        # Guard the threads, the pending tasks, the idle count and the stop: a thread ending its task takes the next
        # one, or waits for it (`_idle_count` threads do) until `start` gives it one or `_stopping` is set.
        self._condition = threading.Condition()

        self._threads: List[threading.Thread] = []
        self._pending_tasks: Deque[Callable[[], None]] = deque()
        self._idle_count = 0
        self._exceptions: List[BaseException] = []
        self._stopping = False
        self._active = False

    @override
    def __enter__(self) -> "ThreadGroup":
        if self._active:
            raise RuntimeError("Thread group is already entered.")
        self._stopping = False
        self._active = True
        return self

    @override
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        alive_count, dropped_task_count = self._join()

        self._active = False
        if exc_type is not None:
            return

        # Copy: a thread still running can add an exception.
        exceptions = list(self._exceptions)
        if exceptions:
            raise ThreadError(f"Exception raised in {len(exceptions)} thread(s).", exceptions) from exceptions[0]

        if alive_count:
            message = f"Thread(s) still running after {self._join_timeout} second(s): {alive_count}."
            if dropped_task_count:
                message += f" Task(s) not started: {dropped_task_count}."
            raise ThreadTimeoutError(message)

    def start(self, target: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> ThreadGroupFuture[T]:
        """
        Call `target(*args, **kwargs)` in a new thread of the group, and return its future return value.
        """

        if not self._active:
            raise RuntimeError("Thread group is not entered: threads must be started inside its `with` block.")

        future: ThreadGroupFuture[T] = ThreadGroupFuture()

        def task() -> None:
            try:
                future._set_value(target(*args, **kwargs)) # noqa: SLF001
            except BaseException as e:
                self._exceptions.append(e)

        with self._condition:
            self._pending_tasks.append(task)
            if self._idle_count:
                self._idle_count -= 1
                self._condition.notify()
            elif self._max_threads is None or len(self._threads) < self._max_threads:
                self._threads.append(threading.Thread(target=self._run_tasks, daemon=self._daemon))
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

    def _run_tasks(self) -> None:
        # Body of a thread: the pending tasks, waiting for the next one while none is pending, until the stop.
        while True:
            with self._condition:
                while not self._pending_tasks:
                    if self._stopping:
                        return
                    self._idle_count += 1
                    # Woken by `start` for a task, taken meanwhile by a thread that ended its own: wait again.
                    self._condition.wait()
                task = self._pending_tasks.popleft()
            task()

    def _join(self) -> Tuple[int, int]:
        """
        Wait for the end of the threads, the ones started meanwhile included, and
        return the number of threads still alive and the number of tasks dropped,
        both 0 unless `join_timeout` expired: the threads still running must not
        take the tasks pending after the exit.
        """

        with self._condition:
            # The threads end once no task is pending, the idle ones at once.
            self._stopping = True
            self._idle_count = 0
            self._condition.notify_all()

        timer = Timer(self._join_timeout) if self._join_timeout is not None else None
        while True:
            with self._condition:
                self._threads = [thread for thread in self._threads if thread.is_alive()]
                if not self._threads or (timer is not None and timer.has_expired()):
                    # Nothing pending without timeout: a thread ends with the queue empty.
                    dropped_task_count = len(self._pending_tasks)
                    self._pending_tasks.clear()
                    return len(self._threads), dropped_task_count
                thread = self._threads[0]
            thread.join(None if timer is None else timer.remaining_time)
