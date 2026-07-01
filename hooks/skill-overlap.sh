#!/usr/bin/env bash
# skill-overlap.sh — dedupe helper for the self-learning loop.
# Usage: skill-overlap.sh <keyword> [keyword...]
# Searches *.md files in known skill/recipe dirs for each keyword and prints matches.
# Always exits 0. Pure bash+grep+find; no network calls; no deps beyond coreutils.
set -uo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: skill-overlap.sh <keyword> [keyword...]"
  echo "  Searches skill/recipe .md files for keywords to detect overlap before adding new skills."
  exit 0
fi

# Build list of search roots that actually exist
roots=()
for dir in \
  "$HOME/.claude/skills" \
  "$HOME/.claude/plugins" \
  "$PWD/.claude/skills" \
  "$PWD/.claude/recipes"; do
  [ -d "$dir" ] && roots+=("$dir")
done

if [ ${#roots[@]} -eq 0 ]; then
  echo "(no skill/recipe directories found; checked ~/.claude/skills, ~/.claude/plugins, .claude/skills, .claude/recipes)"
  echo ""
  echo "JUDGE overlap vs contradiction yourself and PROPOSE-not-apply via the skill-creator skill."
  exit 0
fi

for kw in "$@"; do
  echo "=== keyword: $kw ==="
  found=0
  for root in "${roots[@]}"; do
    # grep -rinI: recursive, case-insensitive, line numbers, skip binary files
    # limit to ~20 hits per keyword per root to stay concise
    hits=$(grep -rinI -- "$kw" "$root" --include="*.md" 2>/dev/null | head -n 20 || true)
    if [ -n "$hits" ]; then
      found=1
      echo "  [root: $root]"
      while IFS= read -r line; do
        echo "  $line"
      done <<< "$hits"
    fi
  done
  if [ "$found" -eq 0 ]; then
    echo "  (no overlap found)"
  fi
  echo ""
done

echo "NOTE: JUDGE whether each match is an overlap (refine existing) or contradiction (flag conflict) — PROPOSE-not-apply via the skill-creator skill."
exit 0
