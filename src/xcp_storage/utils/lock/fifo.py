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
import re
import time

from xcp_storage.config.platform import RUNTIME_DIR_PATH
import xcp_storage.log as log
from xcp_storage.network.socket import (
    create_unix_client_sock,
    Socket,
    SocketBusyError,
    SocketDisconnectedError,
    SocketError,
    SocketNotListeningError,
)
from xcp_storage.utils.lock import (
    DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
    DEFAULT_LOCK_DURATION_THRESHOLD,
    HandleLock,
    LockError,
    ReadWriteHandleLock,
)
from xcp_storage.utils.service import (
    escape_service_instance,
    ServiceError,
    start_service,
    unescape_service_instance,
)
from xcp_storage.utils.time import Timer

from xcp_storage.typing import (
    Final,
    Optional,
    override,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

# Protocol of the `xcp-storage-fifo-lock` daemon (see `daemons/xcp-storage-fifo-lock`):
# - The client connects to the unix socket of the lock and sends its mode: one byte.
# - The daemon answers one byte, `L`, when the lock is granted.
# - The lock is held as long as the connection is open: closing it releases the lock.
_LOCK_MODE_SHARED: Final = b"R"
_LOCK_MODE_EXCLUSIVE: Final = b"W"
_LOCK_SERVER_REPLY: Final = b"L"

# ------------------------------------------------------------------------------

# Directory of the sockets of the services: one socket, and one service instance, per lock name.
# (Must match the unit `xcp-storage-fifo-lock@.service`.)
_LOCKS_DIR_PATH: Final = RUNTIME_DIR_PATH / "xcp-storage" / "locks"

# Name of the lock daemon, also the name of its template service.
_LOCK_DAEMON_NAME: Final = "xcp-storage-fifo-lock"

# Name of a service instance: the template itself is the name with an empty instance.
_LOCK_SERVICE_NAME_FORMAT: Final = f"{_LOCK_DAEMON_NAME}@{{}}.service"

# A name is a file name and a systemd instance name: keep it simple and safe.
_LOCK_NAME_REGEX: Final = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")

# When the service is started on demand: maximum time in seconds to wait for its socket.
_SERVICE_START_TIMEOUT: Final = 5.0

_SERVICE_START_POLL_INTERVAL: Final = 0.01

# ------------------------------------------------------------------------------

# Time to wait in connect step to reach the UNIX server socket.
# With a timeout, the connection never waits, it can only fails
# at once with `SocketBusyError` instead of waiting for a free place.
_MIN_CONNECT_TIMEOUT: Final = 0.01

# The daemon answers asynchronously, even when the lock is free. So any finite timeout, including a single
# attempt (`timeout <= 0`), must still leave it a short time to reply.
_MIN_ACQUIRE_TIMEOUT: Final = 0.1

# The connection can be lost while waiting in the queue (the daemon crashed or
# was restarted/updated): the request is then sent again for a few attempts.
_MAX_CONNECTION_ATTEMPTS: Final = 3

# ------------------------------------------------------------------------------

class FifoLock(HandleLock):
    """
    Exclusive FIFO lock between processes on one machine, based on a templated service `xcp-storage-fifo-lock`.

    Design notes:
    - A lock is identified by its `name`, for one name a corresponding UNIX socket is created to
      communicate with a service instance: `xcp-storage-fifo-lock@<name>.service`.
    - All requests are executed in arrival order: nobody can starve.
    - A service releases the lock when the process dies: there is no stale lock to clean up.
    - A service is started on demand.
    - If the connection is lost before the lock is granted, the request is sent again a few times.
      If the server is unreachable, an exception is raised.
    """

    def __init__(
        self,
        name: str,
        *,
        acquire_duration_threshold: Optional[float] = DEFAULT_LOCK_ACQUIRE_DURATION_THRESHOLD,
        lock_duration_threshold: Optional[float] = DEFAULT_LOCK_DURATION_THRESHOLD
    ) -> None:
        if not _LOCK_NAME_REGEX.fullmatch(name):
            raise ValueError(f"Invalid lock name: `{name}`.")

        self._socket: Optional[Socket] = None

        super().__init__(
            name,
            acquire_duration_threshold=acquire_duration_threshold,
            lock_duration_threshold=lock_duration_threshold
        )
        self._name = name
        self._path = self.get_lock_path(name)

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        return self._path

    @staticmethod
    def get_lock_path(lock_name: str) -> Path:
        return _LOCKS_DIR_PATH / lock_name

    @staticmethod
    def get_service_name(lock_name: str) -> str:
        return _LOCK_SERVICE_NAME_FORMAT.format(escape_service_instance(lock_name))

    @staticmethod
    def get_lock_name(service_name: str) -> str:
        prefix, suffix = _LOCK_SERVICE_NAME_FORMAT.split("{}")
        lock_name = unescape_service_instance(service_name[len(prefix):-len(suffix)])
        if not _LOCK_NAME_REGEX.fullmatch(lock_name) or FifoLock.get_service_name(lock_name) != service_name:
            raise ValueError(f"Invalid lock service name: `{service_name}`.")
        return lock_name

    @override
    def _is_acquired(self) -> bool:
        return self._socket is not None

    @override
    def _close_handle(self) -> None:
        socket = self._socket
        assert socket is not None
        self._socket = None

        socket.close()

    @override
    def _try_acquire(self, *, shared: bool, timeout: Optional[float]) -> bool:
        self._check_not_locked()

        if timeout is not None:
            timeout = max(timeout, _MIN_ACQUIRE_TIMEOUT)
        timer = None if timeout is None else Timer(timeout)

        self._tracer.start_acquire()
        for attempt in range(1, _MAX_CONNECTION_ATTEMPTS + 1):
            try:
                self._socket = self._try_server_lock(shared=shared, timer=timer)
                break
            except SocketDisconnectedError as e:
                # Never try again after the deadline: the caller has waited long enough.
                if (attempt == _MAX_CONNECTION_ATTEMPTS or (
                    timer is not None and timer.has_expired()
                )):
                    raise LockError(f"Lost connection with lock server `{self._name}`.") from e
                logger.warning("Lost connection with lock server `%s`, trying again.", self._name)
            except SocketError as e:
                # Not a lost connection (e.g. file descriptor out of range for `select`): trying again is useless.
                raise LockError(f"Unable to communicate with lock server `{self._name}`.") from e

        if self._socket is not None:
            self._notify_acquired(shared=shared)
            return True
        return False

    def _try_server_lock(self, *, shared: bool, timer: Optional[Timer]) -> Optional[Socket]:
        socket = self._connect(timer)
        if socket is None:
            return None

        acquired = False
        try:
            socket.send(_LOCK_MODE_SHARED if shared else _LOCK_MODE_EXCLUSIVE)

            timeout = None if timer is None else timer.remaining_time
            if not socket.wait_readable(timeout=timeout):
                return None

            reply = bytearray(len(_LOCK_SERVER_REPLY))
            socket.receive(reply)
            if bytes(reply) != _LOCK_SERVER_REPLY:
                raise LockError(f"Unexpected answer from lock server `{self._name}`.")

            acquired = True
            return socket
        finally:
            if not acquired:
                socket.close()

    def _connect(self, timer: Optional[Timer]) -> Optional[Socket]:
        service_name = self.get_service_name(self._name)
        service_start_timer: Optional[Timer] = None
        while True:
            timeout = None if timer is None else max(timer.remaining_time, _MIN_CONNECT_TIMEOUT)

            try:
                socket = Socket(create_unix_client_sock(self._path, timeout=timeout))
                socket.timeout = None # Reset timeout. We must have a blocking socket after this point.
                return socket
            except SocketNotListeningError as e:
                if service_start_timer is None:
                    self._start_service(service_name)
                    service_start_timer = Timer(_SERVICE_START_TIMEOUT)
                elif service_start_timer.has_expired():
                    raise LockError(f"Lock server `{self._name}` is not reachable.") from e
            except SocketBusyError:
                # The queue of connections of the daemon is full: wait for a free place, like a queued request.
                pass
            except SocketError as e:
                raise LockError(f"Unable to connect to lock server `{self._name}`.") from e

            if timer is not None and timer.has_expired():
                return None
            time.sleep(_SERVICE_START_POLL_INTERVAL)

    @staticmethod
    def _start_service(service_name: str) -> None:
        try:
            start_service(service_name)
        except ServiceError as e:
            raise LockError(f"Unable to start lock service `{service_name}`.") from e

# ------------------------------------------------------------------------------

class ReadWriteFifoLock(FifoLock, ReadWriteHandleLock):
    pass
