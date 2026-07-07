"""Candidate detection + filtering + origin-trial detection (T013, T014).

Pure functions over "raw element" dicts (as extracted by the Playwright layer in
crawl.py), so the classification logic is unit-testable without a browser.

Rules (spec FR-002, clarify decision D7):
- Truly hidden elements (`display:none`) are EXCLUDED entirely.
- Cosmetic/ambiguous elements are SURFACED but flagged `low` confidence — never
  silently dropped, so the human reviewer makes the final call.
"""

from __future__ import annotations

import re
from typing import Any

from .models import Candidate, CandidateType, Confidence, CrawlMeta

# Markers suggesting a cosmetic / non-actionable widget → low confidence.
_COSMETIC_MARKERS = (
    "cookie",
    "consent",
    "gdpr",
    "carousel",
    "slider",
    "search",  # search-as-you-type widgets
    "language-select",
    "locale",
)

# Keywords suggesting a genuine, agent-relevant action → high confidence.
_ACTION_KEYWORDS = (
    "add to cart",
    "addtocart",
    "add-to-cart",
    "buy",
    "checkout",
    "book",
    "reserve",
    "order",
    "contact",
    "send",
    "submit",
    "subscribe",
    "sign up",
    "signup",
    "register",
    "request",
    "quote",
    "booking",
    "appointment",
)


def _matches(haystack: str, needles: tuple[str, ...]) -> bool:
    h = haystack.lower()
    return any(n in h for n in needles)


def _classify_form(raw: dict[str, Any]) -> Confidence:
    class_id = raw.get("classId", "")
    role = raw.get("role", "")
    if role == "search" or _matches(class_id, _COSMETIC_MARKERS):
        return Confidence.LOW
    if not raw.get("hasVisibleInputs", False):
        return Confidence.LOW
    return Confidence.HIGH


def _classify_button(raw: dict[str, Any]) -> Confidence:
    signal = f"{raw.get('text', '')} {raw.get('classId', '')} {raw.get('role', '')}"
    if _matches(signal, _COSMETIC_MARKERS) and not _matches(signal, _ACTION_KEYWORDS):
        return Confidence.LOW
    return Confidence.HIGH if _matches(signal, _ACTION_KEYWORDS) else Confidence.LOW


def build_candidates(raw_elements: list[dict[str, Any]], page_url: str) -> list[Candidate]:
    """Turn raw extracted elements into Candidates (excluding hidden ones)."""
    candidates: list[Candidate] = []
    n = 0
    for raw in raw_elements:
        if raw.get("displayNone", False):
            continue  # FR-002: exclude truly hidden elements
        kind = raw.get("kind")
        if kind == "form":
            ctype, confidence = CandidateType.FORM, _classify_form(raw)
        elif kind == "button":
            ctype, confidence = CandidateType.BUTTON, _classify_button(raw)
        else:
            continue
        n += 1
        candidates.append(
            Candidate(
                id=f"c{n}",
                type=ctype,
                confidence=confidence,
                page_url=page_url,
                html_snippet=raw.get("outerHTML", ""),
                visible=bool(raw.get("visible", True)),
            )
        )
    return candidates


_META_ORIGIN_TRIAL = re.compile(
    r"""<meta[^>]+http-equiv\s*=\s*["']origin-trial["']""",
    re.IGNORECASE,
)


def detect_origin_trial(html: str, headers: dict[str, str]) -> tuple[bool, str | None]:
    """FR-017: does the page advertise a WebMCP origin trial? Informational only."""
    if _META_ORIGIN_TRIAL.search(html or ""):
        return True, "meta"
    # Header names are case-insensitive.
    if any(k.lower() == "origin-trial" for k in headers):
        return True, "header"
    return False, None


def build_meta(page_url: str, html: str, headers: dict[str, str]) -> CrawlMeta:
    advertised, source = detect_origin_trial(html, headers)
    return CrawlMeta(
        page_url=page_url,
        origin_trial_advertised=advertised,
        origin_trial_source=source,
    )
