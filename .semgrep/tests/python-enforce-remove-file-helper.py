import contextlib
import os
import os as operating_system
from pathlib import Path

from xcp_storage.utils.file import remove_file

# ------------------------------------------------------------------------------
# `os` function: called, or passed as a function.
# ------------------------------------------------------------------------------

def remove_os(path: Path) -> None:
    # ruleid: python-enforce-remove-file-helper
    os.remove(path)
    # ruleid: python-enforce-remove-file-helper
    operating_system.remove(path)
    # ruleid: python-enforce-remove-file-helper
    os.unlink(path)
    # ruleid: python-enforce-remove-file-helper
    operating_system.unlink(path)
    # ruleid: python-enforce-remove-file-helper
    remove = os.remove
    # ok: python-enforce-remove-file-helper
    remove_file(path)
    # ok: python-enforce-remove-file-helper
    remove_file(path, missing_ok=True)
    # ok: python-enforce-remove-file-helper
    os.rmdir(path)
    # ok: python-enforce-remove-file-helper
    os.removedirs(path)

# ------------------------------------------------------------------------------
# `Path` method: on an instance or on the class, called or not.
# ------------------------------------------------------------------------------

def remove_path(path: Path, stack: contextlib.ExitStack) -> None:
    # ruleid: python-enforce-remove-file-helper
    path.unlink()
    # ruleid: python-enforce-remove-file-helper
    path.unlink(missing_ok=True)
    # ruleid: python-enforce-remove-file-helper
    (path / "file").unlink()
    # ruleid: python-enforce-remove-file-helper
    Path.unlink(path)
    # ruleid: python-enforce-remove-file-helper
    stack.callback(path.unlink)
    # ok: python-enforce-remove-file-helper
    stack.callback(remove_file, path)
    # ok: python-enforce-remove-file-helper
    path.rmdir()
