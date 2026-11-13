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
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from tests.backends.drbd import (
    DrbdDebugFs,
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
from xcp_storage.utils.process import CommandResult

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

_DRBD_MODULE: Final = Drbd.__module__

# ------------------------------------------------------------------------------

@pytest.fixture
def mock_run_command() -> Iterator[MagicMock]:
    with patch(f"{_DRBD_MODULE}.run_command", autospec=True) as mock_run_command:
        yield mock_run_command

@pytest.fixture
def mock_get_process_cmdline() -> Iterator[MagicMock]:
    with patch(f"{_DRBD_MODULE}.get_process_cmdline", autospec=True) as mock_get_process_cmdline:
        yield mock_get_process_cmdline

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
            stdout="[]", stderr="xcp-volume-frite: No such resource\n", ret_code=10
        )
        with caplog.at_level(log.INFO):
            assert _get_drbd_status("xcp-volume-frite") == {}
        assert (
            "Failed to get DRBD status of resource `xcp-volume-frite`: "
            "`xcp-volume-frite: No such resource` (exit code 10)."
        ) in caplog.text

    def test_command_not_found(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.side_effect = FileNotFoundError(2, "No such file or directory", _EXEC_PATH_DRBDSETUP)
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert (
            "Failed to get DRBD status of resource `xcp-volume-patate`: "
            f"`[Errno 2] No such file or directory: '{_EXEC_PATH_DRBDSETUP}'`."
        ) in caplog.text

    @pytest.mark.parametrize("stdout", ["", "["])
    def test_malformed_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture, stdout: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=stdout)
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert "Failed to read DRBD status of resource `xcp-volume-patate` as JSON" in caplog.text

    def test_empty_list(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.return_value = CommandResult(stdout="[]")
        with caplog.at_level(log.INFO):
            assert _get_drbd_status(TEST_DRBD_RESOURCE_NAME) == {}
        assert "Failed to parse DRBD configuration" in caplog.text

# ------------------------------------------------------------------------------

class TestGetDrbdConnectionAddress:
    def test_connection_address_a(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, TEST_DRBD_SECONDARY_NODE_NAME) == \
            TEST_DRBD_SECONDARY_NODE_ADDRESS

    def test_connection_address_b(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: str
    ) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_secondary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, TEST_DRBD_PRIMARY_NODE_NAME) == \
            TEST_DRBD_PRIMARY_NODE_ADDRESS

    def test_unknown_node(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        mock_run_command.return_value = CommandResult(stdout=drbd_json_status_primary)
        assert Drbd.get_connection_address(TEST_DRBD_RESOURCE_NAME, "sr123-s67") == ""

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(stderr="xcp-volume-frite: No such resource\n", ret_code=10)
        assert Drbd.get_connection_address("xcp-volume-frite", TEST_DRBD_SECONDARY_NODE_NAME) == ""

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
        mock_run_command.return_value = CommandResult(stderr="xcp-volume-frite: No such resource\n", ret_code=10)
        assert Drbd.get_primary_address("xcp-volume-frite") == ""

# ------------------------------------------------------------------------------

# Fields to set in a DRBD status: path of their object in the status, name and value of each field.
DrbdStatusFields = Sequence[Tuple[Tuple[Any, ...], str, Any]]

class TestIsDrbdHealthy:
    RESOURCE_PATH: Final = ()
    LOCAL_VOLUME_PATH: Final = ("devices", 0)
    CONNECTION_PATH: Final = ("connections", 0)
    PEER_VOLUME_PATH: Final = ("connections", 0, "peer_devices", 0)

    # Healthy.
    LOCAL_CLIENT_FIELDS: Final = (
        (LOCAL_VOLUME_PATH, "disk-state", DrbdDiskState.DISKLESS),
        (LOCAL_VOLUME_PATH, "client", True)
    )
    PEER_CLIENT_FIELDS: Final = (
        (PEER_VOLUME_PATH, "peer-disk-state", DrbdDiskState.DISKLESS),
        (PEER_VOLUME_PATH, "peer-client", True)
    )

    # Not healthy.
    LOCAL_DETACHED_DISK_FIELDS: Final = (
        (LOCAL_VOLUME_PATH, "disk-state", DrbdDiskState.DISKLESS),
    )
    PEER_DETACHED_DISK_FIELDS: Final = (
        (PEER_VOLUME_PATH, "peer-disk-state", DrbdDiskState.DISKLESS),
    )

    @staticmethod
    def set_status_fields(mock_run_command: MagicMock, status_json: str, fields: DrbdStatusFields) -> None:
        status = json.loads(status_json)
        for path, name, value in fields:
            status_object = status[0]
            for path_key in path:
                status_object = status_object[path_key]
            status_object[name] = value
        mock_run_command.return_value = CommandResult(stdout=json.dumps(status))

    @pytest.mark.parametrize("fields", [
        (),
        LOCAL_CLIENT_FIELDS,
        PEER_CLIENT_FIELDS
    ], ids=["diskful", "local-diskless", "peer-diskless"])
    def test_healthy(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdStatusFields
    ) -> None:
        self.set_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    @pytest.mark.parametrize("fields", [
        ((LOCAL_VOLUME_PATH, "disk-state", DrbdDiskState.OUTDATED), ),
        ((PEER_VOLUME_PATH, "peer-disk-state", DrbdDiskState.OUTDATED), ),
        ((CONNECTION_PATH, "connection-state", DrbdConnectionState.CONNECTING), ),
        LOCAL_DETACHED_DISK_FIELDS,
        PEER_DETACHED_DISK_FIELDS,
        (*LOCAL_CLIENT_FIELDS, *PEER_CLIENT_FIELDS),
        ((RESOURCE_PATH, "suspended", True), ),
        ((LOCAL_VOLUME_PATH, "quorum", False), )
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
        self, mock_run_command: MagicMock, drbd_json_status_primary: str, fields: DrbdStatusFields
    ) -> None:
        self.set_status_fields(mock_run_command, drbd_json_status_primary, fields)
        assert not Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    def test_invalid_status(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        status = json.loads(drbd_json_status_primary)
        del status[0]["devices"]
        mock_run_command.return_value = CommandResult(stdout=json.dumps(status))

        assert not Drbd.is_healthy(TEST_DRBD_RESOURCE_NAME)

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult(stderr="xcp-volume-frite: No such resource\n", ret_code=10)
        assert not Drbd.is_healthy("xcp-volume-frite")

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

        drbd_debug_fs.write_openers("res-test", 0, "".join(
            f"{d['process_name']} {d['pid']} {d['open_duration']}\n"
            if not d.get("invalid_cmdline")
            else d["invalid_cmdline"]
            for d in data
        ))

        cmdline_mapping = {d["pid"]: d["cmdline"] for d in opener_data}
        mock_get_process_cmdline.side_effect = lambda pid: cmdline_mapping.get(pid, [])

        openers = Drbd.get_local_openers("res-test", 0)

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
        drbd_debug_fs.write_openers("res-test", 0, f"{line}\n")

        with caplog.at_level(log.WARNING):
            assert Drbd.get_local_openers("res-test", 0) == []
        assert f"Unable to parse DRBD opener line of volume `res-test/0` with: `{line}`." in caplog.text

    @pytest.mark.usefixtures("drbd_debug_fs")
    def test_file_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        openers_path = _get_drbd_debug_resource_openers_path("res-test", 0)

        with caplog.at_level(log.INFO):
            assert Drbd.get_local_openers("res-test", 0) == []
        assert (
            "Unable to get DRBD openers of volume `res-test/0`: "
            f"`[Errno 2] No such file or directory: '{openers_path}'`."
        ) in caplog.text

# ------------------------------------------------------------------------------

class TestDemoteDrbd:
    def test_success(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = CommandResult()
        assert Drbd.demote("res-test")

    def test_command_not_found(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.side_effect = FileNotFoundError(2, "No such file or directory", _EXEC_PATH_DRBDSETUP)
        with caplog.at_level(log.INFO):
            assert not Drbd.demote("res-test")
        assert (
            "Failed to demote DRBD resource `res-test`: "
            f"`[Errno 2] No such file or directory: '{_EXEC_PATH_DRBDSETUP}'`."
        ) in caplog.text

    def test_demote_drbd_open_on_another_node(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        stderr = (
            "xcp-volume-ad084d58-c12b-42df-affa-8cda2321580b: State change failed: "
            "(-12) Device is held open by someone\n"
            "additional info from kernel:\n"
            "/dev/drbd1261 open_ro_cnt:0, open_rw_cnt:2; list of openers follows\n"
            "drbd1261 opened by python (pid 483388) at 2026-06-30 21:15:38.690\n"
            "drbd1261 opened by python (pid 482584) at 2026-06-30 21:14:14.425\n"
        )
        mock_run_command.return_value = CommandResult(stderr=stderr, ret_code=11)

        with caplog.at_level(log.INFO):
            assert not Drbd.demote("res-test")
        assert f"Failed to demote DRBD resource `res-test`: `{stderr}`." in caplog.text

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
            lambda: Drbd.get_connection_address(resource_name, TEST_DRBD_SECONDARY_NODE_NAME),
            lambda: Drbd.get_primary_address(resource_name),
            lambda: Drbd.get_local_openers(resource_name, 0),
            lambda: Drbd.is_healthy(resource_name),
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
