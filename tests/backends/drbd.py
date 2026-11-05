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

from xcp_storage.backends.drbd import _get_drbd_debug_resource_openers_path, Drbd

from xcp_storage.typing import Final, Iterator

# ==============================================================================

_DRBD_MODULE: Final = Drbd.__module__

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

@pytest.fixture
def drbd_json_status_primary() -> str:
    return json.dumps([{
        "name": "xcp-volume-patate",
        "node-id": 1,
        "role": "Primary",
        "suspended": False,
        "suspended-user": False,
        "suspended-no-data": False,
        "suspended-fencing": False,
        "suspended-quorum": False,
        "force-io-failures": False,
        "write-ordering": "flush",
        "devices": [{
            "volume": 0,
            "minor": 1261,
            "disk-state": "UpToDate",
            "client": False,
            "open": False,
            "quorum": True,
            "size": 2109208,
            "read": 0,
            "written": 0,
            "al-writes": 0,
            "bm-writes": 0,
            "upper-pending": 0,
            "lower-pending": 0
        }],
        "connections": [{
            "peer-node-id": 0,
            "name": "sr123-s1",
            "connection-state": "Connected",
            "congested": False,
            "peer-role": "Secondary",
            "tls": False,
            "ap-in-flight": 0,
            "rs-in-flight": 0,
            "paths": [{
                "this_host": {
                    "address": "10.10.0.13",
                    "port": 7261,
                    "family": "ipv4"
                },
                "remote_host": {
                    "address": "10.10.0.12",
                    "port": 7261,
                    "family": "ipv4"
                },
                "established": True
            }],
            "peer_devices": [{
                "volume": 0,
                "replication-state": "Established",
                "peer-disk-state": "UpToDate",
                "peer-client": False,
                "resync-suspended": "no",
                "received": 0,
                "sent": 0,
                "out-of-sync": 0,
                "pending": 0,
                "unacked": 0,
                "has-sync-details": False,
                "has-online-verify-details": False,
                "percent-in-sync": 100
            }]
        }]
    }])

@pytest.fixture
def drbd_json_status_secondary() -> str:
    return json.dumps([{
        "name": "xcp-volume-patate",
        "node-id": 0,
        "role": "Secondary",
        "suspended": False,
        "suspended-user": False,
        "suspended-no-data": False,
        "suspended-fencing": False,
        "suspended-quorum": False,
        "force-io-failures": False,
        "write-ordering": "flush",
        "devices": [{
            "volume": 0,
            "minor": 1261,
            "disk-state": "UpToDate",
            "client": False,
            "open": False,
            "quorum": True,
            "size": 2109208,
            "read": 0,
            "written": 0,
            "al-writes": 0,
            "bm-writes": 0,
            "upper-pending": 0,
            "lower-pending": 0
        }],
        "connections": [{
            "peer-node-id": 1,
            "name": "sr123-s2",
            "connection-state": "Connected",
            "congested": False,
            "peer-role": "Primary",
            "tls": False,
            "ap-in-flight": 0,
            "rs-in-flight": 0,
            "paths": [{
                "this_host": {
                    "address": "10.10.0.12",
                    "port": 7261,
                    "family": "ipv4"
                },
                "remote_host": {
                    "address": "10.10.0.13",
                    "port": 7261,
                    "family": "ipv4"
                },
                "established": True
            }],
            "peer_devices": [{
                "volume": 0,
                "replication-state": "Established",
                "peer-disk-state": "UpToDate",
                "peer-client": False,
                "resync-suspended": "no",
                "received": 0,
                "sent": 0,
                "out-of-sync": 0,
                "pending": 0,
                "unacked": 0,
                "has-sync-details": False,
                "has-online-verify-details": False,
                "percent-in-sync": 100
            }]
        }]
    }])
