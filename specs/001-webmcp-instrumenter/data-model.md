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
| `page_url` | string (URL) | The crawled top URL (single URL per run — D6). |
| `html_snippet` | string | Raw outerHTML of the element. |
| `visible` | boolean | `false` for elements present but not `display:none`-hidden. |
| `frame_url` | string (URL) | FR-018: the frame the element lives in (== `page_url` for the main document). |
| `owner_instrumentable` | boolean | FR-018: `false` when the element is in a **cross-origin** frame the site owner can't instrument (only the embedding vendor could). Never approve these. |

**Validation**: truly hidden (`display:none`) elements are excluded entirely (FR-002);
everything surfaced has a `confidence`. Empty result = empty array, not an error.

**Page-level `_meta`** (one object per crawl run, alongside the candidates array):

| Field | Type | Notes |
|-------|------|-------|
| `page_url` | string (URL) | The crawled URL. |
| `origin_trial_advertised` | boolean | FR-017: page carries **any** origin-trial token (not necessarily WebMCP). Informational only; never a crawl filter. |
| `origin_trial_source` | `meta` \| `header` \| null | How the trial token was advertised. |
| `origin_trial_features` | array of string | FR-017: decoded `feature` names from the token(s). Third-party widgets (reCAPTCHA, analytics) inject tokens for unrelated features, so this disambiguates. Empty if no token or none decoded. |
| `origin_trial_webmcp` | boolean | FR-017: true only when a decoded feature identifies **WebMCP** — the Experiment-B-relevant signal. A token present with `webmcp: false` means the trial belongs to some other Chrome feature. |
| `page_language` | string \| null | BCP-47 tag from `<html lang>` or the `Content-Language` header (e.g. `en`, `nl-be`). **Feeds FR-003**: the drafter needs it to write descriptions in the site's primary language, because a bare `<form>` snippet carries no language signal. Null when undeterminable. |
| `iframes` | array of {url, cross_origin} | FR-018: frames found below the top document. A `cross_origin: true` entry that contained candidates is the "primary action is a third-party widget" finding. |

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
