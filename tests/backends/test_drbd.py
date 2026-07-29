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

import copy
from pathlib import Path
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from xcp_storage.backends.drbd import (
    Drbd,
    DrbdOpener,
    DrbdRemoteOpener,
    DrbdVolumeSpecifier,
)
from xcp_storage.network.tcp_client import TcpClientError
from xcp_storage.rpc.server import RpcApiServer
from xcp_storage.utils.json.rpc.client import JsonRpcClient

from xcp_storage.typing import (
    Any,
    Dict,
    Final,
    List,
    Tuple,
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
    ("/invalid/path/format", ""),
    ("/dev/drbd/by-res/missing-volume-number", ""),
    ("../missing-volume-number", "")
])
def test_get_drbd_name_from_path(path: str, expected_name: str) -> None:
    assert Drbd.get_name_from_path(path) == expected_name

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestGetDrbdConnectionAddress:
    def test_connection_address_a(
        self, mock_run_command: MagicMock, drbd_json_status_primary: MagicMock
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s1") == "10.10.0.12"

    def test_connection_address_b(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: MagicMock
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_secondary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s2") == "10.10.0.13"

    def test_invalid_resource_with_valid_json(
        self, mock_run_command: MagicMock, drbd_json_status_primary: MagicMock
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s67") == ""

    def test_valid_resource_with_invalid_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run_command.return_value = ("[]", "", 0)
        with caplog.at_level("INFO"):
            assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s1") == ""
            assert "Failed to parse DRBD configuration" in caplog.text

    def test_valid_resource_with_malformed_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run_command.return_value = ("[", "", 0)
        with caplog.at_level("INFO"):
            assert Drbd.get_connection_address("xcp-volume-patate", "sr123-s1") == ""
            assert "Failed to read DRBD status as JSON" in caplog.text

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestGetDrbdPrimaryAddress:
    def test_primary_local(
        self, mock_run_command: MagicMock, drbd_json_status_primary: MagicMock
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_primary, "", 0)
        assert Drbd.get_primary_address("xcp-volume-patate") == "10.10.0.13"

    def test_primary_remote(
        self, mock_run_command: MagicMock, drbd_json_status_secondary: MagicMock
    ) -> None:
        mock_run_command.return_value = (drbd_json_status_secondary, "", 0)
        assert Drbd.get_primary_address("xcp-volume-patate") == "10.10.0.13"

    def test_invalid_resource_with_valid_json(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = ("[]", "xcp-volume-frite: No such resource", 10)
        assert Drbd.get_primary_address("xcp-volume-frite") == ""

    def test_valid_resource_with_invalid_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run_command.return_value = ("[]", "", 0)
        with caplog.at_level("INFO"):
            assert Drbd.get_primary_address("xcp-volume-patate") == ""
            assert "Failed to parse DRBD configuration" in caplog.text

    def test_valid_resource_with_malformed_json(
        self, mock_run_command: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run_command.return_value = ("[", "", 0)
        with caplog.at_level("INFO"):
            assert Drbd.get_primary_address("xcp-volume-patate") == ""
            assert "Failed to read DRBD status as JSON" in caplog.text

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

class TestDrbdVolumeSpecifier:
    def test_parse_ok(self) -> None:
        volume_specifier = DrbdVolumeSpecifier.parse("res-test/0")

        assert volume_specifier.resource_name == "res-test"
        assert volume_specifier.volume_number == 0

    def test_parse_multi_slash(self) -> None:
        volume_specifier = DrbdVolumeSpecifier.parse("res-test/hello/0")

        assert volume_specifier.resource_name == "res-test/hello"
        assert volume_specifier.volume_number == 0

    def test_parse_fail(self) -> None:
        with pytest.raises(ValueError, match="Invalid volume specifier: `res-test`. " \
                           "Expected format: `<resource_name>/<volume_number>`."):
            DrbdVolumeSpecifier.parse("res-test")

    def test_str(self) -> None:
        volume_specifier = DrbdVolumeSpecifier(resource_name="res-test", volume_number=0)
        assert str(volume_specifier) == "res-test/0"

# ------------------------------------------------------------------------------

@patch.object(Drbd, "get_local_openers")
class TestGetDrbdOpeners:
    SERVER_COUNT: Final = 3
    RESOURCE_COUNT: Final = 2

    @pytest.mark.parametrize("rpc_servers", [SERVER_COUNT], indirect=True)
    def test_multi_openers(self, mock_get_local_openers: MagicMock, rpc_servers: List[RpcApiServer]) -> None:
        base_data: List[DrbdOpener] = [DrbdOpener(
            pid=82584,
            process_name="tapback",
            cmdline=["tapback", "-d", "-x", "1"],
            open_duration=86143
        ), DrbdOpener(
            pid=83388,
            process_name="python",
            cmdline=["storage"],
            open_duration=1877
        )]

        peer_addresses = [(rpc_server.address, rpc_server.port) for rpc_server in rpc_servers]
        volume_specifiers = [
            DrbdVolumeSpecifier(resource_name=f"res-test-{i}", volume_number=0)
            for i in range(self.RESOURCE_COUNT)
        ]

        data: List[List[DrbdOpener]] = []
        expected: List[DrbdRemoteOpener] = []

        for i in range(self.SERVER_COUNT):
            for j in range(self.RESOURCE_COUNT):
                data.append(copy.deepcopy(base_data))

                # Make some value unique for each server/resource pair.
                for opener in data[-1]:
                    opener.pid += 100000 * (j + i * self.RESOURCE_COUNT)
                    expected.append(DrbdRemoteOpener(
                        opener=opener,
                        volume_specifier=volume_specifiers[j],
                        peer_address=peer_addresses[i]
                    ))

        mock_get_local_openers.side_effect = data
        openers = Drbd.get_openers(peer_addresses, volume_specifiers)

        assert len(openers) == len(expected)
        assert openers == expected

    @pytest.mark.parametrize("rpc_servers", [SERVER_COUNT], indirect=True)
    def test_connection_refused(self, mock_get_local_openers: MagicMock, rpc_servers: List[RpcApiServer]) -> None:
        data: List[DrbdOpener] = [DrbdOpener(
            pid=82584,
            process_name="tapback",
            cmdline=["tapback", "-d", "-x", "1"],
            open_duration=86143
        )]

        peer_addresses = [(rpc_server.address, rpc_server.port) for rpc_server in rpc_servers]
        volume_specifiers = [
            DrbdVolumeSpecifier(resource_name=f"res-test-{i}", volume_number=0)
            for i in range(self.RESOURCE_COUNT)
        ]

        peer_addresses.append(("invalid", 0))
        mock_get_local_openers.return_value = data

        original_connect = JsonRpcClient.connect
        def side_effect_connect(self: JsonRpcClient, *args: Any, **kwargs: Any) -> None: # noqa: ANN401
            if self.address == "invalid":
                raise TcpClientError("Unable to connect to server.")

            original_connect(self, *args, **kwargs)

        with patch.object(JsonRpcClient, "connect", side_effect=side_effect_connect, autospec=True), \
            pytest.raises(TcpClientError):
            Drbd.get_openers(peer_addresses, volume_specifiers)

    def test_no_peer(self, mock_get_local_openers: MagicMock) -> None:
        data: List[DrbdOpener] = [DrbdOpener(
            pid=82584,
            process_name="tapback",
            cmdline=["tapback", "-d", "-x", "1"],
            open_duration=86143
        )]

        peer_addresses: List[Tuple[str, int]] = []
        volume_specifiers = [
            DrbdVolumeSpecifier(resource_name=f"res-test-{i}", volume_number=0)
            for i in range(self.RESOURCE_COUNT)
        ]

        mock_get_local_openers.return_value = data
        assert Drbd.get_openers(peer_addresses, volume_specifiers) == []

    @pytest.mark.parametrize("rpc_servers", [SERVER_COUNT], indirect=True)
    def test_no_volume(self, mock_get_local_openers: MagicMock, rpc_servers: List[RpcApiServer]) -> None:
        data: List[DrbdOpener] = [DrbdOpener(
            pid=82584,
            process_name="tapback",
            cmdline=["tapback", "-d", "-x", "1"],
            open_duration=86143
        )]

        peer_addresses = [(rpc_server.address, rpc_server.port) for rpc_server in rpc_servers]
        volume_specifiers: List[DrbdVolumeSpecifier] = []

        mock_get_local_openers.return_value = data
        assert Drbd.get_openers(peer_addresses, volume_specifiers) == []

# ------------------------------------------------------------------------------

@patch("xcp_storage.backends.drbd.run_command")
class TestDemoteDrbd:
    def test_success(self, mock_run_command: MagicMock) -> None:
        mock_run_command.return_value = ("", "", 0)
        assert Drbd.demote("res-test")

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
