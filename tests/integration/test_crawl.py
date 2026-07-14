"""US1 integration test (T016): crawl the fixture with a real browser."""

from pathlib import Path

from webmcp_instrumenter.crawl import crawl_url

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE = FIXTURES / "sample_site.html"


def test_crawl_fixture_detects_flags_and_excludes():
    result = crawl_url(FIXTURE.as_uri())

    # Hidden form is excluded entirely; 4 candidates remain.
    assert len(result.candidates) == 4
    assert all("secret" not in c.html_snippet for c in result.candidates)

    highs = [c for c in result.candidates if c.confidence.value == "high"]
    lows = [c for c in result.candidates if c.confidence.value == "low"]
    assert len(highs) == 2  # contact form + add-to-cart button
    assert len(lows) == 2  # search widget + cookie button

    # FR-017: origin trial advertised via meta tag.
    assert result.meta.origin_trial_advertised is True
    assert result.meta.origin_trial_source == "meta"

    # FR-003: page language captured from <html lang="en"> for the drafter.
    assert result.meta.page_language == "en"


def test_crawl_descends_into_iframes():
    # FR-018: the reservation form lives in an iframe, not the top document.
    result = crawl_url((FIXTURES / "iframe_site.html").as_uri())

    snippets = " ".join(c.html_snippet for c in result.candidates)
    assert "newsletter" in snippets  # top-document form
    assert "booking" in snippets  # form found *inside* the iframe

    # The iframe was recorded in _meta; srcdoc is same-origin so it's instrumentable.
    assert len(result.meta.iframes) == 1
    assert all(c.owner_instrumentable for c in result.candidates)


def test_crawl_result_matches_candidates_contract():
    from webmcp_instrumenter.io import validate_against

    result = crawl_url(FIXTURE.as_uri())
    validate_against(result.to_dict(), "candidates.schema.json")  # raises if invalid
