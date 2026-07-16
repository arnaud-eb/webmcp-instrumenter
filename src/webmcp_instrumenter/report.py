"""US5 report stage (T034, T035).

Reads invocation events from the Worker's scoped read path and prints counts grouped by
site + tool, plus a week-over-week view (FR-012). Unlike the client logger, `report` is
operator-run and MAY fail loudly — a missing sink/token or a bad range is an error, not a
silent no-op.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from .config import Config


@dataclass
class ToolStat:
    site: str
    tool_name: str
    total: int = 0
    success: int = 0
    failure: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "tool_name": self.tool_name,
            "total": self.total,
            "success": self.success,
            "failure": self.failure,
        }


@dataclass
class ReportData:
    from_: str
    to: str
    total: int = 0
    by_tool: list[ToolStat] = field(default_factory=list)
    by_week: dict[str, int] = field(default_factory=dict)  # ISO "YYYY-Www" -> count

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_,
            "to": self.to,
            "total": self.total,
            "by_tool": [t.to_dict() for t in self.by_tool],
            "by_week": self.by_week,
        }


def fetch_events(from_: str, to: str, cfg: Config | None = None) -> list[dict[str, Any]]:
    """GET the Worker read path for [from_, to] (both dates inclusive)."""
    cfg = cfg or Config.from_env()
    resp = httpx.get(
        cfg.report_endpoint(),
        params={"from": from_, "to": to + "T23:59:59.999Z"},  # make `to` inclusive of its day
        headers={"Authorization": f"Bearer {cfg.require_report_token()}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    events = data.get("events", [])
    return events if isinstance(events, list) else []


def summarize(events: list[dict[str, Any]], from_: str, to: str) -> ReportData:
    """Group events by site+tool and bucket by ISO week (FR-012)."""
    by: dict[tuple[str, str], ToolStat] = {}
    weeks: dict[str, int] = defaultdict(int)
    for e in events:
        site, tool = e.get("site", ""), e.get("tool_name", "")
        stat = by.setdefault((site, tool), ToolStat(site, tool))
        stat.total += 1
        if e.get("success"):
            stat.success += 1
        else:
            stat.failure += 1
        try:
            d = datetime.fromisoformat(str(e.get("ts", "")).replace("Z", "+00:00")).date()
            iso = d.isocalendar()
            weeks[f"{iso[0]}-W{iso[1]:02d}"] += 1
        except ValueError:
            pass  # unparseable timestamp — counted in totals, omitted from the weekly view
    tools = sorted(by.values(), key=lambda s: (s.site, s.tool_name))
    return ReportData(
        from_=from_,
        to=to,
        total=sum(t.total for t in tools),
        by_tool=tools,
        by_week=dict(sorted(weeks.items())),
    )


def format_report(r: ReportData, fmt: str = "table") -> str:
    if fmt == "json":
        return json.dumps(r.to_dict(), indent=2)
    lines = [f"Invocations {r.from_} → {r.to}:  {r.total} total"]
    if not r.total:
        lines.append("  (no events in range)")
        return "\n".join(lines)
    lines.append("")
    lines.append("  By site + tool:")
    width = max(len(f"{t.site} / {t.tool_name}") for t in r.by_tool)
    for t in r.by_tool:
        label = f"{t.site} / {t.tool_name}".ljust(width)
        lines.append(f"    {label}  {t.total:>5}  ({t.success} ok, {t.failure} fail)")
    lines.append("")
    lines.append("  Week over week:")
    for wk, n in r.by_week.items():
        lines.append(f"    {wk}  {n:>5}  {'█' * min(n, 40)}")
    return "\n".join(lines)


def build_report(from_: str, to: str, fmt: str = "table", cfg: Config | None = None) -> str:
    return format_report(summarize(fetch_events(from_, to, cfg), from_, to), fmt)
