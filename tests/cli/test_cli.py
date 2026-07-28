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

from dataclasses import dataclass
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from xcp_storage.rpc.server import RpcApiServer
from xcp_storage_cli import main as cli_main, parse_args
from xcp_storage_cli.args import GlobalArgs
from xcp_storage_cli.commands.command import Command

from xcp_storage.typing import Final, Generator, List, Tuple

# ==============================================================================

@dataclass
class MockCli:
    args: List[str]

@pytest.fixture
def mock_cli() -> Generator[MockCli, None, None]:
    mock_cli = MockCli([])

    original_parse_args = parse_args
    def side_effect_parse_args() -> Tuple[Command, GlobalArgs]:
        return original_parse_args(mock_cli.args)

    with patch("xcp_storage_cli.parse_args", side_effect=side_effect_parse_args):
        yield mock_cli

# ------------------------------------------------------------------------------

class TestCli:
    NEGATIVE_INT: Final = -4
    NEGATIVE_FLOAT: Final = -1.0

    def test_no_command(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = []

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 2

        _, err = capsys.readouterr()
        assert err.startswith("usage:")

    def test_help(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = ["--help"]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 0

        out, _ = capsys.readouterr()
        assert out.startswith("usage:")

    def test_negative_timeout(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = ["-t", str(self.NEGATIVE_FLOAT)]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 2

        _, err = capsys.readouterr()
        assert err.startswith("usage:")
        assert f"{self.NEGATIVE_FLOAT} is a negative float, but a positive float was expected" in err

    def test_negative_port(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = ["-p", str(self.NEGATIVE_INT)]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 2

        _, err = capsys.readouterr()
        assert err.startswith("usage:")
        assert f"{self.NEGATIVE_INT} is a negative int, but a positive int was expected" in err

    def test_negative_indent(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = ["--indent", str(self.NEGATIVE_INT)]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 2

        _, err = capsys.readouterr()
        assert err.startswith("usage:")
        assert f"{self.NEGATIVE_INT} is a negative int, but a positive int was expected" in err

# ------------------------------------------------------------------------------

class TestCliWithCommand:
    COMMAND_NAME: Final = "llcall"

    MESSAGE: Final = "Moshimoshi, Storage-San?"

    def test_no_args(self, mock_cli: MockCli) -> None:
        mock_cli.args = [self.COMMAND_NAME]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 2

    def test_help(self, capsys: pytest.CaptureFixture[str], mock_cli: MockCli) -> None:
        mock_cli.args = [self.COMMAND_NAME, "--help"]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 0

        out, _ = capsys.readouterr()
        assert out.startswith("usage:")

    def test_unreachable_server(self, caplog: pytest.LogCaptureFixture, mock_cli: MockCli) -> None:
        mock_cli.args = ["-a", "some_unreachable_server", self.COMMAND_NAME, "echo.echo"]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert "Unable to connect to server." in record.message

    def test_timeout(self, caplog: pytest.LogCaptureFixture, rpc_server: RpcApiServer, mock_cli: MockCli) -> None:
        mock_cli.args = [
            "-a", rpc_server.address,
            "-p", str(rpc_server.port),
            "-t", "0.2",
            self.COMMAND_NAME,
            "echo.defer_echo",
            json.dumps({"message": self.MESSAGE, "delay": 1.0})
        ]

        with pytest.raises(SystemExit) as e:
            cli_main()

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert "Socket timeout." in record.message

    def test_command(self, capsys: pytest.CaptureFixture[str], rpc_server: RpcApiServer, mock_cli: MockCli) -> None:
        mock_cli.args = [
            "-a", rpc_server.address,
            "-p", str(rpc_server.port),
            self.COMMAND_NAME,
            "echo.echo",
            json.dumps({"message": self.MESSAGE})
        ]

        cli_main()

        out, _ = capsys.readouterr()
        assert out == f'"{self.MESSAGE}"\n'

    @patch("sys.stdin.read")
    def test_stdin_arg(
        self,
        mock_stdin_read: MagicMock,
        capsys: pytest.CaptureFixture[str],
        rpc_server: RpcApiServer,
        mock_cli: MockCli
    ) -> None:
        mock_stdin_read.return_value = json.dumps({"message": self.MESSAGE})
        mock_cli.args = [
            "-a", rpc_server.address,
            "-p", str(rpc_server.port),
            self.COMMAND_NAME,
            "echo.echo",
            "-"
        ]

        cli_main()

        out, _ = capsys.readouterr()
        assert out == f'"{self.MESSAGE}"\n'
