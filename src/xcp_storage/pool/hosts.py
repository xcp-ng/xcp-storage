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

import ipaddress
import json
import time

from xcp_storage.config.platform import XCP_STORAGE_STATE_DIR_PATH
from xcp_storage.utils.check import check_ipv4_address
from xcp_storage.utils.file import write_file_atomically
from xcp_storage.utils.firewall import update_firewall_allowlist

from xcp_storage.typing import (
    Final,
    List,
    Optional,
    Sequence,
)

# ==============================================================================

# Kept across reboots: the last addresses known are there before XAPI answers.
POOL_HOSTS_PATH: Final = XCP_STORAGE_STATE_DIR_PATH / "pool-hosts.json"

# Version of the format of `POOL_HOSTS_PATH`.
_POOL_HOSTS_SCHEMA_VERSION: Final = 1

# Allowlist of the firewall accepting the addresses of the hosts of the pool only,
# used by the ports reserved to them.
_POOL_ONLY_FIREWALL_ALLOWLIST: Final = "xcp-storage-pool-hosts-only"

# ------------------------------------------------------------------------------

class PoolHostsError(Exception):
    """
    The file of the addresses of the pool hosts cannot be read or written.
    """

# ------------------------------------------------------------------------------

def read_pool_host_addresses() -> Optional[List[str]]:
    """
    Return the addresses of the hosts of the pool known by this host, `None` if not
    known yet. `PoolHostsError` is raised if the file cannot be read or is invalid.
    """

    try:
        text = POOL_HOSTS_PATH.read_text()
    except FileNotFoundError:
        return None
    except OSError as e:
        raise PoolHostsError(f"Unable to read the hosts of the pool in `{POOL_HOSTS_PATH}`: `{e}`.") from None

    try:
        data = json.loads(text)
    except ValueError:
        data = None

    addresses: Optional[List] = None
    if isinstance(data, dict) and data.get("version") == _POOL_HOSTS_SCHEMA_VERSION:
        addresses = data.get("addresses")

    if not isinstance(addresses, list) or not all(isinstance(address, str) for address in addresses):
        raise PoolHostsError(f"Invalid pool hosts file: `{POOL_HOSTS_PATH}`.")

    return addresses

def update_pool_host_addresses(addresses: Sequence[str]) -> None:
    """
    Set the addresses of the hosts of the pool (IPv4, this host included):
    written in `POOL_HOSTS_PATH` if they changed. Firewall is also updated
    when addresses are changed.
    `PoolHostsError` is raised if the file cannot be written.
    """

    if not addresses:
        raise ValueError("No host address given.")

    for address in addresses:
        check_ipv4_address(address, "IPv4 address")

    # Canonical and sorted: the same addresses always give the same file.
    canonical_addresses = sorted({str(ipaddress.IPv4Address(address)) for address in addresses})

    try:
        current_addresses = read_pool_host_addresses()
    except PoolHostsError:
        current_addresses = None

    if current_addresses != canonical_addresses:
        text = json.dumps({
            "version": _POOL_HOSTS_SCHEMA_VERSION,
            "update_time": time.time(),
            "addresses": canonical_addresses
        }, indent=4) + "\n"

        try:
            POOL_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            write_file_atomically(POOL_HOSTS_PATH, text)
        except OSError as e:
            raise PoolHostsError(f"Unable to write the hosts of the pool in `{POOL_HOSTS_PATH}`: `{e}`.") from None

    update_firewall_allowlist(_POOL_ONLY_FIREWALL_ALLOWLIST, canonical_addresses)
