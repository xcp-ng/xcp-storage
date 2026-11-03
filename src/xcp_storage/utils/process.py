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

from xcp_storage.config.platform import PROC_DIR_PATH
import xcp_storage.log as log

from xcp_storage.typing import (
    Any,
    Callable,
    List,
    Literal,
    Optional,
    overload,
    Tuple,
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

def _get_process_cmdline_path(pid: int) -> Path:
    return PROC_DIR_PATH / str(pid) / "cmdline"

def get_process_cmdline(pid: int) -> List[str]:
    path = _get_process_cmdline_path(pid)
    try:
        return [arg.decode(errors="replace") for arg in path.read_bytes().split(b"\0") if arg]
    except Exception as e:
        logger.info("Unable to get command line of PID `%d`: `%s`.", pid, e)
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
        raise ProcessError(f"Unable to kill process `{process.pid}`.") from e

    if not has_ended:
        raise ProcessTimeoutError(f"Process `{process.pid}` did not end after `SIGKILL`.")

# ------------------------------------------------------------------------------

class CommandError(Exception):
    def __init__(self, code: Optional[int], cmd: str, reason: str) -> None:
        super().__init__("Command execution error.")
        self.code = code
        self.cmd = cmd
        self.reason = reason

def default_ret_code_callback(_stdout: str, _stderr: str, ret_code: int) -> int:
    return ret_code

# ------------------------------------------------------------------------------

CommandResultType = Union[str, Tuple[str, str, int]]

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
) -> Tuple[str, str, int]:
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
) -> CommandResultType:
    ...

def run_internal_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> CommandResultType:
    try:
        # TODO(XCPNG-3032): Remove noqa warn and use `capture_output` after we discontinue support for Python 3.6.
        result = subprocess.run( # noqa: UP022
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            encoding="utf-8",
            timeout=timeout
        )
    except Exception as e:
        raise CommandError(None, str(args), reason=f"Failed to run command: `{e}`.") from e

    stdout, stderr, ret_code = result.stdout, result.stderr, result.returncode

    if expected_ret_code is not None and ret_code != expected_ret_code:
        if not quiet:
            logger.error(
                "Command `%s` exited with code %d: `%s`.",
                " ".join(args),
                ret_code,
                stderr.strip()
            )
        raise CommandError(ret_code_callback(stdout, stderr, ret_code), str(args), reason=stderr.strip())

    if simple:
        return stdout
    return stdout, stderr, ret_code

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
) -> Tuple[str, str, int]:
    ...

def run_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False,
    timeout: Optional[float] = None
) -> CommandResultType:
    logger.info("Running command `%s`.", " ".join(args))
    return run_internal_command(
        args,
        simple=simple,
        expected_ret_code=expected_ret_code,
        ret_code_callback=ret_code_callback,
        quiet=quiet,
        timeout=timeout
    )
