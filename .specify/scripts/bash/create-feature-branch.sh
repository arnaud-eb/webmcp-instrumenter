#!/usr/bin/env bash
# after_specify hook helper: cut a git feature branch matching the active spec
# directory. The branch name is the basename of feature_directory in
# .specify/feature.json (e.g. specs/002-foo -> 002-foo).
#
# Idempotent and safe: no-op if already on that branch, checks it out if it
# already exists, creates it otherwise. Never fails the caller (always exit 0).
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT" || exit 0

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "[branch-hook] not a git repo; skipping"; exit 0; }

[ -f .specify/feature.json ] || {
  echo "[branch-hook] no .specify/feature.json; skipping"; exit 0; }

FEATURE_DIR="$(sed -n 's/.*"feature_directory"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  .specify/feature.json | head -1)"
[ -n "$FEATURE_DIR" ] || {
  echo "[branch-hook] feature_directory empty; skipping"; exit 0; }

BRANCH="$(basename "$FEATURE_DIR")"
CURRENT="$(git branch --show-current 2>/dev/null || echo '')"

if [ "$CURRENT" = "$BRANCH" ]; then
  echo "[branch-hook] already on $BRANCH"
elif git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH" && echo "[branch-hook] switched to existing branch $BRANCH"
else
  git checkout -b "$BRANCH" && echo "[branch-hook] created and switched to $BRANCH"
fi
exit 0
