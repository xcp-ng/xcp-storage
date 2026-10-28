import asyncio
from asyncio import ensure_future
import concurrent.futures
from concurrent.futures import Future
import re

from xcp_storage.utils.thread import ThreadGroup, ThreadGroupFuture

# ------------------------------------------------------------------------------
# Created as a future: `x = asyncio.Future()`, `x = loop.create_future()`, `x = asyncio.ensure_future(...)`.
# ------------------------------------------------------------------------------

async def create(loop: asyncio.AbstractEventLoop) -> None:
    # ruleid: python-enforce-future-variable-suffix
    plain = Future()
    # ruleid: python-enforce-future-variable-suffix
    prefixed = concurrent.futures.Future()
    # ruleid: python-enforce-future-variable-suffix
    pending = asyncio.Future()
    # ruleid: python-enforce-future-variable-suffix
    group_result = ThreadGroupFuture()
    # ruleid: python-enforce-future-variable-suffix
    created = loop.create_future()
    # ruleid: python-enforce-future-variable-suffix
    executed = asyncio.get_event_loop().run_in_executor(None, len, "abc")
    # ruleid: python-enforce-future-variable-suffix
    ensured = asyncio.ensure_future(work())
    # ruleid: python-enforce-future-variable-suffix
    imported = ensure_future(work())
    # ruleid: python-enforce-future-variable-suffix
    threadsafe = asyncio.run_coroutine_threadsafe(work(), loop)
    # ruleid: python-enforce-future-variable-suffix
    wrapped = asyncio.wrap_future(prefixed)
    # ok: python-enforce-future-variable-suffix
    future = loop.create_future()
    # ok: python-enforce-future-variable-suffix
    executed_future = loop.run_in_executor(None, len, "abc")
    # ok: python-enforce-future-variable-suffix
    length = await loop.run_in_executor(None, len, "abc")
    # ok: python-enforce-future-variable-suffix
    task = asyncio.create_task(work())
    # ok: python-enforce-future-variable-suffix
    loop_task = loop.create_task(work())
    # ok: python-enforce-future-variable-suffix
    other = MyFuture()
    # ok: python-enforce-future-variable-suffix
    created_list = loop.create_future_list()

class CreatedHolder:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        # ruleid: python-enforce-future-variable-suffix
        self.reply = loop.create_future()
        # ok: python-enforce-future-variable-suffix
        self.reply_future = loop.create_future()

# ------------------------------------------------------------------------------
# Started by a thread group: `x = thread_group.start(...)`, `x = self._thread_group.defer_start(...)`.
# ------------------------------------------------------------------------------

def run(thread_group: ThreadGroup, other_thread_group: ThreadGroup) -> None:
    # ruleid: python-enforce-future-variable-suffix
    length = thread_group.start(len, "abc")
    # ruleid: python-enforce-future-variable-suffix
    delayed = thread_group.defer_start(1.0, len, "abc")
    # ruleid: python-enforce-future-variable-suffix
    other = other_thread_group.start(len, "abc")
    # ruleid: python-enforce-future-variable-suffix
    annotated: object = thread_group.start(len, "abc")
    # ok: python-enforce-future-variable-suffix
    future = thread_group.start(len, "abc")
    # ok: python-enforce-future-variable-suffix
    length_future = thread_group.defer_start(1.0, len, "abc")
    # ok: python-enforce-future-variable-suffix
    index = re.match("a", "a").start(0)
    # ok: python-enforce-future-variable-suffix
    started = thread_groups.start(len, "abc")
    # ok: python-enforce-future-variable-suffix
    joined = thread_group.join()

class Holder:
    def __init__(self, thread_group: ThreadGroup) -> None:
        self._thread_group = thread_group
        # ruleid: python-enforce-future-variable-suffix
        self.result = self._thread_group.start(len, "abc")
        # ok: python-enforce-future-variable-suffix
        self.result_future = self._thread_group.start(len, "abc")

# ------------------------------------------------------------------------------
# Declared as a future: `x: ThreadGroupFuture[int]`, `x: Optional[asyncio.Future[int]]`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-future-variable-suffix
length: ThreadGroupFuture[int] = get_future()
# ruleid: python-enforce-future-variable-suffix
nothing: ThreadGroupFuture[Optional[int]] = get_future()
# ruleid: python-enforce-future-variable-suffix
plain: ThreadGroupFuture
# ruleid: python-enforce-future-variable-suffix
prefixed: thread.ThreadGroupFuture[int]
# ruleid: python-enforce-future-variable-suffix
asyncio_result: asyncio.Future[int] = get_future()
# ruleid: python-enforce-future-variable-suffix
concurrent_result: Optional[concurrent.futures.Future[int]] = None
# ruleid: python-enforce-future-variable-suffix
bare: Future
# ruleid: python-enforce-future-variable-suffix
optional: Optional[ThreadGroupFuture[int]] = None
# ruleid: python-enforce-future-variable-suffix
final: Final[ThreadGroupFuture[int]] = get_future()
# ruleid: python-enforce-future-variable-suffix
union: Union[None, ThreadGroupFuture[Dict[str, int]]] = None
# ruleid: python-enforce-future-variable-suffix
pipe: ThreadGroupFuture[int] | None = None
# ruleid: python-enforce-future-variable-suffix
reverse_pipe: None | ThreadGroupFuture[int] = None
# ok: python-enforce-future-variable-suffix
length_future: ThreadGroupFuture[int] = get_future()
# ok: python-enforce-future-variable-suffix
FUTURE: Optional[ThreadGroupFuture[int]] = None
# ok: python-enforce-future-variable-suffix
group: ThreadGroup = get_group()
# ok: python-enforce-future-variable-suffix
futures: List[ThreadGroupFuture[int]] = []
# ok: python-enforce-future-variable-suffix
other: MyThreadGroupFutureList = get_list()
# ok: python-enforce-future-variable-suffix
running: asyncio.Task[int] = get_task()

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-future-variable-suffix
        self.result: Optional[ThreadGroupFuture[int]] = None
        # ok: python-enforce-future-variable-suffix
        self.result_future: Optional[ThreadGroupFuture[int]] = None

# ruleid: python-enforce-future-variable-suffix
def wait(result: ThreadGroupFuture[int]) -> None:
    pass

def wait_all(
    # ruleid: python-enforce-future-variable-suffix
    first: ThreadGroupFuture[int],
    second_future: ThreadGroupFuture[int],
) -> None:
    pass

# ok: python-enforce-future-variable-suffix
def wait_future(future: ThreadGroupFuture[int], result_future: Optional[ThreadGroupFuture[int]]) -> None:
    pass
