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

from xcp_storage.config.platform import XCP_STORAGE_RUNTIME_DIR_PATH
from xcp_storage.utils.firewall.interface import FirewallBackend
from xcp_storage.utils.firewall.iptables import IptablesFirewallBackend
from xcp_storage.utils.lock.file import FileLock

from xcp_storage.typing import (
    Final,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

# ==============================================================================

_LOCK_PATH: Final = XCP_STORAGE_RUNTIME_DIR_PATH / "firewall.lock"

# ------------------------------------------------------------------------------

def _get_firewall_backend() -> FirewallBackend:
    return IptablesFirewallBackend()

@contextlib.contextmanager
def _locked_firewall_backend() -> Iterator[FirewallBackend]:
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(_LOCK_PATH):
        yield _get_firewall_backend()

# ------------------------------------------------------------------------------

def update_firewall_tcp_port(
    port: int,
    *,
    open_port: bool,
    stateful: bool = True,
    allowlist: Optional[str] = None
) -> None:
    """
    Open or close the TCP port `port`: to any address, or to the addresses of the allowlist `allowlist` only (see
    `create_firewall_allowlist`, created before opening the port). Nothing done if it is already in this state.
    """

    with _locked_firewall_backend() as backend:
        backend.update_tcp_port(port, open_port=open_port, stateful=stateful, allowlist=allowlist)

def update_firewall_tcp_port_range(
    ports: Tuple[int, int],
    *,
    open_ports: bool,
    stateful: bool = True,
    allowlist: Optional[str] = None
) -> None:
    """
    Same as `update_firewall_tcp_port`, for the TCP ports `ports[0]` to `ports[1]`.
    """

    with _locked_firewall_backend() as backend:
        backend.update_tcp_port_range(ports, open_ports=open_ports, stateful=stateful, allowlist=allowlist)

def create_firewall_allowlist(name: str) -> None:
    """
    Create the allowlist `name` if missing. An existing allowlist is kept as it is.
    """

    with _locked_firewall_backend() as backend:
        backend.create_allowlist(name)

def update_firewall_allowlist(name: str, addresses: Sequence[str]) -> None:
    """
    Set the allowlist `name` (created if missing) to the IPv4 addresses `addresses`.
    Nothing done if it already holds exactly these addresses.
    """

    with _locked_firewall_backend() as backend:
        backend.update_allowlist(name, addresses)
