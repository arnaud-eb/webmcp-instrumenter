# WebMCP Concierge Instrumenter — Design

## Architecture overview

Four stages, run as separate CLI commands so each is independently testable
and re-runnable (crawling is slow and flaky; you don't want to redo it just
because the LLM draft needs a tweak):

```
1. crawl      URL        -> candidates.json
2. draft      candidates.json -> contracts.json   (LLM-assisted, human-edited)
3. generate   contracts.json  -> snippet.html/js, webmcp-manifest.json, logger.js
4. report     (reads logging endpoint) -> weekly counts
```

No web app, no database beyond a single logging table. This is a personal
tool, not a product — resist the urge to build a UI for it.

## Stack decision

**Language: Python.**
Reasoning: this is a scripting/automation shape of problem (crawl, transform,
generate text), it's genuinely a decent low-stakes place to practice Python
given you're actively learning it, and there's no reason to reach for
Next.js/TS here — that stack earns its keep when there's a UI or ongoing
web app, and there isn't one in this scope. If you'd rather keep this in
TypeScript for consistency with ListingLux AI, swap Playwright's Python
bindings for the Node ones and Claude's Python SDK for the TS SDK — the
rest of the design doesn't change.

- **Crawling:** Playwright (Python). Handles JS-rendered forms, which plain
  requests/BeautifulSoup would miss on most modern e-commerce sites.
- **LLM drafting:** Claude API (Sonnet is enough for this; no need for
  extended reasoning on tool-schema drafting). Structured JSON output via
  a strict system prompt — see data model below.
- **Logging endpoint:** simplest thing that works — a single Supabase table
  with a public insert-only REST endpoint (Supabase anon key scoped to
  insert-only via RLS policy). No need for a custom backend.
- **Reporting:** a single Python script that queries Supabase and prints a
  table (pandas optional, not required for this volume of data).

## Data model

**candidates.json** (output of `crawl`)
```json
[
  {
    "id": "c1",
    "type": "form",
    "confidence": "high",
    "page_url": "https://example.com/contact",
    "html_snippet": "<form id=\"contact\">...</form>",
    "visible": true
  }
]
```

**contracts.json** (output of `draft`, human-editable before `generate` runs)
```json
[
  {
    "candidate_id": "c1",
    "tool_name": "submit_contact_form",
    "description": "Submit a contact inquiry with name, email, and message.",
    "input_schema": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "email": { "type": "string" },
        "message": { "type": "string" }
      },
      "required": ["name", "email", "message"]
    },
    "api": "declarative",
    "review_status": "approved"
  }
]
```
`review_status` gates whether `generate` will emit code for it — anything
not `approved` gets skipped, which is the human gate from NG2.

**invocation log event** (what the client-side logger posts)
```json
{
  "site": "example.com",
  "tool_name": "submit_contact_form",
  "timestamp": "2026-07-01T10:00:00Z",
  "success": true,
  "param_keys": ["name", "email", "message"]
}
```
Note: `param_keys`, not `param_values` — this is the GDPR-minimization
decision from NG4, and it's a design constraint, not an afterthought bolted
on later.

## Key decisions & tradeoffs

- **Why no auto-deploy (NG2):** auto-injecting a snippet into someone else's
  live site without a review step is both a liability risk (a bad schema
  or a mis-mapped field breaks their checkout) and a trust problem for a
  concierge relationship. The extra manual paste-in step costs minutes and
  buys a lot of safety.
- **Why manual origin-trial tokens (NG3):** origin trial tokens are scoped
  per-origin by design. Automating token issuance across customer domains
  adds real complexity (token lifecycle, renewal, revocation handling) for
  a stage where you don't yet know if there's demand for the automation.
  Manual for now; revisit only if Experiment B says go.
- **Why Supabase over a custom backend:** this needs to exist for 4–6 weeks
  to answer one question. A hand-rolled backend is over-engineering for a
  throwaway measurement tool — this is a good spot to *not* apply SDD rigor
  to infrastructure that doesn't need it.
- **Why re-runnable stages instead of one script:** the LLM draft step is
  the one most likely to need human correction. Splitting stages means
  re-running `draft` after a prompt tweak doesn't force you to re-crawl.

## Open questions to resolve during `clarify` (before implementation starts)
- Do we need multi-page crawl (e.g., follow "contact," "shop," "book now"
  nav links automatically) or is single-URL-at-a-time acceptable for v1?
- Should low-confidence candidates be shown for review or silently dropped?
- What's the actual go/no-go site list — which 5 sites, confirmed access?
- Which logging sink? Supabase is only one option and its free tier auto-pauses
  after ~1 week of inactivity (Arnaud is also already at the 2-active-project free
  cap). The sink must stay reachable for the full 4–6 week window without dropping
  events (constitution Principle III). Candidates: Supabase (paused-project tradeoff),
  Cloudflare Workers + D1/KV, Upstash — pick one during clarify before Phase 0 (T0.1).
