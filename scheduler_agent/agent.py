from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass

from delivery_agent.agent import DeliveryAgent
from scheduler_agent.repository import MessageTaskRepository
from schemas.contract import MessageTask, TaskStatus


@dataclass
class SchedulerAgent:
    """Coordinates database polling and delivery handoff."""

    repository: MessageTaskRepository
    delivery_agent: DeliveryAgent
    batch_size: int = 10

    @classmethod
    def from_env(cls) -> "SchedulerAgent":
        database_path = os.getenv("DATABASE_PATH") or "message_tasks.db"
        return cls(
            repository=MessageTaskRepository(database_path),
            delivery_agent=DeliveryAgent.from_env(),
        )

    def schedule(self, task: MessageTask) -> int:
        return self.repository.add_task(task)

    async def run_once(self) -> int:
        signals = self.repository.claim_due_tasks(limit=self.batch_size)
        delivered_count = 0

        for signal in signals:
            try:
                await self.delivery_agent.deliver(signal)
            except Exception as exc:
                self.repository.update_status(signal.task_id, TaskStatus.FAILED, str(exc))
            else:
                self.repository.update_status(signal.task_id, TaskStatus.SUCCESS)
                delivered_count += 1

        return delivered_count

    async def run_forever(self, poll_interval_seconds: int = 60) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(poll_interval_seconds)
