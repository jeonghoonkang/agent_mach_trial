from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Persisted scheduler states for message tasks."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MessageTask(BaseModel):
    """Data extracted by the parser agent and stored by the scheduler."""

    recipient_identifier: str = Field(
        ...,
        description="Telegram recipient name, @username, or phone number",
    )
    target_time: datetime = Field(
        ...,
        description="Scheduled delivery time in ISO 8601 format",
    )
    raw_message: str = Field(
        ...,
        description="Message body to send",
    )


class DeliverySignal(BaseModel):
    """Signal passed from the scheduler agent to the delivery agent."""

    task_id: int
    telethon_target: str
    final_text: str


class StoredMessageTask(MessageTask):
    """Message task as stored in the scheduler database."""

    task_id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    last_error: Optional[str] = None
