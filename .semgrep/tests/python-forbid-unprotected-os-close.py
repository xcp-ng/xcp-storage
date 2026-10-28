import contextlib
import os

# ------------------------------------------------------------------------------
# `os.close` protected against `OSError`, or not.
# ------------------------------------------------------------------------------

def close(fd: int) -> None:
    # ruleid: python-forbid-unprotected-os-close
    os.close(fd)
    try:
        # ruleid: python-forbid-unprotected-os-close
        os.close(fd)
    except ValueError:
        pass
    try:
        # ok: python-forbid-unprotected-os-close
        os.close(fd)
    except OSError:
        pass
    try:
        # ok: python-forbid-unprotected-os-close
        os.close(fd)
    except OSError as error:
        log(error)
    with contextlib.suppress(OSError):
        # ok: python-forbid-unprotected-os-close
        os.close(fd)
