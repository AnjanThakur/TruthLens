import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Generic, TypeVar

T = TypeVar("T")


class AsyncMemo(Generic[T]):
    """Bounded process-local TTL cache; identical concurrent calls share a success."""

    def __init__(self, ttl: int, capacity: int):
        self.ttl, self.capacity = ttl, capacity
        self.entries: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self.locks: dict[str, tuple[asyncio.Lock, int]] = {}

    async def run(
        self, key: str, factory: Callable[[], Awaitable[T]], cacheable: Callable[[T], bool]
    ) -> tuple[T, bool, float]:
        lock, users = self.locks.get(key, (asyncio.Lock(), 0))
        self.locks[key] = (lock, users + 1)
        try:
            async with lock:
                cached = self.entries.get(key)
                age = time.monotonic() - cached[0] if cached else 0
                if cached and age < self.ttl:
                    self.entries.move_to_end(key)
                    return deepcopy(cached[1]), True, age
                self.entries.pop(key, None)
                value = await factory()
                if self.ttl and cacheable(value):
                    self.entries[key] = (time.monotonic(), deepcopy(value))
                    while len(self.entries) > self.capacity:
                        self.entries.popitem(last=False)
                return value, False, 0
        finally:
            remaining = self.locks[key][1] - 1
            if remaining:
                self.locks[key] = (lock, remaining)
            else:
                self.locks.pop(key)
