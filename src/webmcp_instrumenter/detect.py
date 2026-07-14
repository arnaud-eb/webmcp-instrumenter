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
                frame_url=raw.get("frameUrl", page_url),
                # FR-018: a cross-origin frame is not owner-instrumentable.
                owner_instrumentable=not bool(raw.get("crossOrigin", False)),
            )
        )
    return candidates


def is_cross_origin(base_url: str, frame_url: str) -> bool:
    """FR-018: does `frame_url` sit on a different origin than `base_url`?

    Frames with no real origin (about:blank, empty, data:, srcdoc) are treated as
    same-origin — they are part of the owner's own page.
    """
    from urllib.parse import urlparse

    if not frame_url or frame_url.startswith(("about:", "data:", "blob:")):
        return False
    b, f = urlparse(base_url), urlparse(frame_url)
    if not f.hostname:  # e.g. file:// frames — same document tree
        return False
    return (b.scheme, b.hostname, b.port) != (f.scheme, f.hostname, f.port)


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


_HTML_LANG = re.compile(
    r"""<html[^>]*?\blang\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def detect_page_language(html: str, headers: dict[str, str]) -> str | None:
    """FR-003: the site's primary language, for drafting descriptions.

    Prefers `<html lang>`, falls back to the `Content-Language` response header.
    Returns a lowercased BCP-47 tag (e.g. "en", "nl-be"), or None if undeterminable.
    """
    match = _HTML_LANG.search(html or "")
    if match:
        return match.group(1).strip().lower()
    for key, value in headers.items():
        if key.lower() == "content-language" and value.strip():
            # A header may list several; the first is the primary.
            return value.split(",")[0].strip().lower()
    return None


def build_meta(page_url: str, html: str, headers: dict[str, str]) -> CrawlMeta:
    advertised, source = detect_origin_trial(html, headers)
    return CrawlMeta(
        page_url=page_url,
        origin_trial_advertised=advertised,
        origin_trial_source=source,
        page_language=detect_page_language(html, headers),
    )
