from __future__ import annotations

import argparse
from datetime import datetime, timezone

from parser_agent.agent import ParsingAgent
from scheduler_agent.agent import SchedulerAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse and schedule a Telegram message request.")
    parser.add_argument("text", help="Natural language scheduling request")
    parser.add_argument("--now", help="Reference time in ISO 8601 format")
    args = parser.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    task = ParsingAgent().parse(args.text, now=now)
    task_id = SchedulerAgent.from_env().schedule(task)
    print(f"scheduled task_id={task_id}")


if __name__ == "__main__":
    main()
