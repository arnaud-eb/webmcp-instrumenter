# Tasks: WebMCP Concierge Instrumenter

**Input**: Design documents from `specs/001-webmcp-instrumenter/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included **selectively** — for the three constitution non-negotiables (fail-open
logger, param-keys-only, approved-gate) and the two file contracts. Not full TDD everywhere.

**Organization**: Grouped by user story (US1–US6 from spec.md) for independent build/test.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US6 per spec.md; Setup/Foundational/Polish have no story label
- Paths follow plan.md: `src/webmcp_instrumenter/`, `worker/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization.

- [x] T001 Create project structure per plan.md (`src/webmcp_instrumenter/`, `src/webmcp_instrumenter/llm/`, `src/webmcp_instrumenter/templates/`, `worker/`, `tests/{unit,integration,fixtures}/`)
- [x] T002 Initialize Python 3.13 project: `pyproject.toml` with deps (playwright, anthropic, jsonschema, httpx, typer, pytest) + a 3.13 venv; `pip install -e .`
- [x] T003 [P] Install Playwright Chromium binaries (`playwright install chromium`)
- [x] T004 [P] Configure ruff (lint+format) and pytest in `pyproject.toml`
- [x] T005 [P] Scaffold the Cloudflare Worker project in `worker/` (`wrangler.toml`, `package.json`, `src/index.ts` stub)
- [x] T006 Confirm local WebMCP test harness: `chrome://flags/#enable-webmcp-testing` enabled + `navigator.modelContext` present on a localhost page *(env prerequisite — already verified 2026-07-06; re-confirm after any Chrome update)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared code every story depends on. **⚠️ No user story starts until this is done.**

- [x] T007 Define core models (`Candidate`, `Contract`, `InvocationEvent`, `Report`) per data-model.md in `src/webmcp_instrumenter/models.py`
- [x] T008 [P] JSON load/save + JSON-Schema validation helper (validates against `specs/001-webmcp-instrumenter/contracts/*.schema.json`) in `src/webmcp_instrumenter/io.py`
- [x] T009 [P] Config/env management (Anthropic API key, sink URL, timeouts) in `src/webmcp_instrumenter/config.py`
- [x] T010 CLI skeleton wiring the four subcommands (`crawl`/`draft`/`generate`/`report`) with typer in `src/webmcp_instrumenter/cli.py`

**Checkpoint**: Foundation ready — user stories can begin.

---

## Phase 3: User Story 1 — Crawl & detect candidates (Priority: P1) 🎯 MVP

**Goal**: Given a URL, emit `candidates.json` of detected form/button actions.

**Independent Test**: Run `crawl` on a fixture page → validates against
`contracts/candidates.schema.json`; the form is a `high`-confidence candidate; hidden
elements excluded; low-confidence surfaced flagged; `_meta.origin_trial_advertised` present.

- [x] T011 [P] [US1] HTML fixtures (a real form, a `display:none` form, a cosmetic widget, an origin-trial `<meta>` case) in `tests/fixtures/`
- [x] T012 [US1] `crawl` command: Playwright render + extract `<form>` and interactive buttons with outerHTML in `src/webmcp_instrumenter/crawl.py`
- [x] T013 [US1] Detection/filtering: exclude `display:none`; flag cosmetic/ambiguous as `confidence:"low"` (never drop) in `src/webmcp_instrumenter/detect.py`
- [x] T014 [US1] Origin-trial detection (FR-017): check `origin-trial` meta tag + `Origin-Trial` response header → `_meta` (informational only) in `src/webmcp_instrumenter/detect.py`
- [x] T015 [US1] Emit `candidates.json` (array + `_meta`) validated via the T008 helper
- [x] T016 [P] [US1] Integration test: crawl fixtures → expected candidate set incl. flag/exclude behavior in `tests/integration/test_crawl.py`

**Checkpoint**: US1 independently functional — you can inventory a site.

---

## Phase 4: User Story 2 — Draft tool contracts (Priority: P1)

**Goal**: Turn each candidate into a draft `contracts.json` entry (name/description/schema).

**Independent Test**: Feed `candidates.json` → `contracts.json` with snake_case `tool_name`,
≤300-char `description`, valid `input_schema`, `review_status:"needs_review"`; ambiguous
fields flagged for review.

- [x] T017 [US2] `LLMProvider` interface (draft-a-contract method, structured JSON out) in `src/webmcp_instrumenter/llm/base.py`
- [x] T018 [US2] Claude provider implementation (strict system prompt for schema drafting) in `src/webmcp_instrumenter/llm/claude.py`
- [x] T019 [US2] `draft` command: per candidate → contract; ambiguous/low-confidence → `needs_review` (FR-004) in `src/webmcp_instrumenter/draft.py`
- [x] T020 [US2] Validate output: `jsonschema`-valid `input_schema`, snake_case name, ≤300-char description; emit `contracts.json` validated against `contracts/contracts.schema.json`
- [x] T021 [P] [US2] Unit test: ambiguous field → `needs_review`; malformed LLM output handled without crash in `tests/unit/test_draft.py`

**Checkpoint**: US1 + US2 work — drafts ready for human review.

---

## Phase 5: User Story 3 — Generate implementation snippets (Priority: P1)

**Goal**: For **approved** contracts, emit declarative attrs / `registerTool()` blocks +
manifest + `logger.js`. First shippable instrumentation.

**Independent Test**: Given approved + non-approved contracts → code emitted ONLY for
approved; manifest lists exactly those; no secrets in any output; nothing approved → no code.

- [ ] T022 [US3] `generate` command with the **approved-only gate** (`review_status=="approved"`, else skip) in `src/webmcp_instrumenter/generate.py`
- [ ] T023 [P] [US3] Declarative emitter (`toolname`/`tooldescription` on form, `toolparamdescription` on inputs) in `src/webmcp_instrumenter/generate.py`
- [ ] T024 [P] [US3] Imperative `registerTool()` JS emitter in `src/webmcp_instrumenter/generate.py`
- [ ] T025 [P] [US3] `.well-known/webmcp` manifest emitter from `src/webmcp_instrumenter/templates/manifest.json.j2`
- [ ] T026 [US3] `logger.js` emitter (non-blocking, posts `param_keys` only) from `src/webmcp_instrumenter/templates/logger.js.j2`
- [ ] T027 [P] [US3] Unit test (**Principle I + FR-007**): only approved emitted; manifest = approved set; no secrets present in `tests/unit/test_generate.py`

**Checkpoint**: 🚀 P1 MVP complete — crawl→draft→generate produces instrumentation for a site.

---

## Phase 6: User Story 4 — Log real invocations (Priority: P2)

**Goal**: Stand up the Cloudflare sink + a fail-open logger capturing PII-free events.

**Independent Test**: Invoke a registered tool → event stored with `param_keys` only (no
values); take the sink offline → tool call + page still succeed.

- [ ] T028 [US4] D1 schema (`invocations` table, `param_keys` column only — no value columns) in `worker/schema.sql`
- [ ] T029 [US4] Worker `POST /events` insert-only endpoint (rejects value-bearing fields) in `worker/src/index.ts`
- [ ] T030 [P] [US4] Worker read path for `report` (scoped, date-range query) in `worker/src/index.ts`
- [ ] T031 [US4] `wrangler.toml` D1 binding + deploy config; deploy the Worker
- [ ] T032 [US4] Finalize `logger.js` template: fire-and-forget, swallow all errors (Principle III / FR-010) in `src/webmcp_instrumenter/templates/logger.js.j2`
- [ ] T033 [P] [US4] Test (**Principle II + III**): event payload has key names only / no values; simulated sink outage does not throw into host page in `tests/unit/test_logger.py`

**Checkpoint**: US4 works — real invocations are captured, safely.

---

## Phase 7: User Story 5 — Weekly invocation report (Priority: P2)

**Goal**: `report` prints counts by site + tool with a week-over-week view.

**Independent Test**: With seeded events, `report --from --to` prints correct grouped counts
+ weekly view; empty range → empty groups, exit 0.

- [ ] T034 [US5] `report` command: query D1 read path for a date range; group by site + tool in `src/webmcp_instrumenter/report.py`
- [ ] T035 [US5] Week-over-week view + `--format table|json` in `src/webmcp_instrumenter/report.py`
- [ ] T036 [P] [US5] Integration test: seeded events → expected grouped + weekly counts in `tests/integration/test_report.py`

**Checkpoint**: US5 works — the go/no-go signal is readable.

---

## Phase 8: User Story 6 — Validate registration (Priority: P3)

**Goal**: A manual checklist to confirm tools registered correctly before trusting output.

**Independent Test**: Walk the checklist on a deployed page → confirms tools visible in the
inspector, schema validates, no secrets.

- [ ] T037 [US6] Write the manual validation checklist (Model Context Tool Inspector / `navigator.modelContext.getTools()` steps, schema-validity, no-secrets check) in `docs/validation-checklist.md`
- [ ] T038 [US6] Align the checklist with `quickstart.md` localhost end-to-end steps (US1–US6 walkthrough)

**Checkpoint**: All user stories independently functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T039 [P] `README.md`: install, the 4-stage pipeline, localhost quickstart pointer
- [ ] T040 [P] Additional unit tests for edge cases (empty candidate list, nothing approved, unrenderable page) in `tests/unit/`
- [ ] T040a [P] Integration test for stage independence (FR-013 / SC-006): re-running `draft` on an existing `candidates.json` does NOT re-invoke `crawl`, and each stage reads/writes only its own file boundary, in `tests/integration/test_stage_independence.py`
- [ ] T041 ruff lint/format clean across `src/` and `tests/`
- [ ] T042 Run `quickstart.md` end-to-end on localhost and confirm all steps green
- [ ] T043 [P] Package metadata + console-script entry point (`webmcp-instrument`) in `pyproject.toml`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)** → no deps.
- **Foundational (P2)** → after Setup; **blocks all user stories**.
- **User stories (P3–P8)** → all after Foundational.
  - **US2 depends on US1** (needs `candidates.json`). **US3 depends on US2** (needs
    `contracts.json`). US1→US2→US3 is the P1 pipeline chain.
  - **US5 depends on US4** (report reads what the logger/sink writes).
  - **US6 depends on US3** (validates generated/deployed output) and benefits from US4.
- **Polish (P9)** → after the desired stories.

### Within each story

- Fixtures/tests (where present) alongside implementation; models → services → command.
- Commit after each task or logical group.

### Parallel opportunities

- Setup: T003, T004, T005 in parallel.
- Foundational: T008, T009 in parallel (T007 first; T010 after models).
- US1: T011 (fixtures) ∥ start of T016 (test); US3 emitters T023/T024/T025 in parallel.
- Different developers could take US4 (Worker/TS) and US5 (report/Python) in parallel once
  the sink contract (T028/T029) is fixed.

---

## Parallel Example: User Story 3

```bash
# The three emitters touch independent concerns — build in parallel:
Task: "Declarative emitter (toolname/tooldescription/toolparamdescription)"
Task: "Imperative registerTool() JS emitter"
Task: "Manifest emitter from templates/manifest.json.j2"
```

---

## Implementation Strategy

### MVP scope

- **Smallest independently testable slice**: **US1** (crawl → `candidates.json`).
- **First genuinely useful deliverable**: **US1 + US2 + US3** (the P1 triad) — this is what
  produces pasteable instrumentation for a site. Treat the P1 triad as milestone 1.
- **Measurement increment**: add **US4 + US5** (P2) — the actual Experiment B signal.
- **Confidence increment**: add **US6** (P3).

### Build order (recommended)

1. Setup + Foundational → foundation ready.
2. US1 → US2 → US3 (P1 triad) → **validate the whole pipeline on localhost** (T006 harness).
3. US4 → US5 (stand up sink + report) → confirm end-to-end logging.
4. US6 (validation checklist) + Polish.
5. Then Phase 6 real-deploy work (Shopify store / origin-trial token / organic traffic) —
   tracked in the informal root `tasks.md`, gated behind the store setup, and NOT part of
   this build's code.

---

## Notes

- `[P]` = different files, no incomplete-task deps.
- `[Story]` label ties each task to a spec.md user story for traceability (SDD rule: a task
  that doesn't trace to a story is scope creep).
- The three constitution non-negotiables have explicit test tasks (T027, T033) — do not
  drop them.
- Everything through Phase 9 is exercisable on localhost with the WebMCP flag (T006); no
  Shopify store or origin-trial token required until the real-deploy phase.
