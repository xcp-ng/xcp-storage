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

import pytest

from tests.utils.exception import raises_exactly
from xcp_storage.utils.thread import ThreadError, ThreadGroup, ThreadGroupFuture, ThreadTimeoutError
from xcp_storage.utils.time import Clock

from xcp_storage.typing import Final, Optional

# ==============================================================================

class TestThreadGroup:
    THREAD_DELAY: Final = 0.1
    JOIN_TIMEOUT: Final = 0.1

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

    def test_join_timeout(self) -> None:
        release_event = threading.Event()
        try:
            message = f"Thread(s) still running after {self.JOIN_TIMEOUT} second(s): 1/2."
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

    @pytest.mark.parametrize("daemon", [False, True])
    def test_daemon_mode(self, *, daemon: bool) -> None:
        with ThreadGroup(daemon=daemon) as thread_group:
            daemon_future = thread_group.start(lambda: threading.current_thread().daemon)
        assert daemon_future.value == daemon
