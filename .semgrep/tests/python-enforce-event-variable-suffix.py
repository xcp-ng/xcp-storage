import asyncio
import multiprocessing
import multiprocessing.synchronize
import threading
from threading import Event

# ------------------------------------------------------------------------------
# Created as an event: `x = threading.Event()`, `x = context.Event()` (multiprocessing), `x = asyncio.Event()`.
# ------------------------------------------------------------------------------

def create() -> None:
    context = multiprocessing.get_context("fork")
    # ruleid: python-enforce-event-variable-suffix
    release = threading.Event()
    # ruleid: python-enforce-event-variable-suffix
    imported = Event()
    # ruleid: python-enforce-event-variable-suffix
    started = context.Event()
    # ruleid: python-enforce-event-variable-suffix
    stopped = multiprocessing.Event()
    # ruleid: python-enforce-event-variable-suffix
    ready = asyncio.Event()
    # ok: python-enforce-event-variable-suffix
    event = threading.Event()
    # ok: python-enforce-event-variable-suffix
    release_event = threading.Event()
    # ok: python-enforce-event-variable-suffix
    startup_event = context.Event()
    # ok: python-enforce-event-variable-suffix
    other = MyEvent()
    # ok: python-enforce-event-variable-suffix
    log = threading.EventLog()

class Holder:
    def __init__(self) -> None:
        # ruleid: python-enforce-event-variable-suffix
        self._startup = threading.Event()
        # ok: python-enforce-event-variable-suffix
        self._startup_event = threading.Event()

# ------------------------------------------------------------------------------
# Declared as an event: `x: threading.Event`, `x: "multiprocessing.synchronize.Event"`.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-event-variable-suffix
release: threading.Event = get_event()
# ruleid: python-enforce-event-variable-suffix
plain: Event
# ruleid: python-enforce-event-variable-suffix
forward: "multiprocessing.synchronize.Event"
# ruleid: python-enforce-event-variable-suffix
optional: Optional[threading.Event] = None
# ruleid: python-enforce-event-variable-suffix
final: Final[threading.Event] = get_event()
# ruleid: python-enforce-event-variable-suffix
union: Union[None, threading.Event] = None
# ruleid: python-enforce-event-variable-suffix
pipe: threading.Event | None = None
# ruleid: python-enforce-event-variable-suffix
reverse_pipe: None | asyncio.Event = None
# ok: python-enforce-event-variable-suffix
release_event: threading.Event = get_event()
# ok: python-enforce-event-variable-suffix
EVENT: Optional[threading.Event] = None
# ok: python-enforce-event-variable-suffix
events: List[threading.Event] = []
# ok: python-enforce-event-variable-suffix
other: MyEventList = get_list()

class DeclaredHolder:
    def __init__(self) -> None:
        # ruleid: python-enforce-event-variable-suffix
        self.startup: Optional[threading.Event] = None
        # ok: python-enforce-event-variable-suffix
        self.startup_event: Optional[threading.Event] = None

# ruleid: python-enforce-event-variable-suffix
def acquire(startup: "multiprocessing.synchronize.Event") -> None:
    pass

def wait_all(
    # ruleid: python-enforce-event-variable-suffix
    first: threading.Event,
    second_event: threading.Event,
) -> None:
    pass

# ok: python-enforce-event-variable-suffix
def acquire_event(startup_event: "multiprocessing.synchronize.Event", event: Optional[threading.Event]) -> None:
    pass
