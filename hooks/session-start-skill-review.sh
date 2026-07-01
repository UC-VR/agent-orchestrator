#!/usr/bin/env bash
# SessionStart hook: v2 self-learning loop. Non-blocking. Always exit 0.
# Branch A (reconcile due): delta >= threshold -> escalated nudge, update reconcile counter.
# Branch B (normal review): marker exists -> count sessions, emit enriched nudge.
# Branch C: silent.
set -uo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
input=$(cat 2>/dev/null || true)
cwd=$(printf '%s' "$input" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{process.stdout.write(String(JSON.parse(d).cwd??""))}catch(e){process.stdout.write("")}})' 2>/dev/null)
[ -z "$cwd" ] && cwd="$PWD"
src=$(printf '%s' "$input" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{process.stdout.write(String(JSON.parse(d).source??""))}catch(e){process.stdout.write("")}})' 2>/dev/null)

# suppress nudge when SessionStart fires due to context compaction
[ "$src" = "compact" ] && exit 0

marker="$cwd/.claude/.skill-update-pending"
learnings="$cwd/.claude/journal/LEARNINGS.md"
state="$cwd/.claude/.reconcile-state"
threshold="${SELF_LEARNING_RECONCILE_THRESHOLD:-10}"

# learnings_total: count sentinel lines; 0 if file missing or grep finds nothing
learnings_total=0
if [ -f "$learnings" ]; then
  learnings_total=$(grep -c -x -F '<!-- learning -->' "$learnings" 2>/dev/null || true)
  # grep -c can return empty on some platforms; normalise
  [[ "$learnings_total" =~ ^[0-9]+$ ]] || learnings_total=0
fi

# last: integer from state file; 0 if missing or non-numeric
last=0
if [ -f "$state" ]; then
  raw=$(cat "$state" 2>/dev/null | tr -d '[:space:]' || true)
  [[ "$raw" =~ ^[0-9]+$ ]] && last="$raw"
fi

delta=$(( learnings_total - last ))

# Ensure threshold is numeric; treat non-numeric as 10
[[ "$threshold" =~ ^[0-9]+$ ]] || threshold=10

if [ "$threshold" -gt 0 ] && [ "$learnings_total" -gt 0 ] && [ "$delta" -ge "$threshold" ]; then
  # Branch A: reconcile pass due
  printf '%s' "$learnings_total" > "$state" 2>/dev/null || true
  rm -f "$marker" 2>/dev/null || true
  ctx="Self-learning loop — RECONCILE PASS DUE: ${delta} new learnings recorded since the last reconcile. Do a deeper consolidation (PROPOSE-not-apply): 1) Read .claude/journal/LEARNINGS.md (all recent '<!-- learning -->' blocks) plus recent session journals. 2) Cross-reference every candidate update against existing skills/recipes using: bash ${HOOK_DIR}/skill-overlap.sh <keywords> — identify duplications, contradictions, and stale guidance. 3) PROPOSE a consolidated set of skill/recipe edits via the skill-creator skill: group related learnings, resolve contradictions explicitly, refine existing skills rather than adding overlapping ones. Never auto-apply. The reconcile counter has been reset."
  node -e 'process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:process.argv[1]}}))' "$ctx" 2>/dev/null
elif [ -f "$marker" ]; then
  # Branch B: normal review nudge
  count=$(wc -l < "$marker" 2>/dev/null | tr -d ' ' || echo "0")
  [[ "$count" =~ ^[0-9]+$ ]] || count=0
  rm -f "$marker" 2>/dev/null || true
  ctx="Self-learning loop: ${count} prior session(s) recorded in .claude/journal/ since the last review. Before proposing any skill/recipe change, do this PROPOSE-not-apply debrief (skip if not relevant): 1) DEBRIEF — open the most recent .claude/journal/<date>-<session>.md entries, read the transcript(s) they reference, and synthesize what was learned, what was decided/changed, and candidate skill/recipe updates. 2) CAPTURE — append a learning block to .claude/journal/LEARNINGS.md. Each block MUST start with a line containing exactly '<!-- learning -->' (this is how the loop counts learnings), followed by '## <YYYY-MM-DD> · session <id>' and the fields **Learned:**, **Decided:**, **Candidate skill/recipe updates:**, **Dedupe check:**. 3) DEDUPE GATE — for each candidate update, run: bash ${HOOK_DIR}/skill-overlap.sh <keywords> to find existing skills/recipes that overlap or contradict. If it duplicates an existing skill, refine that skill instead of adding a new one; if it contradicts one, flag the conflict explicitly. Only PROPOSE edits via the skill-creator skill — never auto-apply."
  node -e 'process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:process.argv[1]}}))' "$ctx" 2>/dev/null
fi
# Branch C: no output
exit 0
