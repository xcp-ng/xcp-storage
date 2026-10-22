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
import fcntl
import os
from pathlib import PurePath

from xcp_storage.utils.file import close_fd
from xcp_storage.utils.lock import (
    DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
    DEFAULT_LOCK_DURATION_THRESHOLD,
    HandleLock,
    LockError,
    ReadWriteHandleLock,
)
from xcp_storage.utils.sync import wait_for_condition

from xcp_storage.typing import (
    Final,
    Optional,
    override,
    Union,
)

# ==============================================================================

_FLOCK_POLL_INTERVAL: Final = 0.05

# ------------------------------------------------------------------------------

class FileLock(HandleLock):
    """
    Exclusive lock between processes on one machine, based on a lock file.

    Design notes:
    - The kernel releases the lock when the process dies: there is no stale lock to clean up.
    - The lock file is never deleted: and that's correct! This avoids creating a lock that
      would use a new inode, which could have bad consequences...
    - The parent directory must exist. A local file system is required (`flock` is not reliable
      on every network file system).
    """

    def __init__(
        self,
        path: Union[str, PurePath],
        *,
        acquire_duration_threshold: Optional[float] = DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
        lock_duration_threshold: Optional[float] = DEFAULT_LOCK_DURATION_THRESHOLD
    ) -> None:
        # Set first: `__del__` must work even if the validation fails.
        self._fd: Optional[int] = None

        lock_path = str(path)
        if not lock_path:
            raise ValueError(f"Invalid lock path `{lock_path}`.")

        super().__init__(
            lock_path,
            acquire_duration_threshold=acquire_duration_threshold,
            lock_duration_threshold=lock_duration_threshold
        )
        self._path = lock_path

    def __del__(self) -> None:
        if self._fd is not None:
            close_fd(self._fd)

    @property
    def path(self) -> str:
        return self._path

    @override
    def _is_acquired(self) -> bool:
        return self._fd is not None

    @override
    def _try_acquire(self, *, shared: bool, timeout: Optional[float]) -> bool:
        self._check_not_locked()

        # 1. Open lock path.
        self._tracer.start_acquire()
        try:
            fd = os.open(self._path, os.O_RDONLY | os.O_CREAT | os.O_CLOEXEC, 0o600)
        except OSError as e:
            raise LockError(f"Unable to open lock file `{self._path}`.") from e

        # 2. Try effective lock.
        acquired = False
        lock_flags = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        try:
            if timeout is None:
                acquired = self._flock(fd, lock_flags)
            else:
                lock_flags |= fcntl.LOCK_NB
                acquired = bool(wait_for_condition(lambda: self._flock(fd, lock_flags), timeout, _FLOCK_POLL_INTERVAL))
        finally:
            if not acquired:
                close_fd(fd)

        # 3. Update lock and log delay if necessary.
        if acquired:
            self._fd = fd
            self._notify_acquired(shared=shared)
        return acquired

    @override
    def _close_handle(self) -> None:
        fd = self._fd
        assert fd is not None
        self._fd = None

        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        close_fd(fd)

    def _flock(self, fd: int, flags: int) -> bool:
        try:
            fcntl.flock(fd, flags)
            return True
        except BlockingIOError:
            return False
        except OSError as e:
            raise LockError(f"Unable to lock on `{self._path}`.") from e

# ------------------------------------------------------------------------------

class ReadWriteFileLock(FileLock, ReadWriteHandleLock):
    pass
