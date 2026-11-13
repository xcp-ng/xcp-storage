import os
import unittest.mock
from unittest import mock
from unittest.mock import DEFAULT, patch

import pytest

# ------------------------------------------------------------------------------
# Decorator of a function: target and `autospec=True` only.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep")
def test_without_autospec() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep", autospec=False)
def test_autospec_false() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep", return_value=None, autospec=True)
def test_other_argument() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep", None)
def test_value() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch("time.sleep", autospec=True)
def test_simple() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch('time.sleep', autospec=True)
def test_simple_single_quotes() -> None:
    pass

# ------------------------------------------------------------------------------
# Target outside the allowed external functions: project object, f-string, other external function.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-simple-patch-decorator
@patch("xcp_storage.utils.service.run_command", autospec=True)
def test_project_target() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch(f"{MODULE}.run_command", autospec=True)
def test_f_string_target() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch("socket.socket", autospec=True)
def test_other_external_target() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleeper", autospec=True)
def test_longer_external_target() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch("fcntl.flock", autospec=True)
def test_flock() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch("os.close", autospec=True)
def test_close() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch("socket.socketpair", autospec=True)
def test_socketpair() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@patch("time.monotonic", autospec=True)
def test_monotonic() -> None:
    pass

# ------------------------------------------------------------------------------
# Decorator `patch.object`, `patch.multiple` or `patch.dict`: the target is not a plain string.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-simple-patch-decorator
@patch.object(Target, "method", autospec=True)
def test_patch_object() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch.multiple("os", autospec=True, close=DEFAULT)
def test_patch_multiple() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@patch.dict(os.environ, {"LANG": "C"})
def test_patch_dict() -> None:
    pass

# ------------------------------------------------------------------------------
# Decorator of a class or a method, among other decorators.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep")
class TestClass:
    # ruleid: python-enforce-simple-patch-decorator
    @patch("time.monotonic")
    @pytest.mark.parametrize("value", [1])
    def test_method(self) -> None:
        pass

    # ok: python-enforce-simple-patch-decorator
    @pytest.mark.parametrize("value", [1])
    @patch("time.monotonic", autospec=True)
    def test_simple_method(self) -> None:
        pass

# ok: python-enforce-simple-patch-decorator
@patch("time.monotonic", autospec=True)
# ruleid: python-enforce-simple-patch-decorator
@patch("time.sleep")
# ok: python-enforce-simple-patch-decorator
@pytest.mark.parametrize("value", [1])
def test_several_decorators() -> None:
    pass

# ------------------------------------------------------------------------------
# Not a decorator: `patch` called or used as a context manager.
# ------------------------------------------------------------------------------

def test_context_manager() -> None:
    # ok: python-enforce-simple-patch-decorator
    with patch("xcp_storage.utils.service.run_command"):
        pass
    # ok: python-enforce-simple-patch-decorator
    patcher = patch("time.sleep", return_value=None)

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch.object`, `mock.patch.dict`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-simple-patch-decorator
@unittest.mock.patch("time.sleep")
def test_prefixed() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@mock.patch.object(Target, "method", autospec=True)
def test_prefixed_patch_object() -> None:
    pass

# ruleid: python-enforce-simple-patch-decorator
@mock.patch.dict(os.environ, {"LANG": "C"})
def test_prefixed_patch_dict() -> None:
    pass

# ok: python-enforce-simple-patch-decorator
@unittest.mock.patch("time.sleep", autospec=True)
def test_prefixed_simple() -> None:
    pass
