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
import gc
import logging
import multiprocessing
import multiprocessing.synchronize
from pathlib import Path
import re
import signal
import threading
import time
from unittest.mock import patch

import pytest

from tests.utils.fd import count_open_fds
from xcp_storage.utils.lock import (
    LockError,
    LockTimeoutError,
)
from xcp_storage.utils.lock.file import FileLock, ReadWriteFileLock

from xcp_storage.typing import (
    Callable,
    cast,
    Final,
    Iterator,
    List,
    Optional,
    Type,
)

# ==============================================================================

@pytest.fixture
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "test.lock"

# ------------------------------------------------------------------------------

# `TestFileLock` only uses the base `Lock` interface (`acquire`, `try_acquire`, `release`, `with`) and
# runs it on both classes: the exclusive side of a `ReadWriteFileLock` must behave like a `FileLock`.
LockFactory = Type[FileLock]

@pytest.fixture(params=[FileLock, ReadWriteFileLock])
def lock_factory(request: pytest.FixtureRequest) -> LockFactory:
    return cast(LockFactory, request.param)

# ------------------------------------------------------------------------------

class TestFileLock:
    def test_context_manager(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)
        with lock:
            assert not lock_factory(lock_path).try_acquire()
        assert lock_factory(lock_path).try_acquire()

    def test_context_manager_with_exception(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)
        exception_reason = "Décapitation!"
        with pytest.raises(RuntimeError, match=exception_reason), lock:
            raise RuntimeError(exception_reason)
        assert lock_factory(lock_path).try_acquire()

    def test_acquire_success_on_read_only_file(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock_path.touch(mode=0o400)
        assert lock_factory(lock_path).try_acquire()

    def test_acquire_and_release(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)

        lock.acquire()
        assert lock_path.exists()
        assert not lock_factory(lock_path).try_acquire()

        lock.release()

        assert lock_path.exists()
        assert lock_factory(lock_path).try_acquire()

    def test_acquire_and_release_with_two_locks(self, lock_path: Path, lock_factory: LockFactory) -> None:
        first_lock = lock_factory(lock_path)
        second_lock = lock_factory(lock_path)

        first_lock.acquire()
        assert not second_lock.try_acquire()

        first_lock.release()
        assert second_lock.try_acquire()

    def test_cannot_acquire_when_locked(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)
        lock.acquire()

        exception_message = f"Lock on `{lock_path}` is already exclusive locked by this instance."

        with pytest.raises(LockError, match=exception_message):
            lock.acquire()
        with pytest.raises(LockError, match=exception_message):
            lock.try_acquire()

        assert not lock_factory(lock_path).try_acquire()
        lock.release()

        assert lock_factory(lock_path).try_acquire()

    def test_acquire_timeout(self, lock_path: Path, lock_factory: LockFactory) -> None:
        first_lock = lock_factory(lock_path)
        second_lock = lock_factory(lock_path)

        timeout = 0.2
        exception_message = f"Timeout while acquiring exclusive lock on `{lock_path}`."

        with first_lock:
            start_time = time.monotonic()
            with pytest.raises(LockTimeoutError, match=exception_message):
                second_lock.acquire(timeout=timeout)
            assert time.monotonic() - start_time >= timeout

            start_time = time.monotonic()
            with pytest.raises(LockTimeoutError, match=exception_message):
                second_lock.acquire(timeout=0)
            assert time.monotonic() - start_time < 0.05

            assert not second_lock.try_acquire()

        assert second_lock.try_acquire()

    def test_acquire_on_invalid_path(self, tmp_path: Path, lock_factory: LockFactory) -> None:
        path = tmp_path / "missing_dir" / "test.lock"
        lock = lock_factory(path)

        exception_message = f"Unable to open lock file `{path}`."

        with pytest.raises(LockError, match=exception_message) as exc_info:
            lock.acquire()
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

        with pytest.raises(LockError, match=exception_message) as exc_info:
            lock.try_acquire()
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_cannot_release_unlocked(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)

        exception_message = f"Lock on `{lock_path}` is not locked."

        with pytest.raises(LockError, match=exception_message):
            lock.release()

        lock.acquire()
        lock.release()

        with pytest.raises(LockError, match=exception_message):
            lock.release()

    def test_no_descriptor_leaks_during_acquire(self, lock_path: Path, lock_factory: LockFactory) -> None:
        with lock_factory(lock_path):
            second_lock = lock_factory(lock_path)
            assert count_open_fds(lock_path) == 1
            for _ in range(10):
                assert not second_lock.try_acquire()
                with pytest.raises(LockTimeoutError):
                    second_lock.acquire(timeout=0.05)
            assert count_open_fds(lock_path) == 1

    def test_lock_is_released_when_object_is_deleted(self, lock_path: Path, lock_factory: LockFactory) -> None:
        lock = lock_factory(lock_path)
        lock.acquire()
        assert count_open_fds(lock_path) == 1

        del lock
        gc.collect()

        assert count_open_fds(lock_path) == 0
        assert lock_factory(lock_path).try_acquire()

    @pytest.mark.parametrize("timeout", [None, 0, 0.1])
    def test_flock_error(self, lock_path: Path, lock_factory: LockFactory, timeout: Optional[float]) -> None:
        lock = lock_factory(lock_path)
        exception_message = f"Unable to lock on `{lock_path}`."
        with patch("fcntl.flock", side_effect=OSError(errno.EIO, "")), \
                pytest.raises(LockError, match=exception_message):
            lock.acquire(timeout=timeout)

        assert count_open_fds(lock_path) == 0
        assert lock.try_acquire()
        assert count_open_fds(lock_path) == 1

# ------------------------------------------------------------------------------

class TestReadWriteFileLock:
    def test_shared_context_manager(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        with lock.shared():
            assert ReadWriteFileLock(lock_path).shared_try_acquire()
            assert not ReadWriteFileLock(lock_path).try_acquire()
        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_shared_context_manager_with_exception(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        exception_reason = "Décapitation partagée!"
        with pytest.raises(RuntimeError, match=exception_reason), lock.shared():
            raise RuntimeError(exception_reason)
        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_shared_context_manager_timeout(self, lock_path: Path) -> None:
        exception_message = f"Timeout while acquiring shared lock on `{lock_path}`."
        with ReadWriteFileLock(lock_path):
            second_lock = ReadWriteFileLock(lock_path)
            with pytest.raises(LockTimeoutError, match=exception_message), second_lock.shared(timeout=0.1):
                pytest.fail("The lock must not be acquired.")

    def test_shared_acquire_success_on_read_only_file(self, lock_path: Path) -> None:
        lock_path.touch(mode=0o400)
        assert ReadWriteFileLock(lock_path).shared_try_acquire()

    def test_shared_acquire_and_release(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)

        lock.shared_acquire()
        assert lock_path.exists()
        assert not ReadWriteFileLock(lock_path).try_acquire()

        lock.shared_release()

        assert lock_path.exists()
        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_shared_acquire_and_release_with_two_locks(self, lock_path: Path) -> None:
        writer = ReadWriteFileLock(lock_path)
        reader = ReadWriteFileLock(lock_path)

        writer.acquire()
        assert not reader.shared_try_acquire()

        writer.release()
        assert reader.shared_try_acquire()

    def test_cannot_acquire_when_locked(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        lock.acquire()

        exception_message = f"Lock on `{lock_path}` is already exclusive locked by this instance."

        # Note: `acquire`/`release` already handled by `TestFileLock`.
        with pytest.raises(LockError, match=exception_message):
            lock.shared_acquire()
        with pytest.raises(LockError, match=exception_message):
            lock.shared_try_acquire()

        assert not ReadWriteFileLock(lock_path).shared_try_acquire()
        lock.release()

        assert ReadWriteFileLock(lock_path).shared_try_acquire()

    def test_cannot_acquire_when_shared_locked(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        lock.shared_acquire()

        exception_message = f"Lock on `{lock_path}` is already shared locked by this instance."

        # Note: we must test all cases because we are shared locked.
        # It's not checked by `TestFileLock`.
        with pytest.raises(LockError, match=exception_message):
            lock.shared_acquire()
        with pytest.raises(LockError, match=exception_message):
            lock.shared_try_acquire()
        with pytest.raises(LockError, match=exception_message):
            lock.acquire()
        with pytest.raises(LockError, match=exception_message):
            lock.try_acquire()

        assert not ReadWriteFileLock(lock_path).try_acquire()
        lock.shared_release()

        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_shared_acquire_timeout(self, lock_path: Path) -> None:
        first_lock = ReadWriteFileLock(lock_path)
        second_lock = ReadWriteFileLock(lock_path)

        timeout = 0.2
        exception_message = f"Timeout while acquiring shared lock on `{lock_path}`."

        with first_lock:
            start_time = time.monotonic()
            with pytest.raises(LockTimeoutError, match=exception_message):
                second_lock.shared_acquire(timeout=timeout)
            assert time.monotonic() - start_time >= timeout

            start_time = time.monotonic()
            with pytest.raises(LockTimeoutError, match=exception_message):
                second_lock.shared_acquire(timeout=0)
            assert time.monotonic() - start_time < 0.05

            assert not second_lock.shared_try_acquire()

        assert second_lock.shared_try_acquire()

    def test_multiple_shared_acquire(self, lock_path: Path) -> None:
        locks = [ReadWriteFileLock(lock_path) for _ in range(5)]
        for lock in locks:
            assert lock.shared_try_acquire()

        for lock in locks:
            assert not ReadWriteFileLock(lock_path).try_acquire()
            lock.shared_release()
        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_cannot_shared_release_unlocked(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)

        exception_message = f"Lock on `{lock_path}` is not locked."

        with pytest.raises(LockError, match=exception_message):
            lock.shared_release()

        lock.shared_acquire()
        lock.shared_release()

        with pytest.raises(LockError, match=exception_message):
            lock.shared_release()

    def test_cannot_release_shared_with_release(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        lock.shared_acquire()

        exception_message = (
            f"Lock on `{lock_path}` is shared locked. Incorrect method usage, "
            "`shared_release` must be called instead of `release`."
        )

        with pytest.raises(LockError, match=exception_message):
            lock.release()

        assert not ReadWriteFileLock(lock_path).try_acquire()
        lock.shared_release()
        assert ReadWriteFileLock(lock_path).try_acquire()

    def test_cannot_release_exclusive_with_shared_release(self, lock_path: Path) -> None:
        lock = ReadWriteFileLock(lock_path)
        lock.acquire()

        exception_message = (
            f"Lock on `{lock_path}` is exclusive locked. Incorrect method usage, "
            "`release` must be called instead of `shared_release`."
        )
        with pytest.raises(LockError, match=exception_message):
            lock.shared_release()

        assert not ReadWriteFileLock(lock_path).shared_try_acquire()
        lock.release()
        assert ReadWriteFileLock(lock_path).shared_try_acquire()

# ------------------------------------------------------------------------------

class TestFileLockDurationTraces:
    def test_slow_acquire_is_logged(
        self, lock_path: Path, lock_factory: LockFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        first_lock = lock_factory(lock_path)
        second_lock = lock_factory(lock_path, acquire_duration_threshold=0.1)

        timer = threading.Timer(0.2, first_lock.release)
        first_lock.acquire()

        timer.start()
        with caplog.at_level(logging.DEBUG):
            second_lock.acquire(timeout=5.0)
        timer.join()

        pattern = rf"^Lock on `{re.escape(str(lock_path))}` took \d+\.\d\d second\(s\) to acquire\.$"
        assert [r.levelname for r in caplog.records if re.match(pattern, r.getMessage())] == ["WARNING"]

    def test_long_lock_is_logged(
        self, lock_path: Path, lock_factory: LockFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        lock = lock_factory(lock_path, lock_duration_threshold=0.1)
        with caplog.at_level(logging.DEBUG), lock:
            time.sleep(0.2)

        pattern = rf"^Lock on `{re.escape(str(lock_path))}` locked for \d+\.\d\d second\(s\)\.$"
        assert [r.levelname for r in caplog.records if re.match(pattern, r.getMessage())] == ["WARNING"]

    def test_fast_lock_is_not_logged(
        self, lock_path: Path, lock_factory: LockFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG), lock_factory(lock_path):
            pass
        assert str(lock_path) not in caplog.text

    def test_traces_can_be_disabled(
        self, lock_path: Path, lock_factory: LockFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        lock = lock_factory(lock_path, acquire_duration_threshold=None, lock_duration_threshold=None)
        with caplog.at_level(logging.DEBUG), lock:
            time.sleep(0.05)
        assert str(lock_path) not in caplog.text

# ==============================================================================

class ChildLocker:
    """
    Forked child process acquiring a lock on `path` then holding it until it's killed
    to test locks between processes.
    """

    EXCLUSIVE: Final = 0
    SHARED: Final = 1

    def __init__(self, path: Path, mode: int) -> None:
        context = multiprocessing.get_context("fork")
        self._startup_event = context.Event()
        self._process = context.Process(
            target=self._acquire_lock,
            args=(path, mode, self._startup_event),
            daemon=True
        )
        self._process.start()

    @staticmethod
    def _acquire_lock(path: Path, mode: int, startup_event: "multiprocessing.synchronize.Event") -> None:
        lock = ReadWriteFileLock(path)
        if mode == ChildLocker.SHARED:
            lock.shared_acquire()
        else:
            lock.acquire()
        startup_event.set()
        signal.pause()

    def wait_for_startup(self, *, timeout: float = 2.0) -> bool:
        return self._startup_event.wait(timeout)

    def kill(self) -> None:
        self._process.kill()
        self._process.join()

ChildLockerFactory = Callable[[int], ChildLocker]

@pytest.fixture
def child_locker_factory(lock_path: Path) -> Iterator[ChildLockerFactory]:
    child_processes: List[ChildLocker] = []

    def start(mode: int) -> ChildLocker:
        child_processes.append(ChildLocker(lock_path, mode))
        return child_processes[-1]

    yield start

    for child_process in child_processes:
        child_process.kill()

# ------------------------------------------------------------------------------

class TestFileLockBetweenProcesses:
    def test_exclusive_acquire(self, lock_path: Path, child_locker_factory: ChildLockerFactory) -> None:
        assert child_locker_factory(ChildLocker.EXCLUSIVE).wait_for_startup()

        assert not ReadWriteFileLock(lock_path).shared_try_acquire()
        assert not ReadWriteFileLock(lock_path).try_acquire()

    def test_shared_acquire(self, lock_path: Path, child_locker_factory: ChildLockerFactory) -> None:
        assert child_locker_factory(ChildLocker.SHARED).wait_for_startup()

        assert ReadWriteFileLock(lock_path).shared_try_acquire()
        assert not ReadWriteFileLock(lock_path).try_acquire()

    def test_lock_is_released_when_process_is_killed(
        self, lock_path: Path, child_locker_factory: ChildLockerFactory
    ) -> None:
        child_process = child_locker_factory(ChildLocker.EXCLUSIVE)
        assert child_process.wait_for_startup()
        assert not ReadWriteFileLock(lock_path).shared_try_acquire()

        child_process.kill()

        FileLock(lock_path).acquire(timeout=5.0)

    def test_acquire_waits_for_release(
        self, lock_path: Path, lock_factory: LockFactory, child_locker_factory: ChildLockerFactory
    ) -> None:
        lock = lock_factory(lock_path)
        lock.acquire()

        child_process = child_locker_factory(ChildLocker.EXCLUSIVE)
        assert not child_process.wait_for_startup()

        lock.release()
        assert child_process.wait_for_startup(timeout=0.5)
