from pathlib import Path

# ------------------------------------------------------------------------------
# Assigned an opened file: each way to open a file.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-file-variable-suffix
handle1 = open("x")
# ruleid: python-enforce-file-variable-suffix
handle2 = io.open("x")
# ruleid: python-enforce-file-variable-suffix
handle3 = os.fdopen(3)
# ruleid: python-enforce-file-variable-suffix
handle4 = tempfile.NamedTemporaryFile()
# ruleid: python-enforce-file-variable-suffix
handle5 = tempfile.TemporaryFile()
# ruleid: python-enforce-file-variable-suffix
handle6 = tempfile.SpooledTemporaryFile()
# ruleid: python-enforce-file-variable-suffix
handle7 = sock.makefile()
# ok: python-enforce-file-variable-suffix
handle8 = open_connection()
# ok: python-enforce-file-variable-suffix
LOG_FILE = open("x")

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-file-variable-suffix
        self.handle = open("x")

# ------------------------------------------------------------------------------
# Assigned an opened file: `path.open()`, `with ... as x`.
# ------------------------------------------------------------------------------

def read(lock_path: Path) -> None:
    # ruleid: python-enforce-file-variable-suffix
    handle = lock_path.open()
    # ruleid: python-enforce-file-variable-suffix
    upper = LOCK_PATH.open()
    # ruleid: python-enforce-file-variable-suffix
    with self._path.open() as stream:
        pass
    # ruleid: python-enforce-file-variable-suffix
    with Path("/a").open() as stream2:
        pass
    # ok: python-enforce-file-variable-suffix
    lock_file = LOCK_PATH.open()
    # ok: python-enforce-file-variable-suffix
    content = lock_name.open()
    # ok: python-enforce-file-variable-suffix
    with open("a") as (first, second):
        pass

# ------------------------------------------------------------------------------
# Declared as a file: `x: Optional[TextIO]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-file-variable-suffix
reader: TextIO
# ruleid: python-enforce-file-variable-suffix
reader2: Optional[TextIO] = None
# ruleid: python-enforce-file-variable-suffix
typed: TextIO = open("x")
# ok: python-enforce-file-variable-suffix
log_file: TextIO = open("x")

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-file-variable-suffix
        self.reader: Optional[TextIO] = None
        # ok: python-enforce-file-variable-suffix
        self.reader_file: Optional[TextIO] = None

# ------------------------------------------------------------------------------
# Declared as a file, type wrappers: parameters.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-file-variable-suffix
def write(out: Union[IO[str], TextIO]) -> None:
    pass

# ruleid: python-enforce-file-variable-suffix
def write_final(out: Final[TextIO]) -> None:
    pass

# ok: python-enforce-file-variable-suffix
def write_ok(out_file: Union[IO[str], None], text: str) -> None:
    pass
