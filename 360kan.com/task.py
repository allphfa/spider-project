from apscheduler.schedulers.asyncio import AsyncIOScheduler

from main import MySpider

asyncTask = AsyncIOScheduler()

spider = MySpider()


# 每天执行
@asyncTask.scheduled_job('cron', day_of_week='0-6', hour=0, minute=1, second=5)
async def task_360kan():
    await spider.exit()
    spider.start()

spider.start()

asyncTask.start()
# 事件循环防止退出
spider.exec()


