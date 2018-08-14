from dataclasses import dataclass
from asyncio import Event, sleep, create_task, get_event_loop, Queue
from asyncio import Lock
from types import FunctionType

from framework.core.deque import Deque


@dataclass(init=True)
class UrlTask:
    url: str = None
    callback: FunctionType = None
    save: dict = None


class Spider:
    _urls_queue = Deque()
    _exit_ev = Event()
    _exit_callback_ev = Event()
    _adjust_lock = Lock()
    _running_works = 0
    _event_loop = None
    max_works = 5

    async def crawl(self, url, callback, save=dict(), priority=0):
        if self._exit_ev.is_set():
            return
        value = UrlTask(url=url, callback=callback, save=save)
        await self._urls_queue.put(value, priority)
        await self._adjust_works()


    async def clear_urls(self):
        await self._urls_queue.clear()

    async def on_start(self):
        pass

    async def on_exit(self):
        pass

    async def on_process(self, data: UrlTask):
        pass

    async def _adjust_works(self):
        urls_count = await self._urls_queue.count()
        async with self._adjust_lock:
            if urls_count > self._running_works < self.max_works:
                create_task(self._works())
                self._running_works += 1

    async def _works(self):
        while not self._exit_ev.is_set():
            for fail_count in range(5):
                data = await self._urls_queue.get()
                if not data:
                    if fail_count + 1 < 5:
                        await sleep(0.5)
                    else:
                        await self._exit_works()
                        return
                else:
                    await self.on_process(data)
                    break
        await self._exit_works()

    async def _exit_works(self):
        async with self._adjust_lock:
            self._running_works -= 1
            urls_count = await self._urls_queue.count()
            if not urls_count and self._running_works <= 0:
                self._exit_callback_ev.set()
                return

    async def exit(self, wait=True):
        if self._exit_ev.is_set():
            return
        self._exit_ev.set()
        if not wait:
            return
        while True:
            async with self._adjust_lock:
                if self._running_works == 0:
                    break
            await sleep(0.1)
        self._exit_ev.clear()

    async def _exit(self):
        await self._exit_callback_ev.wait()
        await self.on_exit()
        self._exit_callback_ev.clear()

    async def _main(self):
        await self.on_start()
        await self._exit()

    def get_event_loop(self):
        if not self._event_loop:
            self._event_loop = get_event_loop()
        return self._event_loop

    def start(self, task=None):
        if not task:
            task = self._main()
        loop = self.get_event_loop()
        if loop.is_running():
            loop.create_task(task)
        else:
            loop.run_until_complete(task)
    
    def exec(self):
        self.get_event_loop().run_forever()
