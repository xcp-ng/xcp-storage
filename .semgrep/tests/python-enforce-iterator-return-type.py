import collections.abc
import typing
from typing import Generator as Gen

from xcp_storage.typing import AsyncGenerator, AsyncIterator, Callable, Generator, Iterator

# ------------------------------------------------------------------------------
# Generator neither receiving values (`send`) nor returning one.
# ------------------------------------------------------------------------------

# ruleid: python-enforce-iterator-return-type
def imported() -> Generator[int, None, None]:
    yield 1

# ruleid: python-enforce-iterator-return-type
def prefixed() -> typing.Generator[int, None, None]:
    yield 1

# ruleid: python-enforce-iterator-return-type
def abc_prefixed() -> collections.abc.Generator[int, None, None]:
    yield 1

# ruleid: python-enforce-iterator-return-type
def aliased() -> Gen[int, None, None]:
    yield 1

# ruleid: python-enforce-iterator-return-type
generator_factory: Callable[[], Generator[int, None, None]]

# ok: python-enforce-iterator-return-type
def iterator() -> Iterator[int]:
    yield 1

# ok: python-enforce-iterator-return-type
def receiving() -> Generator[int, str, None]:
    received = yield 1

# ok: python-enforce-iterator-return-type
def returning() -> Generator[int, None, str]:
    yield 1
    return "done"

# ------------------------------------------------------------------------------
# Async generator not receiving values (`asend`).
# ------------------------------------------------------------------------------

# ruleid: python-enforce-iterator-return-type
async def async_imported() -> AsyncGenerator[int, None]:
    yield 1

# ruleid: python-enforce-iterator-return-type
async def async_prefixed() -> typing.AsyncGenerator[int, None]:
    yield 1

# ok: python-enforce-iterator-return-type
async def async_iterator() -> AsyncIterator[int]:
    yield 1

# ok: python-enforce-iterator-return-type
async def async_receiving() -> AsyncGenerator[int, str]:
    received = yield 1
