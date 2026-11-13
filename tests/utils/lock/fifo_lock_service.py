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

from functools import partial
import os
from pathlib import Path
import subprocess
import threading
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import PROJECT_DAEMONS_DIR_PATH, PROJECT_PATH
from xcp_storage.utils.contextlib import scoped_factory
from xcp_storage.utils.lock.fifo import (
    _LOCK_DAEMON_NAME,
    _LOCK_SERVICE_NAME_FORMAT,
    _SERVICE_START_TIMEOUT,
    FifoLock,
)
from xcp_storage.utils.process import kill_process
from xcp_storage.utils.sync import wait_for_condition

from xcp_storage.typing import (
    Callable,
    ContextManager,
    Dict,
    Final,
    Iterator,
)

# ==============================================================================

# Directory of the lock daemon in the sources.
FIFO_LOCK_DAEMON_DIR_PATH: Final = PROJECT_DAEMONS_DIR_PATH / _LOCK_DAEMON_NAME

# Template unit of the lock service in the sources.
FIFO_LOCK_SERVICE_TEMPLATE_NAME: Final = _LOCK_SERVICE_NAME_FORMAT.format("")
FIFO_LOCK_UNIT_PATH: Final = FIFO_LOCK_DAEMON_DIR_PATH / FIFO_LOCK_SERVICE_TEMPLATE_NAME

# Maximum time a launched daemon takes to create its socket (in seconds).
FIFO_LOCK_SERVICE_START_TIMEOUT: Final = _SERVICE_START_TIMEOUT

# Interval between two checks of the state of a daemon or of its socket (in seconds).
FIFO_LOCK_DAEMON_POLL_INTERVAL: Final = 0.01

# ------------------------------------------------------------------------------

# Module of the FIFO locks, whose globals are patched by the tests.
_FIFO_LOCK_MODULE: Final = FifoLock.__module__

# Service start timeout in seconds of the locks when their server is unreachable.
# Short, the socket never appears.
_UNREACHABLE_SERVER_SERVICE_START_TIMEOUT: Final = 0.05

# ------------------------------------------------------------------------------

class FifoLockDaemon:
    """
    Daemon of the FIFO locks, serving the lock whose socket is `socket_path`.
    """

    def __init__(self, exec_path: Path, socket_path: Path) -> None:
        self.socket_path = socket_path
        self._process = subprocess.Popen([str(exec_path), str(socket_path)])
        self._killed = False

    def wait_for_startup(self) -> None:
        """
        Wait for the daemon to create its socket, which it does at startup.
        """

        socket_created = wait_for_condition(
            self.socket_path.exists, FIFO_LOCK_SERVICE_START_TIMEOUT, FIFO_LOCK_DAEMON_POLL_INTERVAL
        )
        assert socket_created, f"The daemon did not create `{self.socket_path}`."

    def is_alive(self) -> bool:
        return not self._killed and self._process.poll() is None

    def kill(self) -> None:
        """
        Kill the daemon, which leaves its socket file behind. Does nothing if it's already killed.
        """

        self._killed = True
        kill_process(self._process)

FifoLockDaemonFactory = Callable[[str], FifoLockDaemon]

# ------------------------------------------------------------------------------

def patched_fifo_locks_dir(dir_path: Path) -> ContextManager[object]:
    """
    Patch FIFO locks directory with another path.
    """

    return patch(f"{_FIFO_LOCK_MODULE}._LOCKS_DIR_PATH", dir_path)

def patched_fifo_lock_service_start_timeout(timeout: float) -> ContextManager[object]:
    """
    Patch the maximum time a FIFO lock waits for the socket of a service it started.
    """

    return patch(f"{_FIFO_LOCK_MODULE}._SERVICE_START_TIMEOUT", timeout)

# ------------------------------------------------------------------------------

class FifoLockServices:
    """
    Fake service manager of the FIFO locks: like systemd, it starts the daemon of any lock on demand.
    """

    def __init__(self, daemon_factory: FifoLockDaemonFactory) -> None:
        self._daemon_factory = daemon_factory
        self._daemons: Dict[str, FifoLockDaemon] = {}
        self._lock = threading.Lock()
        self._owner_pid = os.getpid()

    def start_service(self, service_name: str) -> None:
        """
        Launch the daemon of a lock, don't wait for its socket.
        """

        self._start(FifoLock.get_lock_name(service_name))

    def get_daemon(self, lock_name: str) -> FifoLockDaemon:
        """
        Start the daemon of `lock_name` unless it runs, and wait for its socket.
        """

        daemon = self._start(lock_name)
        daemon.wait_for_startup()
        return daemon

    def _start(self, lock_name: str) -> FifoLockDaemon:
        # A daemon launched by a forked child would never be killed:
        # the parent must start the services before.
        # In a child, `is_alive` cannot see the daemons of the parent and `_lock` may have been copied held.
        assert os.getpid() == self._owner_pid, f"Daemon of lock `{lock_name}` started by a forked process."
        with self._lock:
            daemon = self._daemons.get(lock_name)
            if daemon is None or not daemon.is_alive():
                daemon = self._daemon_factory(lock_name)
                self._daemons[lock_name] = daemon
            return daemon

# ------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fifo_lock_daemon_exec_path(project_build_path: Path) -> Path:
    """
    The `xcp-storage-fifo-lock` daemon built by `project_build_path`: the tests never run an installed one.
    """

    return project_build_path / FIFO_LOCK_DAEMON_DIR_PATH.relative_to(PROJECT_PATH) / _LOCK_DAEMON_NAME

@pytest.fixture
def fifo_locks_dir_path(tmp_path: Path, mock_fifo_lock_start_service: MagicMock) -> Iterator[Path]: # noqa: ARG001
    """
    Used to create the socket FIFO locks in a temporary directory.
    """

    with patched_fifo_locks_dir(tmp_path):
        yield tmp_path

@pytest.fixture
def mock_fifo_lock_start_service() -> Iterator[MagicMock]:
    """
    The service is requested when nobody listens on the socket of a FIFO lock: with this helper, `systemctl`
    is never called. Useful to simulate or test failures.
    """

    with patch(f"{_FIFO_LOCK_MODULE}.start_service", autospec=True) as mock_fifo_lock_start_service:
        yield mock_fifo_lock_start_service

# ------------------------------------------------------------------------------

@pytest.fixture
def fifo_lock_daemon_factory(
    fifo_lock_daemon_exec_path: Path, fifo_locks_dir_path: Path # noqa: ARG001
) -> Iterator[FifoLockDaemonFactory]:
    """
    Start `xcp-storage-fifo-lock` daemons serving a lock name, killed at the end of the test.
    It returns as soon as the process is started: don't wait for socket creation.
    """

    with scoped_factory(partial(FifoLockDaemon, fifo_lock_daemon_exec_path), FifoLockDaemon.kill) as factory:
        def create(lock_name: str) -> FifoLockDaemon:
            return factory(FifoLock.get_lock_path(lock_name))

        yield create

@pytest.fixture
def fifo_lock_services(
    fifo_lock_daemon_factory: FifoLockDaemonFactory, mock_fifo_lock_start_service: MagicMock
) -> FifoLockServices:
    """
    Fake service manager used by tests: the first connection to a FIFO lock without daemon starts one, whatever
    the lock name. Tests use it to get the daemon of a lock name with `FifoLockServices.get_daemon`.
    """

    services = FifoLockServices(fifo_lock_daemon_factory)
    mock_fifo_lock_start_service.side_effect = services.start_service
    return services

# ------------------------------------------------------------------------------

@pytest.fixture
def fifo_lock_service_never_starts(
    fifo_lock_services: FifoLockServices, mock_fifo_lock_start_service: MagicMock # noqa: ARG001
) -> None:
    """
    `start_service` succeeds but launches no daemon: a lock without a running daemon waits for a socket that
    never appears. Daemons already running (e.g. `fifo_lock_daemon`) are not affected.
    """

    mock_fifo_lock_start_service.side_effect = None

@pytest.fixture
def fifo_lock_server_unreachable(fifo_lock_service_never_starts: None) -> Iterator[None]: # noqa: ARG001
    """
    Like `fifo_lock_service_never_starts`, but a lock stops waiting for the socket after
    `_UNREACHABLE_SERVER_SERVICE_START_TIMEOUT`: it fails at once with a "not reachable" error,
    before its own timeout.
    """

    with patched_fifo_lock_service_start_timeout(_UNREACHABLE_SERVER_SERVICE_START_TIMEOUT):
        yield
