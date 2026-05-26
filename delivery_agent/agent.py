from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass

from schemas.contract import DeliverySignal


class DeliveryConfigurationError(RuntimeError):
    """Raised when Telegram delivery cannot be configured."""


class RecipientValidationError(RuntimeError):
    """Raised when a Telegram recipient cannot be resolved."""


@dataclass
class DeliveryAgent:
    """Telethon-backed Telegram delivery agent with spam-protection delay."""

    api_id: int | None = None
    api_hash: str | None = None
    session_name: str = "agent_mach_trial"
    dry_run: bool = True
    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 3.0

    @classmethod
    def from_env(cls) -> "DeliveryAgent":
        api_id = os.getenv("TELEGRAM_API_ID")
        return cls(
            api_id=int(api_id) if api_id else None,
            api_hash=os.getenv("TELEGRAM_API_HASH"),
            session_name=os.getenv("TELEGRAM_SESSION_NAME") or "agent_mach_trial",
            dry_run=(os.getenv("DELIVERY_DRY_RUN", "true").lower() != "false"),
            min_delay_seconds=float(os.getenv("DELIVERY_MIN_DELAY_SECONDS", "2")),
            max_delay_seconds=float(os.getenv("DELIVERY_MAX_DELAY_SECONDS", "3")),
        )

    async def deliver(self, signal: DeliverySignal) -> None:
        delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        await asyncio.sleep(delay)

        if self.dry_run:
            print(
                f"[dry-run] task_id={signal.task_id} "
                f"target={signal.telethon_target!r} text={signal.final_text!r}"
            )
            return

        if self.api_id is None or not self.api_hash:
            raise DeliveryConfigurationError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")

        try:
            from telethon import TelegramClient
        except ImportError as exc:
            raise DeliveryConfigurationError("Install telethon to enable real delivery") from exc

        async with TelegramClient(self.session_name, self.api_id, self.api_hash) as client:
            await client.send_message(signal.telethon_target, signal.final_text)

    async def validate_target(self, target: str) -> str:
        """Resolve a Telegram target without sending a message."""

        if self.api_id is None or not self.api_hash:
            raise DeliveryConfigurationError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required to validate recipients"
            )

        try:
            from telethon import TelegramClient
        except ImportError as exc:
            raise DeliveryConfigurationError("Install telethon to validate recipients") from exc

        try:
            async with TelegramClient(self.session_name, self.api_id, self.api_hash) as client:
                entity = await client.get_entity(target)
        except Exception as exc:
            raise RecipientValidationError(f"Telegram recipient is not reachable: {target}") from exc

        username = getattr(entity, "username", None)
        entity_id = getattr(entity, "id", None)
        if username:
            return f"@{username}"
        if entity_id is not None:
            return str(entity_id)
        return target
