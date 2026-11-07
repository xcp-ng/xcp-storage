# ------------------------------------------------------------------------------
# Conversion by `1024`: `size_kib * 1024`, `size // 1024`...
# ------------------------------------------------------------------------------

def convert(size, size_kib) -> None:
    # ruleid: python-enforce-size-unit-constants
    size = size_kib * 1024
    # ruleid: python-enforce-size-unit-constants
    size = 1024 * size_kib
    # ruleid: python-enforce-size-unit-constants
    size_kib = size / 1024
    # ruleid: python-enforce-size-unit-constants
    size_kib = size // 1024
    # ruleid: python-enforce-size-unit-constants
    size *= 1024
    # ruleid: python-enforce-size-unit-constants
    size /= 1024
    # ruleid: python-enforce-size-unit-constants
    size //= 1024
    # ruleid: python-enforce-size-unit-constants
    size = size_kib * 0x400
    # ruleid: python-enforce-size-unit-constants
    size = size_kib * 1_024
    # ruleid: python-enforce-size-unit-constants
    size = 4 * 1024 * 1024
    # ok: python-enforce-size-unit-constants
    size = size_kib * KIB
    # ok: python-enforce-size-unit-constants
    size_kib = size // KIB
    # ok: python-enforce-size-unit-constants
    size = size_kib * 1000
    # ok: python-enforce-size-unit-constants
    size = size_kib + 1024

# Not a conversion: a count, a buffer length.
# ok: python-enforce-size-unit-constants
FD_SETSIZE = 1024
# ok: python-enforce-size-unit-constants
data = reader.read(1024)

# The units themselves.
# ok: python-enforce-size-unit-constants
KIB = 1024
# ok: python-enforce-size-unit-constants
MIB = KIB * KIB

def use_units() -> None:
    # ok: python-enforce-size-unit-constants
    size = 4 * MIB

# ------------------------------------------------------------------------------
# Power of `1024`: `1024 ** 3`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-size-unit-constants
GIB_SIZE = 1024 ** 3
# ok: python-enforce-size-unit-constants
BIG_NUMBER = 1000 ** 3
# ok: python-enforce-size-unit-constants
SQUARE = KIB ** 2

# ------------------------------------------------------------------------------
# Shift by a unit: `1 << 20`, `size >> 30`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-size-unit-constants
KIB_SIZE = 1 << 10
# ruleid: python-enforce-size-unit-constants
MIB_SIZE = 1 << 20
# ruleid: python-enforce-size-unit-constants
GIB_SIZE = 4 << 30
# ruleid: python-enforce-size-unit-constants
TIB_SIZE = 1 << 40
# ruleid: python-enforce-size-unit-constants
size_mib = size >> 20
# ok: python-enforce-size-unit-constants
flags = 1 << 8
# ok: python-enforce-size-unit-constants
flags = 1 << 100
# ok: python-enforce-size-unit-constants
value = value >> 1
# ok: python-enforce-size-unit-constants
mask = 1 << shift

# ------------------------------------------------------------------------------
# Unit written as a number: MiB, GiB, TiB.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-size-unit-constants
SIZE = 1048576
# ruleid: python-enforce-size-unit-constants
SIZE = 0x100000
# ruleid: python-enforce-size-unit-constants
SIZE = 1073741824
# ruleid: python-enforce-size-unit-constants
SIZE = 1099511627776
# ok: python-enforce-size-unit-constants
SIZE = 1000000
