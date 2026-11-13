import os
import os.path
import os.path as osp
from os import path as os_path
from os.path import ismount
import posixpath
from pathlib import Path, PurePath

from xcp_storage.utils.filesystem import is_mount_point

# ------------------------------------------------------------------------------
# `os.path` function: called, or passed as a function.
# ------------------------------------------------------------------------------

def test_os_path(path: PurePath) -> None:
    # ruleid: python-enforce-mount-point-helper
    os.path.ismount(path)
    # ruleid: python-enforce-mount-point-helper
    osp.ismount(path)
    # ruleid: python-enforce-mount-point-helper
    os_path.ismount(path)
    # ruleid: python-enforce-mount-point-helper
    ismount(path)
    # ruleid: python-enforce-mount-point-helper
    check = os.path.ismount
    # ok: python-enforce-mount-point-helper
    is_mount_point(path)
    # ok: python-enforce-mount-point-helper
    os.path.isdir(path)

# ------------------------------------------------------------------------------
# Same function, through the module that `os.path` points to on POSIX.
# ------------------------------------------------------------------------------

def test_posixpath(path: PurePath) -> None:
    # ruleid: python-enforce-mount-point-helper
    posixpath.ismount(path)
    # ok: python-enforce-mount-point-helper
    posixpath.isdir(path)

# ------------------------------------------------------------------------------
# `Path` method: on an instance or on the class, called or not.
# ------------------------------------------------------------------------------

def test_path_method(path: Path) -> None:
    # ruleid: python-enforce-mount-point-helper
    path.is_mount()
    # ruleid: python-enforce-mount-point-helper
    Path("/var/lib/linstor").is_mount()
    # ruleid: python-enforce-mount-point-helper
    Path.is_mount(path)
    # ruleid: python-enforce-mount-point-helper
    check = path.is_mount
    # ok: python-enforce-mount-point-helper
    path.is_dir()
    # ok: python-enforce-mount-point-helper
    path.is_symlink()
