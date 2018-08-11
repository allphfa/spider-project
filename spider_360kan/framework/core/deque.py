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
    deque_list = deque()
    deque_lock = Lock()
    _counter = itertools.count().__next__

    async def put(self, value, priority=0):
        async with self.deque_lock:
            self.deque_list.append(DequeItem(self._counter(), priority, value))

    async def get(self):
        async with self.deque_lock:
            try:
                item = max(self.deque_list)
                self.deque_list.remove(item)
                return item.value
            except Exception:
                return None

    async def count(self):
        async with self.deque_lock:
            return len(self.deque_list)

    async def clear(self):
        async with self.deque_lock:
            self.deque_list.clear()



"""
@dataclass(init=True)
class PriorityCallback:
    index: int = 0
    priority: int = 0
    callback: function = None


class PriorityCallbackDeque(deque):
    deque_lock = Lock()
    _counter = itertools.count().__next__

    async def put(self, callback, priority:int):
        async with self.deque_lock:
            value = PriorityCallback(index=self._counter(), priority=priority, callback=callback)
            self.deque_list.append(value)

    async def get(self, callback):
"""