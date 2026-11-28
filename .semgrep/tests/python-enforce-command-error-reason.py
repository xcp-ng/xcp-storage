import xcp_storage.utils.process
from xcp_storage.utils.process import CommandError, CommandTimeoutError, run_command

# ------------------------------------------------------------------------------
# Interpolated in an f-string, with or without a conversion.
# ------------------------------------------------------------------------------

def interpolated(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None
    try:
        run_command(args)
    except CommandTimeoutError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceTimeoutError(f"Failed: `{e!s}`.") from None
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e!r}`.") from None
    try:
        run_command(args)
    except xcp_storage.utils.process.CommandError as e:
        # ruleid: python-enforce-command-error-reason
        message = f"Failed: `{e}`."
    try:
        run_command(args)
    except (CommandError, OSError) as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e.reason}`.", e.code) from None
    try:
        run_command(args)
    except OSError as e:
        # ok: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None

# ------------------------------------------------------------------------------
# Converted.
# ------------------------------------------------------------------------------

def converted(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        message = str(e)
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        message = repr(e)
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        message = e.reason

# ------------------------------------------------------------------------------
# Given to a logger, which converts it.
# ------------------------------------------------------------------------------

def logged(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        logger.warning("Failed: `%s`.", e)
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        logger.error("Command `%s` failed: `%s`.", args, e)
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        logger.warning("Failed: `%s`.", e.reason)
    try:
        run_command(args)
    except OSError as e:
        # ok: python-enforce-command-error-reason
        logger.warning("Failed: `%s`.", e)

# ------------------------------------------------------------------------------
# With a `finally` clause.
# ------------------------------------------------------------------------------

def with_finally(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None
    finally:
        cleanup()
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e.reason}`.", e.code) from None
    finally:
        cleanup()

# ------------------------------------------------------------------------------
# With an `else` clause.
# ------------------------------------------------------------------------------

def with_else(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        logger.warning("Failed: `%s`.", e)
    else:
        cleanup()
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        logger.warning("Failed: `%s`.", e.reason)
    else:
        cleanup()

# ------------------------------------------------------------------------------
# With `else` and `finally`.
# ------------------------------------------------------------------------------

def with_else_and_finally(args):
    try:
        run_command(args)
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        message = str(e)
    else:
        cleanup()
    finally:
        close()
    try:
        run_command(args)
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        message = e.reason
    else:
        cleanup()
    finally:
        close()

# ------------------------------------------------------------------------------
# With another handler before.
# ------------------------------------------------------------------------------

def with_other_handler_before(args):
    try:
        run_command(args)
    except asyncio.CancelledError:
        raise
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None
    try:
        run_command(args)
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise
    except CommandError as e:
        # ruleid: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e}`.") from None
    try:
        run_command(args)
    except asyncio.CancelledError:
        raise
    except CommandError as e:
        # ok: python-enforce-command-error-reason
        raise ServiceError(f"Failed: `{e.reason}`.", e.code) from None
