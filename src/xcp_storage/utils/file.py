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
import os
from pathlib import Path, PurePath

from xcp_storage.typing import Final

# ==============================================================================

# `select` only supports the descriptors below this value.
FD_SETSIZE: Final = 1024

# ------------------------------------------------------------------------------

def close_fd(fd: int) -> None:
    """
    Close a file descriptor, ignoring the errors.

    Nothing useful can be done if `close` fails (on Linux the descriptor is released anyway),
    and the error must not hide the exception being handled or break a release.
    """
    with contextlib.suppress(OSError):
        os.close(fd)

def create_hard_link(path: PurePath, target_path: PurePath) -> None:
    """
    Create `path` as a hard link to the file `target_path`.
    `FileExistsError` is raised if `path` exists.
    """

    # TODO(XCPNG-3032): Use `Path.hardlink_to` in python 3.10.
    os.link(target_path, path)

def remove_file(path: PurePath, *, missing_ok: bool = False) -> None:
    """
    Remove a file `path`. Cannot remove a directory.
    `FileNotFoundError` is raised if it does not exist, unless `missing_ok`.
    """

    # TODO(XCPNG-3032): Use `Path.unlink(missing_ok=...)` in python 3.8.
    try:
        Path(path).unlink()
    except FileNotFoundError:
        if not missing_ok:
            raise
