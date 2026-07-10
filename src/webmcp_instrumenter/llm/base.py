"""LLM provider interface (T017).

The drafting seam is provider-agnostic (Constitution Technology Constraints).
A provider turns one Candidate into draft contract fields; all validation and
the human-gate defaulting happen in draft.py, not here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models import Api, Candidate


@dataclass
class DraftedContract:
    """Raw draft fields returned by a provider (pre-validation)."""

    tool_name: str
    description: str
    input_schema: dict[str, Any]
    api: Api
    ambiguous: bool = False  # provider's own low-confidence signal → adds a note
    note: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    def draft(self, candidate: Candidate, page_language: str | None = None) -> DraftedContract:
        """Draft contract fields for a single candidate.

        `page_language` is the crawled page's BCP-47 tag (FR-003). An isolated
        element snippet carries no language signal, so it must be supplied here
        rather than inferred; None means "undeterminable — default to English".
        """
        raise NotImplementedError


def get_provider(name: str) -> LLMProvider:
    """Factory. Imports the concrete provider lazily to avoid hard deps."""
    if name == "claude":
        from .claude import ClaudeProvider

        return ClaudeProvider()
    raise ValueError(f"unknown LLM provider {name!r} (known: 'claude')")
