from contextlib import ExitStack
from pathlib import Path, PurePath

import xcp_storage.utils.file
from xcp_storage.utils.file import create_temporary_directory, create_temporary_file

# ------------------------------------------------------------------------------
# Assigned a path object: `x = Path(...)`, `x = Path(...) / "y"`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-variable-suffix
config = Path("/etc/a.conf")
# ruleid: python-enforce-path-variable-suffix
runtime_dir = PurePath("/run") / "x"
# ruleid: python-enforce-path-variable-suffix
annotated: Final = Path("/a")
# ok: python-enforce-path-variable-suffix
config_path = PurePath("/etc/a.conf")
# ok: python-enforce-path-variable-suffix
CONFIG_PATH: Final = PurePath("/etc/a.conf")

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-path-variable-suffix
        self.runtime = Path("/run") / "x"

# ------------------------------------------------------------------------------
# Assigned a path by an XCP helper: `with create_temporary_directory(...) as x`.
# ------------------------------------------------------------------------------

def use_temporary_directory(stack: ExitStack) -> None:
    # ruleid: python-enforce-path-variable-suffix
    with create_temporary_directory(Path("/var/lib/backup")) as backup:
        pass
    # ruleid: python-enforce-path-variable-suffix
    with xcp_storage.utils.file.create_temporary_directory() as backup2:
        pass
    # ruleid: python-enforce-path-variable-suffix
    with open("a") as file, create_temporary_directory() as backup3:
        pass
    # ruleid: python-enforce-path-variable-suffix
    backup4 = stack.enter_context(create_temporary_directory())
    # ruleid: python-enforce-path-variable-suffix
    annotated_backup: Final = stack.enter_context(create_temporary_directory())
    # ok: python-enforce-path-variable-suffix
    with create_temporary_directory(Path("/var/lib/backup")) as tmp_backup_path:
        pass
    # ok: python-enforce-path-variable-suffix
    tmp_dir_path = stack.enter_context(create_temporary_directory())
    # ok: python-enforce-path-variable-suffix
    with create_temporary_file(Path("/var/lib/backup")) as tmp_file:
        pass
    # ok: python-enforce-path-variable-suffix
    backup_context = create_temporary_directory()

class TemporaryHolder:
    def __init__(self, stack: ExitStack) -> None:
        # ruleid: python-enforce-path-variable-suffix
        self.backup = stack.enter_context(create_temporary_directory())
        # ok: python-enforce-path-variable-suffix
        self.backup_path = stack.enter_context(create_temporary_directory())

# ------------------------------------------------------------------------------
# Derived from a path variable: `x = base_path / "y"`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-variable-suffix
unit = runtime_dir_path / "systemd" / "user"
# ruleid: python-enforce-path-variable-suffix
locks_dir = RUNTIME_DIR_PATH / "locks"
# ruleid: python-enforce-path-variable-suffix
target = manager.runtime_dir_path / "x"
# ruleid: python-enforce-path-variable-suffix
annotated_derived: Final = RUNTIME_DIR_PATH / "x"
# ok: python-enforce-path-variable-suffix
unit_path = runtime_dir_path / "systemd" / "user"
# ok: python-enforce-path-variable-suffix
_LOCKS_DIR_PATH: Final = RUNTIME_DIR_PATH / "locks"
# ok: python-enforce-path-variable-suffix
ratio = total / count
# ok: python-enforce-path-variable-suffix
ratio = pathname / count

class DerivedHolder:
    def __init__(self, base_path: PurePath) -> None:
        # ruleid: python-enforce-path-variable-suffix
        self.socket = base_path / "sock"
        # ok: python-enforce-path-variable-suffix
        self.socket_path = base_path / "sock"

# ------------------------------------------------------------------------------
# Declared as a path: `x: Optional[Path]`, `x: StrPath`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-variable-suffix
final_target: Final[Path] = get_target()
# ruleid: python-enforce-path-variable-suffix
final_param_target: Final[StrPath]
# ok: python-enforce-path-variable-suffix
final_target_path: Final[Path] = get_target()

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-path-variable-suffix
        self.lock: Optional[Path] = None
        # ok: python-enforce-path-variable-suffix
        self.lock_path: Optional[Path] = None

# ruleid: python-enforce-path-variable-suffix
def bind(address: StrPath) -> None:
    pass

# ruleid: python-enforce-path-variable-suffix
def open_lock(lock: Optional[StrPath]) -> None:
    pass

# ok: python-enforce-path-variable-suffix
def bind_path(path: StrPath, socket_path: Union[str, PurePath]) -> None:
    pass

# ok: python-enforce-path-variable-suffix
def named(name: str) -> None:
    pass

# ------------------------------------------------------------------------------
# `EXEC_PATH_*` names: checked by `python-enforce-exec-path-variable-type`.
# ------------------------------------------------------------------------------

# ok: python-enforce-path-variable-suffix
_EXEC_PATH_X: StrPath = "/usr/bin/x"
# ok: python-enforce-path-variable-suffix
_EXEC_PATH_Y = Path("/usr/bin/y")
# ok: python-enforce-path-variable-suffix
EXEC_PATH_Z: Final = BIN_DIR_PATH / "z"
