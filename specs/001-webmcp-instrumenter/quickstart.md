# Quickstart: Validate the Instrumenter End-to-End (localhost)

Proves the whole pipeline works **without a Shopify store or an origin-trial token**, using
the Chrome flag + a localhost page. Covers US1–US4 + US6 and the US5 checklist.

## Prerequisites

- Python 3.12 + this package installed (`pip install -e .`), Playwright browsers
  (`playwright install chromium`).
- Chrome 149 with **`chrome://flags/#enable-webmcp-testing` → Enabled** (relaunch). Verify:
  a tokenless localhost page must expose `navigator.modelContext` (T0.2 gate — see below).
- A deployed logging Worker (`worker/`) via `wrangler deploy`, or `wrangler dev` for local.
- An Anthropic API key in the environment for `draft`.

## Gate check (T0.2) — WebMCP available on localhost

Serve any local page and confirm in DevTools console:

```js
'modelContext' in navigator   // must be true with the flag enabled
```

If `false`, the flag isn't on (secure-context alone is not enough — verified 2026-07-06).

## End-to-end scenario

1. **Crawl** a local fixture page (a form with a couple of fields):

   ```
   webmcp-instrument crawl http://localhost:8099/ --out candidates.json
   ```

   Expect: `candidates.json` validates against `contracts/candidates.schema.json`; the form
   appears as a `high`-confidence candidate; `_meta.origin_trial_advertised` present.

2. **Draft** contracts:

   ```
   webmcp-instrument draft candidates.json --out contracts.json
   ```

   Expect: one contract with snake_case `tool_name`, ≤300-char `description`, valid
   `input_schema`, `review_status: "needs_review"`.

3. **Human gate**: open `contracts.json`, review, set the contract's `review_status` to
   `"approved"`. (Leaving it `needs_review` MUST cause step 4 to emit nothing.)

4. **Generate**:

   ```
   webmcp-instrument generate contracts.json --out-dir ./out
   ```

   Expect: declarative attributes (or a `registerTool()` block), a `.well-known/webmcp`
   manifest listing exactly the approved tool, and `logger.js`. No secrets in any output.

5. **Deploy locally**: paste the generated attributes/snippet + `logger.js` into the local
   fixture page; serve on `http://localhost:8099/`.

6. **Register check (US5)**: load the page in Chrome 149; in console confirm
   `await navigator.modelContext.getTools()` lists your tool with the right schema; confirm
   no secrets in the tool def.

7. **Invoke + log (US4)**: trigger the tool (submit the form / call it). Confirm the Worker
   received a `POST /events` with `param_keys` (key names only, **no values**). Then take the
   Worker offline and invoke again — the page/tool call MUST still succeed (fail-open).

8. **Report (US6)**:

   ```
   webmcp-instrument report --from 2026-07-01 --to 2026-07-31
   ```

   Expect: counts grouped by site and tool, plus a week-over-week view.

## Success = the whole chain green

Passing steps 1–8 validates the pipeline. What this does **not** prove (still needs Phase 6
on a real owned origin): the per-domain origin-trial token step, and real *organic* agent
traffic — the actual Experiment B question.
