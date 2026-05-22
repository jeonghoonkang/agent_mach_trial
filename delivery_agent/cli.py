from __future__ import annotations

import argparse
import asyncio

from delivery_agent.agent import DeliveryAgent
from schemas.contract import DeliverySignal


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a delivery signal through Telegram.")
    parser.add_argument("target", help="Telegram @username, phone number, or peer identifier")
    parser.add_argument("text", help="Message text")
    parser.add_argument("--task-id", type=int, default=0)
    args = parser.parse_args()

    signal = DeliverySignal(
        task_id=args.task_id,
        telethon_target=args.target,
        final_text=args.text,
    )
    asyncio.run(DeliveryAgent.from_env().deliver(signal))


if __name__ == "__main__":
    main()
