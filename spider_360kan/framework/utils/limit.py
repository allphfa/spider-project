import time

from asyncio import Lock, sleep


class Limit(object):
    _count_lock = Lock()
    _fetch_count = 0
    _count_time = 0
    _limit_time = 0
    _limit_count = 0

    async def _start_time(self, limit_time=None, limit_count=None):
        if limit_time and limit_count and not self._count_time:
            self._limit_time = limit_time
            self._limit_count = limit_count
            self._count_time = time.time()
            self._fetch_count = 0

    async def _calc_time(self, wait=False):
        _diff_time = time.time() - self._count_time
        if _diff_time >= self._limit_time:
            await self._start_time()

        # all_time / limit_num = single
        _sig = self._limit_time / self._limit_count
        # cur_time / single = _expect_count
        _expect_count = int(_diff_time / _sig)
        # print(_expect_count, self._fetch_count)
        if wait:
            await sleep(_sig)
        elif _expect_count < self._fetch_count:
            await sleep(_sig)

        self._fetch_count += 1
        if _diff_time > self._limit_time:
            self._count_time = time.time()

    async def wait(self, limit_time=None, limit_count=None, wait=False):
        async with self._count_lock:
            await self._start_time(limit_time, limit_count)
            await self._calc_time(wait)
