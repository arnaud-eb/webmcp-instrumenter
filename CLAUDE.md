# CLAUDE.md — WebMCP Concierge Instrumenter

Standing rules for this repo. For what's true of the *current feature*, read the
active spec under `specs/` (path in `.specify/feature.json`), not this file.

## What this project is

The smallest tool that lets Arnaud run **Experiment B**: instrument a handful of
**test** sites with WebMCP tools and measure real agent-invocation volume over
4–6 weeks. If invocations are real, the AgentBridge product becomes worth
building; if near zero, this tool was the whole spend. This is **not** the
product — resist building one. Primary goal of this build: practice spec-driven
development on a real, moderately complex project.

## Spec-Driven Development workflow (how to work here)

Order: **constitution → specify → clarify → plan → tasks → implement**.

- Source of truth is the spec, not the code. **If reality disagrees with the
  spec while implementing, stop and edit the spec first, then continue.** Do not
  let code and spec quietly diverge — that's the failure mode SDD prevents.
- Governing principles live in `.specify/memory/constitution.md`. It supersedes
  ad-hoc practice; when a change conflicts with a principle, the principle wins
  unless the constitution is amended first.
- Feature artifacts live in `specs/<NNN-name>/`: `spec.md`, `plan.md`,
  `tasks.md`, `checklists/`. `.specify/feature.json` points at the active one.
- Every task in a `tasks.md` should trace back to a user story / requirement.
  If a task doesn't trace to the spec, it's scope creep — flag it.
- A SessionStart hook auto-injects the active feature + next open tasks; an
  after_specify hook auto-cuts a feature branch. Both are project-local.

## Non-negotiables (from the constitution)

1. **Human gate before anything goes live.** No generated artifact reaches a
   third party's site without explicit human review+approval. `generate` emits
   code ONLY for contracts with `review_status: approved`. No auto-deploy, no
   auto origin-trial-token registration. When unsure, flag for review — never
   guess silently.
2. **Privacy by data minimization (GDPR).** The invocation logger records param
   **key names only** — never values. Log events = site, tool name, timestamp,
   success/failure, `param_keys`. No PII by default. No secrets in tool defs.
3. **Non-blocking instrumentation.** Client-side logging MUST fail open: if the
   logging endpoint is unreachable, the agent's tool call and the end user's
   interaction still succeed. Logging is best-effort, never on the critical path.

## Architecture (from design.md)

Four independent, re-runnable CLI stages with plain-file boundaries:

```
crawl    URL              -> candidates.json
draft    candidates.json  -> contracts.json      (LLM-assisted, human-edited)
generate contracts.json   -> snippet.html/js, webmcp-manifest.json, logger.js
report   (reads log sink) -> weekly invocation counts
```

Each stage runs and re-runs on its own (re-running `draft` must not force a
re-`crawl`). Intermediate artifacts are human-inspectable/editable files.

## Stack constraints

- **Language: Python.** Scripting/automation shape; also a deliberate place to
  practice Python. No UI, no web app, no Next.js/TS here.
- **Crawling: Playwright (Python)** — needed for JS-rendered forms.
- **LLM drafting: provider-swappable.** Claude is the default (Sonnet is enough;
  no extended reasoning needed for schema drafting). Do NOT hard-lock a vendor.
- **Logging sink: provider-agnostic, undecided (clarify-stage decision).** Only
  hard requirement: stays reachable for the full multi-week window without
  silently dropping events. Beware free tiers that auto-pause on inactivity.
- **Target runtime: Chrome 149+** (WebMCP origin-trial scope).

## Origin trials (why token setup is manual)

WebMCP is experimental; Chrome enables it per-site via an **origin trial**. Each
origin you deploy to needs its own token, registered by hand at Chrome's
origin-trial console and pasted into the page head
(`<meta http-equiv="origin-trial" content="...">`). Tokens are scoped per-origin
and expire. Automating issuance/renewal/revocation across domains is real
complexity we defer until Experiment B says "go". Manual per-domain for now.

Verified API (Chrome 149, 2026-07-06): imperative `navigator.modelContext`
(`registerTool` / `getTools` / `executeTool` / `ontoolchange`); declarative
attributes `toolname` + `tooldescription` on the form, `toolparamdescription` on
inputs. Local testing without a token: `chrome://flags/#enable-webmcp-testing`.

## Scope discipline (v1 = test sites only)

Real Benelux SMB outreach is **deferred to v2**. v1 target sites:
1. A free Shopify Partners dev store Arnaud owns — full pipeline incl. deploy.
   (Not created yet; setup is a prerequisite needing hands-on help.)
2. Official WebMCP demo apps (`GoogleChromeLabs/webmcp-tools`) — crawl/draft
   only, as a reference to compare drafted contracts against.
3. 2–3 real public sites — **crawl/draft only, never deployed to.**

Right-size everything (Principle V / YAGNI): no dashboard, auth, billing, custom
backend, or UI. Simplest thing that answers the go/no-go question.

## Git / conventions

- Feature work happens on `NNN-name` branches (auto-cut by the after_specify
  hook). The constitution and repo-level SDD scaffold live on `main`.
- Commit when asked. Do not add Claude co-author trailers to commit messages.
- Keep this file under ~200 lines: standing rules only. Feature-specific facts
  belong in the spec, not here.
