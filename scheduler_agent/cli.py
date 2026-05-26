from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from scheduler_agent.agent import SchedulerAgent
from scheduler_agent.apscheduler_runner import run_with_apscheduler
from schemas.contract import MessageTask


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduler agent command line tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a parsed MessageTask JSON file")
    add_parser.add_argument("json_file", type=Path)

    subparsers.add_parser("run-once", help="Process all due tasks once")

    run_parser = subparsers.add_parser("run", help="Run the scheduler loop")
    run_parser.add_argument("--interval", type=int, default=60)

    args = parser.parse_args()
    agent = SchedulerAgent.from_env()

    if args.command == "add":
        payload = json.loads(args.json_file.read_text(encoding="utf-8"))
        task_id = asyncio.run(agent.validate_and_schedule(MessageTask.model_validate(payload)))
        print(task_id)
    elif args.command == "run-once":
        delivered = asyncio.run(agent.run_once())
        print(delivered)
    elif args.command == "run":
        asyncio.run(run_with_apscheduler(args.interval))


if __name__ == "__main__":
    main()
