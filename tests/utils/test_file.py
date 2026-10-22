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
from unittest.mock import patch

import pytest

from xcp_storage.utils.file import close_fd

# ==============================================================================

class TestCloseFd:
    def test_close(self) -> None:
        read_fd, write_fd = os.pipe()
        try:
            close_fd(read_fd)
            with pytest.raises(OSError, match="Bad file descriptor") as exc_info:
                os.fstat(read_fd)
            assert exc_info.value.errno == errno.EBADF
        finally:
            close_fd(write_fd)

    def test_already_closed_fd_is_ignored(self) -> None:
        read_fd, write_fd = os.pipe()
        close_fd(read_fd)
        close_fd(read_fd)
        close_fd(write_fd)

    @pytest.mark.parametrize("error_code", [errno.EBADF, errno.EIO, errno.EINTR])
    def test_error_is_ignored(self, error_code: int) -> None:
        with patch("xcp_storage.utils.file.os.close", side_effect=OSError(error_code)) as mock_close:
            close_fd(42)
        mock_close.assert_called_once_with(42)
