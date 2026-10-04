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
import time

from xcp_storage import log
from xcp_storage.utils.lock import (
    Lock,
    LockError,
    LockTimeoutError,
    ReadWriteLock,
)
from xcp_storage.utils.sync import wait_for_condition

from xcp_storage.typing import (
    Final,
    Optional,
    override,
    Union,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

# Durations (in seconds) above which a slow acquisition / a long hold is logged.
DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD: Final = 1.0
DEFAULT_LOCK_DURATION_THRESHOLD: Final = 5.0

# ------------------------------------------------------------------------------

_FLOCK_POLL_INTERVAL: Final = 0.05

# ------------------------------------------------------------------------------

class FileLock(Lock):
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
        self._path = str(path)
        self._acquire_duration_threshold = acquire_duration_threshold
        self._lock_duration_threshold = lock_duration_threshold
        self._fd: Optional[int] = None
        self._shared_locked = False
        self._acquired_timestamp = 0.0

    def __del__(self) -> None:
        if self._fd is not None:
            with contextlib.suppress(OSError):
                os.close(self._fd)

    @override
    def acquire(self, *, timeout: Optional[float] = None) -> None:
        self._acquire(shared=False, timeout=timeout)

    @override
    def try_acquire(self) -> bool:
        return self._try_acquire(shared=False, timeout=0)

    @override
    def release(self) -> None:
        self._release(shared=False)

    @property
    def path(self) -> str:
        return self._path

    def _acquire(self, *, shared: bool, timeout: Optional[float]) -> None:
        if not self._try_acquire(shared=shared, timeout=timeout):
            raise LockTimeoutError(
                f"Timeout while acquiring {self._get_lock_mode(shared=shared)} lock on `{self._path}`."
            )

    def _try_acquire(self, *, shared: bool, timeout: Optional[float]) -> bool:
        if self._fd is not None:
            raise LockError(
                f"Lock on `{self._path}` is already {self._get_lock_mode(shared=self._shared_locked)} "
                "locked by this instance."
            )

        # 1. Open lock path.
        lock_start_timestamp = time.monotonic()
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
                os.close(fd)

        # 3. Update lock and log delay if necessary.
        if acquired:
            self._fd = fd
            self._shared_locked = shared
            self._acquired_timestamp = time.monotonic()

            if self._acquire_duration_threshold is not None:
                elasped_time = self._acquired_timestamp - lock_start_timestamp
                if elasped_time > self._acquire_duration_threshold:
                    logger.warning("Lock on `%s` took %.2f second(s) to acquire.", self._path, elasped_time)
        return acquired

    def _release(self, *, shared: bool) -> None:
        if self._fd is None:
            raise LockError(f"Lock on `{self._path}` is not locked.")

        if self._shared_locked != shared:
            method_names = ("release", "shared_release")
            raise LockError(
                f"Lock on `{self._path}` is {self._get_lock_mode(shared=self._shared_locked)} "
                f"locked. Incorrect method usage, `{method_names[self._shared_locked]}` must be called "
                f"instead of `{method_names[not self._shared_locked]}`."
            )

        if self._lock_duration_threshold is not None:
            elasped_time = time.monotonic() - self._acquired_timestamp
            if elasped_time > self._lock_duration_threshold:
                logger.warning("Lock on `%s` locked for %.2f second(s).", self._path, elasped_time)

        fd = self._fd
        self._fd = None
        self._shared_locked = False

        try:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _flock(self, fd: int, flags: int) -> bool:
        try:
            fcntl.flock(fd, flags)
            return True
        except BlockingIOError:
            return False
        except OSError as e:
            raise LockError(f"Unable to lock on `{self._path}`.") from e

    @staticmethod
    def _get_lock_mode(*, shared: bool) -> str:
        return "shared" if shared else "exclusive"

# ------------------------------------------------------------------------------

class ReadWriteFileLock(FileLock, ReadWriteLock):
    @override
    def shared_acquire(self, *, timeout: Optional[float] = None) -> None:
        self._acquire(shared=True, timeout=timeout)

    @override
    def shared_try_acquire(self) -> bool:
        return self._try_acquire(shared=True, timeout=0)

    @override
    def shared_release(self) -> None:
        self._release(shared=True)
