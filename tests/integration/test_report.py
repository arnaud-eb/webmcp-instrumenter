"""US5 report tests (T036): seeded events → correct grouped + weekly counts.

Exercises `summarize`/`format_report` directly (no network); `fetch_events` is the thin
httpx wrapper over the Worker read path and is covered by the contract, not re-mocked here.
"""

from webmcp_instrumenter.report import summarize


def _ev(site, tool, ts, success=True):
    return {"site": site, "tool_name": tool, "ts": ts, "success": success, "param_keys": []}


EVENTS = [
    _ev("a.com", "book", "2026-07-06T10:00:00Z"),  # ISO week 28
    _ev("a.com", "book", "2026-07-07T11:00:00Z"),  # week 28
    _ev("a.com", "book", "2026-07-14T09:00:00Z", success=False),  # week 29
    _ev("a.com", "search", "2026-07-14T09:30:00Z"),  # week 29
    _ev("b.com", "checkout", "2026-07-15T12:00:00Z"),  # week 29
]


def test_grouping_by_site_and_tool():
    r = summarize(EVENTS, "2026-07-06", "2026-07-15")
    assert r.total == 5
    stats = {(t.site, t.tool_name): t for t in r.by_tool}
    assert stats[("a.com", "book")].total == 3
    assert stats[("a.com", "book")].success == 2
    assert stats[("a.com", "book")].failure == 1
    assert stats[("b.com", "checkout")].total == 1


def test_week_over_week_buckets():
    r = summarize(EVENTS, "2026-07-06", "2026-07-15")
    assert r.by_week == {"2026-W28": 2, "2026-W29": 3}


def test_empty_range_is_zero_not_error():
    r = summarize([], "2026-07-01", "2026-07-02")
    assert r.total == 0
    assert r.by_tool == []
    assert r.by_week == {}


def test_unparseable_timestamp_counts_in_total_but_not_week():
    r = summarize([_ev("a.com", "book", "not-a-date")], "2026-07-01", "2026-07-31")
    assert r.total == 1
    assert r.by_week == {}
