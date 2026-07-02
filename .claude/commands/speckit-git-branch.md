---
description: Cut a git feature branch matching the active spec directory (after_specify hook)
allowed-tools: Bash(bash .specify/scripts/bash/create-feature-branch.sh)
---

Run the deterministic branch helper and report which branch you ended up on:

```bash
bash .specify/scripts/bash/create-feature-branch.sh
```

This reads `.specify/feature.json`, derives the branch name from the feature
directory basename (e.g. `specs/002-foo` → `002-foo`), and creates/switches to
that branch. It is idempotent — safe to run when the branch already exists or is
already checked out. Do not create the branch by any other means; just run the
script and report its output.
