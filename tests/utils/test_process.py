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

import errno
import os
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tests.utils.exception import raises_exactly
from tests.utils.process import ProcFs
import xcp_storage.log as log
from xcp_storage.utils.math import KIB
from xcp_storage.utils.process import (
    _get_process_cmdline_path,
    CommandError,
    CommandResult,
    CommandTimeoutError,
    get_process_cmdline,
    is_process_running,
    kill_process,
    ProcessError,
    ProcessTimeoutError,
    run_command,
    start_command,
)

from xcp_storage.typing import Final, Type

# ==============================================================================

EXEC_PATH_ECHO: Final = "/usr/bin/echo"
EXEC_PATH_SH: Final = "/bin/sh"

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
            f"Unable to read command line of PID `{self.PID}` from `{cmdline_path}`: `{os.strerror(errno.ENOENT)}`."
        ) in caplog.text

# ------------------------------------------------------------------------------

class TestKillProcess:
    # Safety bound of a kill that must succeed.
    TIMEOUT: Final = 10.0

    def test_signal_failure(self) -> None:
        process = subprocess.Popen([EXEC_PATH_SH, "-c", "exec sleep 1000"])
        try:
            strerror = os.strerror(errno.EPERM)
            with patch.object(
                process, "kill", autospec=True, side_effect=PermissionError(errno.EPERM, strerror)
            ), raises_exactly(ProcessError, f"Unable to kill process `{process.pid}`: `{strerror}`.") as exc_info:
                kill_process(process, timeout=self.TIMEOUT)
            assert exc_info.value.__cause__ is None
        finally:
            kill_process(process, timeout=self.TIMEOUT)

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

# ------------------------------------------------------------------------------

class TestStartCommand:
    # Safety bound of a wait that must see the end of the command.
    WAIT_TIMEOUT: Final = 10.0

    # Wait that must expire: the command does not end by itself.
    EXPIRED_WAIT_TIMEOUT: Final = 0.1

    # Output larger than a pipe buffer (64 KiB on Linux), written before the first wait expires.
    LARGE_OUTPUT_SIZE: Final = 128 * KIB

    SLOW_COMMAND: Final = [EXEC_PATH_SH, "-c", "exec sleep 1000"]

    def test_result(self) -> None:
        with start_command([EXEC_PATH_SH, "-c", "printf hello; printf boom >&2"]) as process:
            assert process.wait(self.WAIT_TIMEOUT)
        assert process.get_result() == CommandResult(stdout="hello", stderr="boom")

    def test_get_result_waits_for_end(self) -> None:
        with start_command([EXEC_PATH_SH, "-c", "sleep 0.1; printf hello"]) as process:
            assert process.get_result() == CommandResult(stdout="hello")

    def test_wait_again_keeps_output(self) -> None:
        # The command writes more than a pipe buffer before the first wait expires,
        # and the rest after: the expired wait must have read the pipe meanwhile,
        # and the next wait must return the whole output.
        stdout_end = "end"
        stdout_content = "\0" * self.LARGE_OUTPUT_SIZE + stdout_end
        script = f"head -c {self.LARGE_OUTPUT_SIZE} /dev/zero; sleep 0.5; printf {stdout_end}"
        with start_command([EXEC_PATH_SH, "-c", script]) as process:
            assert not process.wait(self.EXPIRED_WAIT_TIMEOUT)
            assert process.wait(self.WAIT_TIMEOUT)
            assert process.get_result() == CommandResult(stdout=stdout_content)

    def test_unexpected_ret_code(self, caplog: pytest.LogCaptureFixture) -> None:
        args = [EXEC_PATH_SH, "-c", "printf boom >&2; exit 3"]
        with start_command(args, expected_ret_code=0) as process, \
                raises_exactly(CommandError, "Command execution error.") as exc_info:
            process.get_result()
        assert (exc_info.value.code, exc_info.value.reason) == (3, "boom")
        assert f"Command `{' '.join(args)}` exited with code 3: `boom`." in caplog.text

    def test_start_failure(self, tmp_path: Path) -> None:
        exec_path = tmp_path / "missing"
        with raises_exactly(CommandError, "Command execution error.") as exc_info:
            start_command([str(exec_path)])

        assert exc_info.value.code is None
        cause = exc_info.value.__cause__
        assert isinstance(cause, FileNotFoundError)
        assert cause.filename == str(exec_path)
        assert exc_info.value.reason == f"Failed to run command: `{cause}`."

    def test_kill(self) -> None:
        with start_command(self.SLOW_COMMAND) as process:
            assert not process.wait(self.EXPIRED_WAIT_TIMEOUT)
            process.kill()
            assert process._process.returncode is not None # noqa: SLF001
            assert process.wait()
            with raises_exactly(CommandError, "Command execution error.") as exc_info:
                process.get_result()
        assert exc_info.value.code is None
        assert exc_info.value.reason == "Command was killed."

    @pytest.mark.parametrize(("process_error_type", "command_error_type"), [
        (ProcessError, CommandError),
        (ProcessTimeoutError, CommandTimeoutError),
    ])
    def test_kill_failure(
        self,
        mock_kill_process: MagicMock,
        process_error_type: Type[ProcessError],
        command_error_type: Type[CommandError]
    ) -> None:
        mock_kill_process.side_effect = process_error_type("Boom.")
        with start_command(self.SLOW_COMMAND) as process, \
                raises_exactly(command_error_type, "Command execution error.") as exc_info:
            process.kill(timeout=self.WAIT_TIMEOUT)

        try:
            internal_process = process._process # noqa: SLF001
            mock_kill_process.assert_called_once_with(internal_process, timeout=self.WAIT_TIMEOUT)
            assert exc_info.value.code is None
            assert exc_info.value.reason == "Failed to kill command: `Boom.`."
            assert exc_info.value.__cause__ is None

            # The pipes are closed even when the kill fails.
            assert internal_process.stdout is not None and internal_process.stdout.closed
            assert internal_process.stderr is not None and internal_process.stderr.closed
        finally:
            kill_process(internal_process)

    def test_kill_when_process_is_already_terminated(self) -> None:
        with start_command([EXEC_PATH_SH, "-c", "printf hello"]) as process:
            assert process.wait(self.WAIT_TIMEOUT)
            process.kill()
            assert process.get_result() == CommandResult(stdout="hello")

    def test_exit_kills_on_error(self) -> None:
        error_message = "Caller error."
        with raises_exactly(ValueError, error_message), start_command(self.SLOW_COMMAND) as process:
            raise ValueError(error_message)
        assert process._process.returncode is not None # noqa: SLF001
