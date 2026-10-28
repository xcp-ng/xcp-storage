# ------------------------------------------------------------------------------
# Imports.
# ------------------------------------------------------------------------------

# ruleid: python-forbid-subprocess-usage
import subprocess
# ruleid: python-forbid-subprocess-usage
from subprocess import run
# ruleid: python-forbid-subprocess-usage
from os import system
# ruleid: python-forbid-subprocess-usage
from asyncio import create_subprocess_exec
# ruleid: python-forbid-subprocess-usage
from pty import spawn

# ------------------------------------------------------------------------------
# Calls.
# ------------------------------------------------------------------------------

def run_things(loop) -> None:
    # ruleid: python-forbid-subprocess-usage
    os.system("x")
    # ruleid: python-forbid-subprocess-usage
    os.execvp("x", [])
    # ruleid: python-forbid-subprocess-usage
    os.posix_spawnp("x", [], {})
    # ruleid: python-forbid-subprocess-usage
    asyncio.create_subprocess_shell("x")
    # ruleid: python-forbid-subprocess-usage
    loop.subprocess_exec(None, "x")
    # ruleid: python-forbid-subprocess-usage
    pty.spawn("x")
    # ok: python-forbid-subprocess-usage
    os.path.exists("x")
    # ok: python-forbid-subprocess-usage
    run_command(["x"])
    # ok: python-forbid-subprocess-usage
    os.getpid()

async def wait() -> None:
    # ok: python-forbid-subprocess-usage
    await asyncio.sleep(1)
