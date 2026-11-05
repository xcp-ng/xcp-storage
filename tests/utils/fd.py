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
import gc
import os
from pathlib import PurePath
import resource

import pytest

from xcp_storage.config.platform import PROC_DIR_PATH
from xcp_storage.utils.file import close_fd

from xcp_storage.typing import Final, Iterator, List

# ==============================================================================

_FD_SELF_DIR_PATH: Final = PROC_DIR_PATH / "self" / "fd"

# ------------------------------------------------------------------------------

def count_process_fds() -> int:
    """
    Return the number of descriptors opened by this process.
    """
    return len(list(_FD_SELF_DIR_PATH.iterdir()))

def count_open_fds(path: PurePath) -> int:
    """
    Return the number of descriptors of this process opened on `path`.
    """
    count = 0
    for fd_path in _FD_SELF_DIR_PATH.iterdir():
        with contextlib.suppress(OSError):
            count += os.readlink(fd_path) == str(path)
    return count

@contextlib.contextmanager
def assert_no_fd_leak() -> Iterator[None]:
    """
    Check that this process has as many descriptors opened before and after `yield`.
    """

    gc.collect()
    fd_count = count_process_fds()

    yield

    gc.collect()
    assert count_process_fds() == fd_count

@contextlib.contextmanager
def occupied_low_fds(limit: int) -> Iterator[None]:
    """
    Occupy all the free descriptors below `limit`: the next ones opened by the process are `>= limit`.
    Skips the test if the process cannot open enough descriptors.
    """

    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

    free_count = 64 # Leave extra space beyond the limit.

    required_limit = limit + free_count
    if hard_limit != resource.RLIM_INFINITY and hard_limit < required_limit:
        pytest.skip(f"At least {required_limit} file descriptors are required.")

    resource.setrlimit(resource.RLIMIT_NOFILE, (max(soft_limit, required_limit), hard_limit))
    fds: List[int] = []
    try:
        fd = os.open(os.devnull, os.O_RDONLY | os.O_CLOEXEC)
        fds.append(fd)
        while fd < limit - 1:
            fd = os.dup(fds[0])
            fds.append(fd)
        yield
    finally:
        for fd in fds:
            close_fd(fd)
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft_limit, hard_limit))
