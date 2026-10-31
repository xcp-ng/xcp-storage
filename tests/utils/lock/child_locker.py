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
import multiprocessing
import multiprocessing.synchronize
import signal

import pytest

from tests.utils.lock.lock_variant import (
    DEFAULT_LOCK_ACQUIRE_TIMEOUT,
    LockBackend,
    LockFactory,
    LockMode,
)
from xcp_storage.utils.contextlib import scoped_factory
from xcp_storage.utils.process import kill_process

from xcp_storage.typing import Callable, Iterator

# ==============================================================================

class ChildLocker:
    """
    Forked child process acquiring a lock created by `lock_factory`, then holding it until it's killed.
    """

    def __init__(self, lock_factory: LockFactory, lock_mode: LockMode) -> None:
        context = multiprocessing.get_context("fork")
        self._startup_event = context.Event()
        self._process = context.Process(
            target=self._acquire_lock,
            args=(lock_factory, lock_mode, self._startup_event),
            daemon=True
        )
        self._process.start()

    def wait_for_startup(self, *, timeout: float = DEFAULT_LOCK_ACQUIRE_TIMEOUT) -> bool:
        return self._startup_event.wait(timeout)

    def kill(self) -> None:
        kill_process(self._process)

    @staticmethod
    def _acquire_lock(
        lock_factory: LockFactory,
        lock_mode: LockMode,
        startup_event: "multiprocessing.synchronize.Event"
    ) -> None:
        lock = lock_factory() # Referenced until the end of this function: a deleted lock is released.
        lock_mode.acquire(lock)
        startup_event.set()
        signal.pause()

ChildLockerFactory = Callable[[LockMode], ChildLocker]

@pytest.fixture
def child_locker_factory(lock_backend: LockBackend) -> Iterator[ChildLockerFactory]:
    with scoped_factory(partial(ChildLocker, lock_backend.create_read_write_lock), ChildLocker.kill) as factory:
        yield factory
