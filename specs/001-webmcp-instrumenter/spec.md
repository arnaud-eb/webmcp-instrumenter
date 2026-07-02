# Feature Specification: WebMCP Concierge Instrumenter

**Feature Branch**: `001-webmcp-instrumenter`

**Created**: 2026-07-02

**Status**: Draft

**Input**: Project `requirements.md` + `design.md` (WebMCP Concierge Instrumenter — a
tool to instrument test sites with WebMCP tools and measure real agent-invocation
volume for the Experiment B go/no-go decision).

## User Scenarios & Testing *(mandatory)*

The primary actor throughout is **Arnaud**, operating the tool in a concierge model
(he runs it himself against sites he owns or is authorized to crawl). There is no
end-user-facing UI; "users" of the tool are the operator, and the beneficiaries of
the measurement are the AI agents that may invoke the instrumented tools.

### User Story 1 - Crawl a site and detect candidate actions (Priority: P1)

Arnaud points the tool at a single URL and receives a list of candidate actions
(forms, key buttons) that could plausibly become WebMCP tools, so he does not have to
manually inventory a site's markup.

**Why this priority**: Nothing downstream exists without a candidate inventory. This is
the foundation of the pipeline and delivers standalone value (a site audit) on its own.

**Independent Test**: Run the crawl step against a real URL and confirm it emits a
candidate list where each entry has an element type, page location, and a raw HTML
snippet, with hidden/cosmetic elements excluded or flagged low-confidence.

**Acceptance Scenarios**:

1. **Given** a reachable URL with one or more forms, **When** Arnaud runs the crawl
   step, **Then** he receives a list of candidate actions, each with element type,
   page location, and a raw HTML snippet.
2. **Given** a page containing a hidden form (`display:none`) or a clearly cosmetic
   widget (cookie banner, search-as-you-type box, carousel), **When** the crawl runs,
   **Then** those elements are excluded or flagged as low-confidence rather than
   presented as equal candidates.

---

### User Story 2 - Draft tool contracts from candidates (Priority: P1)

Arnaud turns each candidate into a draft WebMCP tool contract (name, agent-facing
description, input schema), so he edits and approves rather than authoring from scratch.

**Why this priority**: Turning raw markup into structured, agent-readable contracts is
the core intellectual work the tool automates; it is the step that saves the most time.

**Independent Test**: Feed a candidate's HTML to the draft step and confirm it produces
a snake_case name, an agent-facing description under 300 characters in the site's primary
language, and a valid input JSON Schema — flagging ambiguous fields for review instead of
guessing.

**Acceptance Scenarios**:

1. **Given** a candidate action, **When** the draft step processes it, **Then** the
   output contains a snake_case tool name, a description under 300 characters written for
   an agent audience in the site's primary language, and a JSON Schema for inputs.
2. **Given** a candidate with an ambiguous field (e.g. a single "name" field that could
   be full name or first/last), **When** the draft step processes it, **Then** the
   contract is marked as needing review rather than silently guessing a mapping.
3. **Given** a draft contract file, **When** Arnaud edits it by hand and sets a contract's
   review status to approved, **Then** that approval state is preserved for the next step.

---

### User Story 3 - Generate copy-paste implementation snippets (Priority: P1)

For approved contracts, Arnaud gets ready-to-paste output — declarative HTML attributes
for simple forms, imperative registration blocks for custom actions, and a manifest entry
— so instrumenting a site takes minutes, not hours.

**Why this priority**: This is the tangible artifact the operator ships; without it the
drafted contracts have no path onto a page.

**Independent Test**: Given an approved contract, confirm the generate step emits either
declarative HTML attributes or an imperative registration block (matching the contract's
declared style) plus a manifest entry, and emits nothing for contracts not marked approved.

**Acceptance Scenarios**:

1. **Given** an approved contract for an existing form, **When** the generate step runs,
   **Then** it outputs declarative HTML attributes to add to that form.
2. **Given** an approved contract for a custom action, **When** the generate step runs,
   **Then** it outputs an imperative tool-registration code block.
3. **Given** a mix of approved and not-approved contracts, **When** the generate step
   runs, **Then** it emits code only for approved contracts and a manifest listing exactly
   those tools.
4. **Given** any generated artifact, **When** Arnaud inspects it, **Then** it contains no
   secrets or credentials.

---

### User Story 4 - Log real agent invocations (Priority: P2)

Once tools are registered on a site, Arnaud captures each agent invocation as a minimal
event, so he has real data on whether agents actually call the tools instead of a hunch.

**Why this priority**: This is the measurement payoff that answers Experiment B — but it
depends on Stories 1–3 having produced live instrumentation first.

**Independent Test**: Trigger a registered tool and confirm an event is recorded with tool
name, site, timestamp, success/failure, and parameter key names only (no values); then
make the logging destination unreachable and confirm the tool call still succeeds for the
end user.

**Acceptance Scenarios**:

1. **Given** a registered tool is invoked by an agent, **When** the invocation completes,
   **Then** an event is recorded containing site, tool name, timestamp, success/failure,
   and the parameter key names only — never parameter values.
2. **Given** the logging destination is unreachable or erroring, **When** an agent invokes
   a tool, **Then** the tool call and the end user's interaction still succeed, and the
   logging failure is swallowed rather than surfaced to the user or breaking the site.

---

### User Story 5 - Weekly invocation report (Priority: P2)

Arnaud requests a report of invocation counts for a date range, grouped by site and tool,
so he can compare against the Experiment B go/no-go thresholds with a number, not a guess.

**Why this priority**: The report converts raw log events into the decision signal. It is
valuable but strictly downstream of logging (Story 4).

**Independent Test**: With log events present for a date range, run the report and confirm
it prints invocation counts grouped by site and by tool, with a readable week-over-week view.

**Acceptance Scenarios**:

1. **Given** logged invocation events across several sites and tools, **When** Arnaud runs
   the report for a date range, **Then** it outputs invocation counts grouped by site and
   by tool.
2. **Given** multiple weeks of events, **When** the report runs, **Then** a week-over-week
   view makes the go/no-go trend readable at a glance.

---

### User Story 6 - Validate registration before trusting output (Priority: P3)

After deploying instrumentation to a site, Arnaud follows a manual checklist to confirm the
tools actually registered correctly in the target browser, so he is not trusting generated
output blindly.

**Why this priority**: A confidence/QA aid that reduces risk, but it does not itself produce
or measure instrumentation; it supports the other stories.

**Independent Test**: With instrumentation deployed, walk the checklist and confirm it
verifies tools are visible in the tool inspector, schemas validate, and no secrets appear
in tool definitions.

**Acceptance Scenarios**:

1. **Given** instrumentation deployed to a site, **When** Arnaud walks the validation
   checklist, **Then** it confirms tools are visible in the browser's tool inspector, each
   schema validates, and no secrets are present in any tool definition.

---

### Edge Cases

- **Unrenderable pages**: sites behind heavy client-side auth walls or CAPTCHAs that the
  crawler cannot render are out of scope for v1 — the crawl step should fail clearly rather
  than emit garbage candidates.
- **No candidates found**: a page with no forms or actionable buttons yields an empty
  candidate list, not an error.
- **Ambiguous drafts**: contracts the drafter is unsure about are surfaced for review, never
  silently shipped.
- **Logging outage**: an unreachable logging destination must never degrade the host site
  (see Story 4).
- **Nothing approved**: if no contract is approved, the generate step produces no code and
  says so, rather than emitting speculative output.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept a URL and return a list of candidate actions, each with
  element type, page location, and a raw HTML snippet.
- **FR-002**: The tool MUST exclude hidden elements and flag clearly cosmetic widgets as
  low-confidence rather than presenting them as equal candidates.
- **FR-003**: The tool MUST draft, for each candidate, a snake_case tool name, an
  agent-facing description under 300 characters in the site's primary language, and an
  input JSON Schema.
- **FR-004**: The tool MUST flag ambiguous candidates for human review instead of guessing
  a field mapping silently.
- **FR-005**: The tool MUST provide a human review-and-approval gate, and MUST generate
  implementation code only for contracts that have been explicitly approved.
- **FR-006**: The tool MUST generate declarative HTML attributes for existing forms and
  imperative registration blocks for custom actions, matching each contract's declared
  style, plus a manifest entry for each approved tool.
- **FR-007**: Generated artifacts MUST NOT contain secrets or credentials.
- **FR-008**: The tool MUST generate a client-side invocation logger that records, per
  invocation, the site, tool name, timestamp, success/failure, and parameter key names only.
- **FR-009**: The logger MUST NOT record parameter values or any personal data by default.
- **FR-010**: The logger MUST fail open — if the logging destination is unreachable, the
  agent's tool call and the end user's interaction MUST still succeed.
- **FR-011**: The tool MUST produce a manual validation checklist covering tool visibility
  in the target browser's tool inspector, schema validity, and absence of secrets.
- **FR-012**: The tool MUST produce a report of invocation counts for a given date range,
  grouped by site and by tool, including a week-over-week view.
- **FR-013**: Each pipeline step (crawl, draft, generate, report) MUST be independently
  runnable and re-runnable without forcing re-execution of the other steps.
- **FR-014**: Intermediate artifacts between steps MUST be human-inspectable and
  human-editable files.
- **FR-015**: The tool MUST NOT auto-deploy generated code to any site; deployment remains a
  manual paste-in performed by the operator.
- **FR-016**: The logging destination MUST remain reachable for the full multi-week
  measurement window without silently dropping events.

### Key Entities

- **Candidate action**: a detected form or button that could become a WebMCP tool —
  attributes: id, type (form/button), confidence, page location, raw HTML snippet,
  visibility.
- **Tool contract**: a drafted, human-editable WebMCP tool definition — attributes: source
  candidate, tool name, agent-facing description, input schema, registration style
  (declarative/imperative), review status (gates code generation).
- **Invocation event**: a single logged agent call — attributes: site, tool name, timestamp,
  success/failure, parameter key names (no values).
- **Report**: an aggregation of invocation events over a date range, grouped by site and by
  tool, with a week-over-week view.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Arnaud can take one owned site from crawl through draft, generate, manifest,
  and logger in under 2 hours of his active time.
- **SC-002**: After deployment, the weekly report shows invocation counts per site and per
  tool clearly enough to answer the Experiment B go/no-go question with a number rather than
  a guess.
- **SC-003**: 100% of shipped tools originate from a contract the operator explicitly
  approved — no tool reaches a live site without passing the review gate.
- **SC-004**: 0 parameter values and 0 personal-data fields appear in logged events.
- **SC-005**: When the logging destination is unavailable, 100% of tool invocations still
  succeed for the end user (no site breakage attributable to logging).
- **SC-006**: Re-running any single pipeline step after a change does not require re-running
  the others (e.g. a draft re-run does not force a re-crawl).

## Assumptions

- **Operator-run, single actor**: the tool is run by Arnaud in a concierge model against
  sites he owns or is authorized to crawl; there is no multi-user, auth, or billing scope.
- **Crawl granularity (informed default, revisit in clarify)**: v1 processes a single URL
  per invocation; automatic multi-page nav-following (e.g. auto-discovering "contact",
  "shop", "book now") is deferred to v2.
- **Low-confidence handling (informed default, revisit in clarify)**: low-confidence
  candidates are surfaced and flagged for review, not silently dropped — consistent with the
  human-gate principle.
- **Logging destination (revisit in clarify)**: kept provider-agnostic; the only hard
  requirement is FR-016 (stays reachable for the full window, no auto-pause / silent loss).
- **Target sites for v1 are test sites, by deliberate descope** (not real Benelux SMB
  outreach, which is v2): (1) a free dev store Arnaud owns outright, exercising the full
  pipeline including deploy; (2) official WebMCP demo apps, used crawl/draft-only as
  reference; (3) 2–3 real public sites, crawl/draft-only, never deployed to.
- **Target browser & activation**: the instrumented tools target a WebMCP-capable browser
  (Chrome 149+ origin-trial scope); each deployed origin requires its own origin-trial token,
  registered manually per domain.
- **Unrenderable sites out of scope**: sites the crawler cannot render (heavy client-side
  auth walls, CAPTCHAs) are excluded from v1.
- **Primary objective of this build is to practice spec-driven development** on a real,
  moderately complex project; closing real SMB relationships is explicitly deferred.
