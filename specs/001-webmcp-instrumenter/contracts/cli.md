# CLI Contract: `webmcp-instrument`

Four independent, re-runnable subcommands (Principle IV). Text/JSON in → text/JSON out.
Each is idempotent given the same inputs. Non-zero exit on hard failure; warnings to stderr.

## Default output layout (per-site run directories)

Artifacts for one site stay together, so re-crawling site B never clobbers site A:

```
runs/<host>/candidates.json      # crawl
runs/<host>/contracts.json       # draft   (defaults beside its input)
runs/<host>/out/                 # generate (defaults beside its input)
```

`<host>` is the URL's hostname (`https://example.com/contact` → `example.com`); a URL with
no hostname (e.g. `file://`) uses `local`. Every default is overridable with the explicit
flag. Downstream stages default to **their input file's directory**, so passing one
`--out` at crawl time keeps the whole chain together.

## `crawl` (US1)

```
webmcp-instrument crawl <URL> [--out runs/<host>/candidates.json] [--timeout SECONDS]
```

- **Input**: a single URL (one page per run — D6).
- **Output**: `candidates.json` (see `candidates.schema.json`) — array of candidate actions
  plus a top-level `_meta` with `origin_trial_advertised` (FR-017) and `page_language`
  (FR-003). Defaults to `runs/<host>/candidates.json`.
- **Behavior**: render with Playwright; extract forms + interactive buttons; exclude
  `display:none`; flag cosmetic/ambiguous as `confidence: "low"`; never drop low-confidence.
- **Errors**: unrenderable page (auth wall/CAPTCHA) → clear non-zero exit, no partial file.
  No candidates → empty array, exit 0.

## `draft` (US2)

```
webmcp-instrument draft <candidates.json> [--out <input-dir>/contracts.json] [--provider claude]
```

- **Input**: `candidates.json`.
- **Output**: `contracts.json` (see `contracts.schema.json`) — one contract per candidate,
  `review_status: "needs_review"` by default. Defaults to `contracts.json` **beside the
  input file**.
- **Behavior**: per candidate, LLM drafts `tool_name` (snake_case), `description` (≤300
  chars), `input_schema` (validated JSON Schema). Ambiguous/low-confidence → `needs_review`.
  Provider is swappable (`--provider`, default `claude`).
- **Errors**: invalid model output that fails schema validation → that contract marked
  `needs_review` with a note, not a hard failure.

## `generate` (US3)

```
webmcp-instrument generate <contracts.json> [--out-dir <input-dir>/out]
```

- **Input**: `contracts.json` (human-edited; some `approved`). Output defaults to an `out/`
  directory **beside the input file**.
- **Output**: into `--out-dir`: declarative HTML attribute snippets and/or imperative
  `registerTool()` JS blocks (per each contract's `api`), a `.well-known/webmcp` manifest,
  and `logger.js`.
- **Behavior**: emits code **ONLY** for `review_status: "approved"` (Principle I). Manifest
  lists exactly the approved tools. No secrets in any output (FR-007).
- **Errors**: nothing approved → emits no code, prints a clear "0 approved" message, exit 0.

## `report` (US6)

```
webmcp-instrument report [--from DATE] [--to DATE] [--format table|json]
```

- **Input**: date range; reads the Cloudflare D1 sink via its Worker read path.
- **Output**: invocation counts grouped by site and by tool, plus a week-over-week view.
- **Behavior**: read-only. Empty range → empty groups, exit 0.
- **Errors**: sink unreachable → non-zero exit with a clear message (report is operator-run,
  so failing loudly here is correct — unlike the logger, which must fail silently).
