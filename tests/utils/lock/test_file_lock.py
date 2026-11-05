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

import errno
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.utils.exception import raises_exactly
from tests.utils.fd import count_open_fds
from tests.utils.lock.lock_variant import (
    LockBackend,
    LockMode,
    over_lock_modes,
    ReadWriteLockFactory,
)
from xcp_storage.utils.lock import LockError
from xcp_storage.utils.lock.file import FileLock

from xcp_storage.typing import Optional

# ==============================================================================

# Redefine `lock_backend` to only use file lock backend in this file.
@pytest.fixture
def lock_backend(file_lock_backend: LockBackend) -> LockBackend:
    return file_lock_backend

@pytest.fixture
def lock_path(lock_backend: LockBackend) -> Path:
    return Path(lock_backend.resource)

# ------------------------------------------------------------------------------

class TestFileLockPath:
    def test_path(self, lock_path: Path) -> None:
        assert FileLock(lock_path).path == lock_path

    def test_str_path(self, lock_path: Path) -> None:
        assert FileLock(str(lock_path)).path == lock_path

    def test_empty_path(self) -> None:
        with raises_exactly(ValueError, "Invalid lock path: ``."):
            FileLock("")

# ------------------------------------------------------------------------------

@over_lock_modes
class TestFileLock:
    def test_lock_file_is_kept(
        self,
        lock_path: Path,
        read_write_lock_factory: ReadWriteLockFactory,
        lock_mode: LockMode
    ) -> None:
        lock = read_write_lock_factory()

        lock_mode.acquire(lock)

        assert lock_path.exists()
        assert count_open_fds(lock_path) == 1

        lock_mode.release(lock)

        assert lock_path.exists()
        assert count_open_fds(lock_path) == 0

    def test_acquire_on_read_only_file(
        self,
        lock_path: Path,
        read_write_lock_factory: ReadWriteLockFactory,
        lock_mode: LockMode
    ) -> None:
        lock_path.touch(mode=0o400)
        assert lock_mode.try_acquire(read_write_lock_factory())

    def test_acquire_on_invalid_path(
        self,
        tmp_path: Path,
        read_write_lock_factory: ReadWriteLockFactory,
        lock_mode: LockMode
    ) -> None:
        invalid_lock_path = tmp_path / "missing_dir" / "test.lock"
        lock = read_write_lock_factory(invalid_lock_path)
        for timeout in (None, 0):
            with raises_exactly(LockError, f"Unable to open lock file `{invalid_lock_path}`.") as exc_info:
                lock_mode.acquire(lock, timeout=timeout)
            assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    @pytest.mark.parametrize("timeout", [None, 0, 0.1])
    def test_flock_error(
        self,
        lock_backend: LockBackend,
        read_write_lock_factory: ReadWriteLockFactory,
        lock_mode: LockMode,
        timeout: Optional[float]
    ) -> None:
        lock = read_write_lock_factory()
        with patch(
            "fcntl.flock", side_effect=OSError(errno.EIO, ""), autospec=True
        ), lock_backend.raises(LockError, "Unable to lock on `{context}`."):
            lock_mode.acquire(lock, timeout=timeout)

        assert lock_mode.try_acquire(lock)
