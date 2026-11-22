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

from xcp_storage.typing import (
    Optional,
    Sequence,
    Tuple,
)

# ==============================================================================

class FirewallError(Exception):
    def __init__(self, message: str, code: Optional[int] = None) -> None:
        super().__init__(message)
        self.code = code

# ------------------------------------------------------------------------------

class FirewallBackend(ABC):
    """
    Abstract tool managing the firewall of this host.
    """

    @abstractmethod
    def update_tcp_port(self, port: int, *, open_port: bool, stateful: bool, allowlist: Optional[str]) -> None:
        pass # pragma: no cover

    @abstractmethod
    def update_tcp_port_range(
        self, ports: Tuple[int, int], *, open_ports: bool, stateful: bool, allowlist: Optional[str]
    ) -> None:
        pass # pragma: no cover

    @abstractmethod
    def create_allowlist(self, name: str) -> None:
        pass # pragma: no cover

    @abstractmethod
    def update_allowlist(self, name: str, addresses: Sequence[str]) -> None:
        pass # pragma: no cover
