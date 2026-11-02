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
from dataclasses import dataclass
import json
from pathlib import Path
import re

import xcp_storage.log as log
from xcp_storage.utils.process import (
    get_process_cmdline,
    run_command,
)

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    Iterator,
    List,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

DRBD_BY_RES_PATH: Final = "/dev/drbd/by-res/"

DRBD_PORT_RANGE: Final = (7000, 8000)

# ------------------------------------------------------------------------------

_EXEC_PATH_DRBDSETUP: Final = "/usr/sbin/drbdsetup"

_REGEX_DRBD_OPENER_LINE: Final = re.compile(r"(.*)\s+(\d+)\s+(\d+)")

# Characters allowed in a resource name: ASCII only, and neither a path separator nor a leading `-` or `.`.
_REGEX_DRBD_RESOURCE_NAME: Final = re.compile(r"\w[\w.-]*", re.ASCII)

# ------------------------------------------------------------------------------

# Because this module can be used by external layers and RPC, we must have checkers
# to prevent code injection.

def _check_drbd_resource_name(resource_name: str) -> None:
    if not isinstance(resource_name, str):
        raise ValueError(f"Not a DRBD resource name: `{resource_name}`.")
    if not _REGEX_DRBD_RESOURCE_NAME.fullmatch(resource_name):
        raise ValueError(f"Invalid DRBD resource name: `{resource_name}`.")

def _check_drbd_volume_number(volume_number: int) -> None:
    if not isinstance(volume_number, int) or isinstance(volume_number, bool):
        raise ValueError(f"Not a DRBD volume number: `{volume_number}`.")
    if volume_number < 0:
        raise ValueError(f"Invalid DRBD volume number: `{volume_number}`.")

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

def _get_drbd_status(resource_name: str) -> Dict[str, Any]:
    try:
        stdout, stderr, ret_code = run_command([
            _EXEC_PATH_DRBDSETUP, "status", resource_name, "--json"
        ], simple=False)
        if ret_code != 0:
            logger.warning(
                "Failed to get DRBD status of resource `%s`: `%s` (exit code %d).",
                resource_name, stderr.strip(), ret_code
            )
            return {}
    except Exception as e:
        logger.error("Failed to get DRBD status of resource `%s`: `%s`.", resource_name, e)
        return {}

    try:
        status = json.loads(stdout)
    except Exception as e:
        logger.error("Failed to read DRBD status of resource `%s` as JSON: `%s`.", resource_name, e)
        return {}

    with _handle_drbd_json_error():
        return status[0]
    return {}

# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class DrbdOpener:
    pid: int
    process_name: str
    cmdline: List[str]
    # The duration is expressed in milliseconds.
    open_duration: int

# ------------------------------------------------------------------------------

class Drbd:
    @staticmethod
    def build_path(resource_name: str, volume_number: int) -> str:
        _check_drbd_resource_name(resource_name)
        _check_drbd_volume_number(volume_number)
        return f"{DRBD_BY_RES_PATH}{resource_name}/{volume_number}"

    @staticmethod
    def get_name_from_path(path: str) -> str:
        # Assume that we have a path like this:
        # - "/dev/drbd/by-res/<NAME>/0"
        # - "../<NAME>/0"
        if path.startswith(DRBD_BY_RES_PATH):
            prefix_len = len(DRBD_BY_RES_PATH)
        elif path.startswith("../"):
            prefix_len = 3
        else:
            return ""

        res_name_end = path.find("/", prefix_len)
        if res_name_end == -1:
            return ""

        resource_name = path[prefix_len:res_name_end]
        if _REGEX_DRBD_RESOURCE_NAME.fullmatch(resource_name) and path[res_name_end + 1:].isdecimal():
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
            if status["role"] == "Primary":
                return status["connections"][0]["paths"][0]["this_host"]["address"]

            for connection in status["connections"]:
                if connection["peer-role"] == "Primary":
                    return connection["paths"][0]["remote_host"]["address"]

        return ""

    @staticmethod
    def get_local_openers(resource_name: str, volume_number: int) -> List[DrbdOpener]:
        _check_drbd_resource_name(resource_name)
        _check_drbd_volume_number(volume_number)

        path = Path(f"/sys/kernel/debug/drbd/resources/{resource_name}/volumes/{volume_number}/openers")
        try:
            lines = path.read_text().splitlines()
        except Exception as e:
            # The resource is probably available not on this node.
            logger.info("Unable to get DRBD openers of volume `%s/%d`: `%s`.", resource_name, volume_number, e)
            return []

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
                open_duration=int(groups[2])
            ))

        return drbd_openers

    @staticmethod
    def demote(resource_name: str) -> bool:
        _check_drbd_resource_name(resource_name)
        error_message = ""
        try:
            _stdout, stderr, ret_code = run_command([_EXEC_PATH_DRBDSETUP, "secondary", resource_name], simple=False)
            if not ret_code:
                return True
            error_message = stderr
        except Exception as e:
            error_message = str(e)
        logger.error("Failed to demote DRBD resource `%s`: `%s`.", resource_name, error_message)
        return False
