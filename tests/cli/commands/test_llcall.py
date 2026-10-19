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
import logging

import pytest

from xcp_storage_cli.args import GlobalArgs
from xcp_storage_cli.commands.llcall import LlcallArgs, LlcallCommand

from xcp_storage.typing import Final

# ==============================================================================

class TestLlcallCommand:
    MESSAGE: Final = "Moshimoshi, Storage-San?"

    def test_invalid_function(self, caplog: pytest.LogCaptureFixture, args_with_server: GlobalArgs) -> None:
        args = LlcallArgs(**vars(args_with_server), func="thisfunctiondoesnotexist", params=None)
        command = LlcallCommand()

        with pytest.raises(SystemExit) as e:
            command.run(args)

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert record.message == "RPC call failed: Method not found"

    def test_invalid_params(self, caplog: pytest.LogCaptureFixture, args_with_server: GlobalArgs) -> None:
        args = LlcallArgs(**vars(args_with_server), func="echo.echo", params=None)
        command = LlcallCommand()

        with pytest.raises(SystemExit) as e:
            command.run(args)

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert record.message == "RPC call failed: Invalid params"

    def test_empty_params(self, caplog: pytest.LogCaptureFixture, args_with_server: GlobalArgs) -> None:
        args = LlcallArgs(**vars(args_with_server), func="echo.echo", params="{}")
        command = LlcallCommand()

        with pytest.raises(SystemExit) as e:
            command.run(args)

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert record.message == "RPC call failed: Invalid params"

    def test_malformed_params(self, caplog: pytest.LogCaptureFixture, args_with_server: GlobalArgs) -> None:
        args = LlcallArgs(**vars(args_with_server), func="echo.echo", params="{")
        command = LlcallCommand()

        with pytest.raises(SystemExit) as e:
            command.run(args)

        assert e.value.code == 1

        record = caplog.records[-1]
        assert record.levelno == logging.ERROR
        assert record.message == "Invalid JSON-RPC `params` object: " \
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"

    def test_echo(self, capsys: pytest.CaptureFixture[str], args_with_server: GlobalArgs) -> None:
        args = LlcallArgs(**vars(args_with_server), func="echo.echo", params=json.dumps({"message": self.MESSAGE}))
        command = LlcallCommand()

        command.run(args)

        out, _ = capsys.readouterr()
        assert out == f'"{self.MESSAGE}"\n'
