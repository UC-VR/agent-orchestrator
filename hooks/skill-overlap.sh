#!/usr/bin/env bash
# skill-overlap.sh — dedupe helper for the self-learning loop.
# Usage: skill-overlap.sh <keyword> [keyword...]
# Searches SKILL.md + references/*.md files in known skill/recipe roots for each
# keyword and prints matches, de-duplicated by skill. Always exits 0.
# Pure bash+grep+find; no network; no jq.
#
# Env:
#   SKILL_OVERLAP_ROOTS — colon-separated extra roots (MSYS-style paths),
#                         PREPENDED to the built-in roots. Only existing dirs kept.
set -uo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: skill-overlap.sh <keyword> [keyword...]"
  echo "  Searches SKILL.md + references/*.md files for keywords to detect overlap before adding new skills."
  exit 0
fi

# --- Build list of search roots that actually exist -----------------------
# Extra roots from SKILL_OVERLAP_ROOTS (colon-separated) are prepended.
candidate_roots=()
if [ -n "${SKILL_OVERLAP_ROOTS:-}" ]; then
  IFS=':' read -r -a _extra <<< "$SKILL_OVERLAP_ROOTS"
  for d in "${_extra[@]}"; do
    [ -n "$d" ] && candidate_roots+=("$d")
  done
fi
candidate_roots+=(
  "$HOME/.claude/skills"
  "$HOME/.claude/plugins"
  "$HOME/agents/skills"
  "$PWD/.claude/skills"
  "$PWD/.claude/recipes"
)

roots=()
declare -A seen_root=()
for dir in "${candidate_roots[@]}"; do
  [ -d "$dir" ] || continue
  # canonicalize so the same dir reached via $HOME and $PWD isn't scanned twice
  canon=$(realpath "$dir" 2>/dev/null || printf '%s' "$dir")
  [ -n "${seen_root[$canon]:-}" ] && continue
  seen_root["$canon"]=1
  roots+=("$dir")
done

if [ ${#roots[@]} -eq 0 ]; then
  echo "(no skill/recipe directories found; checked SKILL_OVERLAP_ROOTS, ~/.claude/skills, ~/.claude/plugins, ~/agents/skills, .claude/skills, .claude/recipes)"
  echo ""
  echo "JUDGE overlap vs contradiction yourself and PROPOSE-not-apply via the skill-creator skill."
  exit 0
fi

# --- Enumerate candidate files under a root (SKILL.md + references/*.md) ---
# Uses find (GNU grep's --include glob does not reliably honor subpaths on MSYS).
# Excludes _archived, node_modules, .git dirs. NUL-separated output.
list_files() {
  find "$1" \
    \( -type d \( -name _archived -o -name node_modules -o -name .git \) -prune \) -o \
    \( -type f -name 'SKILL.md' -print0 \) -o \
    \( -type f -path '*/references/*.md' -print0 \) 2>/dev/null
}

# skill dir for a matched file (the directory that owns the skill)
skill_dir_of() {
  case "$1" in
    */references/*) printf '%s' "${1%/references/*}" ;;
    *)              printf '%s' "${1%/SKILL.md}" ;;
  esac
}

for kw in "$@"; do
  echo "=== keyword: $kw ==="
  found=0
  for root in "${roots[@]}"; do
    # gather candidate files (NUL-safe)
    files=()
    while IFS= read -r -d '' f; do files+=("$f"); done < <(list_files "$root")
    [ ${#files[@]} -eq 0 ] && continue

    # matching files only (-l), NUL-separated (-Z), case-insensitive, skip binary
    matches=()
    while IFS= read -r -d '' m; do matches+=("$m"); done < <(grep -lIZi -- "$kw" "${files[@]}" 2>/dev/null || true)
    [ ${#matches[@]} -eq 0 ] && continue

    # de-duplicate by skill dir; list each skill once with its matching files
    declare -A seen_skill=()
    printed_root=0
    for m in "${matches[@]}"; do
      sdir=$(skill_dir_of "$m")
      rel="${sdir#"$root"/}"
      relfile="${m#"$sdir"/}"
      # dedupe: list each skill at most once per keyword
      [ -n "${seen_skill[$sdir]:-}" ] && continue
      seen_skill["$sdir"]=1
      if [ "$printed_root" -eq 0 ]; then echo "  [root: $root]"; printed_root=1; fi
      echo "    - $rel  (matched: $relfile)"
      found=1
    done
    unset seen_skill
  done
  if [ "$found" -eq 0 ]; then
    echo "  (no overlap found)"
  fi
  echo ""
done

echo "NOTE: JUDGE whether each match is an overlap (refine existing) or contradiction (flag conflict) — PROPOSE-not-apply via the skill-creator skill."
exit 0
