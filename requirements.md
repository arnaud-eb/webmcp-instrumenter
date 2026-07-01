# WebMCP Concierge Instrumenter — Requirements

## Context
This is not AgentBridge-the-product. It's the smallest tool that lets Arnaud run
Experiment B from the AgentBridge pressure-test: hand-instrument a handful of real
Benelux SMB sites with WebMCP tools, and measure actual agent-invocation volume
over 4–6 weeks. If invocation volume is real, AgentBridge-the-product becomes
worth building. If it's near zero, this tool is the entire spend, not a wasted
platform build.

## Goals (in scope)
- G1: Given a URL, crawl the page(s) and detect candidate actions (forms,
  key buttons) that are plausible WebMCP tools.
- G2: For each candidate, draft a tool name, agent-facing description, and
  JSON Schema (input/output) using an LLM, with a human review/edit step
  before anything ships.
- G3: Generate copy-paste-ready output: Declarative API HTML attributes for
  simple forms, Imperative API `registerTool()` blocks for anything custom,
  and a `.well-known/webmcp` manifest.
- G4: Generate a minimal client-side invocation logger snippet that records
  tool name, timestamp, success/failure, and param *shape* (not values) to
  a single logging endpoint.
- G5: Produce a checklist for manually validating registration in Chrome 149
  using the Model Context Tool Inspector extension / DevTools WebMCP domain.
- G6: Produce a simple weekly count report (invocations by tool, by site)
  that can be read as a table or plotted, sourced from the logging endpoint.

## Non-goals (explicitly out of scope for this build)
- NG1: No multi-tenant dashboard, no auth, no billing.
- NG2: No auto-deployment to a customer's live site — output is
  copy-paste code the site owner (or Arnaud) pastes in manually, so there's
  a human gate before anything goes live on someone else's domain.
- NG3: No automatic origin-trial token registration — token setup per
  domain stays a manual step (see design.md for why).
- NG4: No logging of actual form field *values* — shape/success only,
  to avoid capturing customer PII by default (GDPR minimization).
- NG5: No support for sites without a stable DOM structure Playwright can
  render (heavy client-side auth walls, CAPTCHAs) in v1.

## User stories & acceptance criteria

**US1 — Crawl and detect candidates**
As Arnaud, I want to point the tool at a URL and get a list of candidate
actions, so I don't have to manually inventory every form on a site.
- WHEN the tool is run with a URL THEN it SHALL return a list of candidate
  actions, each with: element type, page location, and a raw HTML snippet.
- WHEN a form is hidden (`display:none`) or clearly cosmetic (search-as-you-type
  UI widgets, cookie banners) THEN it SHALL be excluded or flagged low-confidence.

**US2 — Draft tool contracts**
As Arnaud, I want each candidate turned into a draft WebMCP tool contract,
so I'm editing instead of writing from scratch.
- WHEN a candidate is processed THEN the tool SHALL output a name (snake_case),
  a description (<300 chars, agent-facing, in the site's primary language),
  and a JSON Schema for inputs.
- WHEN the draft is ambiguous (e.g., a field could be "full name" or
  "first/last name") THEN the tool SHALL flag it for manual review rather
  than guess silently.

**US3 — Generate implementation snippets**
As Arnaud, I want ready-to-paste code, so instrumenting a site takes minutes,
not hours.
- WHEN a tool contract is approved THEN the tool SHALL output either
  Declarative HTML attributes (for existing forms) or an Imperative
  `registerTool()` block (for custom actions), plus a `.well-known/webmcp`
  manifest entry.

**US4 — Log real invocations**
As Arnaud, I want to know if agents are actually calling these tools, so I
have real data instead of a hunch.
- WHEN a registered tool is invoked by an agent THEN an event SHALL be
  logged with: tool name, site, timestamp, success/failure, param key names
  only (no values).
- WHEN the logging endpoint is unreachable THEN the tool call SHALL still
  succeed for the end user (logging failure must never break the site).

**US5 — Validate registration**
As Arnaud, I want a manual checklist to confirm tools actually registered
correctly in Chrome 149, so I'm not trusting the LLM's output blindly.
- WHEN instrumentation is deployed to a site THEN the checklist SHALL
  confirm: tools visible in Model Context Tool Inspector, schema validates,
  no secrets present in tool definitions.

**US6 — Weekly report**
As Arnaud, I want a simple report of invocation counts, so I can compare
against the go/no-go thresholds from the pressure-test.
- WHEN requested THEN the tool SHALL output invocation counts grouped by
  site and by tool, for a given date range.

## Constraints
- Target: Chrome 149+ only (origin trial scope).
- Each site needs its own origin trial token — this stays a manual,
  per-domain step (NG3).
- No PII in logs by default (NG4) — GDPR minimization, since Arnaud is a
  processor for any customer site's data even in a concierge/manual model.
- LLM calls for tool drafting should be swappable (Claude/OpenAI) — don't
  hard-lock to one provider in the design.

## Success criteria (ties back to Experiment B go/no-go)
- Tool can fully instrument one real site (crawl → draft → snippet →
  manifest → logger) in under 2 hours of Arnaud's active time.
- After deployment to the target sites, weekly report clearly shows
  invocation counts per site — enough to answer the go/no-go question with
  a number, not a guess.

## Scope note (v1.1 — updated after initial build discussion)
Primary goal for this build is to practice spec-driven development on a
real, moderately complex project — not to close real Benelux SMB
relationships yet. Target sites for v1 are therefore:
1. A Shopify dev store Arnaud owns outright (free via Shopify Partners) —
   exercises the full pipeline including Phase 6 deploy, since no
   third-party permission is needed.
2. Google's official WebMCP demo apps (GoogleChromeLabs/webmcp-tools) —
   used as crawl/draft test cases and as a reference implementation to
   compare drafted tool contracts against.
3. 2–3 real public sites, crawl-and-draft only, never deployed to — used
   to stress-test candidate detection against messy real-world markup.

Real Benelux SMB outreach (the original Experiment B goal) is deferred to
a v2 scope once the pipeline itself is proven out. This is a deliberate
descope, not scope creep — noted here so the tasks.md Phase 6 reflects it.
