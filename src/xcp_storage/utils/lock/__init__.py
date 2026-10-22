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

from abc import abstractmethod
import contextlib
import time
from types import TracebackType

import xcp_storage.log as log

from xcp_storage.typing import (
    Final,
    Iterator,
    Optional,
    override,
    Type,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

# Durations (in seconds) above which a slow acquisition / a long hold is logged.
DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD: Final = 1.0
DEFAULT_LOCK_DURATION_THRESHOLD: Final = 5.0

# ------------------------------------------------------------------------------

class LockError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class LockTimeoutError(LockError):
    pass

# ------------------------------------------------------------------------------

class Lock(contextlib.AbstractContextManager):
    """
    Generic exclusive lock: a single holder at a time.
    """

    @override
    def __enter__(self) -> "Lock":
        self.acquire()
        return self

    @override
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        self.release()

    @abstractmethod
    def acquire(self, *, timeout: Optional[float] = None) -> None:
        """
        Acquire the lock.
        `timeout=None` waits forever, `timeout<=0` makes a single attempt.
        Raises `LockTimeoutError` if the lock cannot be acquired in time.
        """

    @abstractmethod
    def try_acquire(self) -> bool:
        """
        Single attempt: never blocks. Returns False if the lock is held by someone else.
        """

    @abstractmethod
    def release(self) -> None:
        """
        Release the lock.
        Raises `LockError` if this object does not hold it.
        """

# ------------------------------------------------------------------------------

class ReadWriteLock(Lock):
    """
    Generic readers-writer lock.
    Any number of concurrent shared readers OR a single exclusive writer.
    """

    @contextlib.contextmanager
    def shared(self, *, timeout: Optional[float] = None) -> Iterator[None]:
        """
        Context manager equivalent of `with lock:` for a reader.
        """
        self.shared_acquire(timeout=timeout)
        try:
            yield
        finally:
            self.shared_release()

    @abstractmethod
    def shared_acquire(self, *, timeout: Optional[float] = None) -> None:
        """
        Acquire for a reader.
        `timeout` behaves as in `acquire`.
        """

    @abstractmethod
    def shared_try_acquire(self) -> bool:
        """
        Single attempt for a reader: never blocks. Returns False if an exclusive writer exists.
        """

    @abstractmethod
    def shared_release(self) -> None:
        """
        Release for a reader.
        Raises `LockError` if this object does not hold it.
        """

# ------------------------------------------------------------------------------

class HandleLock(Lock):
    """
    Generic readers-writer handle lock.
    It contains common logic of the locks base on handle (file descriptor, connection...).
    """

    def __init__(
        self,
        context: str,
        *,
        acquire_duration_threshold: Optional[float],
        lock_duration_threshold: Optional[float]
    ) -> None:
        self._context = context
        self._shared_locked = False
        self._tracer = LockDurationTracer(
            context,
            acquire_duration_threshold=acquire_duration_threshold,
            lock_duration_threshold=lock_duration_threshold
        )

    @override
    def acquire(self, *, timeout: Optional[float] = None) -> None:
        self._acquire(shared=False, timeout=timeout)

    @override
    def try_acquire(self) -> bool:
        return self._try_acquire(shared=False, timeout=0)

    @override
    def release(self) -> None:
        self._release(shared=False)

    @abstractmethod
    def _is_acquired(self) -> bool:
        pass

    @abstractmethod
    def _try_acquire(self, *, shared: bool, timeout: Optional[float]) -> bool:
        pass

    @abstractmethod
    def _close_handle(self) -> None:
        pass

    def _acquire(self, *, shared: bool, timeout: Optional[float]) -> None:
        if not self._try_acquire(shared=shared, timeout=timeout):
            raise LockTimeoutError(
                f"Timeout while acquiring {self._get_lock_mode(shared=shared)} lock on `{self._context}`."
            )

    def _check_not_locked(self) -> None:
        if self._is_acquired():
            raise LockError(
                f"Lock on `{self._context}` is already {self._get_lock_mode(shared=self._shared_locked)} "
                "locked by this instance."
            )

    def _notify_acquired(self, *, shared: bool) -> None:
        self._shared_locked = shared
        self._tracer.notify_acquired()

    def _release(self, *, shared: bool) -> None:
        if not self._is_acquired():
            raise LockError(f"Lock on `{self._context}` is not locked.")

        if self._shared_locked != shared:
            method_names = ("release", "shared_release")
            raise LockError(
                f"Lock on `{self._context}` is {self._get_lock_mode(shared=self._shared_locked)} "
                f"locked. Incorrect method usage, `{method_names[self._shared_locked]}` must be called "
                f"instead of `{method_names[not self._shared_locked]}`."
            )

        self._tracer.notify_released()
        self._shared_locked = False
        self._close_handle()

    @staticmethod
    def _get_lock_mode(*, shared: bool) -> str:
        return "shared" if shared else "exclusive"

# ------------------------------------------------------------------------------

class ReadWriteHandleLock(HandleLock, ReadWriteLock):
    @override
    def shared_acquire(self, *, timeout: Optional[float] = None) -> None:
        self._acquire(shared=True, timeout=timeout)

    @override
    def shared_try_acquire(self) -> bool:
        return self._try_acquire(shared=True, timeout=0)

    @override
    def shared_release(self) -> None:
        self._release(shared=True)

# ------------------------------------------------------------------------------

class LockDurationTracer:
    """
    Log a warning when a lock takes too long to acquire, or is held for too long.
    A threshold set to `None` disables the corresponding trace.
    """

    def __init__(
        self,
        context: str,
        *,
        acquire_duration_threshold: Optional[float],
        lock_duration_threshold: Optional[float]
    ) -> None:
        self._context = context
        self._acquire_duration_threshold = acquire_duration_threshold
        self._lock_duration_threshold = lock_duration_threshold
        self._acquire_start_time = 0.0
        self._acquired_at = 0.0

    def start_acquire(self) -> None:
        self._acquire_start_time = time.monotonic()

    def notify_acquired(self) -> None:
        self._acquired_at = time.monotonic()
        if self._acquire_duration_threshold is None:
            return

        elapsed_time = self._acquired_at - self._acquire_start_time
        if elapsed_time > self._acquire_duration_threshold:
            logger.warning("Lock on `%s` took %.2f second(s) to acquire.", self._context, elapsed_time)

    def notify_released(self) -> None:
        if self._lock_duration_threshold is None:
            return

        elapsed_time = time.monotonic() - self._acquired_at
        if elapsed_time > self._lock_duration_threshold:
            logger.warning("Lock on `%s` locked for %.2f second(s).", self._context, elapsed_time)
