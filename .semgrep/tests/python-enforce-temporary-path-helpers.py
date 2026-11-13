from pathlib import Path
import tempfile
import tempfile as temporary
from tempfile import mkstemp, NamedTemporaryFile
import uuid

from xcp_storage.utils.file import create_temporary_directory, create_temporary_file

# ------------------------------------------------------------------------------
# `tempfile` function creating a file or a directory: called, or passed as a function.
# ------------------------------------------------------------------------------

def create_with_tempfile(path: Path) -> None:
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.mkstemp(dir=str(path.parent))
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.mkdtemp(dir=str(path.parent))
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.mktemp()
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.NamedTemporaryFile("w", delete=False)
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.TemporaryFile()
    # ruleid: python-enforce-temporary-path-helpers
    tempfile.SpooledTemporaryFile()
    # ruleid: python-enforce-temporary-path-helpers
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        pass
    # ruleid: python-enforce-temporary-path-helpers
    temporary.mkstemp()
    # ruleid: python-enforce-temporary-path-helpers
    mkstemp()
    # ruleid: python-enforce-temporary-path-helpers
    NamedTemporaryFile()
    # ruleid: python-enforce-temporary-path-helpers
    create = tempfile.mkdtemp
    # ok: python-enforce-temporary-path-helpers
    create_temporary_directory(path)
    # ok: python-enforce-temporary-path-helpers
    with create_temporary_file(path) as tmp_file:
        pass
    # ok: python-enforce-temporary-path-helpers
    tempfile.gettempdir()
    # ok: python-enforce-temporary-path-helpers
    tempfile.gettempprefix()

# ------------------------------------------------------------------------------
# Temporary name built by hand: a string ending with `.tmp` (f-strings included, which `"..."` does not match).
# ------------------------------------------------------------------------------

def build_name(path: Path) -> None:
    # ruleid: python-enforce-temporary-path-helpers
    tmp_path = path.with_name(f".{path.name}.tmp")
    # ruleid: python-enforce-temporary-path-helpers
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4()}.tmp")
    # ruleid: python-enforce-temporary-path-helpers
    tmp_path = path.with_name('.volumes.db.tmp')
    # ruleid: python-enforce-temporary-path-helpers
    tmp_path = path.with_suffix(".tmp")
    # ruleid: python-enforce-temporary-path-helpers
    tmp_path = Path(str(path) + ".tmp")
    # ok: python-enforce-temporary-path-helpers
    path.with_name(f".{path.name}.tmp.old")
    # ok: python-enforce-temporary-path-helpers
    Path("/var/tmp") / path.name
    # ok: python-enforce-temporary-path-helpers
    path.with_suffix(".tmpl")
