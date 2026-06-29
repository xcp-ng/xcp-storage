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

import threading
from typing import Generator

import pytest

from xcp_storage.rpc.server import RpcApiServer

from xcp_storage.typing import Final

# ==============================================================================

SERVER_STARTUP_TIMEOUT: Final = 5.0
SERVER_SHUTDOWN_TIMEOUT: Final = 5.0

SERVER_THREAD_SHUTDOWN_TIMEOUT: Final = 5.0

# ------------------------------------------------------------------------------

@pytest.fixture
def rpc_server() -> Generator[RpcApiServer, None, None]:
    server = RpcApiServer("127.0.0.1", 0)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    try:
        assert server.wait_for_startup(timeout=SERVER_STARTUP_TIMEOUT), "Server not started."
        yield server
    finally:
        server.stop(timeout=SERVER_SHUTDOWN_TIMEOUT)
        server_thread.join(timeout=SERVER_THREAD_SHUTDOWN_TIMEOUT)
        assert not server_thread.is_alive(), "Server thread still alive."
