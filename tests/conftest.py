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
import threading

import pytest

from tests.network.tls import (  # noqa: F401
    ssl_contexts,
    tls_contexts,
    TlsContexts,
)
from xcp_storage.rpc.server import RpcApiServer

from xcp_storage.typing import (
    Final,
    Generator,
    List,
    Optional,
)

# ==============================================================================

SERVER_STARTUP_TIMEOUT: Final = 5.0
SERVER_SHUTDOWN_TIMEOUT: Final = 5.0

SERVER_THREAD_SHUTDOWN_TIMEOUT: Final = 5.0

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def _rpc_server(ssl_contexts: Optional[TlsContexts]) -> Generator[RpcApiServer, None, None]: # noqa: F811
    server = RpcApiServer("127.0.0.1", 0, ssl_context=ssl_contexts.server if ssl_contexts else None)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    try:
        assert server.wait_for_startup(timeout=SERVER_STARTUP_TIMEOUT), "Server not started."
        yield server
    finally:
        server.stop(timeout=SERVER_SHUTDOWN_TIMEOUT)
        server_thread.join(timeout=SERVER_THREAD_SHUTDOWN_TIMEOUT)
        assert not server_thread.is_alive(), "Server thread still alive."

@pytest.fixture
def rpc_server(ssl_contexts: Optional[TlsContexts]) -> Generator[RpcApiServer, None, None]: # noqa: F811
    with _rpc_server(ssl_contexts) as server:
        yield server

@pytest.fixture
def rpc_servers(
    request: pytest.FixtureRequest,
    ssl_contexts: Optional[TlsContexts] # noqa: F811
) -> Generator[List[RpcApiServer], None, None]:
    with contextlib.ExitStack() as stack:
        servers = [stack.enter_context(_rpc_server(ssl_contexts)) for _ in range(request.param)]
        yield servers
