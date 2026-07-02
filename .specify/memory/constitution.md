<!--
SYNC IMPACT REPORT
==================
Version change: (template, unversioned) → 1.0.0 → 1.0.1
Bump rationale:
  1.0.0 — MAJOR: first concrete ratification of the constitution from the template;
    all placeholder tokens replaced with project-specific principles.
  1.0.1 — PATCH: clarify site #1 is a free Shopify Partners dev store not yet created
    (setup is a prerequisite task needing hands-on help); no principle change.

Modified principles: N/A (initial ratification — no prior named principles)

Added sections:
  - Core Principles (I–V)
  - Technology Constraints
  - Scope Discipline & Development Workflow
  - Governance

Removed sections: None (all template placeholders resolved)

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gates are generic
     ("Gates determined based on constitution file"); no hardcoded principle names.
  ✅ .specify/templates/spec-template.md — no constitution-derived mandatory
     sections needed changes.
  ✅ .specify/templates/tasks-template.md — task categories already accommodate
     human-review gates and staged CLI outputs; no change required.
  ✅ .specify/templates/checklist-template.md — generic; no change required.

Deferred TODOs: None. RATIFICATION_DATE set to adoption date (2026-07-02).
-->

# WebMCP Concierge Instrumenter Constitution

## Core Principles

### I. Human Gate Before Anything Goes Live (NON-NEGOTIABLE)

No generated artifact reaches a third party's live site without an explicit human
review-and-approve step. The `generate` stage MUST only emit code for contracts whose
`review_status` is `approved`; anything else is skipped. There is NO auto-deployment to
customer sites (NG2) and NO automatic origin-trial token registration (NG3) — both stay
manual, per-domain steps.

Rationale: injecting a bad schema or mis-mapped field into someone else's checkout is a
liability and a trust failure in a concierge relationship. The extra manual paste-in costs
minutes and buys a large margin of safety. When the tool is uncertain (ambiguous field
mapping, low-confidence candidate), it MUST flag for review rather than guess silently.

### II. Privacy by Data Minimization (NON-NEGOTIABLE)

The invocation logger records param key **names only** — never param values (NG4). Log
events are limited to: site, tool name, timestamp, success/failure, and `param_keys`. No
form field values, no PII, is captured by default. Tool definitions MUST NOT embed secrets.

Rationale: Arnaud is a data processor for any customer site's data even in a manual
concierge model, so GDPR minimization is a design constraint baked into the data model —
not an afterthought bolted on later. Any change that would capture values requires an
explicit, documented amendment to this principle.

### III. Non-Blocking Instrumentation

Client-side instrumentation MUST fail open with respect to the host site. If the logging
endpoint is unreachable or errors, the agent's tool call and the end user's interaction
MUST still succeed. Logging is best-effort telemetry; it is never on the critical path of
the site it measures.

Rationale: the tool exists to *measure* real invocation volume for a go/no-go decision. A
measurement apparatus that degrades the thing it measures corrupts both the site owner's
trust and the data.

### IV. Re-runnable, Single-Purpose Stages

The pipeline is four independent CLI stages — `crawl`, `draft`, `generate`, `report` —
each with a text/JSON in → text/JSON out contract (`candidates.json`, `contracts.json`,
snippet/manifest/logger, weekly counts). Each stage MUST be independently runnable and
re-runnable without forcing re-execution of the others. Intermediate artifacts are
human-inspectable and human-editable files, not opaque in-memory state.

Rationale: crawling is slow and flaky and the LLM `draft` step is the one most likely to
need human correction. Splitting stages means a prompt tweak triggers a re-`draft`, not a
re-`crawl`. Plain-file boundaries also give the human gate (Principle I) a natural place to
intervene.

### V. Right-Sized Simplicity (YAGNI)

This is a throwaway measurement tool that must exist for ~4–6 weeks to answer one question,
not a product. NO multi-tenant dashboard, NO auth, NO billing, NO custom backend, NO UI
(NG1). Reach for the simplest thing that works (e.g. a single insert-only Supabase table
over a hand-rolled service). Complexity that is not justified by answering the go/no-go
question is out of scope by default.

Rationale: over-engineering infrastructure for a tool with a known short lifespan is wasted
spend. This is a deliberate place to *not* apply maximal rigor to disposable infrastructure,
while keeping full rigor on the principles above that carry real user/legal risk.

## Technology Constraints

- **Language: Python.** The crawler and all pipeline stages are Python. This is a
  scripting/automation-shaped problem and a deliberate low-stakes place to practice Python;
  there is no UI or standing web app that would justify a Next.js/TS stack here.
- **LLM provider is swappable.** Tool-contract drafting MUST NOT hard-lock to a single
  vendor. Claude is the default (Sonnet is sufficient — no extended reasoning needed for
  schema drafting), but the provider seam stays swappable (e.g. Claude/OpenAI).
- **Crawling: Playwright (Python bindings)** — required to render JS-driven forms that
  plain requests/BeautifulSoup would miss.
- **Target runtime: Chrome 149+ only** (origin-trial scope). Each site requires its own
  origin-trial token, issued manually per domain (see Principle I / NG3).
- **Out of scope in v1:** sites without a stable Playwright-renderable DOM (heavy
  client-side auth walls, CAPTCHAs) (NG5).

## Scope Discipline & Development Workflow

- **Primary objective of this build:** practice spec-driven development on a real,
  moderately complex project — not to close real Benelux SMB relationships yet.
- **Target sites for v1 are test sites, by deliberate descope:**
  1. A free Shopify Partners dev store Arnaud owns outright — exercises the full pipeline
     including the deploy phase, since no third-party permission is needed. Arnaud does not
     yet have this store; **setup of the free Partners dev store is a prerequisite task and
     needs hands-on help** before the deploy phase can be exercised.
  2. Google's official WebMCP demo apps (`GoogleChromeLabs/webmcp-tools`) — crawl/draft
     test cases and a reference implementation to compare drafted contracts against.
  3. 2–3 real public sites, **crawl-and-draft only, never deployed to** — to stress-test
     candidate detection against messy real-world markup.
- **Real Benelux SMB outreach (original Experiment B) is deferred to v2 scope**, once the
  pipeline is proven. This is a deliberate descope, not scope creep, and the tasks plan
  MUST reflect it. Re-expanding scope to live third-party sites requires revisiting this
  section AND satisfying Principle I in full.
- **Validation is manual and mandatory before trusting output:** deployed instrumentation
  MUST be confirmed in Chrome 149 via the Model Context Tool Inspector — tools visible,
  schema validates, no secrets present — rather than trusting LLM output blindly.

## Governance

This constitution supersedes ad-hoc practice for the WebMCP Concierge Instrumenter. When a
proposed change conflicts with a principle here, the principle wins unless this document is
amended first.

- **Amendments** require a documented rationale, an update to this file, and a version bump
  per the policy below. Amendments to a NON-NEGOTIABLE principle (I, II) additionally
  require an explicit note of what risk the change accepts.
- **Versioning policy (semantic):**
  - MAJOR — backward-incompatible governance changes or removal/redefinition of a principle.
  - MINOR — a new principle/section added, or materially expanded guidance.
  - PATCH — clarifications, wording, and non-semantic refinements.
- **Compliance review:** spec, plan, and tasks artifacts MUST be checked against these
  principles (the plan template's Constitution Check gate). Any complexity or scope
  expansion beyond Principle V / the Scope Discipline section MUST be justified in writing
  or rejected. Deviations from Principles I–III are not justifiable within v1 scope.

**Version**: 1.0.1 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-02
