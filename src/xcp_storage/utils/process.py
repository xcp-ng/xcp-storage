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
import multiprocessing.process
import os
from pathlib import Path
import signal
import subprocess
from types import TracebackType

from xcp_storage.config.platform import PROC_DIR_PATH
import xcp_storage.log as log

from xcp_storage.typing import (
    Any,
    Callable,
    List,
    Literal,
    NamedTuple,
    Optional,
    overload,
    override,
    Tuple,
    Type,
    Union,
)

# ==============================================================================

logger = log.get_logger() # Use default logger.

# ------------------------------------------------------------------------------

class ProcessError(Exception):
    """
    Base class of process errors.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

class ProcessTimeoutError(ProcessError):
    """
    An operation (kill, ...) did not complete in time.
    """

# ------------------------------------------------------------------------------

def _get_process_path(pid: int) -> Path:
    return PROC_DIR_PATH / str(pid)

def _get_process_cmdline_path(pid: int) -> Path:
    return _get_process_path(pid) / "cmdline"

# ------------------------------------------------------------------------------

def is_process_running(pid: int) -> bool:
    return _get_process_path(pid).exists()

def get_process_cmdline(pid: int) -> List[str]:
    path = _get_process_cmdline_path(pid)
    try:
        return [arg.decode(errors="replace") for arg in path.read_bytes().split(b"\0") if arg]
    except OSError as e:
        logger.info("Unable to read command line of PID `%d` from `%s`: `%s`.", pid, path, e.strerror)
        return []

# ------------------------------------------------------------------------------

# TODO(XCPNG-3032): Remove the quotes of `subprocess.Popen[Any]` in python 3.9 (not subscriptable before).
def kill_process(
    process: Union[multiprocessing.process.BaseProcess, "subprocess.Popen[Any]"],
    *,
    timeout: Optional[float] = None
) -> None:
    """
    Kill `process` with `SIGKILL` and wait for its end, do nothing if it has already ended: a reaped process is never
    signaled, as its pid may have been reused.

    `timeout` bounds the wait in seconds (`None`: no limit), because a process in uninterruptible sleep (blocked I/O)
    does not end on `SIGKILL`.

    `ProcessTimeoutError` is raised when it expires, `ProcessError` when the process
    cannot be signaled.
    """

    try:
        if isinstance(process, subprocess.Popen):
            process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout)
            has_ended = process.returncode is not None
        else:
            assert process.pid is not None, "The process is not started."
            # `exitcode` reaps the process when it has ended: its pid must not be signaled anymore.
            if process.exitcode is None:
                os.kill(process.pid, signal.SIGKILL)
            process.join(timeout)
            has_ended = process.exitcode is not None
    except OSError as e:
        raise ProcessError(f"Unable to kill process `{process.pid}`: `{e.strerror}`.") from None

    if not has_ended:
        raise ProcessTimeoutError(f"Process `{process.pid}` did not end after `SIGKILL`.")

# ------------------------------------------------------------------------------

class CommandError(Exception):
    def __init__(self, code: Optional[int], cmd: str, reason: str) -> None:
        super().__init__("Command execution error.")
        self.code = code
        self.cmd = cmd
        self.reason = reason

class CommandTimeoutError(CommandError):
    """
    A command did not complete in time.
    """

def default_ret_code_callback(_stdout: str, _stderr: str, ret_code: int) -> int:
    return ret_code

# ------------------------------------------------------------------------------

class CommandResult(NamedTuple):
    """
    Result of `run_command(..., simple=False)`. The defaults describe a command that succeeded without output.
    """

    stdout: str = ""
    stderr: str = ""
    # Exit code of the command.
    ret_code: int = 0

# Result of `run_command`: its stdout, or a `CommandResult` with `simple=False`.
RunCommandResult = Union[str, CommandResult]

# ------------------------------------------------------------------------------

def _create_failed_command_error(
    args: List[str],
    exception: Exception,
    *,
    action: str,
    error_type: Type[CommandError] = CommandError
) -> CommandError:
    """
    Return an error of a command that could not be started or killed (`action`: `run`, `kill`...).
    """

    return error_type(None, str(args), reason=f"Failed to {action} command: `{exception}`.")

def _process_command_result(
    args: List[str],
    result: CommandResult,
    *,
    expected_ret_code: Optional[int],
    ret_code_callback: Callable[[str, str, int], int],
    quiet: bool
) -> CommandResult:
    """
    Return `result`, raise `CommandError` if its exit code is not `expected_ret_code` (`None`: any code accepted).
    """

    if expected_ret_code is not None and result.ret_code != expected_ret_code:
        stderr = result.stderr.strip()
        if not quiet:
            logger.error("Command `%s` exited with code %d: `%s`.", " ".join(args), result.ret_code, stderr)
        raise CommandError(ret_code_callback(result.stdout, result.stderr, result.ret_code), str(args), reason=stderr)
    return result

# ------------------------------------------------------------------------------

@overload
def run_internal_command(
    args: List[str],
    *,
    simple: Literal[True] = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> str:
    ...

@overload
def run_internal_command(
    args: List[str],
    *,
    simple: Literal[False],
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> CommandResult:
    ...

@overload
def run_internal_command(
    args: List[str],
    *,
    simple: bool,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> RunCommandResult:
    ...

def run_internal_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> RunCommandResult:
    try:
        # TODO(XCPNG-3032): Remove noqa warn and use `capture_output` after we discontinue support for Python 3.6.
        process_result = subprocess.run( # noqa: UP022
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            encoding="utf-8",
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError(None, str(args), reason=f"Command did not end within {timeout} second(s).") from None
    except Exception as e:
        raise _create_failed_command_error(args, e, action="run") from e

    result = _process_command_result(
        args,
        CommandResult(process_result.stdout, process_result.stderr, process_result.returncode),
        expected_ret_code=expected_ret_code,
        ret_code_callback=ret_code_callback,
        quiet=quiet
    )

    if simple:
        return result.stdout
    return result

# ------------------------------------------------------------------------------

@overload
def run_command(
    args: List[str],
    *,
    simple: Literal[True] = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> str:
    ...

@overload
def run_command(
    args: List[str],
    *,
    simple: Literal[False],
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> CommandResult:
    ...

def run_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> RunCommandResult:
    logger.info("Running command `%s`.", " ".join(args))
    return run_internal_command(
        args,
        simple=simple,
        expected_ret_code=expected_ret_code,
        ret_code_callback=ret_code_callback,
        quiet=quiet,
        timeout=timeout
    )

# ------------------------------------------------------------------------------

class CommandProcess(contextlib.AbstractContextManager):
    """
    Command started in the background by `start_command`. Leaving the `with` block kills it if `wait` has not seen its
    end: no orphan, even when the caller raises.
    """

    # TODO(XCPNG-3032): Remove the quotes of `subprocess.Popen[str]` in python 3.9 (not subscriptable before).
    def __init__(
        self,
        args: List[str],
        process: "subprocess.Popen[str]",
        *,
        expected_ret_code: Optional[int],
        ret_code_callback: Callable[[str, str, int], int],
        quiet: bool
    ) -> None:
        self._args = args
        self._process = process
        self._expected_ret_code = expected_ret_code
        self._ret_code_callback = ret_code_callback
        self._quiet = quiet
        # Stdout and stderr, read by `wait` once the command has ended.
        self._output: Optional[Tuple[str, str]] = None
        self._killed = False

    @override
    def __enter__(self) -> "CommandProcess":
        return self

    @override
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        self.kill()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait at most `timeout` seconds (`None`: no limit) for the end of the command,
        return whether it has ended (or has been killed).
        """

        if self._output is None and not self._killed:
            try:
                self._output = self._process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                return False
        return True

    def kill(self, timeout: Optional[float] = None) -> None:
        """
        Kill the command and wait at most `timeout` seconds (`None`: no limit) for its end,
        unless `wait` has already seen its end.
        `CommandError` is raised when the command cannot be killed.
        `CommandTimeoutError` is raised when `timeout` expires (a process in uninterruptible
        sleep does not end on `SIGKILL`).
        """

        if self._output is not None or self._killed:
            return

        self._killed = True
        try:
            kill_process(self._process, timeout=timeout)
        except ProcessTimeoutError as e:
            raise _create_failed_command_error(self._args, e, action="kill", error_type=CommandTimeoutError) from None
        except ProcessError as e:
            raise _create_failed_command_error(self._args, e, action="kill") from None
        finally:
            # Not read by `communicate`: a child of the command may still hold the pipes open.
            for file in (self._process.stdout, self._process.stderr):
                if file is not None:
                    file.close()

    def get_result(self) -> CommandResult:
        """
        Wait for the end of the command (no limit) and return its result.
        """

        self.wait()
        if self._output is None:
            raise CommandError(None, str(self._args), reason="Command was killed.")

        stdout, stderr = self._output
        return _process_command_result(
            self._args,
            CommandResult(stdout, stderr, self._process.returncode),
            expected_ret_code=self._expected_ret_code,
            ret_code_callback=self._ret_code_callback,
            quiet=self._quiet
        )

def start_command(
    args: List[str],
    *,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> CommandProcess:
    """
    Start a command in the background, to use in a `with` block: unlike `run_command`, the caller can stop it at any
    time (`CommandProcess.kill`).
    """

    logger.info("Starting command `%s`.", " ".join(args))
    try:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    except Exception as e:
        raise _create_failed_command_error(args, e, action="run") from e

    return CommandProcess(
        args,
        process,
        expected_ret_code=expected_ret_code,
        ret_code_callback=ret_code_callback,
        quiet=quiet
    )
