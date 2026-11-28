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
from dataclasses import (
    dataclass,
    replace,
)
from enum import Enum
import json
from pathlib import Path
import re

import xcp_storage.log as log
from xcp_storage.utils.check import check_non_negative_int, check_regex_match, is_str_unsigned_integer
from xcp_storage.utils.process import (
    CommandError,
    CommandResult,
    get_process_cmdline,
    run_command,
)

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    Iterator,
    List,
    NamedTuple,
    StrPath,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

DRBD_BY_RES_PATH: Final = Path("/dev/drbd/by-res")
DRBD_BY_RES_PREFIX: Final = f"{DRBD_BY_RES_PATH}/"

DRBD_PORT_RANGE: Final = (7000, 8000)

# ------------------------------------------------------------------------------

_EXEC_PATH_DRBDSETUP: Final = "/usr/sbin/drbdsetup"

_DRBD_DEBUG_RESOURCES_PATH: Final = Path("/sys/kernel/debug/drbd/resources")

_DRBDSETUP_TIMEOUT: Final = 10.0

_REGEX_DRBD_OPENER_LINE: Final = re.compile(r"(.*)\s+(\d+)\s+(\d+)")

# Prefix giving the opener that auto-promoted a resource.
_DRBD_AUTO_PROMOTER_LINE_PREFIX: Final = "+"

# Characters allowed in a resource name: ASCII only, and neither a path separator nor a leading `-` or `.`.
_REGEX_DRBD_RESOURCE_NAME: Final = re.compile(r"\w[\w.-]*", re.ASCII)

# ------------------------------------------------------------------------------

class DrbdRole(str, Enum):
    """
    Role of a resource opened for writing (primary), or not,
    as reported by `drbdsetup status --json`.
    """

    PRIMARY = "Primary"
    SECONDARY = "Secondary"

class DrbdDiskState(str, Enum):
    """
    State of a volume of a resource,
    as reported by `drbdsetup status --json`.
    """

    DISKLESS = "Diskless"
    ATTACHING = "Attaching"
    DETACHING = "Detaching"
    FAILED = "Failed"
    NEGOTIATING = "Negotiating"
    INCONSISTENT = "Inconsistent"
    OUTDATED = "Outdated"
    UNKNOWN = "DUnknown"
    CONSISTENT = "Consistent"
    UP_TO_DATE = "UpToDate"

class DrbdConnectionState(str, Enum):
    """
    State of the connection to a peer of a resource,
    as reported by `drbdsetup status --json`.
    """

    STANDALONE = "StandAlone"
    DISCONNECTING = "Disconnecting"
    UNCONNECTED = "Unconnected"
    TIMEOUT = "Timeout"
    BROKEN_PIPE = "BrokenPipe"
    NETWORK_FAILURE = "NetworkFailure"
    PROTOCOL_ERROR = "ProtocolError"
    CONNECTING = "Connecting"
    TEAR_DOWN = "TearDown"
    CONNECTED = "Connected"

@dataclass(frozen=True)
class DrbdOpener:
    pid: int
    process_name: str
    cmdline: List[str]
    # The duration is expressed in milliseconds.
    open_duration: int
    # Opener whose opening auto-promoted the resource (primary role).
    auto_promoter: bool = False

# ------------------------------------------------------------------------------

# Because this module can be used by external layers and RPC, we must have checkers
# to prevent code injection.

def _check_drbd_resource_name(resource_name: str) -> None:
    check_regex_match(resource_name, _REGEX_DRBD_RESOURCE_NAME, "DRBD resource name")

def _check_drbd_volume_number(volume_number: int) -> None:
    check_non_negative_int(volume_number, "DRBD volume number")

# ------------------------------------------------------------------------------

def _get_drbd_debug_resource_openers_path(resource_name: str, volume_number: int) -> Path:
    return _DRBD_DEBUG_RESOURCES_PATH / resource_name / "volumes" / str(volume_number) / "openers"

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def _handle_drbd_json_error() -> Iterator[None]:
    """
    Log instead of raising an error while reading the JSON status of DRBD.

    The log message suggests that the JSON format may have changed BUT it's also logged for valid states that
    don't have the expected keys or items, like a resource without connection or even a connection without path.
    """
    try:
        yield
    except KeyError as e:
        logger.exception(
            "The key `%s` could not be found in the DRBD configuration. The JSON format may have changed.", e
        )
    except Exception as e:
        logger.exception("Failed to parse DRBD configuration: `%s`. The JSON format may have changed.", e)

# ------------------------------------------------------------------------------

def _run_drbdsetup_command(*args: str) -> CommandResult:
    return run_command([_EXEC_PATH_DRBDSETUP, *args], simple=False, timeout=_DRBDSETUP_TIMEOUT)

# ------------------------------------------------------------------------------

def _get_drbd_status(resource_name: str) -> Dict[str, Any]:
    try:
        stdout, stderr, ret_code = _run_drbdsetup_command("status", resource_name, "--json")
        if ret_code != 0:
            logger.warning(
                "Failed to get DRBD status of resource `%s`: `%s` (exit code %d).",
                resource_name, stderr.strip(), ret_code
            )
            return {}
    except CommandError as e:
        logger.error("Failed to get DRBD status of resource `%s`: `%s`.", resource_name, e.reason)
        return {}

    try:
        status = json.loads(stdout)
    except Exception as e:
        logger.error("Failed to read DRBD status of resource `%s` as JSON: `%s`.", resource_name, e)
        return {}

    with _handle_drbd_json_error():
        return status[0]
    return {}

class _DrbdReplica(NamedTuple):
    # A replica of a volume, as seen in a DRBD status: its disk state, and whether it is diskless (DRBD client).
    disk_state: str
    diskless: bool

def _get_drbd_replicas_by_volume(
    status: Dict[str, Any],
    connections: List[Dict[str, Any]]
) -> Dict[int, List[_DrbdReplica]]:
    replicas_by_volume = {
        device["volume"]: [_DrbdReplica(device["disk-state"], device["client"])] for device in status["devices"]
    }
    for connection in connections:
        for peer_device in connection["peer_devices"]:
            replicas_by_volume.setdefault(peer_device["volume"], []).append(
                _DrbdReplica(peer_device["peer-disk-state"], peer_device["peer-client"])
            )
    return replicas_by_volume

# ------------------------------------------------------------------------------

def _parse_drbd_opener_lines(
    resource_name: str, volume_number: int, lines: List[str], *, auto_promoter: bool = False
) -> List[DrbdOpener]:
    # `<process name> <pid> <open duration in ms>` on each line, an invalid line being skipped with a warning.
    drbd_openers = []
    for line in lines:
        match = _REGEX_DRBD_OPENER_LINE.fullmatch(line)
        if not match:
            logger.warning(
                "Unable to parse DRBD opener line of volume `%s/%d` with: `%s`.",
                resource_name,
                volume_number,
                line
            )
            continue

        groups = match.groups()
        pid = int(groups[1])
        drbd_openers.append(DrbdOpener(
            pid=pid,
            process_name=groups[0],
            # Note: `cmdline` is empty for `mount` calls. That's correct because `mount` process is dead.
            cmdline=get_process_cmdline(pid),
            open_duration=int(groups[2]),
            auto_promoter=auto_promoter
        ))
    return drbd_openers

# ------------------------------------------------------------------------------

class Drbd:
    @staticmethod
    def build_path(resource_name: str, volume_number: int) -> Path:
        _check_drbd_resource_name(resource_name)
        _check_drbd_volume_number(volume_number)
        return DRBD_BY_RES_PATH / resource_name / str(volume_number)

    @staticmethod
    def get_name_from_path(path: StrPath) -> str:
        # Assume that we have a path like this:
        # - "/dev/drbd/by-res/<NAME>/0"
        # - "../<NAME>/0"
        path = str(path)
        if path.startswith(DRBD_BY_RES_PREFIX):
            prefix_len = len(DRBD_BY_RES_PREFIX)
        elif path.startswith("../"):
            prefix_len = 3
        else:
            return ""

        res_name_end = path.find("/", prefix_len)
        if res_name_end == -1:
            return ""

        resource_name = path[prefix_len:res_name_end]
        if _REGEX_DRBD_RESOURCE_NAME.fullmatch(resource_name) and is_str_unsigned_integer(path[res_name_end + 1:]):
            return resource_name
        return ""

    @staticmethod
    def get_connection_address(resource_name: str, node_name: str) -> str:
        _check_drbd_resource_name(resource_name)
        status = _get_drbd_status(resource_name)
        if not status:
            return ""

        with _handle_drbd_json_error():
            for connection in status["connections"]:
                if connection["name"] == node_name:
                    return connection["paths"][0]["remote_host"]["address"]
        return ""

    @staticmethod
    def get_primary_address(resource_name: str) -> str:
        _check_drbd_resource_name(resource_name)
        status = _get_drbd_status(resource_name)
        if not status:
            return ""

        with _handle_drbd_json_error():
            if status["role"] == DrbdRole.PRIMARY:
                return status["connections"][0]["paths"][0]["this_host"]["address"]

            for connection in status["connections"]:
                if connection["peer-role"] == DrbdRole.PRIMARY:
                    return connection["paths"][0]["remote_host"]["address"]

        return ""

    @staticmethod
    def get_local_openers(resource_name: str, volume_number: int) -> List[DrbdOpener]:
        _check_drbd_resource_name(resource_name)
        _check_drbd_volume_number(volume_number)

        path = _get_drbd_debug_resource_openers_path(resource_name, volume_number)
        try:
            lines = path.read_text().splitlines()
        except OSError as e:
            # The resource is probably available not on this node.
            logger.info(
                "Unable to read DRBD openers of volume `%s/%d` from `%s`: `%s`.",
                resource_name, volume_number, path, e.strerror
            )
            return []

        # The opener whose opening auto-promoted the resource has its own line, with a prefix
        # (list position is not assumed).
        opener_lines = []
        auto_promoter_lines = []
        for line in lines:
            if line.startswith(_DRBD_AUTO_PROMOTER_LINE_PREFIX):
                auto_promoter_lines.append(line[len(_DRBD_AUTO_PROMOTER_LINE_PREFIX):])
            else:
                opener_lines.append(line)

        drbd_openers = _parse_drbd_opener_lines(resource_name, volume_number, opener_lines)
        auto_promoters = _parse_drbd_opener_lines(resource_name, volume_number, auto_promoter_lines, auto_promoter=True)

        for auto_promoter in auto_promoters:
            index = next((
                index for index, drbd_opener in enumerate(drbd_openers)
                if drbd_opener.pid == auto_promoter.pid and drbd_opener.process_name == auto_promoter.process_name
            ), None)
            if index is None:
                drbd_openers.append(auto_promoter)
            else:
                drbd_openers[index] = replace(drbd_openers[index], auto_promoter=True)

        return drbd_openers

    @staticmethod
    def is_healthy(resource_name: str) -> bool:
        """
        Return whether `resource_name` has its I/O not suspended and the quorum on this node, its peers all connected
        to this node, and, for each volume, its replicas holding data up to date (diskless ones apart), on this node
        and on its peers.
        """

        _check_drbd_resource_name(resource_name)
        status = _get_drbd_status(resource_name)
        if not status:
            return False

        with _handle_drbd_json_error():
            if status["suspended"] or not all(device["quorum"] for device in status["devices"]):
                return False

            connections = status["connections"]
            if any(connection["connection-state"] != DrbdConnectionState.CONNECTED for connection in connections):
                return False

            # Every replica up to date unless diskless, and at least one up to date (not all of them diskless).
            return all(
                all(replica.diskless or replica.disk_state == DrbdDiskState.UP_TO_DATE for replica in replicas) and
                any(replica.disk_state == DrbdDiskState.UP_TO_DATE for replica in replicas)
                for replicas in _get_drbd_replicas_by_volume(status, connections).values()
            )

        return False

    @staticmethod
    def is_promotable(resource_name: str) -> bool:
        """
        Return whether `resource_name` can be promoted on this node now: its I/O not suspended, the quorum on this node,
        no peer primary, and the data of each volume up to date on this node or on a connected peer (e.g. this node
        still synchronizing, or diskless). `True` if already primary on this node.
        """

        _check_drbd_resource_name(resource_name)
        status = _get_drbd_status(resource_name)
        if not status:
            return False

        with _handle_drbd_json_error():
            if (
                status["suspended"] or
                not all(device["quorum"] for device in status["devices"]) or
                any(connection["peer-role"] == DrbdRole.PRIMARY for connection in status["connections"])
            ):
                return False

            # Each volume needs its data up to date somewhere reachable: on this node, or on a peer connected to
            # it (a disconnected peer does not count, even if up to date). The local replica may be synchronizing
            # (inconsistent) or diskless.
            connected_connections = [
                connection for connection in status["connections"]
                if connection["connection-state"] == DrbdConnectionState.CONNECTED
            ]
            return all(
                any(replica.disk_state == DrbdDiskState.UP_TO_DATE for replica in replicas)
                for replicas in _get_drbd_replicas_by_volume(status, connected_connections).values()
            )

        return False

    @staticmethod
    def promote(resource_name: str) -> bool:
        return Drbd._change_role(resource_name, "primary", "promote")

    @staticmethod
    def demote(resource_name: str) -> bool:
        return Drbd._change_role(resource_name, "secondary", "demote")

    @staticmethod
    def _change_role(resource_name: str, command: str, action: str) -> bool:
        # Succeeds if already in the role; a failure is logged.
        _check_drbd_resource_name(resource_name)
        error_message = ""
        try:
            _stdout, stderr, ret_code = _run_drbdsetup_command(command, resource_name)
            if not ret_code:
                return True
            error_message = stderr
        except CommandError as e:
            error_message = e.reason
        logger.error("Failed to %s DRBD resource `%s`: `%s`.", action, resource_name, error_message)
        return False
