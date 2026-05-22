from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from schemas.contract import DeliverySignal, MessageTask, StoredMessageTask, TaskStatus


class MessageTaskRepository:
    """SQLite persistence for scheduled message tasks."""

    def __init__(self, database_path: str | Path = "message_tasks.db") -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_identifier TEXT NOT NULL,
                    target_time TEXT NOT NULL,
                    raw_message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_message_tasks_due
                ON message_tasks(status, target_time)
                """
            )

    def add_task(self, task: MessageTask) -> int:
        now = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO message_tasks (
                    recipient_identifier,
                    target_time,
                    raw_message,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.recipient_identifier,
                    task.target_time.isoformat(),
                    task.raw_message,
                    TaskStatus.PENDING.value,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def claim_due_tasks(self, limit: int = 10, now: datetime | None = None) -> list[DeliverySignal]:
        now = now or self._now()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, recipient_identifier, raw_message
                FROM message_tasks
                WHERE status = ? AND target_time <= ?
                ORDER BY target_time ASC, task_id ASC
                LIMIT ?
                """,
                (TaskStatus.PENDING.value, now.isoformat(), limit),
            ).fetchall()

            signals = [
                DeliverySignal(
                    task_id=int(row["task_id"]),
                    telethon_target=str(row["recipient_identifier"]),
                    final_text=str(row["raw_message"]),
                )
                for row in rows
            ]

            for signal in signals:
                self.update_status(signal.task_id, TaskStatus.PROCESSING)

            return signals

    def update_status(
        self,
        task_id: int,
        status: TaskStatus,
        last_error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE message_tasks
                SET status = ?, updated_at = ?, last_error = ?
                WHERE task_id = ?
                """,
                (status.value, self._now().isoformat(), last_error, task_id),
            )

    def get_task(self, task_id: int) -> StoredMessageTask | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM message_tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_task(row)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_task(self, row: sqlite3.Row) -> StoredMessageTask:
        return StoredMessageTask(
            task_id=int(row["task_id"]),
            recipient_identifier=str(row["recipient_identifier"]),
            target_time=datetime.fromisoformat(str(row["target_time"])),
            raw_message=str(row["raw_message"]),
            status=TaskStatus(str(row["status"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            last_error=row["last_error"],
        )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
