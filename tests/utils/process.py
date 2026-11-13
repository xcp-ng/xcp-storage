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
from unittest.mock import patch

import pytest

from xcp_storage.utils.process import _get_process_cmdline_path, get_process_cmdline

from xcp_storage.typing import Final, Iterator

# ==============================================================================

_PROCESS_MODULE: Final = get_process_cmdline.__module__

# ------------------------------------------------------------------------------

class ProcFs:
    """
    Fake procfs (`/proc`) of `xcp_storage.utils.process` in a temporary directory.
    """

    def write_cmdline(self, pid: int, content: bytes) -> None:
        cmdline_path = _get_process_cmdline_path(pid)
        cmdline_path.parent.mkdir(parents=True, exist_ok=True)
        cmdline_path.write_bytes(content)

@pytest.fixture
def proc_fs(tmp_path: Path) -> Iterator[ProcFs]:
    """
    Empty by default: no process exists.
    """

    with patch(f"{_PROCESS_MODULE}.PROC_DIR_PATH", tmp_path / "proc"):
        yield ProcFs()
