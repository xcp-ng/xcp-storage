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
from xcp_storage.rpc.client import RpcApiClient
from xcp_storage.utils.json import JsonDict
from xcp_storage.utils.process import (
    get_process_cmdline,
    run_command,
)

from xcp_storage.typing import (
    Any,
    cast,
    Dict,
    Final,
    Iterator,
    List,
    override,
    Tuple,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

DRBD_BY_RES_PATH: Final = "/dev/drbd/by-res/"

DRBD_PORT_RANGE: Final = (7000, 8000)

# ------------------------------------------------------------------------------

_EXEC_PATH_DRBDSETUP: Final = "/usr/sbin/drbdsetup"

_REGEX_DRBD_OPENER_LINE: Final = re.compile(r"(.*)\s+([0-9]+)\s+([0-9]+)")

# ------------------------------------------------------------------------------

@contextlib.contextmanager
def _handle_drbd_json_error() -> Iterator[None]:
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
        stdout, _stderr, ret_code = run_command([
            _EXEC_PATH_DRBDSETUP, "status", resource_name, "--json"
        ], simple=False)
        if ret_code != 0:
             return {}
    except Exception as e:
        logger.error("Failed to get DRBD status: `%s`.", e)
        return {}

    try:
        status = json.loads(stdout)
    except Exception as e:
        logger.error("Failed to read DRBD status as JSON: `%s`.", e)
        return {}

    with _handle_drbd_json_error():
        return status[0]
    return {}

# ------------------------------------------------------------------------------

@dataclass
class DrbdOpener:
    pid: int
    process_name: str
    cmdline: List[str]
    # The duration is expressed in milliseconds.
    open_duration: int

@dataclass
class DrbdVolumeSpecifier:
    resource_name: str
    volume_number: int

    @staticmethod
    def parse(specifier_str: str) -> "DrbdVolumeSpecifier":
        """
        Parses a DRBD volume specifier string.

        Expected format: `<resource_name>/<volume_number>`
        """
        try:
            resource_name, volume_number = specifier_str.rsplit("/", 1)
            if not resource_name:
                raise ValueError

            return DrbdVolumeSpecifier(resource_name, int(volume_number))
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid volume specifier: `{specifier_str}`. "
                "Expected format: `<resource_name>/<volume_number>`."
            ) from None

    @override
    def __str__(self) -> str:
        return f"{self.resource_name}/{self.volume_number}"

@dataclass
class DrbdRemoteOpener:
    opener: DrbdOpener
    volume_specifier: DrbdVolumeSpecifier
    peer_address: Tuple[str, int]

# ------------------------------------------------------------------------------

class Drbd:
    @staticmethod
    def build_path(resource_name: str, volume_number: int) -> str:
        return f"{DRBD_BY_RES_PATH}{resource_name}/{volume_number}"

    @staticmethod
    def get_name_from_path(path: str) -> str:
        # Assume that we have a path like this:
        # - "/dev/drbd/by-res/xcp-volume-<UUID>/0"
        # - "../xcp-volume-<UUID>/0"
        if path.startswith(DRBD_BY_RES_PATH):
            prefix_len = len(DRBD_BY_RES_PATH)
        elif path.startswith("../"):
            prefix_len = 3
        else:
            return ""

        res_name_end = path.find("/", prefix_len)
        if res_name_end == -1:
            return ""

        return path[prefix_len:res_name_end]

    @staticmethod
    def get_connection_address(resource_name: str, node_name: str) -> str:
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
        assert resource_name, "Cannot get DRBD openers without resource name."

        path = Path(f"/sys/kernel/debug/drbd/resources/{resource_name}/volumes/{volume_number}/openers")
        try:
            lines = path.read_text().splitlines()
        except Exception as e:
            # The resource is probably available not on this node.
            logger.info("Unable to get DRBD openers of volume `%s/%d`: `%s`.", resource_name, volume_number, e)
            return []

        drbd_openers = []
        for line in lines:
            match = _REGEX_DRBD_OPENER_LINE.match(line)
            if not match:
                logger.warning("Unable to parse DRBD opener line with: `%s`.", line)
                continue

            groups = match.groups()
            pid = int(groups[1])
            drbd_openers.append(DrbdOpener(
                pid=pid,
                process_name=groups[0],
                # Note: `cmdline`` is empty for `mount` calls. Logic the PID is dead.
                cmdline=get_process_cmdline(pid),
                open_duration=int(groups[2])
            ))

        return drbd_openers

    @staticmethod
    def get_openers(
        peer_addresses: List[Tuple[str, int]],
        volume_specifiers: List[DrbdVolumeSpecifier]
    ) -> List[DrbdRemoteOpener]:
        # Need to import here to avoid a circular dependency.
        import xcp_storage.rpc.api as api

        drbd_openers: List[DrbdRemoteOpener] = []

        for addr in peer_addresses:
            rpc_client = RpcApiClient(addr[0], addr[1])
            response = rpc_client.call_api(
                api.drbd.get_openers_from_specifiers,
                volume_specifiers=[str(volume_specifier) for volume_specifier in volume_specifiers]
            )

            for volume_specifier_str, openers in response.items():
                volume_specifier = DrbdVolumeSpecifier.parse(volume_specifier_str)

                drbd_openers.extend(DrbdRemoteOpener(
                    opener=DrbdOpener(**cast(Dict[str, Any], opener_json)),
                    volume_specifier=volume_specifier,
                    peer_address=addr
                ) for opener_json in cast(List[JsonDict], openers))

        return drbd_openers

    @staticmethod
    def demote(resource_name: str) -> bool:
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
