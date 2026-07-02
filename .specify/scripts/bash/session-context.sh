#!/usr/bin/env bash
# SessionStart hook: print the active SDD feature + next open tasks so a resumed
# session (after tmux/caffeinate, /clear, or a fresh start) does not need the
# context re-explained. Output goes to stdout and is injected as context.
# Forgiving by design: never aborts a session start.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)"
[ -n "$ROOT" ] && cd "$ROOT" 2>/dev/null || exit 0

echo "## Active SDD context (auto-injected)"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "- Branch: $(git branch --show-current 2>/dev/null || echo '(detached)')"
fi

FEATURE_DIR=""
if [ -f .specify/feature.json ]; then
  FEATURE_DIR="$(sed -n 's/.*"feature_directory"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    .specify/feature.json | head -1)"
fi

if [ -n "$FEATURE_DIR" ] && [ -d "$FEATURE_DIR" ]; then
  echo "- Feature: $FEATURE_DIR"
  [ -f "$FEATURE_DIR/spec.md" ] && echo "    - spec.md present"
  [ -f "$FEATURE_DIR/plan.md" ] && echo "    - plan.md present"

  TASKS=""
  [ -f "$FEATURE_DIR/tasks.md" ] && TASKS="$FEATURE_DIR/tasks.md"
  [ -z "$TASKS" ] && [ -f tasks.md ] && TASKS="tasks.md"

  if [ -n "$TASKS" ]; then
    echo "    - Next open tasks ($TASKS):"
    grep -nE '^[[:space:]]*- \[ \]' "$TASKS" 2>/dev/null | head -3 | sed 's/^/        /'
    [ "$(grep -cE '^[[:space:]]*- \[ \]' "$TASKS" 2>/dev/null)" = "0" ] && \
      echo "        (all tasks checked off)"
  else
    echo "    - No tasks.md yet — run /speckit-tasks"
  fi
else
  echo "- No active feature resolved (run /speckit-specify)"
fi

echo "- Workflow: constitution → specify → clarify → plan → tasks → implement."
echo "- Rule: if reality disagrees with the spec, edit the spec first, then code."
exit 0
