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
from pathlib import Path, PurePath

from xcp_storage.utils.process import (
    CommandError,
    CommandResult,
    CommandTimeoutError,
    run_command,
)

from xcp_storage.typing import (
    Final,
    List,
    Never,
    Optional,
)

# ==============================================================================

_EXEC_PATH_BLKID: Final = "/usr/sbin/blkid"

_EXEC_PATH_MKFS_EXT4: Final = "/usr/sbin/mkfs.ext4"

_EXEC_PATH_MOUNT: Final = "/usr/bin/mount"
_EXEC_PATH_UMOUNT: Final = "/usr/bin/umount"

_FILESYSTEM_COMMAND_TIMEOUT: Final = 60.0

# Exit code of `blkid` when nothing is found.
_BLKID_NOT_FOUND_CODE: Final = 2

# ------------------------------------------------------------------------------

class FilesystemError(Exception):
    """
    Failure of a file system command. `code` is its exit code, if any.
    """

    def __init__(self, message: str, code: Optional[int] = None) -> None:
        super().__init__(message)
        self.code = code

class FilesystemTimeoutError(FilesystemError):
    """
    A file system command did not end in time.
    """

# ------------------------------------------------------------------------------

def _get_filesystem_command_name(args: List[str]) -> str:
    return PurePath(args[0]).name

def _raise_filesystem_command_error(args: List[str], stderr: str, ret_code: int) -> Never:
    raise FilesystemError(f"Command `{_get_filesystem_command_name(args)}` failed: `{stderr.strip()}`.", ret_code)

def _try_filesystem_command(
    args: List[str], *, timeout: Optional[float] = _FILESYSTEM_COMMAND_TIMEOUT
) -> CommandResult:
    command = _get_filesystem_command_name(args)
    try:
        return run_command(args, simple=False, timeout=timeout)
    except CommandTimeoutError:
        raise FilesystemTimeoutError(f"Command `{command}` did not end within {timeout} second(s).") from None
    except CommandError as e:
        raise FilesystemError(f"Failed to run command `{command}`: `{e.reason}`.", e.code) from None

def _run_filesystem_command(
    args: List[str], *, timeout: Optional[float] = _FILESYSTEM_COMMAND_TIMEOUT
) -> str:
    stdout, stderr, ret_code = _try_filesystem_command(args, timeout=timeout)
    if ret_code != 0:
        _raise_filesystem_command_error(args, stderr, ret_code)
    return stdout

# ------------------------------------------------------------------------------

def get_filesystem_type(path: PurePath) -> Optional[str]:
    """
    Return the type of the file system on the block device `path` (e.g. `ext4`), `None` if none is found.
    `FileNotFoundError` is raised if `path` does not exist.
    """

    if not Path(path).exists():
        raise FileNotFoundError(f"Block device `{path}` does not exist.")

    args = [_EXEC_PATH_BLKID, "-p", "-o", "value", "-s", "TYPE", str(path)]
    stdout, stderr, ret_code = _try_filesystem_command(args)
    if ret_code == _BLKID_NOT_FOUND_CODE:
        return None

    if ret_code != 0:
        _raise_filesystem_command_error(args, stderr, ret_code)

    return stdout.strip() or None

# ------------------------------------------------------------------------------

def create_ext4_filesystem(path: PurePath, *, discard: bool = False) -> None:
    """
    Write a new ext4 file system on the block device `path`, overwriting what it holds.
    `discard`: discard the whole device first, so that a thin device or an SSD gets back the blocks of what it held.
    """

    discard_option = "discard" if discard else "nodiscard"
    # No timeout: can be a long task.
    _run_filesystem_command([_EXEC_PATH_MKFS_EXT4, "-q", "-E", discard_option, str(path)], timeout=None)

# ------------------------------------------------------------------------------

def is_mount_point(path: PurePath) -> bool:
    """
    Test if `path` is a mount point.
    """

    # TODO(XCPNG-3032): Use `os.path` instead of `Path` for old python versions. Change me later.
    return os.path.ismount(path)

def mount_filesystem(path: PurePath, mount_path: PurePath) -> None:
    """
    Mount the file system of the block device `path` on `mount_path`, in read-write mode.
    """

    _run_filesystem_command([_EXEC_PATH_MOUNT, "-w", str(path), str(mount_path)])

def unmount_filesystem(mount_path: PurePath, *, lazy: bool = False) -> None:
    """
    Unmount the file system mounted on `mount_path`, succeeds if nothing is mounted there.
    `lazy`: detached at once, really unmounted once no longer busy.
    """

    if is_mount_point(mount_path):
        _run_filesystem_command([_EXEC_PATH_UMOUNT, *(["-l"] if lazy else []), str(mount_path)])
