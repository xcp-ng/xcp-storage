# ------------------------------------------------------------------------------
# `import X` of a module always imported with `from X import ...`.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-import-of-from-only-modules
import pathlib
# ruleid: python-forbid-import-of-from-only-modules
import enum, functools
# ruleid: python-forbid-import-of-from-only-modules
import xcp_storage.utils.process
# ruleid: python-forbid-import-of-from-only-modules
import tests.network.tls
# ruleid: python-forbid-import-of-from-only-modules
import unittest.mock
# ok: python-forbid-import-of-from-only-modules
from pathlib import Path
# ok: python-forbid-import-of-from-only-modules
import os
# ok: python-forbid-import-of-from-only-modules
import unittest
# ok: python-forbid-import-of-from-only-modules
import tests

# ------------------------------------------------------------------------------
# Modules imported with an alias.
# ------------------------------------------------------------------------------

# ok: python-forbid-import-of-from-only-modules
import xcp_storage.log as log
# ok: python-forbid-import-of-from-only-modules
import xcp_storage.rpc.api as api
# ok: python-forbid-import-of-from-only-modules
import xcp_storage.rpc.modules.echo as echo

# ------------------------------------------------------------------------------
# Not an import: text of a string.
# ------------------------------------------------------------------------------

"""
import pathlib
"""
