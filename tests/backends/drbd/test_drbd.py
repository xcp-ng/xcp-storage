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
import errno
import json
import os
from pathlib import Path
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from tests.backends.drbd import (
    _DRBD_MODULE,
    create_drbdsetup_held_open_error,
    create_drbdsetup_no_such_resource_error,
    DrbdDebugFs,
    DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE,
    DRBDSETUP_STATE_CHANGE_FAILED_EXIT_CODE,
    TEST_DRBD_MISSING_NODE_NAME,
    TEST_DRBD_PRIMARY_NODE_ADDRESS,
    TEST_DRBD_PRIMARY_NODE_NAME,
    TEST_DRBD_RESOURCE_NAME,
    TEST_DRBD_SECONDARY_NODE_ADDRESS,
    TEST_DRBD_SECONDARY_NODE_NAME,
)
from xcp_storage.backends.drbd import (
    _DRBDSETUP_TIMEOUT,
    _EXEC_PATH_DRBDSETUP,
    _get_drbd_debug_resource_openers_path,
    _get_drbd_status,
    Drbd,
    DRBD_BY_RES_PATH,
    DRBD_BY_RES_PREFIX,
    DrbdConnectionState,
    DrbdDiskState,
    DrbdOpener,
    DrbdRole,
)
import xcp_storage.log as log
from xcp_storage.utils.process import _create_failed_command_error, CommandError, CommandResult

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    Iterator,
    List,
    Sequence,
    StrPath,
    Tuple,
)

# ==============================================================================

# Resource unknown to `drbdsetup`, and its answer.
MISSING_RESOURCE_NAME: Final = "xcp-volume-frite"
MISSING_RESOURCE_STDERR: Final = create_drbdsetup_no_such_resource_error(MISSING_RESOURCE_NAME)

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_run_command() -> Iterator[MagicMock]:
    with patch(f"{_DRBD_MODULE}.run_command", autospec=True) as mock_run_command:
        yield mock_run_command

@pytest.fixture
def mock_get_process_cmdline() -> Iterator[MagicMock]:
    with patch(f"{_DRBD_MODULE}.get_process_cmdline", autospec=True) as mock_get_process_cmdline:
        yield mock_get_process_cmdline

@pytest.fixture
def drbdsetup_not_found_error(mock_run_command: MagicMock) -> CommandError:
    error = _create_failed_command_error(
        [_EXEC_PATH_DRBDSETUP],
        FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), _EXEC_PATH_DRBDSETUP),
        action="run"
    )
    mock_run_command.side_effect = error
    return error

# ------------------------------------------------------------------------------
# Helpers to change fields of a DRBD JSON status.
# ------------------------------------------------------------------------------

class DrbdJsonStatusObject(Enum):
    """
    Objects of the DRBD statuses of the fixtures (`drbd_json_status_*`), by their path
    from the resource in the JSON of `drbdsetup status --json`.
    """

    # `suspended`, `role`.
    RESOURCE = ()

    # Volumes on this node: `disk-state`, `client`, `quorum`.
    LOCAL_FIRST_VOLUME = ("devices", 0)
    LOCAL_SECOND_VOLUME = ("devices", 1)

    # The connection to the peer: `connection-state`, `peer-role`.
    CONNECTION = ("connections", 0)

    # Volumes on the peer: `peer-disk-state`, `peer-client`.
    PEER_FIRST_VOLUME = ("connections", 0, "peer_devices", 0)
    PEER_SECOND_VOLUME = ("connections", 0, "peer_devices", 1)

DrbdJsonStatusFields = Sequence[Tuple[DrbdJsonStatusObject, str, Any]]

def set_drbd_json_status_fields(mock_run_command: MagicMock, json_status: str, fields: DrbdJsonStatusFields) -> None:
    status = json.loads(json_status)
    for status_object, name, value in fields:
        json_object = status[0]
        for path_key in status_object.value:
            json_object = json_object[path_key]
        json_object[name] = value
    mock_run_command.return_value = CommandResult(stdout=json.dumps(status))

# ------------------------------------------------------------------------------

@pytest.mark.parametrize("resource_name, volume_number, expected_path", [
    ("volume", 0, DRBD_BY_RES_PATH / "volume" / "0"),
    ("res-1", 2, DRBD_BY_RES_PATH / "res-1" / "2"),
    ("volume-2", 67, DRBD_BY_RES_PATH / "volume-2" / "67")
])
def test_build_drbd_path(resource_name: str, volume_number: int, expected_path: Path) -> None:
    assert Drbd.build_path(resource_name, volume_number) == expected_path

# ------------------------------------------------------------------------------

@pytest.mark.parametrize("path, expected_name", [
    (f"{DRBD_BY_RES_PREFIX}xcp-volume-1/0", "xcp-volume-1"),
    ("../xcp-volume-2/1", "xcp-volume-2"),
    (f"{DRBD_BY_RES_PREFIX}res-1/12", "res-1"),
    (f"{DRBD_BY_RES_PREFIX}xcp-volume-1/0/extra", ""),
    (f"{DRBD_BY_RES_PREFIX}a/b/c", ""),
    ("../a/b/c", ""),
    (f"{DRBD_BY_RES_PREFIX}a/", ""),
    ("../a/", ""),
    (f"{DRBD_BY_RES_PREFIX}a/x", ""),
    (f"{DRBD_BY_RES_PREFIX}a/-1", ""),
    (f"{DRBD_BY_RES_PREFIX}a/\u0661", ""),
    (f"{DRBD_BY_RES_PREFIX}a/0/", ""),
    ("../a/0/", ""),
    ("/invalid/path/format", ""),
    (f"{DRBD_BY_RES_PATH}x/0", ""),
    (f"{DRBD_BY_RES_PREFIX}missing-volume-number", ""),
    ("../missing-volume-number", ""),
    ("", ""),
    (f"{DRBD_BY_RES_PREFIX}/0", ""),
    ("..//0", ""),
    (f"{DRBD_BY_RES_PREFIX}../0", ""),
    ("../../x/0", ""),
    ("../../../x/0", ""),
    ("../../", ""),
    (f"{DRBD_BY_RES_PREFIX}-x/0", ""),
    (f"{DRBD_BY_RES_PREFIX}.ext/0", ""),
    (f"{DRBD_BY_RES_PREFIX}a b/0", ""),
    (Drbd.build_path("res-1", 2), "res-1"),
    (Path("../xcp-volume-2/1"), "xcp-volume-2")
])
def test_get_drbd_name_from_path(path: StrPath, expected_name: str) -> None:
    assert Drbd.get_name_from_path(path) == expected_name

# ------------------------------------------------------------------------------

class TestGetDrbdStatus:
    def test_success(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)

        status = _get_drbd_status(TEST_DRBD_RESOURCE_NAME)

        assert status["name"] == TEST_DRBD_RESOURCE_NAME
        assert status["role"] == DrbdRole.PRIMARY
        mock_run_command.assert_called_once_with(
            [_EXEC_PATH_DRBDSETUP, "status", TEST_DRBD_RESOURCE_NAME, "--json"],
            simple=False,
            timeout=_DRBDSETUP_TIMEOUT
        )

    def test_command_failure(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.return_value = CommandResult(
            stdout="[]", stderr=MISSING_RESOURCE_STDERR, ret_code=DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE
        )
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(MISSING_RESOURCE_NAME) == {}
        assert (
            f"Failed to get DRBD status of resource `{MISSING_RESOURCE_NAME}`: "
            f"`{MISSING_RESOURCE_STDERR.strip()}` (exit code {DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE})."
        ) in caplog.text

    def test_command_not_found(
        self, drbdsetup_not_found_error: CommandError, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert (
            f"Failed to get DRBD status of resource `{TEST_DRBD_RESOURCE_NAME}`: `{drbdsetup_not_found_error.reason}`."
        ) in caplog.text

    @pytest.mark.parametrize("stdout", ["", "["])
    def test_malformed_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture, stdout: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=stdout)
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert f"Failed to read DRBD status of resource `{TEST_DRBD_RESOURCE_NAME}` as JSON" in caplog.text

    def test_empty_list(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.return_value = CommandResult(stdout="[]")
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert "Failed to parse DRBD configuration" in caplog.text

# ------------------------------------------------------------------------------

class TestGetDrbdConnectionAddress:
    def test_peer_address(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, drbd_json_status_secondary: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, TEST_DRBD_SECONDARY_NODE_NAME) == \
            TEST_DRBD_SECONDARY_NODE_ADDRESS

        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_secondary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, TEST_DRBD_PRIMARY_NODE_NAME) == \
            TEST_DRBD_PRIMARY_NODE_ADDRESS

    def test_unknown_node(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, TEST_DRBD_MISSING_NODE_NAME) == ""

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(
            stderr=MISSING_RESOURCE_STDERR, ret_code=DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE
        )
        assert Drbd.get_connection_address(MISSING_RESOURCE_NAME, TEST_DRBD_MISSING_NODE_NAME) == ""

# ------------------------------------------------------------------------------

class TestGetDrbdPrimaryAddress:
    def test_primary_local(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)
        assert Drbd.get_primary_address(TEST_DRBD_RESOURCE_NAME) == TEST_DRBD_PRIMARY_NODE_ADDRESS

    def test_primary_remote(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_secondary)
        assert Drbd.get_primary_address(TEST_DRBD_RESOURCE_NAME) == TEST_DRBD_PRIMARY_NODE_ADDRESS

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(
            stderr=MISSING_RESOURCE_STDERR, ret_code=DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE
        )
        assert Drbd.get_primary_address(MISSING_RESOURCE_NAME) == ""

# ------------------------------------------------------------------------------

class TestIsDrbdHealthy:
    # Healthy.
    LOCAL_CLIENT_FIELDS: Final = (
        (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
        (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "client", True)
    )
    PEER_CLIENT_FIELDS: Final = (
        (DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-disk-state", DrbdDiskState.DISKLESS),
        (DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-client", True)
    )

    # Not healthy.
    LOCAL_DETACHED_DISK_FIELDS: Final = (
        (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
    )
    PEER_DETACHED_DISK_FIELDS: Final = (
        (DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-disk-state", DrbdDiskState.DISKLESS),
    )

    @pytest.mark.parametrize("fields", [
        (),
        LOCAL_CLIENT_FIELDS,
        PEER_CLIENT_FIELDS
    ], ids=["diskful", "local-diskless", "peer-diskless"])
    def test_healthy(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdJsonStatusFields
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    @pytest.mark.parametrize("fields", [
        ((DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.OUTDATED), ),
        ((DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-disk-state", DrbdDiskState.OUTDATED), ),
        ((DrbdJsonStatusObject.CONNECTION, "connection-state", DrbdConnectionState.CONNECTING), ),
        LOCAL_DETACHED_DISK_FIELDS,
        PEER_DETACHED_DISK_FIELDS,
        (*LOCAL_CLIENT_FIELDS, *PEER_CLIENT_FIELDS),
        ((DrbdJsonStatusObject.RESOURCE, "suspended", True), ),
        ((DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "quorum", False), )
    ], ids=[
        "local-volume-outdated",
        "peer-volume-outdated",
        "peer-not-connected",
        "local-disk-detached",
        "peer-disk-detached",
        "no-disk",
        "suspended",
        "no-quorum"
    ])
    def test_not_healthy(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdJsonStatusFields
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert not Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    @pytest.mark.parametrize("fields, healthy", [
        ((
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "client", True)
        ), True),
        ((
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "client", True),
            (DrbdJsonStatusObject.PEER_SECOND_VOLUME, "peer-disk-state", DrbdDiskState.DISKLESS),
            (DrbdJsonStatusObject.PEER_SECOND_VOLUME, "peer-client", True)
        ), False),
        (((DrbdJsonStatusObject.PEER_SECOND_VOLUME, "peer-disk-state", DrbdDiskState.OUTDATED), ), False)
    ], ids=["second-volume-local-diskless", "second-volume-no-disk", "second-volume-peer-outdated"])
    def test_two_volumes(
        self,
        mock_run_command: MagicMock,
        drbd_json_status_primary_two_volumes: str,
        fields: DrbdJsonStatusFields,
        *,
        healthy: bool
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary_two_volumes, fields)
        assert Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME) == healthy

    def test_invalid_status(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        status = json.loads(drbd_json_status_primary)
        del status[0]["devices"]
        mock_run_command.return_value = CommandResult(stdout=json.dumps(status))
        assert not Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(
            stderr=MISSING_RESOURCE_STDERR, ret_code=DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE
        )
        assert not Drbd.is_healthy(MISSING_RESOURCE_NAME)

# ------------------------------------------------------------------------------

class TestGetDrbdLocalOpeners:
    def test_multi_openers(self, drbd_debug_fs: DrbdDebugFs, mock_get_process_cmdline: MagicMock) -> None:
        data: List[Dict[str, Any]] = [{
            "pid": 482584,
            "process_name": "tapback",
            "cmdline": ["tapback", "-d", "-x", "1"],
            "open_duration": 86143
        }, {
            "invalid_cmdline": "invalid_line\n"
        }, {
            "pid": 483388,
            "process_name": "python",
            "cmdline": ["storage"],
            "open_duration": 1877
        }]
        opener_data = [d for d in data if not d.get("invalid_cmdline")]

        drbd_debug_fs.write_openers(TEST_DRBD_RESOURCE_NAME, 0, "".join(
            f"{d['process_name']} {d['pid']} {d['open_duration']}\n"
            if not d.get("invalid_cmdline")
            else d["invalid_cmdline"]
            for d in data
        ))

        cmdline_mapping = {d["pid"]: d["cmdline"] for d in opener_data}
        mock_get_process_cmdline.side_effect = lambda pid: cmdline_mapping.get(pid, [])

        openers = Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0)

        assert len(openers) == len(opener_data)
        for i, expected in enumerate(opener_data):
            assert openers[i] == DrbdOpener(
                pid=expected["pid"],
                process_name=expected["process_name"],
                cmdline=expected["cmdline"],
                open_duration=expected["open_duration"],
            )

    @pytest.mark.parametrize("openers_content", [
        "tapdisk\t482584\t86143\n+tapdisk\t482584\t86143\n",
        "+tapdisk\t482584\t86143\ntapdisk\t482584\t86143\n"
    ], ids=["last", "first"])
    def test_auto_promoter_is_not_duplicated(
        self,
        drbd_debug_fs: DrbdDebugFs,
        mock_get_process_cmdline: MagicMock,
        openers_content: str
    ) -> None:
        drbd_debug_fs.write_openers(TEST_DRBD_RESOURCE_NAME, 0, openers_content)
        mock_get_process_cmdline.return_value = ["tapdisk"]

        assert Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0) == [
            DrbdOpener(pid=482584, process_name="tapdisk", cmdline=["tapdisk"], open_duration=86143, auto_promoter=True)
        ]

    @pytest.mark.parametrize("openers_content", [
        "tapdisk\t482584\t86143\n+mount\t127138\t90000\n",
        "+mount\t127138\t90000\ntapdisk\t482584\t86143\n"
    ], ids=["last", "first"])
    def test_unlisted_auto_promoter_is_added(
        self,
        drbd_debug_fs: DrbdDebugFs,
        mock_get_process_cmdline: MagicMock,
        openers_content: str
    ) -> None:
        # The auto-promoter closed the device, another opener keeps it open: DRBD still writes it.
        drbd_debug_fs.write_openers(TEST_DRBD_RESOURCE_NAME, 0, openers_content)
        mock_get_process_cmdline.return_value = []

        assert Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0) == [
            DrbdOpener(pid=482584, process_name="tapdisk", cmdline=[], open_duration=86143),
            DrbdOpener(pid=127138, process_name="mount", cmdline=[], open_duration=90000, auto_promoter=True)
        ]

    def test_invalid_auto_promoter_line_is_ignored(
        self, drbd_debug_fs: DrbdDebugFs, caplog: pytest.LogCaptureFixture
    ) -> None:
        drbd_debug_fs.write_openers(TEST_DRBD_RESOURCE_NAME, 0, "+mount\n")

        with caplog.at_level(log.WARNING):
            assert Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0) == []
        assert f"Unable to parse DRBD opener line of volume `{TEST_DRBD_RESOURCE_NAME}/0` with: `mount`." in caplog.text

    @pytest.mark.parametrize("line", [
        "python 483388 1877 extra",
        "python 483388",
        "python",
        "483388 1877",
        ""
    ])
    def test_invalid_opener_line_is_ignored(
        self, drbd_debug_fs: DrbdDebugFs, caplog: pytest.LogCaptureFixture, line: str
    ) -> None:
        drbd_debug_fs.write_openers(TEST_DRBD_RESOURCE_NAME, 0, f"{line}\n")

        with caplog.at_level(log.WARNING):
            assert Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0) == []
        assert (
            f"Unable to parse DRBD opener line of volume `{TEST_DRBD_RESOURCE_NAME}/0` with: `{line}`."
        ) in caplog.text

    @pytest.mark.usefixtures("drbd_debug_fs")
    def test_file_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        openers_path = _get_drbd_debug_resource_openers_path(TEST_DRBD_RESOURCE_NAME, 0)

        with caplog.at_level(log.INFO):
            assert Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, 0) == []
        assert (
            f"Unable to read DRBD openers of volume `{TEST_DRBD_RESOURCE_NAME}/0` from `{openers_path}`: "
            f"`{os.strerror(errno.ENOENT)}`."
        ) in caplog.text

# ------------------------------------------------------------------------------

class TestIsDrbdPromotable:
    LOCAL_SECONDARY_FIELDS: Final = ((DrbdJsonStatusObject.RESOURCE, "role", DrbdRole.SECONDARY), )

    @pytest.mark.parametrize("fields", [
        (),
        LOCAL_SECONDARY_FIELDS,
        (*LOCAL_SECONDARY_FIELDS, (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.INCONSISTENT)),
        (
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
            (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "client", True)
        ),
        (
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-disk-state", DrbdDiskState.INCONSISTENT)
        )
    ], ids=["primary", "secondary", "local-synchronizing", "local-diskless", "peer-synchronizing"])
    def test_promotable(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdJsonStatusFields
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert Drbd.is_promotable(TEST_DRBD_RESOURCE_NAME)

    @pytest.mark.parametrize("fields", [
        (
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.INCONSISTENT),
            (DrbdJsonStatusObject.PEER_FIRST_VOLUME, "peer-disk-state", DrbdDiskState.INCONSISTENT)
        ),
        (
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "disk-state", DrbdDiskState.DISKLESS),
            (DrbdJsonStatusObject.CONNECTION, "connection-state", DrbdConnectionState.CONNECTING)
        ),
        ((DrbdJsonStatusObject.RESOURCE, "suspended", True), ),
        ((DrbdJsonStatusObject.LOCAL_FIRST_VOLUME, "quorum", False), )
    ], ids=["no-up-to-date-data", "peer-not-connected", "suspended", "no-quorum"])
    def test_not_promotable(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdJsonStatusFields
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert not Drbd.is_promotable(TEST_DRBD_RESOURCE_NAME)

    @pytest.mark.parametrize("fields, promotable", [
        ((
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "disk-state", DrbdDiskState.INCONSISTENT)
        ), True),
        ((
            *LOCAL_SECONDARY_FIELDS,
            (DrbdJsonStatusObject.LOCAL_SECOND_VOLUME, "disk-state", DrbdDiskState.INCONSISTENT),
            (DrbdJsonStatusObject.PEER_SECOND_VOLUME, "peer-disk-state", DrbdDiskState.INCONSISTENT)
        ), False)
    ], ids=["second-volume-local-synchronizing", "second-volume-no-up-to-date-data"])
    def test_two_volumes(
        self,
        mock_run_command: MagicMock,
        drbd_json_status_primary_two_volumes: str,
        fields: DrbdJsonStatusFields,
        *,
        promotable: bool
    ) -> None:
        set_drbd_json_status_fields(mock_run_command, drbd_json_status_primary_two_volumes, fields)
        assert Drbd.is_promotable(TEST_DRBD_RESOURCE_NAME) == promotable

    def test_peer_primary(self, mock_run_command: MagicMock, drbd_json_status_secondary: str) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_secondary)
        assert not Drbd.is_promotable(TEST_DRBD_RESOURCE_NAME)

    def test_invalid_status(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        status = json.loads(drbd_json_status_primary)
        del status[0]["devices"]
        mock_run_command.return_value = CommandResult(stdout=json.dumps(status))
        assert not Drbd.is_promotable(TEST_DRBD_RESOURCE_NAME)

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(
            stderr=MISSING_RESOURCE_STDERR, ret_code=DRBDSETUP_NO_SUCH_RESOURCE_EXIT_CODE
        )
        assert not Drbd.is_promotable(MISSING_RESOURCE_NAME)

# ------------------------------------------------------------------------------

class TestPromoteDrbd:
    def test_command_not_found(
        self, drbdsetup_not_found_error: CommandError, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(log.INFO):
            assert not Drbd.promote(TEST_DRBD_RESOURCE_NAME)
        assert (
            f"Failed to promote DRBD resource `{TEST_DRBD_RESOURCE_NAME}`: `{drbdsetup_not_found_error.reason}`."
        ) in caplog.text

    def test_primary_on_another_node(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        stderr = f"{TEST_DRBD_RESOURCE_NAME}: State change failed: (-1) Multiple primaries not allowed by config\n"
        mock_run_command.return_value = CommandResult(stderr=stderr, ret_code=DRBDSETUP_STATE_CHANGE_FAILED_EXIT_CODE)
        with caplog.at_level(log.INFO):
            assert not Drbd.promote(TEST_DRBD_RESOURCE_NAME)
        assert f"Failed to promote DRBD resource `{TEST_DRBD_RESOURCE_NAME}`: `{stderr}`." in caplog.text

class TestDemoteDrbd:
    def test_command_not_found(
        self, drbdsetup_not_found_error: CommandError, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(log.INFO):
            assert not Drbd.demote(TEST_DRBD_RESOURCE_NAME)
        assert (
            f"Failed to demote DRBD resource `{TEST_DRBD_RESOURCE_NAME}`: `{drbdsetup_not_found_error.reason}`."
        ) in caplog.text

    def test_demote_drbd_open_on_another_node(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        stderr = (
            f"{create_drbdsetup_held_open_error(TEST_DRBD_RESOURCE_NAME)}"
            "additional info from kernel:\n"
            "/dev/drbd1261 open_ro_cnt:0, open_rw_cnt:2; list of openers follows\n"
            "drbd1261 opened by python (pid 483388) at 2026-06-30 21:15:38.690\n"
            "drbd1261 opened by python (pid 482584) at 2026-06-30 21:14:14.425\n"
        )
        mock_run_command.return_value = CommandResult(stderr=stderr, ret_code=DRBDSETUP_STATE_CHANGE_FAILED_EXIT_CODE)

        with caplog.at_level(log.INFO):
            assert not Drbd.demote(TEST_DRBD_RESOURCE_NAME)
        assert f"Failed to demote DRBD resource `{TEST_DRBD_RESOURCE_NAME}`: `{stderr}`." in caplog.text

# ------------------------------------------------------------------------------

# Resource names and volume numbers can come from an RPC call or external stack: types are not checked at runtime.
# So we test different situations.
@pytest.mark.usefixtures("drbd_debug_fs")
class TestInvalidDrbdArguments:
    INVALID_RESOURCE_NAMES: Final = (
        "", ".", "..", "../x", "x/../y", "a/b", "/abs", "a b", "a\n", "a\x00b", "\u00e9", "-x", "--param", ".ext"
    )
    NOT_RESOURCE_NAMES: Final = (None, 1, b"res")

    INVALID_VOLUME_NUMBERS: Final = (-1, -42)
    NOT_VOLUME_NUMBERS: Final = ("0", "0/../../x", 1.5, True, False, None)

    @pytest.mark.parametrize("resource_name, message", [
        *((name, "Invalid DRBD resource name") for name in INVALID_RESOURCE_NAMES),
        *((name, "Not a DRBD resource name") for name in NOT_RESOURCE_NAMES)
    ])
    def test_invalid_resource_name(
        self,
        mock_run_command: MagicMock,
        resource_name: Any, # noqa: ANN401
        message: str
    ) -> None:
        for call in (
            lambda: Drbd.build_path(resource_name, 0),
            lambda: Drbd.get_connection_address(resource_name, TEST_DRBD_MISSING_NODE_NAME),
            lambda: Drbd.get_primary_address(resource_name),
            lambda: Drbd.get_local_openers(resource_name, 0),
            lambda: Drbd.is_healthy(resource_name),
            lambda: Drbd.is_promotable(resource_name),
            lambda: Drbd.promote(resource_name),
            lambda: Drbd.demote(resource_name)
        ):
            with pytest.raises(ValueError, match=message):
                call()

        mock_run_command.assert_not_called()

    @pytest.mark.parametrize("volume_number, message", [
        *((number, "Invalid DRBD volume number") for number in INVALID_VOLUME_NUMBERS),
        *((number, "Not a DRBD volume number") for number in NOT_VOLUME_NUMBERS)
    ])
    def test_invalid_volume_number(
        self,
        mock_run_command: MagicMock,
        volume_number: Any, # noqa: ANN401
        message: str
    ) -> None:
        for call in (
            lambda: Drbd.build_path(TEST_DRBD_RESOURCE_NAME, volume_number),
            lambda: Drbd.get_local_openers(TEST_DRBD_RESOURCE_NAME, volume_number)
        ):
            with pytest.raises(ValueError, match=message):
                call()

        mock_run_command.assert_not_called()
