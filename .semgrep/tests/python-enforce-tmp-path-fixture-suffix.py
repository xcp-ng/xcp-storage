from pathlib import Path
import unittest.mock
from unittest import mock
from unittest.mock import patch

import pytest

MODULE = "module"

# ------------------------------------------------------------------------------
# Redirected with `patch(...)`: plain or f-string target, any decorator form.
# ------------------------------------------------------------------------------

@pytest.fixture
# ruleid: python-enforce-tmp-path-fixture-suffix
def proc_dir(tmp_path: Path) -> Path:
    path = tmp_path / "proc"
    with patch("module._PROC_DIR_PATH", path):
        yield path

@pytest.fixture
# ruleid: python-enforce-tmp-path-fixture-suffix
def fake_proc(tmp_path: Path) -> object:
    with patch(f"{MODULE}.PROC_DIR_PATH", tmp_path / "proc"):
        yield object()

@pytest.fixture(scope="function")
# ruleid: python-enforce-tmp-path-fixture-suffix
def os_release(request: object, tmp_path: Path) -> object:
    with patch("module._OS_RELEASE_PATH", tmp_path / "os-release") as mock_os_release_path:
        yield mock_os_release_path

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def proc_dir_path(tmp_path: Path) -> Path:
    path = tmp_path / "proc"
    with patch("module._PROC_DIR_PATH", path):
        yield path

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def proc_fs(tmp_path: Path) -> object:
    with patch(f"{MODULE}.PROC_DIR_PATH", tmp_path / "proc"):
        yield object()

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def path(tmp_path: Path) -> Path:
    with patch("module._PROC_DIR_PATH", tmp_path):
        yield tmp_path

# ------------------------------------------------------------------------------
# Redirected with `patch.object(...)`.
# ------------------------------------------------------------------------------

@pytest.fixture
# ruleid: python-enforce-tmp-path-fixture-suffix
def locks_dir(module: object, tmp_path: Path) -> Path:
    with patch.object(module, "_LOCKS_DIR_PATH", tmp_path):
        yield tmp_path

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def locks_dir_path(module: object, tmp_path: Path) -> Path:
    with patch.object(module, "_LOCKS_DIR_PATH", tmp_path):
        yield tmp_path

# ------------------------------------------------------------------------------
# Not a redirected path: no `tmp_path`, an executable (`_EXEC_PATH_*`), no patch, not a fixture.
# ------------------------------------------------------------------------------

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def proc_dir_without_tmp(other_path: Path) -> Path:
    with patch("module._PROC_DIR_PATH", other_path):
        yield other_path

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def service_manager(tmp_path: Path) -> object:
    with patch("module._EXEC_PATH_SYSTEMCTL", str(tmp_path / "systemctl")):
        yield object()

@pytest.fixture
# ok: python-enforce-tmp-path-fixture-suffix
def lock_backend(tmp_path: Path) -> object:
    yield tmp_path / "lock"

# ok: python-enforce-tmp-path-fixture-suffix
def redirect(tmp_path: Path) -> None:
    with patch("module._PROC_DIR_PATH", tmp_path):
        pass

# ------------------------------------------------------------------------------
# Prefixed forms: `unittest.mock.patch`, `mock.patch.object`.
# ------------------------------------------------------------------------------

@pytest.fixture
# ruleid: python-enforce-tmp-path-fixture-suffix
def proc(tmp_path: Path) -> Path:
    with unittest.mock.patch("module._PROC_DIR_PATH", tmp_path):
        yield tmp_path

@pytest.fixture
# ruleid: python-enforce-tmp-path-fixture-suffix
def locks(module: object, tmp_path: Path) -> Path:
    with mock.patch.object(module, "_LOCKS_DIR_PATH", tmp_path):
        yield tmp_path
