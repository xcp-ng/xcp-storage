from pathlib import PurePath

# ------------------------------------------------------------------------------
# Assigned a string: `x = "..."`, `x = f"..."`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-variable-type
config_path = "/etc/a.conf"
# ruleid: python-enforce-path-variable-type
socket_path = f"/run/{name}.sock"
# ok: python-enforce-path-variable-type
config_path = PurePath("/etc/a.conf")
# ok: python-enforce-path-variable-type
lock_path = str(path)
# ok: python-enforce-path-variable-type
_EXEC_PATH_DRBDSETUP: Final = "/usr/sbin/drbdsetup"

class Holder:
    def __init__(self, name: str) -> None:
        # ruleid: python-enforce-path-variable-type
        self.config_path = "/etc/a.conf"
        # ruleid: python-enforce-path-variable-type
        self.socket_path = f"/run/{name}.sock"
        # ok: python-enforce-path-variable-type
        self.config_name = "a.conf"

# ------------------------------------------------------------------------------
# Declared as a string: `x: Optional[str]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-path-variable-type
alone_path: str
# ruleid: python-enforce-path-variable-type
cache_path: str = compute()
# ruleid: python-enforce-path-variable-type
final_path: Final[str] = get_target()
# ok: python-enforce-path-variable-type
final_name: Final[str] = get_target()

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-path-variable-type
        self.lock_path: str = compute()

# ruleid: python-enforce-path-variable-type
def bind(socket_path: str) -> None:
    pass

# ruleid: python-enforce-path-variable-type
def read(path: Optional[str] = None) -> None:
    pass

# ok: python-enforce-path-variable-type
def bind_ok(socket_path: StrPath, path: PurePath, name: str) -> None:
    pass

# ok: python-enforce-path-variable-type
def read_ok(path: Optional[PurePath] = None, sub_path: Path = ROOT_PATH) -> None:
    pass
