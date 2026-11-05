from enum import Enum, IntFlag

# ------------------------------------------------------------------------------
# Members of an `Enum` subclass.
# ------------------------------------------------------------------------------

class Color(Enum):
    # ruleid: python-enforce-enum-uppercase-members
    green = 2
    # ruleid: python-enforce-enum-uppercase-members
    Blue = 3
    # ok: python-enforce-enum-uppercase-members
    RED = 1

    def method(self) -> None:
        # ok: python-enforce-enum-uppercase-members
        local = 1

# ------------------------------------------------------------------------------
# Enum base among other bases.
# ------------------------------------------------------------------------------

class Mode(Base, IntFlag):
    # ruleid: python-enforce-enum-uppercase-members
    read = 1
    # ok: python-enforce-enum-uppercase-members
    WRITE_2 = 2

# ------------------------------------------------------------------------------
# Prefixed enum base.
# ------------------------------------------------------------------------------

class Prefixed(enum.IntEnum):
    # ruleid: python-enforce-enum-uppercase-members
    lower = 1

# ------------------------------------------------------------------------------
# Not an enum.
# ------------------------------------------------------------------------------

class NotEnum(Base):
    # ok: python-enforce-enum-uppercase-members
    lower = 1
