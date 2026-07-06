# WebMCP Concierge Instrumenter — Tasks

Each task is sized to be roughly one agent session (Claude Code / Cursor).
Task IDs map back to the user stories in requirements.md so drift is easy
to spot — if a task doesn't trace to a story, it's scope creep.

> **Phase 0–5 can proceed entirely on localhost — the Shopify store does NOT
> gate early development.** Chrome 149 exposes WebMCP on a tokenless page ONLY
> when you enable `chrome://flags/#enable-webmcp-testing` and relaunch. (Verified
> 2026-07-06: a bare `localhost` page without the flag does NOT get
> `navigator.modelContext` — being a secure context is not enough.) With the flag
> on, the full chain
> crawl → draft → generate → serve on localhost → register → invoke → log → report
> (US1–US4 + US6, plus the US5 checklist) is exercisable today, with no Partners
> store and no token. Phase 6 (T6.1+) is still required for the *real* deploy path
> — the per-domain origin-trial token step and real organic agent traffic are
> exactly what localhost does NOT prove — but it no longer blocks writing/proving
> the code. Build on localhost first; do the store/token/traffic phase once the
> pipeline works.

## Phase 0 — Setup
- [ ] T0.1: Repo scaffold, Python env, Playwright install + browser binaries.
      Logging sink: a **Cloudflare Worker + D1** table with an insert-only POST
      endpoint (chosen in clarify — free tier, no inactivity auto-pause).
      *(No story — infra prerequisite for everything else.)*
- [ ] T0.2: Enable `chrome://flags/#enable-webmcp-testing` in Chrome 149 and
      confirm `navigator.modelContext` exists on a localhost page — unblocks all
      local end-to-end testing without a store or token.
      *(No story — local test-harness prerequisite.)*

## Phase 1 — Crawl (US1)
- [ ] T1.1: `crawl` command: given a URL, render with Playwright, extract
      all `<form>` elements and interactive buttons with their HTML.
- [ ] T1.2: Filter pass: exclude `display:none` elements, flag likely
      cosmetic widgets (cookie banners, carousels) as low-confidence.
- [ ] T1.3: Output `candidates.json` matching the schema in design.md.
- [ ] T1.4: Origin-trial detection (FR-017): report whether the crawled origin
      already advertises a WebMCP origin trial (via `origin-trial` meta tag or
      `Origin-Trial` response header). Informational only — never a crawl filter.
- [ ] T1.5: Manual test against 2 real sites — confirm candidate list is
      sane before moving on (don't automate this check yet, eyeball it).

## Phase 2 — Draft tool contracts (US2)
- [ ] T2.1: Claude API call: given a candidate's HTML, draft name,
      description, input schema, following the format in design.md.
- [ ] T2.2: Ambiguity flagging: if the LLM's own confidence is low, or a
      field name is generic ("name," "info"), mark `review_status: "needs_review"`
      instead of `"approved"`.
- [ ] T2.3: Output `contracts.json`. This file is meant to be hand-edited —
      don't build tooling to edit it, just open it in an editor.

## Phase 3 — Generate code (US3)
- [ ] T3.1: For `approved` contracts with `api: "declarative"`, generate
      the HTML attribute diff (toolname/tooldescription on existing form).
- [ ] T3.2: For `approved` contracts with `api: "imperative"`, generate a
      `registerTool()` JS block.
- [ ] T3.3: Generate `.well-known/webmcp` manifest listing all approved tools.
- [ ] T3.4: Generate the invocation-logger snippet (posts to the Cloudflare
      Worker endpoint, fails silently per US4's non-breaking requirement).

## Phase 4 — Validate (US5)
- [ ] T4.1: Write the manual validation checklist as a markdown file
      (Model Context Tool Inspector steps, schema-validity check, no
      secrets in tool defs).
- [ ] T4.2: Walk the checklist for the first real deployed site, fix any
      registration issues found.

## Phase 5 — Report (US6)
- [ ] T5.1: `report` command: query the Cloudflare D1 logging store for a date
      range, print invocation counts grouped by site and tool.
- [ ] T5.2: Add a simple week-over-week view so the go/no-go signal from
      the pressure-test (organic invocations by week 4) is readable at a
      glance.

## Phase 6 — Deploy to test sites (descoped — see requirements.md v1.1)
- [ ] T6.1a: Create a free Shopify Partners account (partners.shopify.com,
      no billing info). **Needs hands-on help — Arnaud enters his own
      credentials; this is a manual prerequisite, not an agent-automatable step.**
- [ ] T6.1b: Create a **development store** (type: "test and build" — the free,
      non-expiring kind, *not* the transfer-to-client kind). Record the assigned
      `<store>.myshopify.com` origin — this is the owned origin all deploy steps
      target.
- [ ] T6.1c: Seed instrumentable markup: keep Dawn's contact page
      (`/pages/contact`), add 1–2 products so product/add-to-cart forms exist.
      These are the first crawl→draft→deploy candidates.
- [ ] T6.1d: Note the storefront **password gate** (dev stores are password-
      protected by default): either capture the password for Playwright or
      disable the gate for the test window — **crawl (T1.x) prerequisite.**
- [ ] T6.1e: Register a Chrome 149 origin-trial token for the
      `<store>.myshopify.com` origin (manual per-domain step, Principle I / NG3)
      — **deploy (T6.2) prerequisite.**
- [ ] T6.2: Deploy instrumentation + logger to the Shopify dev store, run
      T4.1 checklist.
- [ ] T6.3: Run `crawl` + `draft` (no deploy) against 1–2 of the official
      WebMCP demo apps; compare drafted contracts to their reference
      implementation as a quality check on Phase 2.
- [ ] T6.4: Run `crawl` + `draft` (no deploy) against 2–3 real public
      sites, picked for messy/varied markup, to stress-test detection.
- [ ] T6.5: Let the Shopify dev store logger run a couple of weeks with
      manual test invocations (real organic traffic isn't expected on a
      dev store — this phase is about proving the pipeline works, not
      collecting market signal).
- [ ] T6.6 (deferred to v2): Real Benelux SMB outreach and deployment,
      once the pipeline itself is proven out end-to-end.

---
**Reminder for the implement loop:** if reality disagrees with
requirements.md or design.md while working through these tasks, stop and
edit the spec file first, then continue. Don't let the code and the spec
quietly diverge — that's the failure mode SDD exists to prevent.
