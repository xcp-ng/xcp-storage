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

import threading
import time

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.thread import ThreadError, ThreadGroup, ThreadGroupFuture, ThreadTimeoutError
from xcp_storage.utils.time import Clock

from xcp_storage.typing import Final, List, Optional

# ==============================================================================

class TestThreadGroup:
    THREAD_DELAY: Final = 0.1
    JOIN_TIMEOUT: Final = 0.1

    # Bound of the wait for the start of a task that must start.
    TASK_START_TIMEOUT: Final = 1.0

    NOT_RETURNED_MESSAGE: Final = "Thread did not return."
    NOT_ENTERED_MESSAGE: Final = "Thread group is not entered: threads must be started inside its `with` block."

    def test_result(self) -> None:
        with ThreadGroup() as thread_group:
            length_future: ThreadGroupFuture[int] = thread_group.start(len, "abc")
            nothing_future: ThreadGroupFuture[Optional[int]] = thread_group.start(lambda: None)
        assert length_future.value == 3
        assert nothing_future.value is None

    def test_result_before_task_end(self) -> None:
        release_event = threading.Event()
        with ThreadGroup() as thread_group:
            future = thread_group.start(release_event.wait)
            try:
                with raises_exactly(RuntimeError, self.NOT_RETURNED_MESSAGE):
                    future.value # noqa: B018
            finally:
                release_event.set()
        assert future.value

    def test_result_after_thread_exception(self) -> None:
        def fail() -> int:
            raise ValueError("Failure.")

        with pytest.raises(ThreadError), ThreadGroup() as thread_group:
            future = thread_group.start(fail)
        with raises_exactly(RuntimeError, self.NOT_RETURNED_MESSAGE):
            future.value # noqa: B018

    def test_thread_exceptions(self) -> None:
        exceptions = [ValueError("First."), KeyError("second")]

        def fail(exception: BaseException) -> None:
            raise exception

        with raises_exactly(ThreadError, "Exception raised in 2 thread(s).") as exc_info, \
                ThreadGroup() as thread_group:
            thread_group.start(fail, exceptions[0])
            thread_group.defer_start(self.THREAD_DELAY, fail, exceptions[1])

        assert exc_info.value.exceptions == exceptions
        assert exc_info.value.__cause__ is exceptions[0]

    def test_block_exception_is_kept(self) -> None:
        ended_event = threading.Event()

        def fail_later() -> None:
            ended_event.set()
            raise ValueError("Thread failure.")

        with raises_exactly(RuntimeError, "Block failure."), ThreadGroup() as thread_group:
            thread_group.defer_start(self.THREAD_DELAY, fail_later)
            raise RuntimeError("Block failure.")
        assert ended_event.is_set()

    def test_defer_start(self) -> None:
        clock = Clock()
        with ThreadGroup() as thread_group:
            elapsed_time_future = thread_group.defer_start(self.THREAD_DELAY, lambda: clock.elapsed_time)
        assert elapsed_time_future.value >= self.THREAD_DELAY

    def test_start_outside_block(self) -> None:
        thread_group = ThreadGroup()

        with raises_exactly(RuntimeError, self.NOT_ENTERED_MESSAGE):
            thread_group.start(lambda: None)
        with raises_exactly(RuntimeError, self.NOT_ENTERED_MESSAGE):
            thread_group.defer_start(0, lambda: None)

        with thread_group:
            pass

        with raises_exactly(RuntimeError, self.NOT_ENTERED_MESSAGE):
            thread_group.start(lambda: None)

    def test_enter_twice(self) -> None:
        with ThreadGroup() as thread_group, raises_exactly(RuntimeError, "Thread group is already entered."):
            thread_group.__enter__()

    def test_exit_waits_for_threads(self) -> None:
        with ThreadGroup() as thread_group:
            length_future = thread_group.defer_start(self.THREAD_DELAY, len, "abc")
        assert length_future.value == 3

    def test_max_threads(self) -> None:
        # The tasks in excess are queued, `start` never waits: never more threads at once than allowed,
        # every task run before the exit, the queued ones included.
        lock = threading.Lock()

        max_threads = 2
        thread_count = 5

        running_count = 0
        max_running_count = 0

        def run() -> None:
            nonlocal running_count, max_running_count
            with lock:
                running_count += 1
                max_running_count = max(max_running_count, running_count)

            time.sleep(self.THREAD_DELAY)

            with lock:
                running_count -= 1

        with ThreadGroup(max_threads=max_threads) as thread_group:
            clock = Clock()
            futures = [thread_group.start(run) for _ in range(thread_count)]
            assert clock.elapsed_time < self.THREAD_DELAY

        assert len(futures) == thread_count
        assert all(future.value is None for future in futures)
        assert max_running_count == max_threads

    def test_pending_tasks_order(self) -> None:
        # The tasks queued run in the order of the starts, one thread at a time.
        task_count = 5
        task_indexes: List[int] = []
        with ThreadGroup(max_threads=1) as thread_group:
            for task_index in range(task_count):
                thread_group.start(task_indexes.append, task_index)
        assert task_indexes == list(range(task_count))

    def test_idle_thread_reused(self) -> None:
        # A thread that ended its task takes the next one, a new thread is created only if none is idle.
        max_threads = 2

        ended_event = threading.Event()
        release_event = threading.Event()
        started_event = threading.Event()

        with ThreadGroup(max_threads=max_threads) as thread_group:
            try:
                thread_group.start(ended_event.set)
                assert ended_event.wait(self.TASK_START_TIMEOUT)
                thread_group.start(release_event.wait)
                thread_group.start(started_event.set)
                assert started_event.wait(self.TASK_START_TIMEOUT)
                assert len(thread_group._threads) == max_threads # noqa: SLF001
            finally:
                release_event.set()

    def test_tasks_run_by_the_same_thread(self) -> None:
        task_count = 20
        thread_idents = set()

        with ThreadGroup() as thread_group:
            for _ in range(task_count):
                ended_event = threading.Event()

                def run(ended_event: threading.Event = ended_event) -> None:
                    thread_idents.add(threading.get_ident())
                    ended_event.set()

                thread_group.start(run)
                assert ended_event.wait(self.TASK_START_TIMEOUT)

        assert len(thread_idents) == 1

    def test_start_from_thread(self) -> None:
        # A task starting another one while every thread is busy does not wait for it (no deadlock), the exit does.
        with ThreadGroup(max_threads=1) as thread_group:
            future = thread_group.start(lambda: thread_group.start(len, "abc"))
        assert future.value.value == 3

    @pytest.mark.parametrize("max_threads", [0, -1])
    def test_invalid_max_threads(self, max_threads: int) -> None:
        with raises_exactly(ValueError, f"Invalid maximum thread count: `{max_threads}`."):
            ThreadGroup(max_threads=max_threads)

    def test_join_timeout(self) -> None:
        release_event = threading.Event()
        try:
            message = f"Thread(s) still running after {self.JOIN_TIMEOUT} second(s): 1."
            with raises_exactly(ThreadTimeoutError, message), \
                    ThreadGroup(join_timeout=self.JOIN_TIMEOUT) as thread_group:
                thread_group.start(lambda: None)
                thread_group.start(release_event.wait)
        finally:
            release_event.set()

    def test_join_timeout_is_shared(self) -> None:
        # With a timeout per thread, the exit would wait `thread_count * JOIN_TIMEOUT`.
        thread_count = 5
        release_event = threading.Event()
        try:
            clock = Clock()
            with pytest.raises(ThreadTimeoutError), ThreadGroup(join_timeout=self.JOIN_TIMEOUT) as thread_group:
                for _ in range(thread_count):
                    thread_group.start(release_event.wait)
            assert self.JOIN_TIMEOUT <= clock.elapsed_time < thread_count * self.JOIN_TIMEOUT
        finally:
            release_event.set()

    def test_join_timeout_drops_pending_tasks(self) -> None:
        release_event = threading.Event()
        try:
            message = f"Thread(s) still running after {self.JOIN_TIMEOUT} second(s): 1. Task(s) not started: 1."
            with raises_exactly(ThreadTimeoutError, message), \
                    ThreadGroup(join_timeout=self.JOIN_TIMEOUT, max_threads=1) as thread_group:
                thread_group.start(release_event.wait)
                length_future = thread_group.start(len, "abc")
        finally:
            release_event.set()

        # Never started, even once the thread blocking it ended.
        thread_group._threads[0].join() # noqa: SLF001
        time.sleep(self.THREAD_DELAY)
        with raises_exactly(RuntimeError, self.NOT_RETURNED_MESSAGE):
            length_future.value # noqa: B018

    @pytest.mark.parametrize("daemon", [False, True])
    def test_daemon_mode(self, *, daemon: bool) -> None:
        with ThreadGroup(daemon=daemon) as thread_group:
            daemon_future = thread_group.start(lambda: threading.current_thread().daemon)
        assert daemon_future.value == daemon
