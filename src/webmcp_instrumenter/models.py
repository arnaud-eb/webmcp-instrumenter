"""Core data models for the pipeline (data-model.md).

Plain dataclasses with dict (de)serialization so every stage boundary is a
human-inspectable/editable JSON file (Constitution Principle IV).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CandidateType(StrEnum):
    FORM = "form"
    BUTTON = "button"


class Confidence(StrEnum):
    HIGH = "high"
    LOW = "low"


class Api(StrEnum):
    DECLARATIVE = "declarative"
    IMPERATIVE = "imperative"


class ReviewStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"


@dataclass
class Candidate:
    """A detected form/button that could become a WebMCP tool."""

    id: str
    type: CandidateType
    confidence: Confidence
    page_url: str
    html_snippet: str
    visible: bool
    frame_url: str = ""  # FR-018: the frame it lives in (== page_url for the top document)
    owner_instrumentable: bool = True  # FR-018: false for cross-origin third-party frames

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "confidence": self.confidence.value,
            "page_url": self.page_url,
            "html_snippet": self.html_snippet,
            "visible": self.visible,
            "frame_url": self.frame_url or self.page_url,
            "owner_instrumentable": self.owner_instrumentable,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Candidate:
        return cls(
            id=d["id"],
            type=CandidateType(d["type"]),
            confidence=Confidence(d["confidence"]),
            page_url=d["page_url"],
            html_snippet=d["html_snippet"],
            visible=bool(d["visible"]),
            frame_url=d.get("frame_url", d["page_url"]),
            owner_instrumentable=bool(d.get("owner_instrumentable", True)),
        )


@dataclass
class CrawlMeta:
    """Page-level crawl metadata (FR-017 origin trial, FR-003 page language)."""

    page_url: str
    origin_trial_advertised: bool  # FR-017: ANY origin-trial token present (not necessarily WebMCP)
    origin_trial_source: str | None = None  # "meta" | "header" | None
    origin_trial_features: list[str] = field(default_factory=list)  # FR-017: decoded feature names
    origin_trial_webmcp: bool = False  # FR-017: a decoded feature identifies WebMCP
    page_language: str | None = None  # BCP-47, e.g. "en", "nl-be"
    iframes: list[dict[str, Any]] = field(default_factory=list)  # FR-018: {url, cross_origin}

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_url": self.page_url,
            "origin_trial_advertised": self.origin_trial_advertised,
            "origin_trial_source": self.origin_trial_source,
            "origin_trial_features": self.origin_trial_features,
            "origin_trial_webmcp": self.origin_trial_webmcp,
            "page_language": self.page_language,
            "iframes": self.iframes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CrawlMeta:
        return cls(
            page_url=d["page_url"],
            origin_trial_advertised=bool(d["origin_trial_advertised"]),
            origin_trial_source=d.get("origin_trial_source"),
            origin_trial_features=d.get("origin_trial_features", []),
            origin_trial_webmcp=bool(d.get("origin_trial_webmcp", False)),
            page_language=d.get("page_language"),
            iframes=d.get("iframes", []),
        )


@dataclass
class CrawlResult:
    """Full output of `crawl` — matches contracts/candidates.schema.json."""

    meta: CrawlMeta
    candidates: list[Candidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "_meta": self.meta.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CrawlResult:
        return cls(
            meta=CrawlMeta.from_dict(d["_meta"]),
            candidates=[Candidate.from_dict(c) for c in d["candidates"]],
        )


@dataclass
class Contract:
    """A drafted, human-editable WebMCP tool contract.

    `review_status` gates code generation (Constitution Principle I).
    """

    candidate_id: str
    tool_name: str
    description: str
    input_schema: dict[str, Any]
    api: Api
    review_status: ReviewStatus
    note: str | None = None

    @property
    def is_approved(self) -> bool:
        return self.review_status is ReviewStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "input_schema": self.input_schema,
            "api": self.api.value,
            "review_status": self.review_status.value,
        }
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Contract:
        return cls(
            candidate_id=d["candidate_id"],
            tool_name=d["tool_name"],
            description=d["description"],
            input_schema=d["input_schema"],
            api=Api(d["api"]),
            review_status=ReviewStatus(d["review_status"]),
            note=d.get("note"),
        )


@dataclass
class InvocationEvent:
    """A single logged agent invocation (Principle II: param key names only)."""

    site: str
    tool_name: str
    timestamp: str  # ISO-8601 UTC
    success: bool
    param_keys: list[str]  # NEVER values

    def to_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "success": self.success,
            "param_keys": list(self.param_keys),
        }
