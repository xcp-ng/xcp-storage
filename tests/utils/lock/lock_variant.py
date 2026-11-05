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

from enum import Enum
from pathlib import Path, PurePath

import pytest

from tests.utils.exception import ExceptionT, raises_exactly
from tests.utils.lock.fifo_lock_service import FifoLockDaemon, FifoLockServices
from xcp_storage.utils.contextlib import scoped_factory
from xcp_storage.utils.lock import (
    DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
    DEFAULT_LOCK_DURATION_THRESHOLD,
    HandleLock,
    Lock,
    ReadWriteHandleLock,
    ReadWriteLock,
)
from xcp_storage.utils.lock.fifo import _MIN_ACQUIRE_TIMEOUT, FifoLock, ReadWriteFifoLock
from xcp_storage.utils.lock.file import _FLOCK_POLL_INTERVAL, FileLock, ReadWriteFileLock

from xcp_storage.typing import (
    Callable,
    cast,
    ContextManager,
    Final,
    Iterator,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

HandleLockT = TypeVar("HandleLockT", bound=HandleLock)

# ==============================================================================

# Default timeout of `LockMode.acquire`, and of any acquisition that must succeed (in seconds).
DEFAULT_LOCK_ACQUIRE_TIMEOUT: Final = 0.5

# Resource of `fifo_lock_backend`: the name of the lock created by the factories when a test gives none, shared by
# all the locks of a test. Its daemon is started before the test.
DEFAULT_FIFO_BACKEND_LOCK_NAME: Final = "test-fifo-lock"

# ------------------------------------------------------------------------------

# Bounds of the duration in seconds of a single attempt failing on a held lock.
_FILE_LOCK_SINGLE_ATTEMPT_MIN_DURATION: Final = 0.0
_FILE_LOCK_SINGLE_ATTEMPT_MAX_DURATION: Final = 0.05

_FIFO_LOCK_SINGLE_ATTEMPT_MIN_DURATION: Final = _MIN_ACQUIRE_TIMEOUT
_FIFO_LOCK_SINGLE_ATTEMPT_MAX_DURATION: Final = _MIN_ACQUIRE_TIMEOUT + 0.1

# Shortest timeout of an acquisition that waits in seconds.
_FILE_LOCK_MIN_ACQUIRE_TIMEOUT: Final = _FLOCK_POLL_INTERVAL
_FIFO_LOCK_MIN_ACQUIRE_TIMEOUT: Final = _MIN_ACQUIRE_TIMEOUT

# ------------------------------------------------------------------------------
# Backends.
# ------------------------------------------------------------------------------

# Lock path (`FileLock`) or lock name (`FifoLock`).
LockResource = Union[str, PurePath]

class LockBackend(NamedTuple):
    """
    A lock kind, and the resource shared by the locks of a test.
    """

    lock_class: Type[HandleLock]
    read_write_lock_class: Type[ReadWriteHandleLock]
    resource: LockResource

    # Bounds of the duration in seconds of a single lock attempt (`try_acquire`, or `acquire` with `timeout <= 0`).
    # Min duration is 0 if the backend responds immediately, or a higher value if it requires time to respond
    # (FIFO daemon for example).
    single_attempt_min_duration: float
    single_attempt_max_duration: float

    # Shortest timeout of an acquisition that waits (in seconds): the fastest way to make an acquisition fail
    # on a held lock without a single attempt.
    min_acquire_timeout: float

    @property
    def context(self) -> str:
        """
        Context of the lock messages.
        """

        return str(self.resource)

    def create_lock(
        self,
        resource: Optional[LockResource] = None,
        *,
        acquire_duration_threshold: Optional[float] = DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
        lock_duration_threshold: Optional[float] = DEFAULT_LOCK_DURATION_THRESHOLD
    ) -> HandleLock:
        return self._create(self.lock_class, resource, acquire_duration_threshold, lock_duration_threshold)

    def create_read_write_lock(
        self,
        resource: Optional[LockResource] = None,
        *,
        acquire_duration_threshold: Optional[float] = DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
        lock_duration_threshold: Optional[float] = DEFAULT_LOCK_DURATION_THRESHOLD
    ) -> ReadWriteHandleLock:
        return self._create(self.read_write_lock_class, resource, acquire_duration_threshold, lock_duration_threshold)

    def raises(
        self, exception_class: Type[ExceptionT], message_format: str, **values: object
    ) -> ContextManager[pytest.ExceptionInfo[ExceptionT]]:
        return raises_exactly(exception_class, message_format.format(context=self.context, **values))

    def _create(
        self,
        lock_class: Type[HandleLockT],
        resource: Optional[LockResource],
        acquire_duration_threshold: Optional[float],
        lock_duration_threshold: Optional[float]
    ) -> HandleLockT:
        lock_constructor: Callable[..., HandleLockT] = lock_class
        return lock_constructor(
            resource or self.resource,
            acquire_duration_threshold=acquire_duration_threshold,
            lock_duration_threshold=lock_duration_threshold
        )

# ------------------------------------------------------------------------------

@pytest.fixture(params=["file", "fifo"])
def lock_backend(request: pytest.FixtureRequest) -> LockBackend:
    # Resolved lazily: the FIFO backend needs the daemon (and the build), the file one doesn't.
    return cast(LockBackend, request.getfixturevalue(f"{request.param}_lock_backend"))

# ------------------------------------------------------------------------------

@pytest.fixture
def file_lock_backend(tmp_path: Path) -> LockBackend:
    return LockBackend(
        FileLock,
        ReadWriteFileLock,
        tmp_path / "test.lock",
        _FILE_LOCK_SINGLE_ATTEMPT_MIN_DURATION,
        _FILE_LOCK_SINGLE_ATTEMPT_MAX_DURATION,
        _FILE_LOCK_MIN_ACQUIRE_TIMEOUT
    )

# ------------------------------------------------------------------------------

@pytest.fixture
def fifo_lock_daemon(fifo_lock_services: FifoLockServices) -> FifoLockDaemon:
    """
    Daemon serving the default lock of the FIFO backend.
    """

    return fifo_lock_services.get_daemon(DEFAULT_FIFO_BACKEND_LOCK_NAME)

@pytest.fixture
def fifo_lock_backend(fifo_lock_daemon: FifoLockDaemon) -> LockBackend: # noqa: ARG001
    # Requests `fifo_lock_daemon`: the daemon of the lock is started before the tests.
    return LockBackend(
        FifoLock,
        ReadWriteFifoLock,
        DEFAULT_FIFO_BACKEND_LOCK_NAME,
        _FIFO_LOCK_SINGLE_ATTEMPT_MIN_DURATION,
        _FIFO_LOCK_SINGLE_ATTEMPT_MAX_DURATION,
        _FIFO_LOCK_MIN_ACQUIRE_TIMEOUT
    )

# ------------------------------------------------------------------------------

LockFactory = Callable[..., HandleLock]
ReadWriteLockFactory = Callable[..., ReadWriteHandleLock]

# ------------------------------------------------------------------------------
# Lock modes.
# ------------------------------------------------------------------------------

class LockMode(Enum):
    """
    Define how a holder acquires a lock.
    """

    EXCLUSIVE = "exclusive"
    SHARED = "shared"

    @property
    def is_shared(self) -> bool:
        return self is LockMode.SHARED

    def acquire(self, lock: Lock, *, timeout: Optional[float] = DEFAULT_LOCK_ACQUIRE_TIMEOUT) -> None:
        if self.is_shared:
            self._as_read_write_lock(lock).shared_acquire(timeout=timeout)
        else:
            lock.acquire(timeout=timeout)

    def try_acquire(self, lock: Lock) -> bool:
        if self.is_shared:
            return self._as_read_write_lock(lock).shared_try_acquire()
        return lock.try_acquire()

    def release(self, lock: Lock) -> None:
        if self.is_shared:
            self._as_read_write_lock(lock).shared_release()
        else:
            lock.release()

    def hold(self, lock: Lock) -> ContextManager[object]:
        """
        The context manager of `lock` in this mode: `lock` itself, or `lock.shared()`.
        """

        if self.is_shared:
            return self._as_read_write_lock(lock).shared()
        return lock

    @staticmethod
    def _as_read_write_lock(lock: Lock) -> ReadWriteLock:
        assert isinstance(lock, ReadWriteLock), "Only a `ReadWriteLock` can be shared."
        return lock

# Run a test in each mode.
over_lock_modes = pytest.mark.parametrize(
    "lock_mode", list(LockMode), ids=[lock_mode.value for lock_mode in LockMode]
)

# ------------------------------------------------------------------------------
# Lock classes.
# ------------------------------------------------------------------------------

class LockClass(Enum):
    """
    Indicate which of a backend's two locking classes is used by a test:
    - `LockBackend.lock_class`
    - `LockBackend.read_write_lock_class`
    """

    LOCK = "lock"
    READ_WRITE_LOCK = "read-write-lock"

    def select_factory(self, lock_factory: LockFactory, read_write_lock_factory: ReadWriteLockFactory) -> LockFactory:
        return read_write_lock_factory if self is LockClass.READ_WRITE_LOCK else lock_factory

# ------------------------------------------------------------------------------
# Lock variants.
# ------------------------------------------------------------------------------

class LockVariant(NamedTuple):
    """
    Define how a test utilizes a backend's locks:
    - `factory` creates them using one of the available classes (see `LockClass`),
    - while `mode` handles their acquisition and release (in either exclusive or shared mode).
    """

    factory: LockFactory
    mode: LockMode

_LOCK_VARIANTS: Final = [
    (LockClass.LOCK,            LockMode.EXCLUSIVE),
    (LockClass.READ_WRITE_LOCK, LockMode.EXCLUSIVE),
    (LockClass.READ_WRITE_LOCK, LockMode.SHARED),
]

def _get_lock_variant_id(lock_variant: Tuple[LockClass, LockMode]) -> str:
    lock_class, lock_mode = lock_variant
    return f"{lock_class.value}-{lock_mode.value}" if lock_mode.is_shared else lock_class.value

# ------------------------------------------------------------------------------
# Factory and variants fixtures.
# ------------------------------------------------------------------------------

def _close_lock_handle(lock: HandleLock) -> None:
    if lock._is_acquired(): # noqa: SLF001
        lock._close_handle() # noqa: SLF001

@pytest.fixture
def lock_factory(lock_backend: LockBackend) -> Iterator[LockFactory]:
    with scoped_factory(lock_backend.create_lock, _close_lock_handle) as factory:
        yield factory

@pytest.fixture
def read_write_lock_factory(lock_backend: LockBackend) -> Iterator[ReadWriteLockFactory]:
    with scoped_factory(lock_backend.create_read_write_lock, _close_lock_handle) as factory:
        yield factory

# ------------------------------------------------------------------------------

@pytest.fixture(params=list(LockClass), ids=[lock_class.value for lock_class in LockClass])
def exclusive_lock_factory(
    request: pytest.FixtureRequest, lock_factory: LockFactory, read_write_lock_factory: ReadWriteLockFactory
) -> LockFactory:
    """
    Used to test the exclusive interface on both classes of a backend: `HandleLock` / `ReadWriteHandleLock`.
    """

    lock_class: LockClass = request.param
    return lock_class.select_factory(lock_factory, read_write_lock_factory)

# ------------------------------------------------------------------------------

@pytest.fixture(params=_LOCK_VARIANTS, ids=_get_lock_variant_id)
def lock_variant(
    request: pytest.FixtureRequest, lock_factory: LockFactory, read_write_lock_factory: ReadWriteLockFactory
) -> LockVariant:
    """
    Tests valid in any mode run on both classes of a backend.
    """

    lock_class, lock_mode = request.param
    return LockVariant(lock_class.select_factory(lock_factory, read_write_lock_factory), lock_mode)
