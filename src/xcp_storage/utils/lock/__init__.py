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
from types import TracebackType

from xcp_storage.typing import (
    Iterator,
    Optional,
    override,
    Type,
)

# ==============================================================================

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
