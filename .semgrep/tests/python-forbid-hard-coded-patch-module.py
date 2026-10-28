from unittest import mock
import unittest.mock
from unittest.mock import patch

from xcp_storage.backends.drbd import Drbd

_DRBD_MODULE = Drbd.__module__

# ------------------------------------------------------------------------------
# Patch of a target: `patch(...)`, as a decorator, a context manager or a call.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-hard-coded-patch-module
@patch("xcp_storage.backends.drbd.run_command", autospec=True)
def test_decorator() -> None:
    pass

def test_patch(name: str) -> None:
    # ruleid: python-forbid-hard-coded-patch-module
    with patch("xcp_storage.backends.drbd.run_command", autospec=True) as mock_run_command:
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with mock.patch('xcp_storage.backends.drbd.run_command', autospec=True) as mock_run_command:
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with unittest.mock.patch("xcp_storage.backends.drbd._DRBD_DEBUG_RESOURCES_PATH", "/tmp"):
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch(f"xcp_storage.backends.drbd.{name}", autospec=True) as mock_function:
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch(rf"xcp_storage.backends.drbd.{name}", autospec=True) as mock_function:
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch("xcp_storage.backends.drbd." + name, autospec=True) as mock_function:
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch("""xcp_storage.backends.drbd.run_command""", autospec=True) as mock_run_command:
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch(f"{_DRBD_MODULE}.run_command", autospec=True) as mock_run_command:
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch("time.sleep", autospec=True) as mock_sleep:
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch("xcp_storage_tools.module.function", autospec=True) as mock_function:
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch("tests.xcp_storage.function", autospec=True) as mock_function:
        pass

# ------------------------------------------------------------------------------
# Target given by keyword: `patch(target=...)`.
# ------------------------------------------------------------------------------

def test_patch_keyword() -> None:
    # ruleid: python-forbid-hard-coded-patch-module
    with patch(target="xcp_storage.backends.drbd.run_command", autospec=True) as mock_run_command:
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch(target=f"{_DRBD_MODULE}.run_command", autospec=True) as mock_run_command:
        pass

# ------------------------------------------------------------------------------
# Patch of several attributes of a module: `patch.multiple(...)`.
# ------------------------------------------------------------------------------

def test_patch_multiple() -> None:
    # ruleid: python-forbid-hard-coded-patch-module
    with patch.multiple("xcp_storage.backends.drbd", MAX_SIZE=3):
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch.multiple(target="xcp_storage.backends.drbd", MAX_SIZE=3):
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch.multiple(_DRBD_MODULE, MAX_SIZE=3):
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch.multiple(target=_DRBD_MODULE, MAX_SIZE=3):
        pass

# ------------------------------------------------------------------------------
# Patch of a dictionary: `patch.dict(...)`.
# ------------------------------------------------------------------------------

def test_patch_dict() -> None:
    # ruleid: python-forbid-hard-coded-patch-module
    with patch.dict("xcp_storage.backends.drbd._CACHE", {"key": "value"}):
        pass
    # ruleid: python-forbid-hard-coded-patch-module
    with patch.dict(in_dict="xcp_storage.backends.drbd._CACHE", values={"key": "value"}):
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch.dict(f"{_DRBD_MODULE}._CACHE", {"key": "value"}):
        pass
    # ok: python-forbid-hard-coded-patch-module
    with patch.dict("os.environ", {"KEY": "value"}):
        pass

# ------------------------------------------------------------------------------
# Patch of an attribute of an object: `patch.object(...)`, no module name.
# ------------------------------------------------------------------------------

def test_patch_object() -> None:
    # ok: python-forbid-hard-coded-patch-module
    with patch.object(Drbd, "get_local_openers", autospec=Drbd.get_local_openers) as mock_get_local_openers:
        pass
