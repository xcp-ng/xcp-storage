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

from pathlib import Path

import pytest

from tests.service import ServiceManager
from tests.utils.lock.fifo_lock_service import (
    FIFO_LOCK_SERVICE_START_TIMEOUT,
    FIFO_LOCK_UNIT_PATH,
    patched_fifo_locks_dir,
)
from tests.utils.lock.lock_variant import DEFAULT_LOCK_ACQUIRE_TIMEOUT
from xcp_storage.config.platform import RUNTIME_DIR_PATH
from xcp_storage.utils.lock.fifo import (
    _LOCKS_DIR_PATH,
    ReadWriteFifoLock,
)
from xcp_storage.utils.service import is_service_active, stop_service

from xcp_storage.typing import Final, Iterator

# ==============================================================================

LOCK_NAME: Final = "test-fifo-lock-using-unit"

# ------------------------------------------------------------------------------

@pytest.fixture
def registered_fifo_lock_service(service_manager: ServiceManager, fifo_lock_daemon_exec_path: Path) -> Iterator[str]:
    locks_dir_path = service_manager.runtime_dir_path / _LOCKS_DIR_PATH.relative_to(RUNTIME_DIR_PATH)
    with service_manager.registered_service(FIFO_LOCK_UNIT_PATH, executable_paths=[fifo_lock_daemon_exec_path]), \
            patched_fifo_locks_dir(locks_dir_path):
        service_name = ReadWriteFifoLock.get_service_name(LOCK_NAME)
        try:
            yield service_name
        finally:
            stop_service(service_name)

# ------------------------------------------------------------------------------

class TestFifoLockService:
    def test_service_is_started_on_demand(self, registered_fifo_lock_service: str) -> None:
        assert not is_service_active(registered_fifo_lock_service)

        lock = ReadWriteFifoLock(LOCK_NAME)
        lock.acquire(timeout=FIFO_LOCK_SERVICE_START_TIMEOUT)
        assert is_service_active(registered_fifo_lock_service)
        assert lock.path.exists()
        lock.release()

        # The lock is still usable: the service keeps running, and nothing is started again.
        lock.shared_acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        lock.shared_release()
