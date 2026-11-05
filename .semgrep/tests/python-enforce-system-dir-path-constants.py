from pathlib import Path

# ------------------------------------------------------------------------------
# Plain string: `"/proc/..."`, `Path("/run")`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-system-dir-path-constants
fd_dir_path = Path("/proc/self/fd")
# ruleid: python-enforce-system-dir-path-constants
locks_dir_path = Path("/run/xcp-storage/locks")
# ruleid: python-enforce-system-dir-path-constants
socket_path = "/run/lock.sock"
# ruleid: python-enforce-system-dir-path-constants
OTHER_PROC_PATH: Final = Path("/proc")
# ruleid: python-enforce-system-dir-path-constants
run_dir_path = Path("/run")
# ruleid: python-enforce-system-dir-path-constants
self_path = Path("/proc") / "self"
# ok: python-enforce-system-dir-path-constants
cmdline_path = PROC_DIR_PATH / str(pid) / "cmdline"
# ok: python-enforce-system-dir-path-constants
socket_path = RUNTIME_DIR_PATH / "lock.sock"
# ok: python-enforce-system-dir-path-constants
other_path = Path("/procedure/x")
# ok: python-enforce-system-dir-path-constants
other_path = Path("/running")
# ok: python-enforce-system-dir-path-constants
other_path = Path("/var/run/x")
# ok: python-enforce-system-dir-path-constants
legacy_path = Path("/var/run/xcp-storage")
# ok: python-enforce-system-dir-path-constants
legacy_lock_path = Path("/var/lock/subsys")
# ok: python-enforce-system-dir-path-constants
var_path = Path("/var/runner")
# ok: python-enforce-system-dir-path-constants
var_lib_path = Path("/var/lib/xcp")

# ------------------------------------------------------------------------------
# F-string starting with the directory, whatever its prefix.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-system-dir-path-constants
cmdline_path = Path(f"/proc/{pid}/cmdline")
# ruleid: python-enforce-system-dir-path-constants
socket_path = f"/run/{name}.sock"
# ruleid: python-enforce-system-dir-path-constants
socket_path = f'/run/{name}.sock'
# ruleid: python-enforce-system-dir-path-constants
read(f"/proc/{pid}/status")
# ruleid: python-enforce-system-dir-path-constants
raw_path = rf"/proc/{pid}/cmdline"
# ruleid: python-enforce-system-dir-path-constants
upper_path = F"/run/{name}"
# ruleid: python-enforce-system-dir-path-constants
raw_upper_path = FR"/run/{name}"
# ok: python-enforce-system-dir-path-constants
message = f"See {PROC_DIR_PATH}/self"
# ok: python-enforce-system-dir-path-constants
other_path = f"/runtime/{name}"
# ok: python-enforce-system-dir-path-constants
other_path = f"{base}/proc/{pid}"
# ok: python-enforce-system-dir-path-constants
nested_path = rf"{base}/var/run/{name}"

# ------------------------------------------------------------------------------
# Only real f-strings: not this comment, f"/proc/{pid}", nor the text of a plain string.
# ------------------------------------------------------------------------------

# ok: python-enforce-system-dir-path-constants
text = 'f"/run/x"'

# ------------------------------------------------------------------------------
# Only the literal, not each use of a variable that holds it.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-system-dir-path-constants
MULTIPATH_FLAG = "/run/nonpersistent/multipath_enabled"
# ok: python-enforce-system-dir-path-constants
exists(MULTIPATH_FLAG)

# ------------------------------------------------------------------------------
# The definitions themselves.
# ------------------------------------------------------------------------------

# ok: python-enforce-system-dir-path-constants
PROC_DIR_PATH: Final = Path("/proc")
# ok: python-enforce-system-dir-path-constants
RUNTIME_DIR_PATH: Final = Path("/run")
