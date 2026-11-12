import os
import os as operating_system
from pathlib import Path

from xcp_storage.utils.file import create_hard_link

# ------------------------------------------------------------------------------
# `os` function: called, or passed as a function.
# ------------------------------------------------------------------------------

def link_os(path: Path, target_path: Path) -> None:
    # ruleid: python-enforce-hard-link-helper
    os.link(target_path, path)
    # ruleid: python-enforce-hard-link-helper
    operating_system.link(target_path, path)
    # ruleid: python-enforce-hard-link-helper
    create = os.link
    # ok: python-enforce-hard-link-helper
    create_hard_link(path, target_path)
    # ok: python-enforce-hard-link-helper
    os.symlink(target_path, path)
    # ok: python-enforce-hard-link-helper
    os.readlink(path)

# ------------------------------------------------------------------------------
# `Path` method: on an instance or on the class, called or not.
# ------------------------------------------------------------------------------

def link_path(path: Path, target_path: Path) -> None:
    # ruleid: python-enforce-hard-link-helper
    path.hardlink_to(target_path)
    # ruleid: python-enforce-hard-link-helper
    Path("/var/lib/link").hardlink_to(target_path)
    # ruleid: python-enforce-hard-link-helper
    Path.hardlink_to(path, target_path)
    # ruleid: python-enforce-hard-link-helper
    create = path.hardlink_to
    # ok: python-enforce-hard-link-helper
    path.symlink_to(target_path)
