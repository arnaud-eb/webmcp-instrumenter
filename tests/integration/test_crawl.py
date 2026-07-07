"""US1 integration test (T016): crawl the fixture with a real browser."""

from pathlib import Path

from webmcp_instrumenter.crawl import crawl_url

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_site.html"


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


def test_crawl_result_matches_candidates_contract():
    from webmcp_instrumenter.io import validate_against

    result = crawl_url(FIXTURE.as_uri())
    validate_against(result.to_dict(), "candidates.schema.json")  # raises if invalid
