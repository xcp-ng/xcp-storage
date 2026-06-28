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

import asyncio
import ssl

import xcp_storage.log as log
from xcp_storage.network.protocol import Protocol, ProtocolError
from xcp_storage.network.protocol.xcp import XcpProtocol
from xcp_storage.network.tcp_server import TcpServer
from xcp_storage.utils.json import JsonDict
from xcp_storage.utils.json.rpc import (
    JsonRpcDispatcher,
    JsonRpcRequestProcessor,
    JsonRpcResponse,
    JsonRpcResponseParseError,
)

from xcp_storage.typing import (
    Final,
    Optional,
    override,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

_DEBUG_SERVER: Final = False

# ------------------------------------------------------------------------------

class _JsonRpcServerImpl(TcpServer):
    def __init__(
        self,
        dispatcher: JsonRpcDispatcher,
        address: str,
        port: int,
        ssl_context: Optional[ssl.SSLContext] = None,
        protocol: Optional[Protocol] = None
    ) -> None:
        super().__init__(address, port, ssl_context)
        self._dispatcher = dispatcher
        self._protocol = protocol or XcpProtocol()

    @override
    async def _handle_client_connect(self, client: TcpServer.Client) -> bool:
        error_message = ""
        seq: Optional[int] = None
        try:
            _request = await self._protocol.receive_packet_async(client.reader, (Protocol.MessageType.CONNECT, ))
            return True
        except asyncio.IncompleteReadError:
            logger.warning("Client connection of %s has been closed before request processing!", client)
            return False
        except ProtocolError as e:
            error_message = str(e)
            seq = e.seq
        except Exception as e:
            error_message = str(e)

        logger.error("Error on client %s before request processing: `%s`.", client, error_message)
        await self._send_parse_error(client, self.normalize_seq(seq), error_message)
        return False

    @override
    async def _handle_client_disconnect(self, client: TcpServer.Client) -> None:
        pass

    @override
    async def _handle_client_request(self, client: TcpServer.Client) -> bool:
        error_message = ""
        seq: Optional[int] = None
        payload = None
        try:
            # 1. Get request.
            request = await self._protocol.receive_packet_async(client.reader, (Protocol.MessageType.REQUEST, ))
            if _DEBUG_SERVER:
                logger.debug("Handle client request of %s: %s with payload: `%r`.", client, request, request.payload)
            seq = request.seq

            # 2. Execute request.
            # TODO(XCPNG-3032): Replace with get_running_loop in python 3.7.
            payload = await asyncio.get_event_loop().run_in_executor(
                None,
                self._process_packet_request,
                self._dispatcher,
                request
            )
        except asyncio.IncompleteReadError:
            logger.warning("Client connection of %s has been closed during request processing!", client)
            return False
        except ProtocolError as e:
            error_message = str(e)
            seq = e.seq
        except Exception as e:
            error_message = str(e)

        # 3. Send response.
        seq = self.normalize_seq(seq)
        if payload is not None:
            response = self._protocol.create_packet(Protocol.MessageType.RESPONSE, seq, payload)
            if _DEBUG_SERVER:
                logger.debug("Send client response to %s: %s with payload: `%r`.", client, response, response.payload)
            await self._protocol.send_packet_async(client.writer, response)
        else:
            logger.error("Error on client %s during request processing: `%s`.", client, error_message)
            await self._send_parse_error(client, seq, error_message)

        return True

    async def _send_parse_error(self, client: TcpServer.Client, seq: int, message: str) -> None:
        data: JsonDict = {"message": message}
        payload = JsonRpcResponse(error=JsonRpcResponseParseError(data=data).payload).to_json().encode("utf-8")
        response = self._protocol.create_packet(Protocol.MessageType.RESPONSE, seq, payload)
        await self._protocol.send_packet_async(client.writer, response)

    @staticmethod
    def normalize_seq(seq: Optional[int]) -> int:
        return seq if seq is not None else -1

    @staticmethod
    def _process_packet_request(dispatcher: JsonRpcDispatcher, packet: Protocol.Packet) -> bytes:
        response = JsonRpcRequestProcessor(dispatcher).process(packet.payload.decode("utf-8"))
        if response:
            return response.to_json().encode("utf-8")
        return b""

# ------------------------------------------------------------------------------

class JsonRpcServer:
    def __init__(
        self,
        dispatcher: JsonRpcDispatcher,
        address: str,
        port: int,
        ssl_context: Optional[ssl.SSLContext] = None,
        protocol: Optional[Protocol] = None
    ) -> None:
        self._impl = _JsonRpcServerImpl(dispatcher, address, port, ssl_context, protocol)

    @property
    def address(self) -> str:
        return self._impl.address

    @property
    def port(self) -> int:
        return self._impl.port

    def run(self) -> None:
        self._impl.run()

    def stop(self) -> None:
        self._impl.stop()

    def async_stop(self) -> None:
        self._impl.async_stop()

    def wait_for_startup(self) -> None:
        self._impl.wait_for_startup()

    def wait_for_shutdown(self) -> None:
        self._impl.wait_for_shutdown()
