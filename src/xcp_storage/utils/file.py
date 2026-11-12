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
from pathlib import PurePath

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

def is_mount_point(path: PurePath) -> bool:
    """
    Test if `path` is a mount point.
    """

    # TODO(XCPNG-3032): Use `os.path` instead of `Path` for old python versions. Change me later.
    return os.path.ismount(path)
