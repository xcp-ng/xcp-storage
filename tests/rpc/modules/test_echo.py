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

import pytest

from xcp_storage.network.socket import SocketTimeoutError
import xcp_storage.rpc.api as api
from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.rpc.server import RpcApiServer
from xcp_storage.utils.json.rpc import JsonRpcRequestError, JsonRpcResponseError

from xcp_storage.typing import Final

# ==============================================================================

class TestRpcModuleEcho:
    CLIENT_TIMEOUT: Final = 1.0
    MESSAGE: Final = "Moshimoshi, Storage-San?"

    def test_echo(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)
        response = rpc_client.call_api(api.echo.echo, message=self.MESSAGE)
        assert response == self.MESSAGE

    def test_one_shot_echo(self, rpc_server: RpcApiServer) -> None:
        with RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT) as rpc_client:
            assert rpc_client.connected
            response = rpc_client.call_api(api.echo.echo, message=self.MESSAGE)
            assert response == self.MESSAGE
        assert not rpc_client.connected

    def test_echo_without_message(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)
        with pytest.raises(JsonRpcResponseError, match="Invalid params"):
            rpc_client.call_api(api.echo.echo) # type: ignore[call-arg]

    def test_echo_with_mixed_arguments(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port)
        with pytest.raises(JsonRpcRequestError, match="Positional and named arguments cannot be mixed."):
            rpc_client.call_api(api.echo.echo, self.MESSAGE, message=self.MESSAGE) # type: ignore[misc]

    def test_defer_echo(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=self.CLIENT_TIMEOUT)
        response = rpc_client.call_api(api.echo.defer_echo, message=self.MESSAGE, delay=0.2)
        assert response == self.MESSAGE
        assert rpc_client.connected

    def test_defer_echo_timeout(self, rpc_server: RpcApiServer) -> None:
        rpc_client = RpcApiClient(rpc_server.address, rpc_server.port, client_timeout=0.2) # Use a short timeout here.
        with pytest.raises(SocketTimeoutError):
            rpc_client.call_api(api.echo.defer_echo, message=self.MESSAGE, delay=1.0)
        assert not rpc_client.connected
