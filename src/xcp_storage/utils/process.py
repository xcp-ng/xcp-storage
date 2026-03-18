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

import subprocess

import xcp_storage.log as log

from xcp_storage.typing import (
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
    quiet: bool = False
) -> str:
    ...

@overload
def run_internal_command(
    args: List[str],
    *,
    simple: Literal[False],
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> Tuple[str, str, int]:
    ...

@overload
def run_internal_command(
    args: List[str],
    *,
    simple: bool,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> CommandResultType:
    ...

def run_internal_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> CommandResultType:
    try:
        # TODO(XCPNG-3032): Remove noqa warn and use `capture_output` after we discontinue support for Python 3.6.
        result = subprocess.run( # noqa: UP022
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            encoding="utf-8"
        )
    except Exception as e:
        raise CommandError(None, str(args), reason=f"Failed to run command: `{e}`.") from e

    stdout, stderr = result.stdout, result.stderr

    if expected_ret_code is not None and result.returncode != expected_ret_code:
        if not quiet:
            logger.error(
                "Command `%s` exited with code %d: `%s`.",
                " ".join(args),
                result.returncode,
                stderr.strip()
            )
        raise CommandError(ret_code_callback(stdout, stderr, result.returncode), str(args), reason=stderr.strip())

    if simple:
        return stdout
    return stdout, stderr, result.returncode

# ------------------------------------------------------------------------------

@overload
def run_command(
    args: List[str],
    *,
    simple: Literal[True] = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> str:
    ...

@overload
def run_command(
    args: List[str],
    *,
    simple: Literal[False],
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> Tuple[str, str, int]:
    ...

def run_command(
    args: List[str],
    *,
    simple: bool = True,
    expected_ret_code: Optional[int] = None,
    ret_code_callback: Callable[[str, str, int], int] = default_ret_code_callback,
    quiet: bool = False
) -> CommandResultType:
    logger.info("Running command `%s`.", " ".join(args))
    return run_internal_command(
        args,
        simple=simple,
        expected_ret_code=expected_ret_code,
        ret_code_callback=ret_code_callback,
        quiet=quiet
    )
