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

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from xcp_storage.backends.drbd import (
    _get_drbd_debug_resource_openers_path,
    Drbd,
    DrbdConnectionState,
    DrbdDiskState,
    DrbdRole,
)

from xcp_storage.typing import (
    Final,
    Iterator,
    NamedTuple,
    Sequence,
)

# ==============================================================================

_DRBD_MODULE: Final = Drbd.__module__

# ------------------------------------------------------------------------------

# Resource and nodes of the DRBD statuses of the mocked tests (`drbd_json_status_*`).
TEST_DRBD_RESOURCE_NAME: Final = "xcp-volume-patate"
TEST_DRBD_PRIMARY_NODE_NAME: Final = "sr123-s2"
TEST_DRBD_PRIMARY_NODE_ADDRESS: Final = "10.10.0.13"
TEST_DRBD_SECONDARY_NODE_NAME: Final = "sr123-s1"
TEST_DRBD_SECONDARY_NODE_ADDRESS: Final = "10.10.0.12"

TEST_DRBD_MISSING_NODE_NAME: Final = "sr123-s3"

# Errors of `drbdsetup`: unknown resource, and state change refused (e.g. demotion of a resource held open).
DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE: Final = 10
DRBDSETUP_STATE_CHANGE_FAILED_EXIT_CODE: Final = 11

# ------------------------------------------------------------------------------

class DrbdDebugFs:
    """
    Fake DRBD debugfs (`/sys/kernel/debug/drbd`) in a temporary directory.
    """

    def write_openers(self, resource_name: str, volume_number: int, content: str) -> None:
        openers_path = _get_drbd_debug_resource_openers_path(resource_name, volume_number)
        openers_path.parent.mkdir(parents=True, exist_ok=True)
        openers_path.write_text(content)

@pytest.fixture
def drbd_debug_fs(tmp_path: Path) -> Iterator[DrbdDebugFs]:
    """
    Empty by default: no openers.
    """

    with patch(f"{_DRBD_MODULE}._DRBD_DEBUG_RESOURCES_PATH", tmp_path / "drbd-resources"):
        yield DrbdDebugFs()

# ------------------------------------------------------------------------------

class DrbdStatusNode(NamedTuple):
    """
    Node of the resource of the DRBD statuses of the tests.
    """

    node_id: int
    name: str
    address: str
    role: DrbdRole
    # Diskless replica (DRBD client), like a tie-breaker.
    diskless: bool = False

# ------------------------------------------------------------------------------

def create_drbdsetup_no_such_resource_error(resource_name: str) -> str:
    return f"{resource_name}: No such resource\n"

def create_drbdsetup_held_open_error(resource_name: str) -> str:
    return f"{resource_name}: State change failed: (-12) Device is held open by someone\n"

# ------------------------------------------------------------------------------

def create_drbd_json_status(
    resource_name: str,
    node: DrbdStatusNode,
    peer_nodes: Sequence[DrbdStatusNode],
    volume_numbers: Sequence[int] = (0, )
) -> str:
    # Output of `drbdsetup status --json` on `node`: the volumes are up to date on all the diskful nodes.
    return json.dumps([{
        "name": resource_name,
        "node-id": node.node_id,
        "role": node.role,
        "suspended": False,
        "suspended-user": False,
        "suspended-no-data": False,
        "suspended-fencing": False,
        "suspended-quorum": False,
        "force-io-failures": False,
        "write-ordering": "flush",
        "devices": [{
            "volume": volume_number,
            "minor": 1261,
            "disk-state": DrbdDiskState.DISKLESS if node.diskless else DrbdDiskState.UP_TO_DATE,
            "client": node.diskless,
            "open": False,
            "quorum": True,
            "size": 2109208,
            "read": 0,
            "written": 0,
            "al-writes": 0,
            "bm-writes": 0,
            "upper-pending": 0,
            "lower-pending": 0
        } for volume_number in volume_numbers],
        "connections": [{
            "peer-node-id": peer_node.node_id,
            "name": peer_node.name,
            "connection-state": DrbdConnectionState.CONNECTED,
            "congested": False,
            "peer-role": peer_node.role,
            "tls": False,
            "ap-in-flight": 0,
            "rs-in-flight": 0,
            "paths": [{
                "this_host": {
                    "address": node.address,
                    "port": 7261,
                    "family": "ipv4"
                },
                "remote_host": {
                    "address": peer_node.address,
                    "port": 7261,
                    "family": "ipv4"
                },
                "established": True
            }],
            "peer_devices": [{
                "volume": volume_number,
                "replication-state": "Established",
                "peer-disk-state": DrbdDiskState.DISKLESS if peer_node.diskless else DrbdDiskState.UP_TO_DATE,
                "peer-client": peer_node.diskless,
                "resync-suspended": "no",
                "received": 0,
                "sent": 0,
                "out-of-sync": 0,
                "pending": 0,
                "unacked": 0,
                "has-sync-details": False,
                "has-online-verify-details": False,
                "percent-in-sync": 100
            } for volume_number in volume_numbers]
        } for peer_node in peer_nodes]
    }])
