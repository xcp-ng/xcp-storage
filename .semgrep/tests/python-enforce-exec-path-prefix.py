from pathlib import Path, PurePath

# ------------------------------------------------------------------------------
# Assigned an executable path: `x = "/usr/bin/x"`, `x = Path("/usr/bin/x")`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exec-path-prefix
DRBDSETUP = "/usr/sbin/drbdsetup"
# ruleid: python-enforce-exec-path-prefix
DRBDSETUP = Path("/usr/sbin/drbdsetup")
# ruleid: python-enforce-exec-path-prefix
SYSTEMCTL: Final = "/usr/bin/systemctl"
# ok: python-enforce-exec-path-prefix
_EXEC_PATH_SYSTEMCTL: Final = "/usr/bin/systemctl"
# ok: python-enforce-exec-path-prefix
CONFIG_PATH = PurePath("/etc/a.conf")

class Runner:
    def __init__(self) -> None:
        # ruleid: python-enforce-exec-path-prefix
        self.drbdsetup = "/usr/sbin/drbdsetup"
        # ruleid: python-enforce-exec-path-prefix
        self.drbdadm = Path("/usr/sbin/drbdadm")
        # ruleid: python-enforce-exec-path-prefix
        self.drbdmeta: str = "/usr/sbin/drbdmeta"
        # ok: python-enforce-exec-path-prefix
        self.config = "/etc/a.conf"

# ------------------------------------------------------------------------------
# Assigned the result of `get_exec_path`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-exec-path-prefix
SS: Final = get_exec_path("/usr/sbin/ss", {})

class ExecPathRunner:
    def __init__(self) -> None:
        # ruleid: python-enforce-exec-path-prefix
        self.ss = get_exec_path("/usr/sbin/ss", {})
        # ok: python-enforce-exec-path-prefix
        self._EXEC_PATH_SS = get_exec_path("/usr/sbin/ss", {})

# ------------------------------------------------------------------------------
# Out of scope: `PurePath(...)` (an executable is a real local file, so a `Path`).
# ------------------------------------------------------------------------------

# ok: python-enforce-exec-path-prefix
DRBDSETUP = PurePath("/usr/sbin/drbdsetup")
# ok: python-enforce-exec-path-prefix
_EXEC_PATH_DRBDSETUP = PurePath("/usr/sbin/drbdsetup")

class Tool:
    def __init__(self) -> None:
        # ok: python-enforce-exec-path-prefix
        self.binary = PurePath("/usr/bin/tool")
