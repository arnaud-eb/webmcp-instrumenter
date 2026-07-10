"""Claude drafting provider (T018) — the default (research D3).

Sonnet-class is sufficient for schema drafting; no extended reasoning needed.
Output is constrained to a single JSON object by the system prompt and parsed
defensively; all structural validation happens downstream in draft.py.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import Config
from ..models import Api, Candidate
from .base import DraftedContract, LLMProvider

_SYSTEM = """You draft WebMCP tool contracts for AI agents from a page element's HTML.
Return ONLY a single JSON object (no prose, no code fences) with exactly these keys:
  "tool_name": snake_case, e.g. "submit_contact_form"
  "description": <=300 chars, agent-facing, in the page's primary language
  "input_schema": a JSON Schema object {"type":"object","properties":{...},"required":[...]}
  "api": "declarative" for a plain <form>, "imperative" for a custom/button action
  "ambiguous": true if a field's meaning is unclear (e.g. one "name" field that could be
               full name or first/last) — flag rather than guess
  "note": short reason if ambiguous, else null
Derive input fields from the element's named inputs. Never invent secrets."""

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = _FENCE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to the first {...} block.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


class ClaudeProvider(LLMProvider):
    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or Config.from_env()

    def draft(self, candidate: Candidate) -> DraftedContract:
        import anthropic
        from anthropic.types import TextBlock

        client = anthropic.Anthropic(api_key=self.cfg.require_anthropic_key())
        resp = client.messages.create(
            model=self.cfg.anthropic_model,
            max_tokens=8192,
            # Schema drafting needs no extended reasoning (research D3). Without this,
            # models with adaptive thinking on by default emit a leading ThinkingBlock.
            thinking={"type": "disabled"},
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Element type: {candidate.type.value}\nHTML:\n{candidate.html_snippet}"
                    ),
                }
            ],
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("Claude declined to draft this tool contract")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("draft response truncated — raise max_tokens")

        # `content` is a list of blocks (text / thinking / tool_use). Find the text
        # block rather than assuming it is first.
        text = next((b.text for b in resp.content if isinstance(b, TextBlock)), None)
        if text is None:
            raise RuntimeError("no text block in Claude response")
        data = _parse_json(text)

        api_val = data.get("api")
        api = (
            Api(api_val)
            if api_val in ("declarative", "imperative")
            else (Api.DECLARATIVE if candidate.type.value == "form" else Api.IMPERATIVE)
        )
        return DraftedContract(
            tool_name=str(data.get("tool_name", "")),
            description=str(data.get("description", "")),
            input_schema=data.get("input_schema") or {},
            api=api,
            ambiguous=bool(data.get("ambiguous", False)),
            note=data.get("note"),
        )
