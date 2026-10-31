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

import gc
import multiprocessing
import random
import re
import signal
import threading
import time

import pytest

from tests.utils.exception import raises_exactly
from tests.utils.fd import assert_no_fd_leak
from tests.utils.lock.child_locker import ChildLockerFactory
from tests.utils.lock.lock_variant import (
    DEFAULT_LOCK_ACQUIRE_TIMEOUT,
    LockBackend,
    LockFactory,
    LockMode,
    LockVariant,
    over_lock_modes,
    ReadWriteLockFactory,
)
from tests.utils.thread import create_thread_group
import xcp_storage.log as log
from xcp_storage.utils.lock import (
    DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
    DEFAULT_LOCK_DURATION_THRESHOLD,
    LockError,
    LockTimeoutError,
    ReadWriteLock,
)
from xcp_storage.utils.process import kill_process
from xcp_storage.utils.time import Clock

from xcp_storage.typing import (
    Callable,
    Final,
    List,
    Optional,
)

# ==============================================================================

# Messages of the lock errors.
LOCK_MESSAGE_ALREADY_LOCKED: Final = "Lock on `{context}` is already {mode} locked by this instance."
LOCK_MESSAGE_NOT_LOCKED: Final = "Lock on `{context}` is not locked."
LOCK_MESSAGE_TIMEOUT: Final = "Timeout while acquiring {mode} lock on `{context}`."
LOCK_MESSAGE_WRONG_RELEASE_METHOD: Final = (
    "Lock on `{context}` is {mode} locked. Incorrect method usage, `{expected}` must be called instead of `{wrong}`."
)

# ------------------------------------------------------------------------------

LOCK_RELEASE_METHOD_NAMES: Final = {LockMode.EXCLUSIVE: "release", LockMode.SHARED: "shared_release"}

# ------------------------------------------------------------------------------

# Maximum time an acquisition may last beyond its timeout (in seconds).
LOCK_ACQUIRE_TIMEOUT_TOLERANCE: Final = 0.3

# How long a holder keeps the lock before releasing it, while another one waits for it (in seconds).
LOCK_DEFER_RELEASE_DELAY: Final = 0.2

# ------------------------------------------------------------------------------

class TestLock:
    def test_class_hierarchy(self, lock_backend: LockBackend) -> None:
        assert not issubclass(lock_backend.lock_class, ReadWriteLock)
        assert not hasattr(lock_backend.lock_class, "shared_acquire")
        assert issubclass(lock_backend.read_write_lock_class, lock_backend.lock_class)

    def test_acquire_and_release(self, exclusive_lock_factory: LockFactory) -> None:
        lock = exclusive_lock_factory()
        other_lock = exclusive_lock_factory()

        lock.acquire()
        assert not other_lock.try_acquire()
        lock.release()

        assert other_lock.try_acquire()
        assert not lock.try_acquire()

    def test_context_manager(self, exclusive_lock_factory: LockFactory) -> None:
        other_lock = exclusive_lock_factory()

        with exclusive_lock_factory():
            assert not other_lock.try_acquire()
        assert other_lock.try_acquire()

    def test_context_manager_with_exception(self, lock_variant: LockVariant) -> None:
        exception_reason = "Décapitation!"
        with raises_exactly(RuntimeError, exception_reason), lock_variant.mode.hold(lock_variant.factory()):
            raise RuntimeError(exception_reason)
        assert lock_variant.factory().try_acquire()

    def test_cannot_acquire_twice(self, lock_backend: LockBackend, lock_variant: LockVariant) -> None:
        lock_mode = lock_variant.mode
        lock = lock_variant.factory()

        lock_mode.acquire(lock)

        methods: List[Callable[[], object]] = [lock.acquire, lock.try_acquire]
        if isinstance(lock, ReadWriteLock):
            methods += [lock.shared_acquire, lock.shared_try_acquire]
        for method in methods:
            with lock_backend.raises(LockError, LOCK_MESSAGE_ALREADY_LOCKED, mode=lock_mode.value):
                method()

        other_lock = lock_variant.factory()
        assert not other_lock.try_acquire()

        lock_mode.release(lock)

        assert other_lock.try_acquire()

    def test_cannot_release_unlocked(self, lock_backend: LockBackend, lock_variant: LockVariant) -> None:
        lock_mode = lock_variant.mode
        lock = lock_variant.factory()

        with lock_backend.raises(LockError, LOCK_MESSAGE_NOT_LOCKED):
            lock_mode.release(lock)

        lock_mode.acquire(lock)
        lock_mode.release(lock)

        with lock_backend.raises(LockError, LOCK_MESSAGE_NOT_LOCKED):
            lock_mode.release(lock)

    def test_acquire_timeout(self, lock_backend: LockBackend, lock_variant: LockVariant) -> None:
        lock_mode = lock_variant.mode
        lock = lock_variant.factory()

        timeout = lock_backend.min_acquire_timeout
        single_attempt_min_duration = lock_backend.single_attempt_min_duration
        single_attempt_max_duration = lock_backend.single_attempt_max_duration

        with lock_variant.factory():
            clock = Clock()
            with lock_backend.raises(LockTimeoutError, LOCK_MESSAGE_TIMEOUT, mode=lock_mode.value):
                lock_mode.acquire(lock, timeout=timeout)
            assert timeout <= clock.elapsed_time < timeout + LOCK_ACQUIRE_TIMEOUT_TOLERANCE

            # Single attempts.
            for single_attempt_timeout in (0, -1.0):
                clock.start()
                with lock_backend.raises(LockTimeoutError, LOCK_MESSAGE_TIMEOUT, mode=lock_mode.value):
                    lock_mode.acquire(lock, timeout=single_attempt_timeout)
                assert single_attempt_min_duration <= clock.elapsed_time < single_attempt_max_duration

            clock.start()
            assert not lock_mode.try_acquire(lock)
            assert single_attempt_min_duration <= clock.elapsed_time < single_attempt_max_duration

        # The requests that gave up must not block the next ones.
        assert lock_mode.try_acquire(lock)

    @pytest.mark.parametrize("timeout", [None, 0, -1.0, 1e-9, DEFAULT_LOCK_ACQUIRE_TIMEOUT])
    def test_acquire_with_small_timeout(self, lock_variant: LockVariant, timeout: Optional[float]) -> None:
        # Even a single attempt must succeed on a free lock, whatever the delay of the backend to grant it.
        lock_mode = lock_variant.mode
        lock = lock_variant.factory()

        lock_mode.acquire(lock, timeout=timeout)
        lock_mode.release(lock)

    def test_acquire_waits_for_release(self, lock_variant: LockVariant) -> None:
        lock = lock_variant.factory()
        lock.acquire()

        with create_thread_group() as thread_group:
            thread_group.defer_start(LOCK_DEFER_RELEASE_DELAY, lock.release)

            clock = Clock()
            lock_variant.mode.acquire(lock_variant.factory())
            assert clock.elapsed_time >= LOCK_DEFER_RELEASE_DELAY

    def test_lock_is_released_when_object_is_deleted(
        self, lock_backend: LockBackend, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        # Not created by the factory: it would keep a reference on the lock.
        lock = lock_backend.create_read_write_lock()
        lock.acquire()

        del lock
        gc.collect()

        assert read_write_lock_factory().try_acquire()

    def test_release_with_a_forked_child(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        lock = read_write_lock_factory()
        lock.acquire()

        # The child inherits a copy of the handle and stays alive after the release.
        child_process = multiprocessing.get_context("fork").Process(target=signal.pause, daemon=True)
        child_process.start()
        try:
            lock.release()
            assert read_write_lock_factory().try_acquire()
        finally:
            kill_process(child_process)

    def test_no_file_descriptor_leak(
        self, lock_backend: LockBackend, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        timeout = lock_backend.min_acquire_timeout

        with assert_no_fd_leak():
            for _ in range(50):
                with read_write_lock_factory().shared():
                    pass
                with read_write_lock_factory():
                    pass

            with read_write_lock_factory():
                for _ in range(20):
                    assert not read_write_lock_factory().shared_try_acquire()
                    with pytest.raises(LockTimeoutError):
                        read_write_lock_factory().acquire(timeout=timeout)

# ------------------------------------------------------------------------------

class TestReadWriteLock:
    @pytest.mark.parametrize("held_lock_mode, other_lock_mode", [
        (LockMode.EXCLUSIVE, LockMode.EXCLUSIVE),
        (LockMode.EXCLUSIVE, LockMode.SHARED),
        (LockMode.SHARED, LockMode.EXCLUSIVE),
        (LockMode.SHARED, LockMode.SHARED),
    ], ids=["writer-writer", "writer-reader", "reader-writer", "reader-reader"])
    def test_mode_compatibility(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        held_lock_mode: LockMode,
        other_lock_mode: LockMode
    ) -> None:
        lock = read_write_lock_factory()
        other_lock = read_write_lock_factory()

        are_shared_read_lock = held_lock_mode is LockMode.SHARED and other_lock_mode is LockMode.SHARED

        assert held_lock_mode.try_acquire(lock)
        assert other_lock_mode.try_acquire(other_lock) == are_shared_read_lock
        if are_shared_read_lock:
            other_lock_mode.release(other_lock)

        held_lock_mode.release(lock)
        assert other_lock_mode.try_acquire(other_lock)

    def test_shared_context_manager(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        reader = read_write_lock_factory()
        other_reader = read_write_lock_factory()
        writer = read_write_lock_factory()

        with reader.shared():
            assert other_reader.shared_try_acquire()
            assert not writer.try_acquire()
            other_reader.shared_release()
            assert not writer.try_acquire()

        assert writer.try_acquire()

    def test_shared_context_manager_timeout(
        self, lock_backend: LockBackend, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        lock = read_write_lock_factory()
        lock.acquire()

        timeout = lock_backend.min_acquire_timeout

        with lock_backend.raises(LockTimeoutError, LOCK_MESSAGE_TIMEOUT, mode=LockMode.SHARED.value), \
                read_write_lock_factory().shared(timeout=timeout):
            pytest.fail("The lock must not be acquired.")

    @over_lock_modes
    def test_cannot_release_with_wrong_method(
        self,
        lock_backend: LockBackend,
        read_write_lock_factory: ReadWriteLockFactory,
        lock_mode: LockMode
    ) -> None:
        lock = read_write_lock_factory()
        lock_mode.acquire(lock)

        wrong_lock_mode = LockMode.SHARED if lock_mode is LockMode.EXCLUSIVE else LockMode.EXCLUSIVE
        with lock_backend.raises(
            LockError,
            LOCK_MESSAGE_WRONG_RELEASE_METHOD,
            mode=lock_mode.value,
            expected=LOCK_RELEASE_METHOD_NAMES[lock_mode],
            wrong=LOCK_RELEASE_METHOD_NAMES[wrong_lock_mode]
        ):
            wrong_lock_mode.release(lock)

        other_lock = read_write_lock_factory()
        assert not other_lock.try_acquire()

        lock_mode.release(lock)
        assert other_lock.try_acquire()

    def test_multiple_readers(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        readers = [read_write_lock_factory() for _ in range(5)]
        for reader in readers:
            assert reader.shared_try_acquire()

        writer = read_write_lock_factory()
        for reader in readers:
            assert not writer.try_acquire()
            reader.shared_release()
        assert writer.try_acquire()

    def test_single_attempts_on_free_lock_are_reliable(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        lock = read_write_lock_factory()
        for _ in range(50):
            for lock_mode in LockMode:
                assert lock_mode.try_acquire(lock)
                lock_mode.release(lock)

# ------------------------------------------------------------------------------

class LockExclusionChecker:
    """
    Record readers and writers currently inside a critical section, and the violations of the exclusion.
    """

    # How long a holder stays inside the critical section, so that overlaps have time to happen (in seconds).
    CRITICAL_SECTION_DURATION: Final = 0.001

    def __init__(self) -> None:
        self._mutex = threading.Lock()
        self._holder_counts = dict.fromkeys(LockMode, 0)
        self._violations: List[str] = []

    @property
    def violations(self) -> List[str]:
        return self._violations

    def critical_section(self, lock_mode: LockMode) -> None:
        """
        Critical section of a holder of the lock in `lock_mode`.

        It records a violation if it overlaps with an incompatible holder.
        """

        with self._mutex:
            self._holder_counts[lock_mode] += 1
            writer_count = self._holder_counts[LockMode.EXCLUSIVE]
            reader_count = self._holder_counts[LockMode.SHARED]
            if writer_count > 1 or (writer_count and reader_count):
                self.violations.append(
                    f"{lock_mode.value} holder entered with readers={reader_count} writers={writer_count}."
                )

        time.sleep(self.CRITICAL_SECTION_DURATION)

        with self._mutex:
            self._holder_counts[lock_mode] -= 1

class TestMutualExclusion:
    # Threads competing for the lock.
    THREAD_COUNT: Final = 8

    # Acquisitions made by each thread.
    ITERATION_COUNT: Final = 100

    # Probability that an acquisition is shared: mostly readers, so that they overlap and writers wait behind them.
    READ_RATIO: Final = 0.7

    JOIN_TIMEOUT: Final = ITERATION_COUNT * (DEFAULT_LOCK_ACQUIRE_TIMEOUT + LOCK_ACQUIRE_TIMEOUT_TOLERANCE)

    def test_mutual_exclusion(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        checker = LockExclusionChecker()

        def worker(seed: int) -> None:
            rng = random.Random(seed) # noqa: S311
            lock = read_write_lock_factory()

            for _ in range(self.ITERATION_COUNT):
                lock_mode = LockMode.SHARED if rng.random() < self.READ_RATIO else LockMode.EXCLUSIVE
                # No timeout: the test checks the exclusion, not the fairness. A file lock polls with a timeout and
                # does not queue the waiters: a writer could miss every moment without readers and time out.
                lock_mode.acquire(lock, timeout=None)
                try:
                    checker.critical_section(lock_mode)
                finally:
                    lock_mode.release(lock)

        with create_thread_group(join_timeout=self.JOIN_TIMEOUT) as thread_group:
            for thread_id in range(self.THREAD_COUNT):
                thread_group.start(worker, thread_id)

        assert not checker.violations
        assert read_write_lock_factory().try_acquire()

# ------------------------------------------------------------------------------

class TestLockBetweenProcesses:
    @over_lock_modes
    def test_lock_held_by_another_process(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        child_locker_factory: ChildLockerFactory,
        lock_mode: LockMode
    ) -> None:
        child_locker = child_locker_factory(lock_mode)
        assert child_locker.wait_for_startup()

        assert read_write_lock_factory().shared_try_acquire() == lock_mode.is_shared
        assert not read_write_lock_factory().try_acquire()

    def test_lock_is_released_when_process_is_killed(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        child_locker_factory: ChildLockerFactory
    ) -> None:
        child_locker = child_locker_factory(LockMode.EXCLUSIVE)
        assert child_locker.wait_for_startup()

        lock = read_write_lock_factory()
        assert not lock.shared_try_acquire()
        child_locker.kill()
        lock.acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)

    def test_other_process_waits_for_release(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        child_locker_factory: ChildLockerFactory
    ) -> None:
        lock = read_write_lock_factory()
        lock.acquire()

        child_locker = child_locker_factory(LockMode.EXCLUSIVE)
        assert not child_locker.wait_for_startup()

        lock.release()
        assert child_locker.wait_for_startup()

# ------------------------------------------------------------------------------

class LockDurationTraces:
    """
    Levels of the traces of `LockDurationTracer` captured by `caplog` for the locks of `context`.
    """

    @staticmethod
    def get_acquire_duration_levels(caplog: pytest.LogCaptureFixture, context: str) -> List[str]:
        return LockDurationTraces._get_levels(
            caplog, rf"^Lock on `{re.escape(context)}` took \d+\.\d\d second\(s\) to acquire\.$"
        )

    @staticmethod
    def get_lock_duration_levels(caplog: pytest.LogCaptureFixture, context: str) -> List[str]:
        return LockDurationTraces._get_levels(
            caplog, rf"^Lock on `{re.escape(context)}` locked for \d+\.\d\d second\(s\)\.$"
        )

    @staticmethod
    def _get_levels(caplog: pytest.LogCaptureFixture, pattern: str) -> List[str]:
        return [record.levelname for record in caplog.records if re.match(pattern, record.getMessage())]

class TestLockDurationTraces:
    # How long a test exceeds a threshold, to get a trace (in seconds).
    THRESHOLD_EXCESS: Final = 0.2

    # A threshold, and the expected levels of the traces when the duration is `THRESHOLD_EXCESS`.
    ACQUIRE_THRESHOLDS: Final = [
        (0.1, ["WARNING"]),
        (None, []),
        (0.5, []),
        (DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD, [])
    ]
    LOCK_THRESHOLDS: Final = [
        (0.1, ["WARNING"]),
        (None, []),
        (0.5, []),
        (DEFAULT_LOCK_DURATION_THRESHOLD, [])
    ]
    THRESHOLD_IDS: Final = [
        "exceeded",
        "disabled",
        "not-exceeded",
        "default"
    ]

    @pytest.mark.parametrize("threshold, levels", ACQUIRE_THRESHOLDS, ids=THRESHOLD_IDS)
    def test_slow_acquire(
        self,
        lock_backend: LockBackend,
        lock_variant: LockVariant,
        caplog: pytest.LogCaptureFixture,
        threshold: Optional[float],
        levels: List[str]
    ) -> None:
        lock = lock_variant.factory()
        lock.acquire()

        with create_thread_group() as thread_group, caplog.at_level(log.DEBUG):
            thread_group.defer_start(self.THRESHOLD_EXCESS, lock.release)
            lock_variant.mode.acquire(lock_variant.factory(acquire_duration_threshold=threshold))
        assert LockDurationTraces.get_acquire_duration_levels(caplog, lock_backend.context) == levels

    @pytest.mark.parametrize("threshold, levels", LOCK_THRESHOLDS, ids=THRESHOLD_IDS)
    def test_long_lock(
        self,
        lock_backend: LockBackend,
        lock_variant: LockVariant,
        caplog: pytest.LogCaptureFixture,
        threshold: Optional[float],
        levels: List[str]
    ) -> None:
        lock = lock_variant.factory(lock_duration_threshold=threshold)
        with caplog.at_level(log.DEBUG), lock_variant.mode.hold(lock):
            time.sleep(self.THRESHOLD_EXCESS)
        assert LockDurationTraces.get_lock_duration_levels(caplog, lock_backend.context) == levels

    def test_timed_out_acquire_is_not_logged(
        self,
        lock_backend: LockBackend,
        lock_variant: LockVariant,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        timeout = lock_backend.min_acquire_timeout
        lock = lock_variant.factory(acquire_duration_threshold=timeout / 2)
        with lock_variant.factory(), caplog.at_level(log.DEBUG), pytest.raises(LockTimeoutError):
            lock_variant.mode.acquire(lock, timeout=timeout)
        assert not LockDurationTraces.get_acquire_duration_levels(caplog, lock_backend.context)
