from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler_agent.agent import SchedulerAgent


async def run_with_apscheduler(interval_seconds: int = 60) -> None:
    """Run due-task polling with APScheduler."""

    agent = SchedulerAgent.from_env()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        agent.run_once,
        trigger="interval",
        seconds=interval_seconds,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        scheduler.shutdown(wait=False)
