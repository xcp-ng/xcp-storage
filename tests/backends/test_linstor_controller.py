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
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from xcp_storage.backends.linstor.controller import _SERVICE_LINSTOR_CONTROLLER, LinstorController
from xcp_storage.network.socket import (
    create_client_sock,
    create_server_sock,
    Socket,
    SocketError,
)

from xcp_storage.typing import (
    Callable,
    cast,
    Final,
    Iterator,
    NamedTuple,
    Optional,
    Tuple,
)

# ==============================================================================

MODULE_NAME: Final = "xcp_storage.backends.linstor.controller"

# ------------------------------------------------------------------------------

class TestLinstorControllerGetAddresses:
    class LoopbackSpec(NamedTuple):
        listener_address: str
        client_address: str
        uri_client_address: str

    LOOPBACK_ADDRESSES: Final = ["127.0.0.2", "127.0.0.3", "127.0.0.4"]

    IPV4: Final = LoopbackSpec("127.0.0.1", LOOPBACK_ADDRESSES[0], LOOPBACK_ADDRESSES[0])
    IPV6: Final = LoopbackSpec("::1", "::1", "[::1]")

    ListenFunc = Callable[..., Socket]
    ConnectFunc = Callable[..., Tuple[Socket, Socket]]
    PatchListenerPortFunc = Callable[[Socket], "contextlib.AbstractContextManager[None]"]

    @staticmethod
    @contextlib.contextmanager
    def patch_satellite_ports(plain_port: Optional[int], ssl_port: Optional[int]) -> Iterator[None]:
        with patch.multiple(MODULE_NAME, LINSTOR_SATELLITE_PORT_PLAIN=plain_port, LINSTOR_SATELLITE_PORT_SSL=ssl_port):
            yield

    @pytest.fixture(params=[IPV4, IPV6], ids=["ipv4", "ipv6"])
    def loopback_spec(self, request: pytest.FixtureRequest) -> LoopbackSpec:
        spec = cast(TestLinstorControllerGetAddresses.LoopbackSpec, request.param)
        if spec is self.IPV6:
            try:
                create_server_sock(spec.listener_address, 0).close()
            except SocketError:
                pytest.skip("IPv6 is not available.")
        return spec

    @pytest.fixture
    def sockets(self) -> Iterator[contextlib.ExitStack]:
        with contextlib.ExitStack() as stack:
            yield stack

    @pytest.fixture
    def listen(self, sockets: contextlib.ExitStack) -> ListenFunc:
        def impl(address: str = "127.0.0.1") -> Socket:
            return sockets.enter_context(Socket(create_server_sock(address, 0)))
        return impl

    @pytest.fixture
    def connect(self, sockets: contextlib.ExitStack) -> ConnectFunc:
        def impl(listener: Socket, client_address: str) -> Tuple[Socket, Socket]:
            client = sockets.enter_context(Socket(create_client_sock(
                cast(str, listener.address),
                cast(int, listener.port),
                source_address=client_address,
                keep_alive=False
            )))
            accepted, _ = listener.sock.accept()
            return client, sockets.enter_context(Socket(accepted))
        return impl

    @pytest.fixture(params=["plain", "ssl"])
    def patch_listener_port(self, request: pytest.FixtureRequest, listen: ListenFunc) -> PatchListenerPortFunc:
        unused_port = listen().port

        def impl(listener: Socket) -> "contextlib.AbstractContextManager[None]":
            ports = (listener.port, unused_port)
            return self.patch_satellite_ports(*(ports if request.param == "plain" else reversed(ports)))
        return impl

    def test_no_connection(self, listen: ListenFunc, loopback_spec: LoopbackSpec) -> None:
        listener = listen(loopback_spec.listener_address)

        with self.patch_satellite_ports(listener.port, listener.port):
            assert LinstorController.get_addresses() == []
            assert LinstorController.get_uri() == ""

    def test_closed_connection(
        self,
        listen: ListenFunc,
        connect: ConnectFunc,
        patch_listener_port: PatchListenerPortFunc,
        loopback_spec: LoopbackSpec
    ) -> None:
        listener = listen(loopback_spec.listener_address)
        client, accepted = connect(listener, loopback_spec.client_address)

        accepted.close()
        client.close()

        with patch_listener_port(listener):
            assert LinstorController.get_addresses() == []

    def test_established_connection(
        self,
        listen: ListenFunc,
        connect: ConnectFunc,
        patch_listener_port: PatchListenerPortFunc,
        loopback_spec: LoopbackSpec
    ) -> None:
        listener = listen(loopback_spec.listener_address)
        connect(listener, loopback_spec.client_address)

        with patch_listener_port(listener):
            assert LinstorController.get_addresses() == [loopback_spec.uri_client_address]
            assert LinstorController.get_uri() == f"linstor://{loopback_spec.uri_client_address}"

# ------------------------------------------------------------------------------

@patch(f"{MODULE_NAME}.LinstorController.get_addresses")
class TestLinstorControllerGetUri:
    def test_no_address(self, mock_get_addresses: MagicMock) -> None:
        mock_get_addresses.return_value = []
        assert LinstorController.get_uri() == ""

    def test_one_address(self, mock_get_addresses: MagicMock) -> None:
        mock_get_addresses.return_value = ["10.10.0.13"]
        assert LinstorController.get_uri() == "linstor://10.10.0.13"

    def test_two_addresses(self, mock_get_addresses: MagicMock) -> None:
        mock_get_addresses.return_value = ["10.10.0.13", "10.10.0.14"]
        assert LinstorController.get_uri() == "linstor://10.10.0.13"

    def test_ipv6_address(self, mock_get_addresses: MagicMock) -> None:
        mock_get_addresses.return_value = ["[fe80::2]"]
        assert LinstorController.get_uri() == "linstor://[fe80::2]"

# ------------------------------------------------------------------------------

class TestLinstorControllerService:
    @patch(f"{MODULE_NAME}.is_service_active", return_value=True)
    def test_running(self, mock_is_service_active: MagicMock) -> None:
        assert LinstorController.is_running()
        mock_is_service_active.assert_called_once_with(_SERVICE_LINSTOR_CONTROLLER)

    @patch(f"{MODULE_NAME}.is_service_active", return_value=False)
    def test_not_running(self, mock_is_service_active: MagicMock) -> None:
        assert not LinstorController.is_running()
        mock_is_service_active.assert_called_once_with(_SERVICE_LINSTOR_CONTROLLER)

    @pytest.mark.parametrize("service_name, function_name", [
        ("start", "start_service"),
        ("stop", "stop_service"),
        ("restart", "restart_service")
    ])
    def test_service_command(self, service_name: str, function_name: str) -> None:
        with patch(f"{MODULE_NAME}.{function_name}") as mock_function_name:
            getattr(LinstorController, service_name)()
        mock_function_name.assert_called_once_with(_SERVICE_LINSTOR_CONTROLLER)
