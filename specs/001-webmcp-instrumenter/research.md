# Phase 0 Research: WebMCP Concierge Instrumenter

All Technical Context unknowns were resolved during `/speckit-clarify` (Session 2026-07-06)
and by empirical verification of the WebMCP API in Chrome 149. This document records the
decisions, rationale, and rejected alternatives. **No open `NEEDS CLARIFICATION` remain.**

## D1. Implementation language — Python 3.12

- **Decision**: Python for the instrumenter CLI.
- **Rationale**: Scripting/automation-shaped problem (crawl, transform, generate text); no
  UI or standing web app to justify a TS/Next.js stack; deliberate practice target
  (Constitution / design.md). 3.12 for modern typing + stdlib.
- **Alternatives considered**: TypeScript/Node (rejected — earns its keep only with a UI or
  web app, neither present); Go (rejected — overkill, weaker LLM/crawl ergonomics).

## D2. Crawling — Playwright (Python)

- **Decision**: Playwright with Python bindings; render then extract `<form>` + interactive
  buttons.
- **Rationale**: Modern e-commerce/SMB forms are JS-rendered; plain requests/BeautifulSoup
  would miss them. Playwright gives a real DOM to inspect and compute visibility.
- **Alternatives considered**: requests + BeautifulSoup (rejected — no JS rendering);
  Selenium (rejected — heavier, slower than Playwright for this).

## D3. LLM drafting — Claude, behind a swappable provider interface

- **Decision**: Default to Claude (Sonnet-class is sufficient for schema drafting) via an
  `LLMProvider` interface with a single concrete `claude.py`; structured JSON output enforced
  by a strict prompt + `jsonschema` validation of the result.
- **Rationale**: Constitution requires provider-swappability (no vendor hard-lock). Schema
  drafting does not need extended reasoning. Validating the returned schema locally guards
  against malformed model output.
- **Alternatives considered**: hard-locking one vendor (rejected — violates constraint);
  local/OSS model (rejected — quality/effort not worth it at this stage).

## D4. Logging sink — Cloudflare Workers + D1

- **Decision**: A minimal Cloudflare Worker exposing an insert-only POST endpoint backed by
  a D1 (SQLite) table; `report` reads via a scoped read path.
- **Rationale**: Must stay reachable for the full 4–6 week window without silently dropping
  events (FR-016). Cloudflare free tier does **not** auto-pause on inactivity. Avoids the
  Supabase free-tier problems (2-active-project cap; ~1-week idle auto-pause) and needs no
  hand-rolled backend (Principle V).
- **Alternatives considered**: Supabase (rejected — auto-pause risks silent event loss +
  operator already at the 2-project free cap); Upstash (viable no-pause alternative, held in
  reserve); custom backend (rejected — over-engineering for a throwaway measurement tool).

## D5. WebMCP target API — verified in Chrome 149 (2026-07-06)

- **Decision**: Emit both APIs; `generate` picks per contract via its `api` field.
  - **Imperative**: `navigator.modelContext.registerTool(...)`; runtime surface also exposes
    `getTools()`, `executeTool()`, `ontoolchange`. A registered tool object is
    `{name, description, inputSchema, origin, window}` where `inputSchema` is JSON Schema.
  - **Declarative**: `toolname` + `tooldescription` attributes on the `<form>`;
    `toolparamdescription` on each `<input>`.
- **Rationale**: Verified empirically against Google's "Le Petit Bistro" demo in Chrome 149
  — `getTools()` returned the declaratively-registered tool. Matches what design.md assumed;
  no breaking API change since the build started.
- **Activation**: Origin trial Chrome 149–156; token via `<meta http-equiv="origin-trial">`
  or `Origin-Trial:` header. Local dev requires `chrome://flags/#enable-webmcp-testing`
  (verified: a tokenless localhost page does NOT expose the API without the flag —
  secure-context alone is insufficient).

## D6. Crawl granularity — single URL per run (v1)

- **Decision**: Process exactly one URL per `crawl` invocation.
- **Rationale**: YAGNI / Principle V; multi-page nav-following adds crawl-surface and
  flakiness for little v1 value. Deferred to v2.
- **Alternatives considered**: auto-follow nav links (deferred — v2 scope).

## D7. Low-confidence handling — surface, flagged

- **Decision**: Emit low-confidence candidates in `candidates.json` flagged
  (`confidence: "low"`); exclude only truly hidden (`display:none`) elements.
- **Rationale**: Human-gate principle — the reviewer decides; never silently drop a real
  action buried in messy markup.
- **Alternatives considered**: silent drop below threshold (rejected — risks missing genuine
  actions).

## D8. Stage boundaries — plain JSON files

- **Decision**: `crawl → candidates.json → draft → contracts.json → generate → snippets`.
  `contracts.json` is human-editable; `review_status` gates generation.
- **Rationale**: Re-runnability (Principle IV): a prompt tweak re-runs `draft` without
  re-crawling; the file boundary is where the human gate lives.
- **Alternatives considered**: single in-memory pipeline (rejected — forces re-crawl on any
  downstream change; no natural human-edit point).
