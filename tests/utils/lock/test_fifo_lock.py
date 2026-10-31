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
from pathlib import Path, PurePath
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from tests.network import busy_unix_server_sock
from tests.utils.exception import raises_exactly
from tests.utils.fd import assert_no_fd_leak, occupied_low_fds
from tests.utils.lock.fifo_lock_service import (
    FIFO_LOCK_DAEMON_POLL_INTERVAL,
    FIFO_LOCK_SERVICE_START_TIMEOUT,
    FIFO_LOCK_SERVICE_TEMPLATE_NAME,
    FifoLockDaemon,
    FifoLockServices,
)
from tests.utils.lock.lock_variant import (
    DEFAULT_FIFO_BACKEND_LOCK_NAME,
    DEFAULT_LOCK_ACQUIRE_TIMEOUT,
    LockBackend,
    LockFactory,
    LockMode,
    ReadWriteLockFactory,
)
from tests.utils.lock.pending_acquisition import PendingAcquisitionFactory, QueuedWriterFactory
from tests.utils.thread import create_thread_group
from xcp_storage.network.socket import (
    create_unix_client_sock,
    create_unix_server_sock,
    socket_wait_readable,
    SocketDisconnectedError,
)
from xcp_storage.utils.file import FD_SETSIZE
from xcp_storage.utils.lock import LockError, LockTimeoutError
from xcp_storage.utils.lock.fifo import (
    _LOCK_DAEMON_NAME,
    _LOCK_SERVICE_NAME_FORMAT,
    _MAX_CONNECTION_ATTEMPTS,
    FifoLock,
    ReadWriteFifoLock,
)
from xcp_storage.utils.service import escape_service_instance, ServiceError
from xcp_storage.utils.sync import wait_for_condition

from xcp_storage.typing import (
    Final,
    Iterator,
    List,
    Optional,
)

# ==============================================================================

# Messages of the FIFO lock errors.
LOCK_MESSAGE_INVALID_NAME: Final = "Invalid lock name: `{name}`."
LOCK_MESSAGE_INVALID_SERVICE_NAME: Final = "Invalid lock service name: `{service_name}`."
LOCK_MESSAGE_SERVICE_START_FAILURE: Final = "Unable to start lock service `{service_name}`."
LOCK_MESSAGE_SERVER_NOT_REACHABLE: Final = "Lock server `{name}` is not reachable."
LOCK_MESSAGE_CONNECTION_FAILURE: Final = "Unable to connect to lock server `{name}`."
LOCK_MESSAGE_COMMUNICATION_FAILURE: Final = "Unable to communicate with lock server `{name}`."
LOCK_MESSAGE_LOST_CONNECTION: Final = "Lost connection with lock server `{name}`."
LOCK_MESSAGE_UNEXPECTED_ANSWER: Final = "Unexpected answer from lock server `{name}`."

# ------------------------------------------------------------------------------

# Lock whose daemon is not started before the tests: the first acquisition starts its service.
# The `-` checks the escaping of the service name.
ON_DEMAND_LOCK_NAME: Final = "on-demand-lock"
ON_DEMAND_SERVICE_NAME: Final = _LOCK_SERVICE_NAME_FORMAT.format("on\\x2ddemand\\x2dlock")

# ------------------------------------------------------------------------------

DEFAULT_FIFO_BACKEND_SERVICE_NAME: Final = _LOCK_SERVICE_NAME_FORMAT.format(
    escape_service_instance(DEFAULT_FIFO_BACKEND_LOCK_NAME)
)

# Maximum number of connections served by the daemon (`MAX_CLIENTS`: see C code).
FIFO_LOCK_DAEMON_MAX_CLIENTS: Final = 128

# ------------------------------------------------------------------------------

# Redefine `lock_backend` to only use file FIFO backend in this file.
@pytest.fixture
def lock_backend(fifo_lock_backend: LockBackend) -> LockBackend:
    return fifo_lock_backend

# ------------------------------------------------------------------------------

class TestFifoLockName:
    def test_name_and_path(self, fifo_locks_dir_path: Path, exclusive_lock_factory: LockFactory) -> None:
        lock = exclusive_lock_factory()
        assert isinstance(lock, FifoLock)
        assert lock.name == DEFAULT_FIFO_BACKEND_LOCK_NAME
        assert lock.path == FifoLock.get_lock_path(lock.name) == fifo_locks_dir_path / lock.name

    @pytest.mark.parametrize("name", ["", ".hidden", "-opt", "a/b", "../a", "a b", "a@b", "é"])
    def test_invalid_name(self, name: str) -> None:
        with raises_exactly(ValueError, LOCK_MESSAGE_INVALID_NAME.format(name=name)):
            FifoLock(name)

    def test_get_service_name(self) -> None:
        assert FifoLock.get_service_name(DEFAULT_FIFO_BACKEND_LOCK_NAME) == DEFAULT_FIFO_BACKEND_SERVICE_NAME
        assert ReadWriteFifoLock.get_service_name(ON_DEMAND_LOCK_NAME) == ON_DEMAND_SERVICE_NAME

    def test_get_lock_name(self) -> None:
        assert FifoLock.get_lock_name(DEFAULT_FIFO_BACKEND_SERVICE_NAME) == DEFAULT_FIFO_BACKEND_LOCK_NAME
        assert ReadWriteFifoLock.get_lock_name(ON_DEMAND_SERVICE_NAME) == ON_DEMAND_LOCK_NAME

    @pytest.mark.parametrize("service_name", [
        "",
        "other@lock.service",
        FIFO_LOCK_SERVICE_TEMPLATE_NAME,
        _LOCK_SERVICE_NAME_FORMAT.format(ON_DEMAND_LOCK_NAME),
        _LOCK_SERVICE_NAME_FORMAT.format("a/b"),
        f"{_LOCK_DAEMON_NAME}@{DEFAULT_FIFO_BACKEND_LOCK_NAME}.socket",
    ], ids=["empty", "other-service", "template", "unescaped", "invalid-lock-name", "wrong-suffix"])
    def test_get_lock_name_of_invalid_service_name(self, service_name: str) -> None:
        with raises_exactly(ValueError, LOCK_MESSAGE_INVALID_SERVICE_NAME.format(service_name=service_name)):
            FifoLock.get_lock_name(service_name)

# ------------------------------------------------------------------------------

class TestFifoLock:
    def test_lock_is_released_when_connection_is_closed(
        self, fifo_lock_daemon: FifoLockDaemon, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        lock = read_write_lock_factory()

        # Raw protocol: a client that dies without any explicit release.
        with create_unix_client_sock(fifo_lock_daemon.socket_path) as unix_client:
            unix_client.sendall(b"W")
            assert unix_client.recv(8) == b"L"
            assert not lock.try_acquire()
        assert lock.try_acquire()

# ------------------------------------------------------------------------------

class TestArrivalOrder:
    # Time given in seconds to a request to reach the daemon, before sending the next one or
    # checking that it was not granted.
    REQUEST_DELIVERY_DELAY: Final = 0.2

    def test_requests_are_served_in_arrival_order(self, exclusive_lock_factory: LockFactory) -> None:
        request_count = 16
        order: List[int] = []

        def lock_in_order(index: int) -> None:
            with exclusive_lock_factory():
                order.append(index)

        with create_thread_group() as thread_group, exclusive_lock_factory():
            for index in range(request_count):
                thread_group.start(lock_in_order, index)
                time.sleep(self.REQUEST_DELIVERY_DELAY)
        assert order == list(range(request_count))

    def test_writer_is_not_overtaken_by_later_readers(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        pending_acquisition_factory: PendingAcquisitionFactory,
        queued_writer_factory: QueuedWriterFactory
    ) -> None:
        reader = read_write_lock_factory()
        reader.shared_acquire()

        queued_writer = queued_writer_factory()

        # A reader arrives after the queued writer: it must wait, even if a reader holds the lock.
        late_reader = pending_acquisition_factory(LockMode.SHARED)
        assert late_reader.is_waiting_for_acquisition(delay=self.REQUEST_DELIVERY_DELAY)
        assert queued_writer.is_waiting_for_acquisition()

        reader.shared_release()
        assert queued_writer.wait_for_acquisition(), queued_writer.acquire_exception
        assert late_reader.is_waiting_for_acquisition()

        queued_writer.lock.release()
        assert late_reader.wait_for_acquisition()

    def test_consecutive_readers_are_granted_together(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        # The N readers are queued behind the holder: they must be granted at the same time.
        reader_count = 16
        barrier = threading.Barrier(reader_count)

        def read() -> None:
            with read_write_lock_factory().shared(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT):
                barrier.wait(DEFAULT_LOCK_ACQUIRE_TIMEOUT)

        with create_thread_group() as thread_group, read_write_lock_factory():
            for _ in range(reader_count):
                thread_group.start(read)
            time.sleep(self.REQUEST_DELIVERY_DELAY)

# ------------------------------------------------------------------------------

class TestOnDemandService:
    def test_service_is_started_when_socket_is_missing(
        self, read_write_lock_factory: ReadWriteLockFactory, mock_fifo_lock_start_service: MagicMock
    ) -> None:
        lock = read_write_lock_factory(ON_DEMAND_LOCK_NAME)
        lock.acquire(timeout=FIFO_LOCK_SERVICE_START_TIMEOUT)
        lock.release()

        # The service is running now: it is not started again.
        lock.shared_acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        lock.shared_release()

        mock_fifo_lock_start_service.assert_called_once_with(ON_DEMAND_SERVICE_NAME)

    def test_service_is_started_when_socket_is_stale(
        self, read_write_lock_factory: ReadWriteLockFactory, mock_fifo_lock_start_service: MagicMock
    ) -> None:
        on_demand_path = FifoLock.get_lock_path(ON_DEMAND_LOCK_NAME)
        create_unix_server_sock(on_demand_path).close()
        assert on_demand_path.exists()

        read_write_lock_factory(ON_DEMAND_LOCK_NAME).acquire(timeout=FIFO_LOCK_SERVICE_START_TIMEOUT)
        mock_fifo_lock_start_service.assert_called_once_with(ON_DEMAND_SERVICE_NAME)

    def test_service_is_not_started_when_daemon_runs(
        self, read_write_lock_factory: ReadWriteLockFactory, mock_fifo_lock_start_service: MagicMock
    ) -> None:
        read_write_lock_factory().acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        mock_fifo_lock_start_service.assert_not_called()

    def test_service_start_failure(
        self, read_write_lock_factory: ReadWriteLockFactory, mock_fifo_lock_start_service: MagicMock
    ) -> None:
        mock_fifo_lock_start_service.side_effect = ServiceError("Boom.")
        with raises_exactly(LockError, LOCK_MESSAGE_SERVICE_START_FAILURE.format(service_name=ON_DEMAND_SERVICE_NAME)):
            read_write_lock_factory(ON_DEMAND_LOCK_NAME).acquire()

    @pytest.mark.usefixtures("fifo_lock_server_unreachable")
    @pytest.mark.parametrize("timeout", [None, DEFAULT_LOCK_ACQUIRE_TIMEOUT])
    def test_service_never_listens(
        self,
        exclusive_lock_factory: LockFactory,
        mock_fifo_lock_start_service: MagicMock,
        timeout: Optional[float]
    ) -> None:
        with raises_exactly(LockError, LOCK_MESSAGE_SERVER_NOT_REACHABLE.format(name=ON_DEMAND_LOCK_NAME)):
            exclusive_lock_factory(ON_DEMAND_LOCK_NAME).acquire(timeout=timeout)
        mock_fifo_lock_start_service.assert_called_once_with(ON_DEMAND_SERVICE_NAME)

    @pytest.mark.usefixtures("fifo_lock_service_never_starts")
    def test_timeout_while_waiting_for_the_service(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        with pytest.raises(LockTimeoutError):
            read_write_lock_factory(ON_DEMAND_LOCK_NAME).acquire(timeout=0)

# ------------------------------------------------------------------------------

class TestLimits:
    # Lock served by a server that never accepts (see `busy_unix_server_sock`).
    BUSY_LOCK_NAME: Final = "busy-lock"

    # Make a socket path longer than the maximum length of the path of a UNIX socket.
    TOO_LONG_LOCK_NAME: Final = "x" * 200

    def test_unix_socket_path_too_long(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        with raises_exactly(LockError, LOCK_MESSAGE_CONNECTION_FAILURE.format(name=self.TOO_LONG_LOCK_NAME)):
            read_write_lock_factory(self.TOO_LONG_LOCK_NAME).acquire()

    @pytest.mark.usefixtures("fifo_lock_server_unreachable")
    def test_no_file_descriptor_leak_on_connection_failures(
        self, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        with read_write_lock_factory():
            pass

        with assert_no_fd_leak():
            for _ in range(20):
                for lock_name in (ON_DEMAND_LOCK_NAME, self.TOO_LONG_LOCK_NAME):
                    with pytest.raises(LockError):
                        read_write_lock_factory(lock_name).acquire()

    def test_file_descriptor_out_of_select_range(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        lock = read_write_lock_factory()

        # Test `select` limit range.
        with occupied_low_fds(FD_SETSIZE), raises_exactly(
            LockError, LOCK_MESSAGE_COMMUNICATION_FAILURE.format(name=DEFAULT_FIFO_BACKEND_LOCK_NAME)
        ):
            lock.acquire()
        assert lock.try_acquire()

    def test_more_clients_than_the_daemon_accepts(self, read_write_lock_factory: ReadWriteLockFactory) -> None:
        # A reader beyond the limit of the daemon cannot be served, even if the lock is shared. Its request
        # must be withdrawn cleanly, and be served as soon as a slot is free.
        holders = [read_write_lock_factory() for _ in range(FIFO_LOCK_DAEMON_MAX_CLIENTS)]
        for holder in holders:
            holder.shared_acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)

        extra_lock = read_write_lock_factory()
        assert not extra_lock.shared_try_acquire()
        with pytest.raises(LockTimeoutError):
            extra_lock.shared_acquire(timeout=0)

        holders.pop().shared_release()
        extra_lock.shared_acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        extra_lock.shared_release()

        assert not extra_lock.try_acquire()
        for holder in holders:
            holder.shared_release()
        assert extra_lock.try_acquire()

    def test_full_connection_queue_ends_with_timeout(
        self, read_write_lock_factory: ReadWriteLockFactory, mock_fifo_lock_start_service: MagicMock
    ) -> None:
        # A server that never accepts: once its listen queue is full, new connections fail at once.
        with busy_unix_server_sock(FifoLock.get_lock_path(self.BUSY_LOCK_NAME)):
            lock = read_write_lock_factory(self.BUSY_LOCK_NAME)
            assert not lock.try_acquire()
            with pytest.raises(LockTimeoutError):
                lock.acquire(timeout=0)
        mock_fifo_lock_start_service.assert_not_called()

# ------------------------------------------------------------------------------

class TestDaemonFailures:
    @pytest.mark.usefixtures("fifo_lock_server_unreachable")
    def test_release_after_daemon_death(
        self, fifo_lock_daemon: FifoLockDaemon, read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        lock = read_write_lock_factory()
        lock.acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        fifo_lock_daemon.kill()

        # The holder cannot know that the daemon is gone: the release must not fail.
        lock.release()

        with raises_exactly(LockError, LOCK_MESSAGE_SERVER_NOT_REACHABLE.format(name=DEFAULT_FIFO_BACKEND_LOCK_NAME)):
            lock.acquire()

    @pytest.mark.usefixtures("fifo_lock_server_unreachable")
    def test_daemon_dies_while_waiting(
        self,
        fifo_lock_daemon: FifoLockDaemon,
        read_write_lock_factory: ReadWriteLockFactory,
        queued_writer_factory: QueuedWriterFactory
    ) -> None:
        read_write_lock_factory().shared_acquire()
        queued_writer = queued_writer_factory()
        fifo_lock_daemon.kill()

        assert not queued_writer.wait_for_acquisition()
        assert isinstance(queued_writer.acquire_exception, LockError)

    @pytest.mark.usefixtures("fifo_lock_server_unreachable")
    def test_daemon_restarted_on_same_socket(
        self,
        fifo_lock_daemon: FifoLockDaemon,
        fifo_lock_services: FifoLockServices,
        read_write_lock_factory: ReadWriteLockFactory
    ) -> None:
        lock = read_write_lock_factory()

        fifo_lock_daemon.kill()

        # A killed daemon leaves its socket file behind: connections are refused until the restart.
        assert fifo_lock_daemon.socket_path.exists()
        with raises_exactly(LockError, LOCK_MESSAGE_SERVER_NOT_REACHABLE.format(name=DEFAULT_FIFO_BACKEND_LOCK_NAME)):
            lock.acquire()

        fifo_lock_services.start_service(DEFAULT_FIFO_BACKEND_SERVICE_NAME)

        def try_acquire_when_restarted() -> bool:
            with contextlib.suppress(LockError):
                return lock.try_acquire()
            return False

        assert wait_for_condition(
            try_acquire_when_restarted, FIFO_LOCK_SERVICE_START_TIMEOUT, FIFO_LOCK_DAEMON_POLL_INTERVAL
        )

    def test_queued_request_survives_daemon_restart(
        self,
        fifo_lock_daemon: FifoLockDaemon,
        read_write_lock_factory: ReadWriteLockFactory,
        queued_writer_factory: QueuedWriterFactory,
        mock_fifo_lock_start_service: MagicMock
    ) -> None:
        read_write_lock_factory().shared_acquire(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT)
        queued_writer = queued_writer_factory(timeout=DEFAULT_LOCK_ACQUIRE_TIMEOUT + FIFO_LOCK_SERVICE_START_TIMEOUT)

        fifo_lock_daemon.kill()
        assert queued_writer.wait_for_acquisition(), queued_writer.acquire_exception

        mock_fifo_lock_start_service.assert_called_once_with(DEFAULT_FIFO_BACKEND_SERVICE_NAME)

    def test_lost_connection(self, lock_backend: LockBackend, read_write_lock_factory: ReadWriteLockFactory) -> None:
        timeout = lock_backend.min_acquire_timeout
        lock = read_write_lock_factory()

        def fail(**_: object) -> None:
            time.sleep(2 * timeout)
            raise SocketDisconnectedError("Connection lost.")

        with patch.object(lock, "_try_server_lock", side_effect=fail, autospec=True) as mock_try_server_lock, \
                raises_exactly(LockError, LOCK_MESSAGE_LOST_CONNECTION.format(name=DEFAULT_FIFO_BACKEND_LOCK_NAME)):
            lock.acquire(timeout=timeout)
        assert mock_try_server_lock.call_count == 1

# ------------------------------------------------------------------------------

class TestLockServerReply:
    # Lock served by `fake_lock_server`.
    LOCK_NAME: Final = "fake"

    # How long `fake_lock_server` keeps a connection open after its reply (in seconds).
    CLOSE_DELAY: Final = 0.3

    @classmethod
    @contextlib.contextmanager
    def fake_lock_server(cls, socket_path: PurePath, reply: bytes) -> Iterator[List[socket.socket]]:
        """
        Server answering `reply` to every request, then closing the connection after
        `CLOSE_DELAY`. Yields the accepted connections.
        """

        stopped_event = threading.Event()
        connections: List[socket.socket] = []

        with create_unix_server_sock(socket_path) as unix_server:
            def serve() -> None:
                while not stopped_event.is_set():
                    if not socket_wait_readable(unix_server, timeout=FIFO_LOCK_DAEMON_POLL_INTERVAL):
                        continue

                    unix_client, _ = unix_server.accept()
                    connections.append(unix_client)

                    unix_client.recv(1)
                    unix_client.sendall(reply)
                    time.sleep(cls.CLOSE_DELAY)
                    unix_client.close()

            with create_thread_group() as thread_group:
                thread_group.start(serve)
                try:
                    yield connections
                finally:
                    stopped_event.set()

    @pytest.mark.parametrize("reply, message_format, connection_count", [
        # A protocol error is not a lost connection: nothing is sent again.
        (b"N", LOCK_MESSAGE_UNEXPECTED_ANSWER, 1),
        # No answer, then the connection closes: the request is sent again.
        (b"", LOCK_MESSAGE_LOST_CONNECTION, _MAX_CONNECTION_ATTEMPTS),
        # Extra data after a valid answer is not read: the lock is granted.
        (b"LL", None, 1),
    ], ids=["unexpected", "no-answer", "extra-data"])
    def test_acquire_handles_reply(
        self,
        read_write_lock_factory: ReadWriteLockFactory,
        reply: bytes,
        message_format: Optional[str],
        connection_count: int
    ) -> None:
        timeout = _MAX_CONNECTION_ATTEMPTS * self.CLOSE_DELAY + DEFAULT_LOCK_ACQUIRE_TIMEOUT

        lock = read_write_lock_factory(self.LOCK_NAME)
        with self.fake_lock_server(FifoLock.get_lock_path(self.LOCK_NAME), reply) as connections:
            if message_format is None:
                lock.acquire(timeout=timeout)
            else:
                with raises_exactly(LockError, message_format.format(name=self.LOCK_NAME)):
                    lock.acquire(timeout=timeout)
            assert len(connections) == connection_count
