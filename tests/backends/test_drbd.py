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

from pathlib import Path
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from xcp_storage.backends.drbd import (
    _get_drbd_status,
    Drbd,
    DrbdOpener,
)

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    List,
)

# ==============================================================================

@pytest.mark.parametrize("resource_name, volume_number, expected_path", [
    ("volume", 0, "/dev/drbd/by-res/volume/0"),
    ("res-1", 2, "/dev/drbd/by-res/res-1/2"),
    ("volume-2", 67, "/dev/drbd/by-res/volume-2/67")
])
def test_build_drbd_path(resource_name: str, volume_number: int, expected_path: str) -> None:
    assert Drbd.build_path(resource_name, volume_number) == expected_path

# ------------------------------------------------------------------------------

@pytest.mark.parametrize("path, expected_name", [
    ("/dev/drbd/by-res/xcp-volume-1/0", "xcp-volume-1"),
    ("../xcp-volume-2/1", "xcp-volume-2"),
    ("/dev/drbd/by-res/res-1/12", "res-1"),
    ("/dev/drbd/by-res/xcp-volume-1/0/extra", ""),
    ("/dev/drbd/by-res/a/b/c", ""),
    ("../a/b/c", ""),
    ("/dev/drbd/by-res/a/", ""),
    ("../a/", ""),
    ("/dev/drbd/by-res/a/x", ""),
    ("/dev/drbd/by-res/a/-1", ""),
    ("/dev/drbd/by-res/a/0/", ""),
    ("../a/0/", ""),
    ("/invalid/path/format", ""),
    ("/dev/drbd/by-res/missing-volume-number", ""),
    ("../missing-volume-number", ""),
    ("", ""),
    ("/dev/drbd/by-res//0", ""),
    ("..//0", ""),
    ("/dev/drbd/by-res/../0", ""),
    ("../../x/0", ""),
    ("../../../x/0", ""),
    ("../../", ""),
    ("/dev/drbd/by-res/-x/0", ""),
    ("/dev/drbd/by-res/.ext/0", ""),
    ("/dev/drbd/by-res/a b/0", "")
])
def test_get_drbd_name_from_path(path: str, expected_name: str) -> None:
    assert Drbd.get_name_from_path(path) == expected_name

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestGetDrbdStatus:
    def test_success(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)

        status = _get_drbd_status("xcp-volume-patate")

        assert status["name"] == "xcp-volume-patate"
        assert status["role"] == "Primary"
        mock_run_command.assert_called_once_with(
            ["/usr/sbin/drbdsetup", "status", "xcp-volume-patate", "--json"], simple=False
        )

    def test_command_failure(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.return_value = ("[]", "xcp-volume-frite: No such resource\n", 10)
        with caplog.at_level("INFO"):
            assert _get_drbd_status("xcp-volume-frite") == {}
        assert (
            "Failed to get DRBD status of resource `xcp-volume-frite`: "
            "`xcp-volume-frite: No such resource` (exit code 10)."
        ) in caplog.text

    def test_command_not_found(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.side_effect = FileNotFoundError(2, "No such file or directory", "/usr/sbin/drbdsetup")
        with caplog.at_level("INFO"):
            assert _get_drbd_status("xcp-volume-patate") == {}
        assert (
            "Failed to get DRBD status of resource `xcp-volume-patate`: "
            "`[Errno 2] No such file or directory: '/usr/sbin/drbdsetup'`."
        ) in caplog.text

    @pytest.mark.parametrize("stdout", ["", "["])
    def test_malformed_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture, stdout: str
    ) -> None:
        mock_run_command.return_value = (stdout, "", 0)
        with caplog.at_level("INFO"):
            assert _get_drbd_status("xcp-volume-patate") == {}
        assert "Failed to read DRBD status of resource `xcp-volume-patate` as JSON" in caplog.text

    def test_empty_list(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.return_value = ("[]", "", 0)
        with caplog.at_level("INFO"):
            assert _get_drbd_status("xcp-volume-patate") == {}
        assert "Failed to parse DRBD configuration" in caplog.text

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestGetDrbdConnectionAddress:
    def test_connection_address_a(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s1") == "10.10.0.12"

    def test_connection_address_b(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: str
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_secondary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s2") == "10.10.0.13"

    def test_unknown_node(self, mock_run_command: MagicMock, drbd_json_status_primary: str) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s67") == ""

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = ("", "xcp-volume-frite: No such resource\n", 10)
        assert Drbd.get_connection_address("xcp-volume-frite", "sr123-s1") == ""

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestGetDrbdPrimaryAddress:
    def test_primary_local(
        self, mock_run_command: MagicMock, drbd_json_status_primary: str
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_primary_address("xcp-volume-patate") == "10.10.0.13"

    def test_primary_remote(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: str
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_secondary, "", 0)
        assert Drbd.get_primary_address("xcp-volume-patate") == "10.10.0.13"

    def test_status_error(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = ("", "xcp-volume-frite: No such resource\n", 10)
        assert Drbd.get_primary_address("xcp-volume-frite") == ""

# ------------------------------------------------------------------------------

@patch.object(Path, "read_text")
class TestGetDrbdLocalOpeners:
    @patch("xcp_storage.backends.drbd.get_process_cmdline")
    def test_multi_openers(self, mock_get_cmdline: MagicMock, mock_read_text: MagicMock) -> None:
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

        mock_read_text.return_value = "".join(
            f"{d['process_name']} {d['pid']} {d['open_duration']}\n"
            if not d.get("invalid_cmdline")
            else d["invalid_cmdline"]
            for d in data
        )

        cmdline_mapping = {d["pid"]: d["cmdline"] for d in opener_data}
        mock_get_cmdline.side_effect = lambda pid: cmdline_mapping.get(pid, [])

        openers = Drbd.get_local_openers("res-test", 0)

        assert len(openers) == len(opener_data)
        for i, expected in enumerate(opener_data):
            assert openers[i] == DrbdOpener(
                pid=expected["pid"],
                process_name=expected["process_name"],
                cmdline=expected["cmdline"],
                open_duration=expected["open_duration"],
            )

    @pytest.mark.parametrize("line", [
        "python 483388 1877 extra",
        "python 483388",
        "python",
        "483388 1877",
        ""
    ])
    def test_invalid_opener_line_is_ignored(
        self, mock_read_text: MagicMock, caplog: pytest.LogCaptureFixture, line: str
    ) -> None:
        mock_read_text.return_value = f"{line}\n"

        with caplog.at_level("WARNING"):
            assert Drbd.get_local_openers("res-test", 0) == []
        assert f"Unable to parse DRBD opener line of volume `res-test/0` with: `{line}`." in caplog.text

    def test_file_not_found(
        self, mock_read_text: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        openers_path = "/sys/kernel/debug/drbd/resources/res-test/volumes/0/openers"
        mock_read_text.side_effect = FileNotFoundError(
            2,
            "No such file or directory",
            openers_path
        )
        with caplog.at_level("INFO"):
            assert Drbd.get_local_openers("res-test", 0) == []
        assert (
            "Unable to get DRBD openers of volume `res-test/0`: "
            f"`[Errno 2] No such file or directory: '{openers_path}'`."
        ) in caplog.text

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestDemoteDrbd:
    def test_success(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = ("", "", 0)
        assert Drbd.demote("res-test")

    def test_command_not_found(self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        mock_run_command.side_effect = FileNotFoundError(2, "No such file or directory", "/usr/sbin/drbdsetup")
        with caplog.at_level("INFO"):
            assert not Drbd.demote("res-test")
        assert (
            "Failed to demote DRBD resource `res-test`: "
            "`[Errno 2] No such file or directory: '/usr/sbin/drbdsetup'`."
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
        mock_run_command.return_value = ("", stderr, 11)

        with caplog.at_level("INFO"):
            assert not Drbd.demote("res-test")
        assert f"Failed to demote DRBD resource `res-test`: `{stderr}`." in caplog.text

# ------------------------------------------------------------------------------

# Resource names and volume numbers can come from an RPC call or external stack: types are not checked at runtime.
# So we test different situations.
@patch.object(Path, "read_text")
@patch("xcp_storage.backends.drbd.run_command")
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
        mock_read_text: MagicMock,
        resource_name: Any, # noqa: ANN401
        message: str
    ) -> None:
        for call in (
            lambda: Drbd.build_path(resource_name, 0),
            lambda: Drbd.get_connection_address(resource_name, "sr123-s1"),
            lambda: Drbd.get_primary_address(resource_name),
            lambda: Drbd.get_local_openers(resource_name, 0),
            lambda: Drbd.demote(resource_name)
        ):
            with pytest.raises(ValueError, match=message):
                call()

        mock_run_command.assert_not_called()
        mock_read_text.assert_not_called()

    @pytest.mark.parametrize("volume_number, message", [
        *((number, "Invalid DRBD volume number") for number in INVALID_VOLUME_NUMBERS),
        *((number, "Not a DRBD volume number") for number in NOT_VOLUME_NUMBERS)
    ])
    def test_invalid_volume_number(
        self,
        mock_run_command: MagicMock,
        mock_read_text: MagicMock,
        volume_number: Any, # noqa: ANN401
        message: str
    ) -> None:
        for call in (
            lambda: Drbd.build_path("res-test", volume_number),
            lambda: Drbd.get_local_openers("res-test", volume_number)
        ):
            with pytest.raises(ValueError, match=message):
                call()

        mock_run_command.assert_not_called()
        mock_read_text.assert_not_called()
