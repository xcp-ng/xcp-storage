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

from tests.backends.linstor import LinstorServiceSpec, LinstorServiceTests
from xcp_storage.backends.linstor.controller import _SERVICE_LINSTOR_CONTROLLER, LinstorController
from xcp_storage.network.socket import (
    create_tcp_client_sock,
    create_tcp_server_sock,
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

_LINSTOR_CONTROLLER_MODULE: Final = LinstorController.__module__

_LINSTOR_CONTROLLER_SERVICE_SPEC: Final = LinstorServiceSpec(
    LinstorController, _SERVICE_LINSTOR_CONTROLLER, ("start", "stop", "restart")
)

# ------------------------------------------------------------------------------

class TestLinstorControllerService(LinstorServiceTests):
    @pytest.fixture
    def linstor_service_spec(self) -> LinstorServiceSpec:
        return _LINSTOR_CONTROLLER_SERVICE_SPEC

    @pytest.fixture(params=_LINSTOR_CONTROLLER_SERVICE_SPEC.commands)
    def command(self, request: pytest.FixtureRequest) -> str:
        return request.param

# ------------------------------------------------------------------------------

class TestLinstorControllerGetAddresses:
    class LoopbackSpec(NamedTuple):
        listener_address: str
        client_address: str
        uri_client_address: str

    LOOPBACK_ADDRESSES: Final = ["127.0.0.2", "127.0.0.3", "127.0.0.4"]

    IPV4: Final = LoopbackSpec("127.0.0.1", LOOPBACK_ADDRESSES[0], LOOPBACK_ADDRESSES[0])
    IPV6: Final = LoopbackSpec("::1", "::1", "[::1]")

    ListenFunction = Callable[..., Socket]
    ConnectFunction = Callable[..., Tuple[Socket, Socket]]
    MockListenerPortFunction = Callable[[Socket], "contextlib.AbstractContextManager[None]"]

    @staticmethod
    @contextlib.contextmanager
    def mock_satellite_ports(plain_port: Optional[int], ssl_port: Optional[int]) -> Iterator[None]:
        with patch.multiple(
            _LINSTOR_CONTROLLER_MODULE, LINSTOR_SATELLITE_PORT_PLAIN=plain_port, LINSTOR_SATELLITE_PORT_SSL=ssl_port
        ):
            yield

    @pytest.fixture(params=["plain", "ssl"])
    def mock_listener_port(self, request: pytest.FixtureRequest, listen: ListenFunction) -> MockListenerPortFunction:
        unused_port = listen().port

        def impl(listener: Socket) -> "contextlib.AbstractContextManager[None]":
            ports = (listener.port, unused_port)
            return self.mock_satellite_ports(*(ports if request.param == "plain" else reversed(ports)))
        return impl

    @pytest.fixture(params=[IPV4, IPV6], ids=["ipv4", "ipv6"])
    def loopback_spec(self, request: pytest.FixtureRequest) -> LoopbackSpec:
        spec = cast(TestLinstorControllerGetAddresses.LoopbackSpec, request.param)
        if spec is self.IPV6:
            try:
                create_tcp_server_sock(spec.listener_address, 0).close()
            except SocketError:
                pytest.skip("IPv6 is not available.")
        return spec

    @pytest.fixture
    def sockets(self) -> Iterator[contextlib.ExitStack]:
        with contextlib.ExitStack() as stack:
            yield stack

    @pytest.fixture
    def listen(self, sockets: contextlib.ExitStack) -> ListenFunction:
        def impl(address: str = "127.0.0.1") -> Socket:
            return sockets.enter_context(Socket(create_tcp_server_sock(address, 0)))
        return impl

    @pytest.fixture
    def connect(self, sockets: contextlib.ExitStack) -> ConnectFunction:
        def impl(listener: Socket, client_address: str) -> Tuple[Socket, Socket]:
            client = sockets.enter_context(Socket(create_tcp_client_sock(
                cast(str, listener.address),
                cast(int, listener.port),
                source_address=client_address,
                keep_alive=False
            )))
            accepted, _ = listener.sock.accept()
            return client, sockets.enter_context(Socket(accepted))
        return impl

    def test_no_connection(self, listen: ListenFunction, loopback_spec: LoopbackSpec) -> None:
        listener = listen(loopback_spec.listener_address)

        with self.mock_satellite_ports(listener.port, listener.port):
            assert LinstorController.get_addresses() == []
            assert LinstorController.get_uri() == ""

    def test_closed_connection(
        self,
        listen: ListenFunction,
        connect: ConnectFunction,
        mock_listener_port: MockListenerPortFunction,
        loopback_spec: LoopbackSpec
    ) -> None:
        listener = listen(loopback_spec.listener_address)
        client, accepted = connect(listener, loopback_spec.client_address)

        accepted.close()
        client.close()

        with mock_listener_port(listener):
            assert LinstorController.get_addresses() == []

    def test_established_connection(
        self,
        listen: ListenFunction,
        connect: ConnectFunction,
        mock_listener_port: MockListenerPortFunction,
        loopback_spec: LoopbackSpec
    ) -> None:
        listener = listen(loopback_spec.listener_address)
        connect(listener, loopback_spec.client_address)

        with mock_listener_port(listener):
            assert LinstorController.get_addresses() == [loopback_spec.uri_client_address]
            assert LinstorController.get_uri() == f"linstor://{loopback_spec.uri_client_address}"

# ------------------------------------------------------------------------------

class TestLinstorControllerGetUri:
    LOCAL_ADDRESS: Final = "10.10.0.12:3366"
    PEER_ADDRESS: Final = "10.10.0.13"
    IPV6_PEER_ADDRESS: Final = "[fe80::2]"
    PEER_PORT: Final = 51234

    @pytest.fixture
    def mock_run_command(self) -> Iterator[MagicMock]:
        with patch(f"{_LINSTOR_CONTROLLER_MODULE}.run_command", autospec=True) as mock_run_command:
            yield mock_run_command

    @classmethod
    def get_ss_output(cls, *peer_addresses: str) -> str:
        # Columns of `ss -tnH state established`: receive queue, send queue, local address, peer address.
        return "".join(f"0 0 {cls.LOCAL_ADDRESS} {address}:{cls.PEER_PORT}\n" for address in peer_addresses)

    @pytest.mark.parametrize("peer_addresses, expected_uri", [
        ((), ""),
        ((PEER_ADDRESS,), f"linstor://{PEER_ADDRESS}"),
        ((PEER_ADDRESS, "10.10.0.14"), f"linstor://{PEER_ADDRESS}"),
        ((IPV6_PEER_ADDRESS,), f"linstor://{IPV6_PEER_ADDRESS}")
    ])
    def test_get_uri(self, mock_run_command: MagicMock, peer_addresses: Tuple[str, ...], expected_uri: str) -> None:
        mock_run_command.return_value = self.get_ss_output(*peer_addresses)
        assert LinstorController.get_uri() == expected_uri
