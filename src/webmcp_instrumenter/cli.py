"""CLI entry point wiring the four re-runnable stages (T010).

Each subcommand reads/writes its own file boundary so stages stay independently
re-runnable (Constitution Principle IV). Stage modules are imported lazily so a
missing optional dependency for one stage never blocks the others.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import typer

app = typer.Typer(
    add_completion=False,
    help="WebMCP Concierge Instrumenter — crawl → draft → generate → report.",
)


def run_dir_for(url: str) -> Path:
    """Per-site run directory: `runs/<host>` (`runs/local` when the URL has no host)."""
    return Path("runs") / (urlparse(url).hostname or "local")


@app.command()
def crawl(
    url: str = typer.Argument(..., help="A single page URL to crawl."),
    out: Path | None = typer.Option(
        None, "--out", help="Output candidates file [default: runs/<host>/candidates.json]."
    ),
    timeout: float = typer.Option(None, "--timeout", help="Render timeout (seconds)."),
) -> None:
    """US1: render a URL and detect candidate WebMCP actions."""
    from .crawl import crawl_url

    if out is None:
        out = run_dir_for(url) / "candidates.json"

    result = crawl_url(url, timeout_s=timeout)
    from .io import save_json, validate_against

    payload = result.to_dict()
    validate_against(payload, "candidates.schema.json")
    save_json(out, payload)
    n_high = sum(1 for c in result.candidates if c.confidence.value == "high")
    n_low = len(result.candidates) - n_high
    typer.echo(f"crawl: {len(result.candidates)} candidate(s) ({n_high} high, {n_low} low) → {out}")
    if result.meta.origin_trial_webmcp:
        typer.echo(
            f"  ✓ origin advertises a WebMCP origin trial ({result.meta.origin_trial_source})"
        )
    elif result.meta.origin_trial_advertised:
        feats = ", ".join(result.meta.origin_trial_features) or "feature undetermined"
        typer.echo(
            f"  note: origin carries an origin-trial token, but NOT for WebMCP "
            f"({result.meta.origin_trial_source}: {feats})"
        )
    n_third_party = sum(1 for c in result.candidates if not c.owner_instrumentable)
    if n_third_party:
        hosts = sorted({f["url"] for f in result.meta.iframes if f["cross_origin"]})
        typer.echo(
            f"  ⚠ {n_third_party} candidate(s) in a cross-origin third-party widget you "
            f"cannot instrument (only the vendor can): {', '.join(hosts)}"
        )


@app.command()
def draft(
    candidates: Path = typer.Argument(..., help="candidates.json from `crawl`."),
    out: Path | None = typer.Option(
        None, "--out", help="Output contracts file [default: beside the input file]."
    ),
    provider: str = typer.Option("claude", "--provider", help="LLM provider."),
) -> None:
    """US2: draft a tool contract per candidate (human-edited before generate)."""
    from .draft import draft_contracts

    if out is None:
        out = candidates.parent / "contracts.json"

    contracts = draft_contracts(candidates, provider=provider)
    from .io import save_json, validate_against

    payload = [c.to_dict() for c in contracts]
    validate_against(payload, "contracts.schema.json")
    save_json(out, payload)
    n_review = sum(1 for c in contracts if not c.is_approved)
    typer.echo(
        f"draft: {len(contracts)} contract(s) → {out} "
        f"({n_review} need review — edit and set review_status: approved)"
    )


@app.command()
def generate(
    contracts: Path = typer.Argument(..., help="contracts.json (approved) from `draft`."),
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Output directory [default: <input-dir>/out]."
    ),
) -> None:
    """US3: emit code for APPROVED contracts only (human gate)."""
    from .generate import generate as run_generate

    if out_dir is None:
        out_dir = contracts.parent / "out"

    summary = run_generate(contracts, out_dir)
    if summary.approved == 0:
        typer.echo("generate: 0 approved contracts — nothing emitted.")
        return
    typer.echo(
        f"generate: emitted {summary.approved} tool(s) → {out_dir} "
        f"({summary.declarative} declarative, {summary.imperative} imperative); "
        f"manifest + logger.js written."
    )


@app.command()
def report(
    from_: str = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)."),
    to: str = typer.Option(None, "--to", help="End date (YYYY-MM-DD)."),
    format: str = typer.Option("table", "--format", help="table|json"),
) -> None:
    """US5: weekly invocation counts (implemented in the P2 phase)."""
    typer.echo("report: not implemented yet (US5 / P2 phase).")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
