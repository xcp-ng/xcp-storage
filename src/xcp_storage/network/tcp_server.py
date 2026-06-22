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

from abc import ABC, abstractmethod
import asyncio
import ssl
import sys
import threading

import xcp_storage.log as log
from xcp_storage.network.socket import create_server_sock, Socket
from xcp_storage.utils.asyncio import cancel_event_loop_tasks, close_stream_writer

from xcp_storage.typing import (
    Any,
    Optional,
    override,
    Set,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

class TcpServerError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)

# ------------------------------------------------------------------------------

class TcpServer(ABC):
    class Client:
        def __init__(
            self,
            peername: Any, # noqa: ANN401
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
        ) -> None:
            self.peername: Any = peername
            self.reader = reader
            self.writer = writer

        @override
        def __str__(self) -> str:
            return str(self.peername)

    def __init__(self, address: str, port: int, ssl_context: Optional[ssl.SSLContext] = None) -> None:
        self._address = address
        self._port = port
        self._ssl_context = ssl_context

        self._running = False

        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._startup_event = threading.Event()
        self._shutdown_event = threading.Event()

        self._server_socket: Optional[Socket] = None
        self._server: Optional[asyncio.AbstractServer] = None

        self._clients: Set[TcpServer.Client] = set()

    @property
    def address(self) -> str:
        return self._address

    @property
    def port(self) -> int:
        # Return trivial port if it's not 0. As reminder, 0 = dynamic binding.
        if self._port or not self._server_socket:
            return self._port

        port = self._server_socket.port
        return port if port is not None else 0

    def run(self) -> None: # noqa: C901
        if self._running:
            raise TcpServerError("Server is already running.")

        self._startup_event.clear()
        self._shutdown_event.clear()
        self._running = True

        try:
            logger.info("Running TCP server on `%s:%d`...", self._address, self._port)
            self._server_socket = Socket(create_server_sock(
                self._address,
                self._port,
                reuse_address=True,
                keep_alive=True,
                timeout=0.0, # 0 here to set non-blocking mode.
                ssl_context=self._ssl_context
            ))

            try:
                old_event_loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop.
                old_event_loop = None

            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            server_params = {
                "client_connected_cb": self._handle_client,
                "sock": self._server_socket.sock
            }

            if sys.version_info < (3, 8):
                # TODO(XCPNG-3032): Workaround for old python versions. Remove me later.
                # In fact we must give `loop` param for these versions and the entire
                # event loop management is also required just for it.
                server_params["loop"] = self._event_loop

            self._server = self._event_loop.run_until_complete(
                asyncio.start_server(**server_params) # type: ignore[arg-type]
            )
            self._startup_event.set()

            logger.info("TCP server started!")
            self._event_loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Closing server because break signal has been received...")
        except Exception:
            self._startup_event.set()
            raise
        finally:
            if self._server:
                self._server.close()
                # TODO(XCPNG-3032): Use `abort_clients` only.
                for client in list(self._clients):
                    try:
                        client.writer.transport.abort()
                    except Exception as e: # noqa: PERF203
                        logger.debug("Failed to abort client %s transport: `%s`.", client, e)
                self._server = None

            if self._event_loop:
                try:
                    cancel_event_loop_tasks(self._event_loop)
                finally:
                    self._event_loop.close()
                    self._event_loop = None
                    if old_event_loop:
                        asyncio.set_event_loop(old_event_loop)

            if self._server_socket:
                self._server_socket.close()
                self._server_socket = None

            self._clients.clear()
            self._running = False
            self._shutdown_event.set()

    def stop(self) -> bool:
        if self.async_stop():
            self.wait_for_shutdown()
            return True
        return False

    def async_stop(self) -> bool:
        if self._event_loop and self._event_loop.is_running():
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
            return True
        return False

    def wait_for_startup(self) -> None:
        self._startup_event.wait()

    def wait_for_shutdown(self) -> None:
        self._shutdown_event.wait()

    async def _handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter
    ) -> None:
        client = self.Client(client_writer.get_extra_info("peername"), client_reader, client_writer)
        logger.info("New client %s connected.", client)
        self._clients.add(client)

        rejected = False
        try:
            if not await self._handle_client_connect(client):
                rejected = True
                return
            while not client_writer.transport.is_closing():
                if not await self._handle_client_request(client):
                    break
            logger.info("Client %s has terminated.", client)
        except asyncio.TimeoutError as e:
            logger.warning("Timeout reached for client %s: `%s`.", client, e)
        except asyncio.IncompleteReadError as e:
            logger.warning("Connection closed for client %s: `%s`.", client, e)
        except Exception as e:
            logger.error("Unhandled exception for client %s: `%s`.", client, e)
        finally:
            if not rejected:
                try:
                    await self._handle_client_disconnect(client)
                except Exception as e:
                    logger.error("Unhandled exception for client %s during disconnect: `%s`.", client, e)

            await close_stream_writer(client_writer)
            logger.info("Client %s disconnected.", client)
            self._clients.remove(client)

    @abstractmethod
    async def _handle_client_connect(self, client: Client) -> bool:
        return False

    @abstractmethod
    async def _handle_client_disconnect(self, client: Client) -> None:
        pass

    @abstractmethod
    async def _handle_client_request(self, client: Client) -> bool:
        return False
