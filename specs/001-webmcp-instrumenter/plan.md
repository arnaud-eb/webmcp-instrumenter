# Implementation Plan: WebMCP Concierge Instrumenter

**Branch**: `001-webmcp-instrumenter` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-webmcp-instrumenter/spec.md`

## Summary

A Python CLI (`webmcp-instrument`) with four independent, re-runnable subcommands —
`crawl`, `draft`, `generate`, `report` — that turns a URL into WebMCP tool instrumentation
and a client-side invocation logger, with a human review gate before any code is emitted.
The logger posts minimal, PII-free events (param key names only) to a Cloudflare Worker +
D1 sink that stays reachable for the full multi-week window. Purpose: measure real
agent-invocation volume (Experiment B) on test sites. Stages exchange plain JSON files
(`candidates.json` → `contracts.json` → generated snippets) so each stage runs, re-runs, and
is human-edited independently.

## Technical Context

**Language/Version**: Python 3.13 (instrumenter CLI) — latest-but-one, fully supported by
all deps; the machine's system 3.9 is EOL and must be upgraded (`brew install python@3.13`
or pyenv). Logging sink Worker: TypeScript on Cloudflare Workers runtime.

**Primary Dependencies**: Playwright (Python) for JS-rendered crawling; Anthropic SDK
(Claude, the default drafting provider) behind a swappable `LLMProvider` interface;
`jsonschema` to validate drafted input schemas; `httpx` for the report query; `typer` (or
stdlib `argparse`) for the CLI. Worker: `wrangler` + D1 (SQLite).

**Storage**: Cloudflare D1 (SQLite) behind an insert-only Worker HTTP endpoint for
invocation events. Intermediate pipeline artifacts are local JSON files
(`candidates.json`, `contracts.json`) — no local database.

**Testing**: pytest (unit + integration). HTML fixtures for crawl/detection tests. Worker:
lightweight endpoint test (fire-and-forget contract, insert-only).

**Target Platform**: CLI runs on macOS/Linux (developer machine). Generated instrumentation
targets Chrome 149+ (WebMCP origin-trial scope; local dev via
`chrome://flags/#enable-webmcp-testing`). Sink runs on Cloudflare's edge.

**Project Type**: Single-project CLI tool + a minimal companion Worker for the logging sink.

**Performance Goals**: Not throughput-sensitive. Guided by SC-001 (instrument one site in
<2h active human time) and low data volume (≤ ~10k events over 4–6 weeks). Crawl of a single
page should complete in seconds–low-tens-of-seconds.

**Constraints**: GDPR data minimization (param key names only, no values — Principle II);
non-blocking logger (fails open — Principle III); human review gate before code emission
(Principle I); LLM provider must be swappable; single-URL crawl per run (v1); logging sink
must not auto-pause / silently drop events (FR-016).

**Scale/Scope**: A handful of test sites; one operator (Arnaud); ~4–6 week measurement
window; personal tool, not multi-tenant.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Evaluated against Constitution v1.0.2 (`.specify/memory/constitution.md`):

| Principle | Gate | Status |
|-----------|------|--------|
| I. Human gate before live | `generate` emits code ONLY for `review_status: approved`; no auto-deploy; no auto token registration | ✅ PASS — enforced in `generate` stage design; deploy is manual paste-in |
| II. Privacy by data minimization | Logger records `param_keys` only; no values, no PII; no secrets in tool defs | ✅ PASS — event schema has no value fields; generate strips/forbids secrets |
| III. Non-blocking instrumentation | Logger fails open; host site + tool call succeed if sink unreachable | ✅ PASS — logger snippet is fire-and-forget with swallowed errors |
| IV. Re-runnable, single-purpose stages | 4 CLI stages, JSON file boundaries, each independently re-runnable | ✅ PASS — crawl/draft/generate/report decoupled via files |
| V. Right-sized simplicity (YAGNI) | No UI, no auth, no billing, no custom backend, single project | ✅ PASS — sink is a minimal Worker, not a hand-rolled service |

**Initial gate: PASS.** No violations — Complexity Tracking left empty.
**Post-design re-check (after Phase 1): PASS** — data model, contracts, and quickstart
introduce no new backend, no value-logging, and preserve the review gate and file boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/001-webmcp-instrumenter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI + file + endpoint contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/webmcp_instrumenter/
├── __init__.py
├── cli.py               # entry point; wires the 4 subcommands
├── models.py            # Candidate, Contract, InvocationEvent, Report dataclasses
├── crawl.py             # US1: Playwright render → detect candidates → candidates.json
├── detect.py            # US1: form/button extraction + low-confidence flagging + FR-017
├── draft.py             # US2: candidate → LLM-drafted contract (name/desc/schema)
├── generate.py          # US3: approved contracts → declarative attrs / registerTool() / manifest / logger
├── report.py            # US6: query D1 sink → counts by site/tool + week-over-week
├── llm/
│   ├── base.py          # LLMProvider interface (swappable)
│   └── claude.py        # default Claude implementation
└── templates/
    ├── logger.js.j2     # US4: non-blocking invocation logger snippet
    └── manifest.json.j2 # .well-known/webmcp manifest

worker/                  # Cloudflare Worker + D1 logging sink (US4 backend)
├── src/index.ts         # insert-only POST endpoint + read for report
├── schema.sql           # D1 table: invocation events (param_keys only)
└── wrangler.toml

tests/
├── unit/                # detection, drafting-format, generation, logger-failopen
├── integration/         # crawl→draft→generate on HTML fixtures; report over seeded D1
└── fixtures/            # sample HTML pages (messy markup, hidden/cosmetic elements)
```

**Structure Decision**: Single Python project (Option 1) — the instrumenter is a CLI/scripting
tool with no UI or standing web app (Constitution Principle V). The only non-Python artifact
is `worker/`, a minimal Cloudflare Worker that is the logging sink; it is intentionally tiny
infrastructure, not a second application. Generated outputs (snippets, manifest, `logger.js`)
are emitted to an operator-chosen output directory, not committed to this repo.

## Complexity Tracking

> No constitution violations — no entries required.
