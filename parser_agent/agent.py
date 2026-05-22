from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from schemas.contract import MessageTask


SYSTEM_INSTRUCTION = """\
You are a parsing agent that converts a user's Telegram scheduling request into JSON.

Return only this JSON object:
{
  "recipient_identifier": "Telegram recipient name, @username, or phone number",
  "target_time": "ISO 8601 datetime",
  "raw_message": "message body to send"
}

Rules:
1. Extract the recipient identifier, scheduled time, and message body.
2. Resolve relative time expressions using the provided current time.
3. Do not include markdown, explanation, or extra keys.
"""


class ParsingError(RuntimeError):
    """Raised when the parser cannot produce a valid MessageTask."""


class ParsingAgent:
    """Gemma/Ollama-backed parser for natural language message requests."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "gemma4"
        self.timeout_seconds = timeout_seconds

    def parse(self, user_text: str, now: datetime | None = None) -> MessageTask:
        now = now or datetime.now(timezone.utc)
        prompt = self._build_prompt(user_text=user_text, now=now)
        raw_response = self._generate(prompt)
        payload = self._extract_json(raw_response)
        return MessageTask.model_validate(payload)

    def _build_prompt(self, user_text: str, now: datetime) -> str:
        return "\n".join(
            [
                SYSTEM_INSTRUCTION,
                "",
                f"Current time: {now.isoformat()}",
                f"User request: {user_text}",
            ]
        )

    def _generate(self, prompt: str) -> str:
        request_payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ParsingError(f"Failed to call Ollama parser: {exc}") from exc

        generated = data.get("response")
        if not isinstance(generated, str) or not generated.strip():
            raise ParsingError("Ollama response did not include a non-empty response field")
        return generated

    def _extract_json(self, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParsingError(f"Parser output was not valid JSON: {raw_response}") from exc

        if not isinstance(payload, dict):
            raise ParsingError("Parser output must be a JSON object")
        return payload
