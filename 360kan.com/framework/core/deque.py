import itertools

from dataclasses import dataclass
from collections import deque
from asyncio import Lock


@dataclass(init=True)
class DequeItem:
    index: int = 0
    priority: int = 0
    value: any = None

    def __gt__(self, other):
        return self.priority > other.priority


@dataclass(init=True)
class Deque:
    _deque_list = deque()
    _deque_lock = Lock()
    _counter = itertools.count().__next__

    async def put(self, value, priority=0):
        async with self._deque_lock:
            _next = self._counter()
            if priority < 0:
                priority = _next
            self._deque_list.append(DequeItem(_next, priority, value))

    async def get(self):
        async with self._deque_lock:
            try:
                item = max(self._deque_list)
                self._deque_list.remove(item)
                return item.value
            except Exception:
                return None

    async def count(self):
        async with self._deque_lock:
            return len(self._deque_list)

    async def clear(self):
        async with self._deque_lock:
            self._deque_list.clear()
