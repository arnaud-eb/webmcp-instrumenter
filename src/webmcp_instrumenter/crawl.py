"""US1 crawl stage (T012): render a URL with Playwright and extract candidates.

The DOM extraction happens in the page (one `evaluate` call) and returns "raw
element" dicts; all classification lives in detect.py so it stays testable.
"""

from __future__ import annotations

from .config import Config
from .detect import build_candidates, build_meta, is_cross_origin
from .models import CrawlResult

# Collect forms and standalone buttons with the signals detect.py needs.
_EXTRACT_JS = r"""
() => {
  const isDisplayNone = (el) => {
    let node = el;
    while (node && node.nodeType === 1) {
      if (getComputedStyle(node).display === 'none') return true;
      node = node.parentElement;
    }
    return false;
  };
  const rich = [];
  document.querySelectorAll('form').forEach((f) => {
    const inputs = [...f.querySelectorAll('input, select, textarea')];
    const visibleInputs = inputs.filter(i => (i.type || '').toLowerCase() !== 'hidden');
    rich.push({
      kind: 'form',
      outerHTML: f.outerHTML,
      displayNone: isDisplayNone(f),
      visible: f.getClientRects().length > 0,
      role: f.getAttribute('role') || '',
      classId: `${f.className || ''} ${f.id || ''} ${f.getAttribute('name') || ''}`,
      hasVisibleInputs: visibleInputs.length > 0,
      text: '',
    });
  });
  const btnSel = 'button, input[type=submit], input[type=button], [role=button]';
  document.querySelectorAll(btnSel).forEach((b) => {
    if (b.closest('form')) return;
    rich.push({
      kind: 'button',
      outerHTML: b.outerHTML,
      displayNone: isDisplayNone(b),
      visible: b.getClientRects().length > 0,
      role: b.getAttribute('role') || '',
      classId: `${b.className || ''} ${b.id || ''}`,
      text: (b.innerText || b.value || b.getAttribute('aria-label') || '').trim(),
    });
  });
  return rich;
}
"""


def crawl_url(url: str, timeout_s: float | None = None) -> CrawlResult:
    """Render `url`, detect candidate actions, and return a CrawlResult.

    Raises RuntimeError if the page cannot be rendered (FR: fail clearly on
    unrenderable pages rather than emitting garbage).
    """
    # Imported lazily so `draft`/`generate` don't require Playwright to be present.
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    cfg = Config.from_env()
    timeout_ms = int((timeout_s if timeout_s is not None else cfg.crawl_timeout_s) * 1000)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                response = page.goto(url, wait_until="load", timeout=timeout_ms)
            except PlaywrightError as exc:
                raise RuntimeError(f"crawl: could not render {url!r}: {exc}") from exc
            # FR-019: SPAs hydrate after `load`; wait for the page to settle so we extract
            # the rendered app, not just its shell. Best-effort — pages that never go idle
            # (analytics beacons, long-polling) just fall through with whatever rendered.
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except PlaywrightError:
                pass
            html = page.content()
            headers = dict(response.headers) if response is not None else {}

            # FR-018: extract from every frame, not just the top document. Real SMB
            # actions are often embedded third-party widgets in (cross-origin) iframes.
            raw_elements: list[dict] = []
            iframes: list[dict] = []
            for frame in page.frames:
                frame_url = frame.url or url
                cross = is_cross_origin(url, frame_url)
                if frame.parent_frame is not None:  # not the top document
                    iframes.append({"url": frame_url, "cross_origin": cross})
                try:
                    frame_raw = frame.evaluate(_EXTRACT_JS)
                except PlaywrightError:
                    continue  # detached / not-yet-loaded frame — skip
                for r in frame_raw:
                    r["frameUrl"] = frame_url
                    r["crossOrigin"] = cross
                raw_elements.extend(frame_raw)
        finally:
            browser.close()

    candidates = build_candidates(raw_elements, url)
    meta = build_meta(url, html, headers)
    meta.iframes = iframes
    return CrawlResult(meta=meta, candidates=candidates)
