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
    _urls = Deque()
    _exit_ev = Event()
    _exit_callback = Queue()
    _adjust_lock = Lock()
    _running_works = 0

    max_works = 5
    loop = None

    """
    _priority_lock = Lock()
    _crawl_priority_callback = []
    # 队列写的麻烦，懒得写了
    @staticmethod
    def config(priority=0):
        def warp(func):
            def inner(self, *args, **kwargs):
                async with self._priority_lock:
                    sum(map(self._crawl_priority_callback, key=))
                return func(*args, **kwargs)
            return inner
        return warp
    """

    async def crawl(self, url, callback, save=dict(), priority=0):
        value = UrlTask(url=url, callback=callback, save=save)
        await self._urls.put(value, priority)
        await self._adjust_works()

    async def exit(self, callback=None):
        await sleep(0.5)
        self._exit_ev.set()
        while True:
            async with self._adjust_lock:
                if self._running_works == 0:
                    break
            await sleep(0.1)
        await self._exit_callback.put(callback)

    async def clear_urls(self):
        await self._urls.clear()

    async def on_start(self):
        pass

    async def on_exit(self):
        pass

    async def on_process(self, data: UrlTask):
        pass

    async def _adjust_works(self):
        urls_count = await self._urls.count()
        async with self._adjust_lock:
            if urls_count > self._running_works < self.max_works:
                create_task(self._works())
                self._running_works += 1

    async def _exit_works(self):
        async with self._adjust_lock:
            self._running_works -= 1
            urls_count = await self._urls.count()
            if not urls_count and self._running_works <= 0:
                self._exit_ev.set()
                await self._exit_callback.put(self.on_exit)
                return

    async def _works(self):
        while not self._exit_ev.is_set():
            for fail_count in range(5):
                data = await self._urls.get()
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

    async def _exit(self):
        await self._exit_ev.wait()
        callback = await self._exit_callback.get()
        if callback:
            await callback()
        self._exit_ev.clear()

    async def _main(self):
        self._exit_ev.clear()
        await self.on_start()
        await self._exit()

    def start(self):
        self.loop = get_event_loop()
        if self.loop.is_running():
            self.loop.create_task(self._main())
        else:
            self.loop.run_until_complete(self._main())

    def exec(self):
        if not self.loop:
            raise ValueError('The "run" function has not been executed yet')
        self.loop.run_forever()
