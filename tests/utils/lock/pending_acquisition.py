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

from functools import partial
import threading

import pytest

from tests.utils.lock.fifo_lock_service import FIFO_LOCK_DAEMON_POLL_INTERVAL
from tests.utils.lock.lock_variant import (
    DEFAULT_LOCK_ACQUIRE_TIMEOUT,
    LockFactory,
    LockMode,
    ReadWriteLockFactory,
)
from tests.utils.thread import create_thread_group
from xcp_storage.utils.sync import wait_for_condition
from xcp_storage.utils.thread import ThreadGroup

from xcp_storage.typing import (
    Callable,
    Iterator,
    Optional,
)

# ==============================================================================

class PendingAcquisition:
    """
    Acquisition of a lock created by `lock_factory`, run in a thread of `thread_group`:
    the test checks later whether it is still waiting or how it ended.
    """

    def __init__(
        self,
        thread_group: ThreadGroup,
        lock_factory: LockFactory,
        lock_mode: LockMode,
        *,
        timeout: float = DEFAULT_LOCK_ACQUIRE_TIMEOUT
    ) -> None:
        self.lock = lock_factory()
        self.acquire_exception: Optional[BaseException] = None
        self._timeout = timeout
        self._acquired = False
        self._ended_event = threading.Event()
        thread_group.start(self._run, lock_mode)

    def is_waiting_for_acquisition(self, *, delay: float = 0.0) -> bool:
        """
        Return whether the acquisition is still in progress
        (neither acquired nor failed) after `delay` seconds.
        """

        return not self._ended_event.wait(delay)

    def wait_for_acquisition(self) -> bool:
        """
        Wait for the end of the acquisition, and return whether the lock was acquired:
        false if it timed out or failed (see `acquire_exception`).
        """

        self._ended_event.wait(self._timeout)
        return self._acquired

    def _run(self, lock_mode: LockMode) -> None:
        try:
            lock_mode.acquire(self.lock, timeout=self._timeout)
            self._acquired = True
        except BaseException as e:
            self.acquire_exception = e
        finally:
            self._ended_event.set()

PendingAcquisitionFactory = Callable[..., PendingAcquisition]

@pytest.fixture
def pending_acquisition_factory(read_write_lock_factory: ReadWriteLockFactory) -> Iterator[PendingAcquisitionFactory]:
    with create_thread_group() as thread_group:
        yield partial(PendingAcquisition, thread_group, read_write_lock_factory)

# ------------------------------------------------------------------------------

QueuedWriterFactory = Callable[..., PendingAcquisition]

@pytest.fixture
def queued_writer_factory(
    read_write_lock_factory: ReadWriteLockFactory, pending_acquisition_factory: PendingAcquisitionFactory
) -> QueuedWriterFactory:
    """
    Starts the acquisition of a writer, and waits until its request is in the queue of the daemon. The queue is
    detected with readers probes, refused only behind a writer: the lock must be held by readers.
    """

    probe_lock = read_write_lock_factory()

    def is_probe_refused() -> bool:
        if probe_lock.shared_try_acquire():
            probe_lock.shared_release()
            return False
        return True

    def queue_writer(*, timeout: float = DEFAULT_LOCK_ACQUIRE_TIMEOUT) -> PendingAcquisition:
        assert not is_probe_refused(), "The lock must be held by readers to detect the queued writer."
        writer = pending_acquisition_factory(LockMode.EXCLUSIVE, timeout=timeout)
        assert wait_for_condition(is_probe_refused, timeout, FIFO_LOCK_DAEMON_POLL_INTERVAL)
        return writer

    return queue_writer
