from pathlib import Path, PurePath, PosixPath

from xcp_storage.config.platform import get_exec_path
from xcp_storage.typing import Final, Optional, StrPath

BIN_DIR_PATH: Final = Path("/usr/bin")

# ------------------------------------------------------------------------------
# Assigned a path object: `x = Path(...)`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_A = Path("/usr/sbin/a")
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_B: Final = Path("/usr/sbin/b")
# ruleid: python-enforce-exec-path-variable-type
EXEC_PATH_C: Final = PurePath("/usr/sbin/c")
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_D: Final = PosixPath("/usr/sbin/d")
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_SYSTEMCTL: Final = "/usr/bin/systemctl"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_SS: Final = get_exec_path("/usr/sbin/ss", {"debian": "/usr/bin/ss"})
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_R: Final = get_exec_path("/usr/sbin/r", {}).strip()
# ok: python-enforce-exec-path-variable-type
CONFIG_PATH: Final = Path("/etc/xcp-storage/rpc.conf")

class Tool:
    def __init__(self, base_path: Path) -> None:
        # ruleid: python-enforce-exec-path-variable-type
        self._EXEC_PATH_K = Path("/usr/sbin/k")
        # ok: python-enforce-exec-path-variable-type
        self._EXEC_PATH_M = "/usr/sbin/m"

# ------------------------------------------------------------------------------
# Derived with `/`: `x = Path(...) / "y"`, `x = base_path / "y"`, whatever the base.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_E: Final = Path("/usr") / "sbin" / "e"
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_F: Final = BIN_DIR_PATH / "f"
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_G = BIN_DIR_PATH / "g"
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_S = self._path/"s"
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_X = base / "x"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_O: Final = str(BIN_DIR_PATH / "o")
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_P: Final = f"{BIN_DIR_PATH}/p"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_Q: Final = "/usr/sbin/" + "q"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_T: Final = get_exec_path("/usr/sbin/t", {}) + "/x"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_U: Final = os.path.join(base, "u")
# ok: python-enforce-exec-path-variable-type
daemon_exec_path: Path = BIN_DIR_PATH / "daemon"

class DerivedTool:
    def __init__(self, base_path: Path) -> None:
        # ruleid: python-enforce-exec-path-variable-type
        self._EXEC_PATH_N = base_path / "n"
        # ruleid: python-enforce-exec-path-variable-type
        self._EXEC_PATH_P = Path("/usr") / "p"

# ------------------------------------------------------------------------------
# Declared as a path object: `x: Final[Path]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_H: Final[Path] = get_exec_path("/usr/sbin/h", {})
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_I: Optional[PurePath] = None
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_J: StrPath
# ruleid: python-enforce-exec-path-variable-type
_EXEC_PATH_V: Union[str, Path] = "/usr/bin/v"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_N: Final[str] = "/usr/sbin/n"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_W: Final[str] = "/usr/bin/w"
# ok: python-enforce-exec-path-variable-type
_EXEC_PATH_PATTERN: Optional[str] = None

class DeclaredTool:
    def __init__(self, base_path: Path) -> None:
        # ruleid: python-enforce-exec-path-variable-type
        self.EXEC_PATH_L: Path = base_path / "l"
        # ruleid: python-enforce-exec-path-variable-type
        self.EXEC_PATH_O: Optional[Path] = None
        # ok: python-enforce-exec-path-variable-type
        self.EXEC_PATH_Q: Optional[str] = None
