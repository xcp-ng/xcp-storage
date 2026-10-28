import os
import sys
from unittest import mock
import unittest.mock
from unittest.mock import patch

import pytest

import xcp_storage.log as log
from xcp_storage.network.protocol.xcp import XcpProtocol
from xcp_storage.utils.lock.fifo import (
    _MIN_ACQUIRE_TIMEOUT,
    FifoLock,
)

from tests.utils.helpers import Helper

MODULE = "xcp_storage.utils.process"
TARGET = "os.close"

# ------------------------------------------------------------------------------
# Target given as a string: allowed external functions only.
# ------------------------------------------------------------------------------

def test_string_target() -> None:
    # ruleid: python-enforce-simple-patch-in-test
    with patch("xcp_storage.utils.service.run_command", autospec=True) as mock_run_command:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch(f"{MODULE}.PROC_DIR_PATH", "/tmp"):
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch(f"os.{os.close.__name__}", autospec=True) as mock_close:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch(TARGET, autospec=True) as mock_close:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch("socket.socket", autospec=True) as mock_socket:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch("os.close_range", autospec=True) as mock_close_range:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch("fcntl.flock", autospec=True) as mock_flock:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch("os.close", autospec=True) as mock_close:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch("socket.socketpair", autospec=True) as mock_socketpair:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch('time.monotonic', autospec=True) as mock_monotonic:
        pass

class TestClass:
    # ruleid: python-enforce-simple-patch-in-test
    @patch("xcp_storage.utils.service.run_command", autospec=True)
    def test_decorator(self) -> None:
        pass

    # ok: python-enforce-simple-patch-in-test
    @patch("time.sleep", autospec=True)
    def test_allowed_decorator(self) -> None:
        pass

    def test_nested_function(self) -> None:
        def run() -> None:
            # ruleid: python-enforce-simple-patch-in-test
            with patch("xcp_storage.utils.service.run_command", autospec=True) as mock_run_command:
                pass

# ------------------------------------------------------------------------------
# Several targets or a dictionary: `patch.multiple(...)`, `patch.dict(...)`.
# ------------------------------------------------------------------------------

def test_patch_multiple() -> None:
    # ruleid: python-enforce-simple-patch-in-test
    with patch.multiple("os", autospec=True, close=mock.DEFAULT) as mock_functions:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.dict(os.environ, {"LANG": "C"}):
        pass

# ------------------------------------------------------------------------------
# Attribute of an imported name, or of its attribute; not of an object created by the test.
# ------------------------------------------------------------------------------

def test_patch_object(rpc_client: object) -> None:
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(XcpProtocol, "MAX_PACKET_SIZE", 3):
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(FifoLock, "_try_server_lock", autospec=True) as mock_try_server_lock:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(log, "_LOGGER", autospec=True) as mock_logger:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(log._LOGGER, "error", autospec=True) as mock_error:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(os, "close", autospec=True) as mock_close:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(sys, "__excepthook__", autospec=True) as mock_excepthook:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with patch.object(Helper, "method", autospec=True) as mock_method:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch.object(rpc_client, "_call", autospec=True) as mock_call:
        pass
    # ok: python-enforce-simple-patch-in-test
    with patch.object(rpc_client._protocol, "send_packet", autospec=True) as mock_send_packet:
        pass

# ------------------------------------------------------------------------------
# Not a test: a fixture, or any other function.
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_run_command() -> object:
    # ok: python-enforce-simple-patch-in-test
    with patch("xcp_storage.utils.service.run_command", autospec=True) as mock_run_command:
        yield mock_run_command

def run() -> None:
    # ok: python-enforce-simple-patch-in-test
    with patch.object(FifoLock, "_try_server_lock", autospec=True) as mock_try_server_lock:
        pass

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch.object`, `mock.patch.multiple`, `mock.patch.dict`.
# ------------------------------------------------------------------------------

def test_prefixed() -> None:
    # ruleid: python-enforce-simple-patch-in-test
    with unittest.mock.patch("xcp_storage.utils.service.run_command", autospec=True) as mock_run_command:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with mock.patch.object(FifoLock, "_try_server_lock", autospec=True) as mock_try_server_lock:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with unittest.mock.patch.multiple("os", autospec=True, close=mock.DEFAULT) as mock_functions:
        pass
    # ruleid: python-enforce-simple-patch-in-test
    with mock.patch.dict(os.environ, {"LANG": "C"}):
        pass
    # ok: python-enforce-simple-patch-in-test
    with unittest.mock.patch("os.close", autospec=True) as mock_close:
        pass
