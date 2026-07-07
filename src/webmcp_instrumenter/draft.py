"""US2 draft stage (T019, T020).

Turns each candidate into a Contract. Every drafted contract defaults to
`needs_review` — draft NEVER auto-approves; the human sets `approved` (the gate
from Constitution Principle I). Validation problems and ambiguity are recorded as
notes so the reviewer knows what to check; malformed model output never crashes
the stage (FR-004).
"""

from __future__ import annotations

import re
from pathlib import Path

import jsonschema

from .io import load_json
from .llm.base import DraftedContract, LLMProvider, get_provider
from .models import Candidate, Contract, CrawlResult, ReviewStatus

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


def _to_snake(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    if s and s[0].isdigit():
        s = f"tool_{s}"
    return s


def _finalize(candidate: Candidate, drafted: DraftedContract) -> Contract:
    """Validate drafted fields and build a needs_review Contract with notes."""
    notes: list[str] = []
    if drafted.ambiguous and drafted.note:
        notes.append(drafted.note)
    elif drafted.ambiguous:
        notes.append("provider flagged ambiguity")

    # tool_name → snake_case (coerce if possible, else flag)
    name = drafted.tool_name
    if not _SNAKE.match(name or ""):
        coerced = _to_snake(name or "")
        if _SNAKE.match(coerced):
            name = coerced
            notes.append("tool_name coerced to snake_case")
        else:
            name = "unnamed_tool"
            notes.append("invalid tool_name — please rename")

    # description ≤300, non-empty
    desc = (drafted.description or "").strip()
    if not desc:
        desc = "TODO: describe this tool for the agent"
        notes.append("empty description — please write one")
    elif len(desc) > 300:
        desc = desc[:300]
        notes.append("description truncated to 300 chars")

    # input_schema must be a valid JSON Schema
    schema = drafted.input_schema or {"type": "object", "properties": {}}
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError:
        schema = {"type": "object", "properties": {}}
        notes.append("invalid input_schema — reset to empty; please define")

    # Low-confidence candidates always warrant a closer look.
    if candidate.confidence.value == "low":
        notes.append("low-confidence candidate")

    return Contract(
        candidate_id=candidate.id,
        tool_name=name,
        description=desc,
        input_schema=schema,
        api=drafted.api,
        review_status=ReviewStatus.NEEDS_REVIEW,  # human gate — never auto-approve
        note="; ".join(notes) if notes else None,
    )


def draft_contracts(
    candidates_path: str | Path,
    provider: str = "claude",
    provider_impl: LLMProvider | None = None,
) -> list[Contract]:
    """Draft a contract per candidate. `provider_impl` allows test injection."""
    crawl = CrawlResult.from_dict(load_json(candidates_path))
    prov = provider_impl or get_provider(provider)
    return [_finalize(cand, prov.draft(cand)) for cand in crawl.candidates]
