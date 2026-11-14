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

import os

import pytest

from tests.utils.exception import raises_exactly
from tests.utils.process import ProcFs
import xcp_storage.log as log
from xcp_storage.utils.process import (
    _get_process_cmdline_path,
    CommandResult,
    CommandTimeoutError,
    get_process_cmdline,
    is_process_running,
    run_command,
)

from xcp_storage.typing import Final

# ==============================================================================

EXEC_PATH_ECHO: Final = "/usr/bin/echo"

# ------------------------------------------------------------------------------

class TestIsProcessRunning:
    PID: Final = 67

    def test_running(self, proc_fs: ProcFs) -> None:
        proc_fs.write_cmdline(self.PID, b"tapdisk\x00")
        assert is_process_running(self.PID)

    @pytest.mark.usefixtures("proc_fs")
    def test_not_running(self) -> None:
        assert not is_process_running(self.PID)

    def test_current_process(self) -> None:
        assert is_process_running(os.getpid())

# ------------------------------------------------------------------------------

class TestGetProcessCmdline:
    PID: Final = 67

    def test_success(self, proc_fs: ProcFs) -> None:
        proc_fs.write_cmdline(self.PID, b"python\x00-m\x00pytest\x00")
        assert get_process_cmdline(self.PID) == ["python", "-m", "pytest"]

    def test_null_args(self, proc_fs: ProcFs) -> None:
        proc_fs.write_cmdline(self.PID, b"abricot\x00\x00\x00-orange\x00\x00jus ananas \x00")
        assert get_process_cmdline(self.PID) == ["abricot", "-orange", "jus ananas "]

    def test_non_utf8_args(self, proc_fs: ProcFs) -> None:
        proc_fs.write_cmdline(self.PID, b"prog\x00\xff\xfe\x00arg\x00")
        assert get_process_cmdline(self.PID) == ["prog", "\ufffd\ufffd", "arg"]

    @pytest.mark.usefixtures("proc_fs")
    def test_pid_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        cmdline_path = _get_process_cmdline_path(self.PID)

        with caplog.at_level(log.INFO):
            assert get_process_cmdline(self.PID) == []

        assert (
            f"Unable to get command line of PID `{self.PID}`: "
            f"`[Errno 2] No such file or directory: '{cmdline_path}'`."
        ) in caplog.text

# ------------------------------------------------------------------------------

class TestRunCommand:
    def test_result(self) -> None:
        result = run_command([EXEC_PATH_ECHO, "hello"], simple=False)
        assert result == CommandResult(stdout="hello\n")
        assert (result.stdout, result.stderr, result.ret_code) == ("hello\n", "", 0)

class TestRunCommandWithTimeout:
    TIMEOUT: Final = 0.2

    def test_timeout(self) -> None:
        with raises_exactly(CommandTimeoutError, "Command execution error.") as exc_info:
            run_command(["/usr/bin/sleep", "10"], timeout=self.TIMEOUT)
        assert exc_info.value.code is None
        assert exc_info.value.reason == f"Command did not end within {self.TIMEOUT} second(s)."

    def test_success_within_timeout(self) -> None:
        assert run_command([EXEC_PATH_ECHO, "hello"], timeout=10.0) == "hello\n"
