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
from unittest.mock import MagicMock, patch

import pytest

import xcp_storage.log as log
from xcp_storage.utils.process import CommandError, get_process_cmdline, run_command

from xcp_storage.typing import Final

# ==============================================================================

class TestRunCommandWithTimeout:
    def test_timeout(self) -> None:
        with pytest.raises(CommandError) as exc_info:
            run_command(["/usr/bin/sleep", "10"], timeout=0.2)
        assert exc_info.value.code is None
        assert "timed out" in exc_info.value.reason

    def test_success_within_timeout(self) -> None:
        assert run_command(["/usr/bin/echo", "hello"], timeout=10.0) == "hello\n"

# ------------------------------------------------------------------------------

@patch.object(Path, "read_bytes")
class TestGetProcessCmdline:
    PID: Final = 67

    def test_success(self, mock_read_bytes: MagicMock) -> None:
        mock_read_bytes.return_value = b"python\x00-m\x00pytest\x00"
        assert get_process_cmdline(self.PID) == ["python", "-m", "pytest"]

    def test_null_args(self, mock_read_bytes: MagicMock) -> None:
        mock_read_bytes.return_value = b"abricot\x00\x00\x00-orange\x00\x00jus ananas \x00"
        assert get_process_cmdline(self.PID) == ["abricot", "-orange", "jus ananas "]

    def test_non_utf8_args(self, mock_read_bytes: MagicMock) -> None:
        mock_read_bytes.return_value = b"prog\x00\xff\xfe\x00arg\x00"
        assert get_process_cmdline(self.PID) == ["prog", "\ufffd\ufffd", "arg"]

    def test_pid_not_found(self, mock_read_bytes: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        cmdline_path = f"/proc/{self.PID}/cmdline"
        mock_read_bytes.side_effect = FileNotFoundError(2, "No such file or directory", cmdline_path)

        with caplog.at_level(log.INFO):
            assert get_process_cmdline(self.PID) == []

        assert (
            f"Unable to get command line of PID `{self.PID}`: "
            f"`[Errno 2] No such file or directory: '{cmdline_path}'`."
        ) in caplog.text
