"""Candidate detection + filtering + origin-trial detection (T013, T014).

Pure functions over "raw element" dicts (as extracted by the Playwright layer in
crawl.py), so the classification logic is unit-testable without a browser.

Rules (spec FR-002, clarify decision D7):
- Truly hidden elements (`display:none`) are EXCLUDED entirely.
- Cosmetic/ambiguous elements are SURFACED but flagged `low` confidence — never
  silently dropped, so the human reviewer makes the final call.
"""

from __future__ import annotations

import base64
import json
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


_META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_HTTP_EQUIV_OT = re.compile(r"""http-equiv\s*=\s*["']origin-trial["']""", re.IGNORECASE)
_META_CONTENT = re.compile(r"""content\s*=\s*["']([^"']*)["']""", re.IGNORECASE)


def _origin_trial_tokens(html: str, headers: dict[str, str]) -> tuple[list[str], str | None]:
    """Collect raw origin-trial tokens from meta tags and the Origin-Trial header."""
    meta_tokens: list[str] = []
    for tag in _META_TAG.findall(html or ""):  # attribute order varies — scan each tag
        if _HTTP_EQUIV_OT.search(tag):
            m = _META_CONTENT.search(tag)
            if m and m.group(1).strip():
                meta_tokens.append(m.group(1).strip())
    header_tokens: list[str] = []
    for key, value in headers.items():  # header names are case-insensitive
        if key.lower() == "origin-trial" and value.strip():
            header_tokens.extend(t.strip() for t in value.split(",") if t.strip())
    source = "meta" if meta_tokens else "header" if header_tokens else None
    return meta_tokens + header_tokens, source


_OT_PAYLOAD_OFFSET = 69  # version(1) + Ed25519 signature(64) + payload length(4, big-endian)


def _decode_ot_feature(token: str) -> str | None:
    """Pull the `feature` name out of an origin-trial token, or None if undecodable.

    Token layout (trial token v2/v3): a version byte, a 64-byte signature, a 4-byte
    big-endian payload length, then the JSON payload. We must skip past the signature before
    hunting for the JSON — the random signature bytes can themselves contain `{`/`}`, so a
    naive brace search on the whole buffer latches onto the signature, not the payload.
    """
    try:
        raw = base64.b64decode(token)
    except (ValueError, TypeError):
        return None
    if len(raw) < _OT_PAYLOAD_OFFSET:
        return None
    length = int.from_bytes(raw[65:_OT_PAYLOAD_OFFSET], "big")
    tail = raw[_OT_PAYLOAD_OFFSET:]
    body = tail[:length] if 0 < length <= len(tail) else tail
    start, end = body.find(b"{"), body.rfind(b"}")
    if start == -1 or end <= start:
        return None
    try:
        payload = json.loads(body[start : end + 1].decode("utf-8", "replace"))
    except (ValueError, UnicodeDecodeError):
        return None
    feature = payload.get("feature") if isinstance(payload, dict) else None
    return feature if isinstance(feature, str) and feature else None


def _is_webmcp_feature(feature: str) -> bool:
    # Heuristic: Chrome hasn't published the exact registered feature string, so match the
    # obvious identifiers. Tighten to an exact string once confirmed. (FR-017)
    f = feature.lower()
    return "webmcp" in f or "modelcontext" in f


def detect_origin_trial(
    html: str, headers: dict[str, str]
) -> tuple[bool, str | None, list[str], bool]:
    """FR-017: report origin-trial tokens the page carries — decoded, not just present.

    Tokens are feature-scoped; an embedded reCAPTCHA/analytics widget injects a token for an
    unrelated Chrome trial. Returns (advertised, source, feature_names, is_webmcp). WebMCP is
    asserted only when a decoded feature identifies it; unrelated features are reported by name.
    """
    tokens, source = _origin_trial_tokens(html, headers)
    if not tokens:
        return False, None, [], False
    features = [f for f in (_decode_ot_feature(t) for t in tokens) if f]
    is_webmcp = any(_is_webmcp_feature(f) for f in features)
    return True, source, features, is_webmcp


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
    advertised, source, features, is_webmcp = detect_origin_trial(html, headers)
    return CrawlMeta(
        page_url=page_url,
        origin_trial_advertised=advertised,
        origin_trial_source=source,
        origin_trial_features=features,
        origin_trial_webmcp=is_webmcp,
        page_language=detect_page_language(html, headers),
    )
