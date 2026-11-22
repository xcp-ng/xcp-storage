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

from tests.network.fault_injecting_tcp_proxy import FaultInjectingTcpProxy

from xcp_storage.typing import (
    Final,
    override,
)

# ==============================================================================

class FaultInjectingHttpProxy(FaultInjectingTcpProxy):
    """
    `FaultInjectingTcpProxy` for an HTTP server: a lost response can skip requests
    with a safe method (`GET`, `HEAD`...), which change nothing on the server.

    Not handled: pipelined requests, `100 Continue`, ...
    """

    # Requests whose method is safe (RFC 9110): they only read.
    _SAFE_REQUEST_PREFIXES: Final = (b"GET ", b"HEAD ", b"OPTIONS ", b"TRACE ")

    _REQUEST_START_SIZE: Final = max(len(prefix) for prefix in _SAFE_REQUEST_PREFIXES)

    def __init__(self, address: str, port: int) -> None:
        super().__init__(address, port, request_start_size=self._REQUEST_START_SIZE)
        self._skip_safe_requests = False

    @override
    def lose_next_response(self, *, skip_safe_requests: bool = False) -> None:
        with self._next_response_fault_lock:
            self._skip_safe_requests = skip_safe_requests
            super().lose_next_response()

    @override
    def hang_next_response(self) -> None:
        with self._next_response_fault_lock:
            self._skip_safe_requests = False
            super().hang_next_response()

    @override
    def _is_response_fault_target(self, request_data: bytes) -> bool:
        return not self._skip_safe_requests or not request_data.startswith(self._SAFE_REQUEST_PREFIXES)
