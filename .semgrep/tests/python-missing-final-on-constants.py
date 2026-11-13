from enum import Enum

# ------------------------------------------------------------------------------
# Module constants.
# ------------------------------------------------------------------------------

# ruleid: python-missing-final-on-constants
TIMEOUT = 30
# ruleid: python-missing-final-on-constants
_PRIVATE_LIMIT = 4
# ruleid: python-missing-final-on-constants
TYPED: int = 3
# ok: python-missing-final-on-constants
TIMEOUT_OK: Final = 30
# ok: python-missing-final-on-constants
NAMED: Final[int] = 30
# ok: python-missing-final-on-constants
lower = 1
# ok: python-missing-final-on-constants
_ = compute()

# ------------------------------------------------------------------------------
# Type variables.
# ------------------------------------------------------------------------------

# ok: python-missing-final-on-constants
T = TypeVar("T")
# ok: python-missing-final-on-constants
P = ParamSpec("P")

# ------------------------------------------------------------------------------
# Class constants.
# ------------------------------------------------------------------------------

class Holder:
    # ruleid: python-missing-final-on-constants
    LIMIT = 5

class Child(Parent):
    # ruleid: python-missing-final-on-constants
    MEMBER = 1

# ------------------------------------------------------------------------------
# Enum members, prefixed base included.
# ------------------------------------------------------------------------------

class Color(Enum):
    # ok: python-missing-final-on-constants
    RED = 1

class PrefixedColor(enum.Enum):
    # ok: python-missing-final-on-constants
    BLUE = 2
