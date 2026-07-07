---
description: Refresh the auto-generated active-feature snapshot in CLAUDE.md (after_plan hook)
allowed-tools: Bash(bash .specify/scripts/bash/update-agent-context.sh)
---

Run the agent-context refresh helper and report the snapshot it wrote:

```bash
bash .specify/scripts/bash/update-agent-context.sh
```

This reads `.specify/feature.json` + the active `plan.md` and rewrites only the
`AGENT-CONTEXT` marker block in `CLAUDE.md` (language, deps, storage, feature dir,
branch). Hand-written standing rules are untouched. It is idempotent — just run it
and report the result.
