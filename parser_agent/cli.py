from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from parser_agent.agent import ParsingAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a Telegram scheduling request.")
    parser.add_argument("text", help="Natural language request to parse")
    parser.add_argument("--now", help="Reference time in ISO 8601 format")
    args = parser.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    task = ParsingAgent().parse(args.text, now=now)
    print(json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
