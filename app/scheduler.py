"""Daily 09:00 job to refresh national mortgage benchmark snapshots from FRED."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.rates import refresh_today_snapshot
from app.store import RateStore


def start_daily_job(settings: Settings, store: RateStore) -> AsyncIOScheduler:
    async def job() -> None:
        await refresh_today_snapshot(settings, store)

    sched = AsyncIOScheduler(timezone=settings.schedule_tz)
    sched.add_job(
        job,
        CronTrigger(hour=9, minute=0, timezone=settings.schedule_tz),
        id="daily_mortgage_fetch",
        replace_existing=True,
    )
    sched.start()
    return sched
