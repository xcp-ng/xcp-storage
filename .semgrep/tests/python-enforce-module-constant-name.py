from typing import Final

from xcp_storage.backends.drbd import Drbd
from xcp_storage.backends.linstor_controller import LinstorController

# ------------------------------------------------------------------------------
# Assigned the module of an object: `_DRBD_MODULE = Drbd.__module__`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-module-constant-name
DRBD_MODULE = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_drbd_module = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_MODULE_DRBD = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_MODULE = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_DRBD_MOD = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_DRBD__MODULE = Drbd.__module__
# ruleid: python-enforce-module-constant-name
_DRBD_MODULE_NAME = Drbd.__module__
# ok: python-enforce-module-constant-name
_DRBD_MODULE = Drbd.__module__
# ok: python-enforce-module-constant-name
_LINSTOR_CONTROLLER_MODULE = LinstorController.__module__
# ok: python-enforce-module-constant-name
_DRBD9_MODULE = Drbd.__module__
# ok: python-enforce-module-constant-name
_OTHER_NAME = Drbd.__name__
# ok: python-enforce-module-constant-name
_MODULE_NAME = "module"

# ------------------------------------------------------------------------------
# Also matches annotated assignments (`x: T = ...`).
# ------------------------------------------------------------------------------

# ruleid: python-enforce-module-constant-name
_drbd: Final = Drbd.__module__
# ok: python-enforce-module-constant-name
_ANNOTATED_DRBD_MODULE: Final = Drbd.__module__

# ------------------------------------------------------------------------------
# Module level only: a function or a class may read `__module__` under another name.
# ------------------------------------------------------------------------------

def get_module_name() -> str:
    # ok: python-enforce-module-constant-name
    module_name = Drbd.__module__
    return module_name

async def get_module_name_async() -> str:
    # ok: python-enforce-module-constant-name
    module_name = Drbd.__module__
    return module_name

class LinstorServiceSpec:
    # ok: python-enforce-module-constant-name
    module_name = LinstorController.__module__

    @property
    def patched_module(self) -> str:
        # ok: python-enforce-module-constant-name
        name = self.__class__.__module__
        return name
