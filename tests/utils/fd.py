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

from xcp_storage.config.platform import PROC_DIR_PATH

from xcp_storage.typing import Final

# ==============================================================================

_FD_SELF_DIR_PATH: Final = PROC_DIR_PATH / "self" / "fd"

# ------------------------------------------------------------------------------

def count_open_fds(path: PurePath) -> int:
    """
    Return the number of descriptors of this process opened on `path`.
    """
    count = 0
    for fd_path in _FD_SELF_DIR_PATH.iterdir():
        with contextlib.suppress(OSError):
            count += os.readlink(fd_path) == str(path)
    return count
