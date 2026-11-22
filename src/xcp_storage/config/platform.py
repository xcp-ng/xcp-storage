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

from enum import Enum
from functools import lru_cache
from pathlib import Path

from xcp_storage.config.build_config import (
    FIREWALL_BACKEND,
    FIREWALL_INPUT_CHAIN,
    POOL_BACKEND,
)

from xcp_storage.typing import Final, Mapping, Tuple

# ==============================================================================
# Attributes that depend on the execution environment.
# Its primary purpose is to decouple the storage logic from the underlying
# host's specificities (OS, firewall rules, ...).
# ==============================================================================

class FirewallBackendType(Enum):
    """
    Backend managing the firewall of a host.
    """

    IPTABLES = "iptables"

class PoolBackendType(Enum):
    """
    Backend managing the hosts of the pool.
    """

    XAPI = "xapi"

# ------------------------------------------------------------------------------

FIREWALL_BACKEND_TYPE: Final = FirewallBackendType(FIREWALL_BACKEND)

DEFAULT_FIREWALL_INPUT_CHAIN: Final = FIREWALL_INPUT_CHAIN

POOL_BACKEND_TYPE: Final = PoolBackendType(POOL_BACKEND)

# ------------------------------------------------------------------------------
# Default system paths.
# ------------------------------------------------------------------------------

CONFIG_DIR_PATH: Final = Path("/etc")
PROC_DIR_PATH: Final = Path("/proc")
RUNTIME_DIR_PATH: Final = Path("/run")
STATE_DIR_PATH: Final = Path("/var/lib")

# ------------------------------------------------------------------------------
# XCP paths.
# ------------------------------------------------------------------------------

_XCP_STORAGE_DIR_NAME: Final = "xcp-storage"

# Configuration files of xcp-storage.
XCP_STORAGE_CONFIG_DIR_PATH: Final = CONFIG_DIR_PATH / _XCP_STORAGE_DIR_NAME

# Runtime files of xcp-storage (locks, sockets, datapath states...).
XCP_STORAGE_RUNTIME_DIR_PATH: Final = RUNTIME_DIR_PATH / _XCP_STORAGE_DIR_NAME

# Persistent files of xcp-storage local to the host (host list, backups...).
XCP_STORAGE_STATE_DIR_PATH: Final = STATE_DIR_PATH / _XCP_STORAGE_DIR_NAME

# ------------------------------------------------------------------------------

_OS_RELEASE_PATH: Final = CONFIG_DIR_PATH / "os-release"

@lru_cache(maxsize=None)
def get_os_ids() -> Tuple[str, ...]:
    """
    Get the IDs of the current distribution, most specific first: `ID` followed
    by the values of `ID_LIKE` (e.g. `("ubuntu", "debian")`). The result is
    cached. An empty tuple is returned if `/etc/os-release` can't be read.
    """

    try:
        lines = _OS_RELEASE_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    values = {}
    for line in lines:
        key, _separator, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")

    return tuple(values.get("ID", "").split() + values.get("ID_LIKE", "").split())

def get_exec_path(default: str, by_os_id: Mapping[str, str]) -> str:
    """
    Get the path of an executable: the one registered for the first matching OS
    ID, otherwise `default`.
    """

    return next((by_os_id[os_id] for os_id in get_os_ids() if os_id in by_os_id), default)
