# Phase 1 Data Model: WebMCP Concierge Instrumenter

Four entities flow through the pipeline. Intermediate entities are persisted as plain JSON
files (human-inspectable/editable); invocation events live in Cloudflare D1. Full JSON
Schemas for the two file artifacts are in [`contracts/`](./contracts/).

## Candidate action

Output of `crawl` (one record per detected form/button). File: `candidates.json` (array).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Stable within a crawl (e.g. `c1`, `c2`). |
| `type` | enum: `form` \| `button` | Kind of detected action. |
| `confidence` | enum: `high` \| `low` | `low` = cosmetic/ambiguous, surfaced flagged (D7). |
| `page_url` | string (URL) | Where it was found (single URL per run — D6). |
| `html_snippet` | string | Raw outerHTML of the element. |
| `visible` | boolean | `false` for elements present but not `display:none`-hidden. |

**Validation**: truly hidden (`display:none`) elements are excluded entirely (FR-002);
everything surfaced has a `confidence`. Empty result = empty array, not an error.

**Page-level (FR-017)**: the crawl also reports, once per run, whether the origin advertises
a WebMCP origin trial — `origin_trial_advertised: boolean` + `source: "meta" | "header" |
null`. Informational only; never a crawl filter. Carried in a top-level `_meta` object
alongside the candidates array (see contract).

## Tool contract

Output of `draft`, human-editable before `generate`. File: `contracts.json` (array).

| Field | Type | Notes |
|-------|------|-------|
| `candidate_id` | string | FK → Candidate.id. |
| `tool_name` | string (snake_case) | Agent-facing tool name. |
| `description` | string, ≤300 chars | Agent-facing, in the site's primary language. |
| `input_schema` | JSON Schema object | `{type, properties, required}`; validated with `jsonschema`. |
| `api` | enum: `declarative` \| `imperative` | Selects the generated form (D5). |
| `review_status` | enum: `needs_review` \| `approved` | **Gates generation** (Principle I). |

**State transitions** (`review_status`): `needs_review` → `approved` (human edit only).
`generate` emits code **only** for `approved`; anything else is skipped. `draft` sets
`needs_review` when the model is low-confidence or a field name is generic/ambiguous (FR-004).

**Validation**: `tool_name` snake_case; `description` non-empty and ≤300 chars;
`input_schema` is valid JSON Schema; no secrets/credentials anywhere in the record (FR-007).

## Invocation event

What the generated `logger.js` POSTs per agent invocation. Stored in D1.

| Field | Type | Notes |
|-------|------|-------|
| `site` | string | Origin/host the tool is deployed on. |
| `tool_name` | string | Which tool was invoked. |
| `timestamp` | string (ISO-8601 UTC) | When. |
| `success` | boolean | Did the tool call succeed. |
| `param_keys` | string[] | **Key names only — never values** (Principle II / FR-009). |

**Validation / invariants**: no value fields exist in the schema at all (minimization by
construction). The POST is fire-and-forget: any failure is swallowed client-side so the host
site and tool call still succeed (Principle III / FR-010).

## Report

Output of `report` (US6). Derived, not stored.

| Field | Type | Notes |
|-------|------|-------|
| `date_range` | {from, to} | Query window. |
| `by_site_tool` | rows of {site, tool_name, count} | Invocation counts grouped by site + tool. |
| `by_week` | rows of {week, site, tool_name, count} | Week-over-week view for the go/no-go trend. |

**Validation**: counts are non-negative integers; a range with no events yields empty groups,
not an error.
