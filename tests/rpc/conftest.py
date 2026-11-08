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

import ssl

import pytest

from tests.network.tls import (  # noqa: F401
    client_ssl_context,
    ssl_contexts,
    tls_contexts,
    TlsContexts,
)
from tests.rpc import RPC_CLIENT_TIMEOUT, RpcClientFactory
from tests.utils.thread import create_thread_group
from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.rpc.server import RpcApiServer
from xcp_storage.utils.contextlib import scoped_factory

from xcp_storage.typing import (
    Final,
    Iterator,
    Optional,
)

# ==============================================================================

_RPC_SERVER_STARTUP_TIMEOUT: Final = 5.0
_RPC_SERVER_SHUTDOWN_TIMEOUT: Final = 5.0

_RPC_SERVER_THREAD_SHUTDOWN_TIMEOUT: Final = 5.0

# ------------------------------------------------------------------------------

@pytest.fixture
def rpc_server(
    request: pytest.FixtureRequest,
    ssl_contexts: Optional[TlsContexts] # noqa: F811
) -> Iterator[RpcApiServer]:
    server_class = getattr(request, "param", RpcApiServer)
    server = server_class("127.0.0.1", 0, ssl_context=ssl_contexts.server if ssl_contexts else None)
    with create_thread_group(join_timeout=_RPC_SERVER_THREAD_SHUTDOWN_TIMEOUT) as thread_group:
        thread_group.start(server.run)
        try:
            assert server.wait_for_startup(timeout=_RPC_SERVER_STARTUP_TIMEOUT), "Server not started."
            yield server
        finally:
            server.stop(timeout=_RPC_SERVER_SHUTDOWN_TIMEOUT)

@pytest.fixture
def rpc_client_factory(
    rpc_server: RpcApiServer,
    client_ssl_context: Optional[ssl.SSLContext] # noqa: F811
) -> Iterator[RpcClientFactory]:
    def create(*, client_timeout: float = RPC_CLIENT_TIMEOUT) -> RpcApiClient:
        return RpcApiClient(
            rpc_server.address,
            rpc_server.port,
            ssl_context=client_ssl_context,
            client_timeout=client_timeout
        )

    # Do not rely on the garbage collector: a test can keep a client alive (e.g. through a mock that wraps
    # one of its methods), and its socket would stay open after the test.
    with scoped_factory(create, RpcApiClient.disconnect) as factory:
        yield factory
