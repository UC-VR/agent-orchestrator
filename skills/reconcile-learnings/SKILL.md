---
name: reconcile-learnings
description: "Reconcile the self-learning journal: consolidate <!-- learning --> blocks from LEARNINGS.md, dedupe against existing skills/recipes, and PROPOSE updates via skill-creator. Triggers on: 'reconcile learnings', 'run a learnings reconcile', 'consolidate learnings', 'learning reconcile', 'reconcile my learnings'."
---

# reconcile-learnings

Manual trigger for the v2 self-learning loop reconcile pass. Run this when prompted by the escalated SessionStart nudge, or any time you want to consolidate accumulated learnings into skill/recipe improvements.

## Procedure (PROPOSE-not-apply; never auto-apply changes)

### 1. Read the learning journal

Open `.claude/journal/LEARNINGS.md` and locate every block marked with the sentinel:

```
<!-- learning -->
```

Each block follows this structure:
```
<!-- learning -->
## YYYY-MM-DD · session <id>
**Learned:** ...
**Decided:** ...
**Candidate skill/recipe updates:** ...
**Dedupe check:** ...
```

Also read recent session journals in `.claude/journal/` (files named `<date>-<session_id>.md`) for context on what those sessions covered.

### 2. Cross-reference candidates against existing skills

For each candidate skill/recipe update identified in step 1, run the dedupe helper:

```bash
bash ${CLAUDE_SKILL_DIR}/../../hooks/skill-overlap.sh <keywords>
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory (`skills/reconcile-learnings/`), so `../../hooks/` points at the `hooks/` directory shipped with the agent-orchestrator plugin. For a hand-copied install where the plugin's hooks were not installed, use `~/.claude/hooks/skill-overlap.sh` instead.

Replace `<keywords>` with 1-3 terms describing the candidate (e.g., `bash error-handling`, `google sheets append`).

Interpret the output:
- **Overlap found** — refine the existing skill rather than creating a new one.
- **Contradiction found** — flag the conflict explicitly in your proposal.
- **No overlap** — safe to propose as a new skill/recipe, but verify it isn't covered by a skill with a different name.

### 3. PROPOSE a consolidated set of edits

Group related learnings from multiple sessions into coherent updates. For each proposed change:

- Invoke the `skill-creator` skill to scaffold or update the target skill/recipe.
- State what changed and why (reference the source learning blocks by date/session).
- Resolve contradictions between learnings explicitly — do not silently drop one side.
- Prefer refining existing skills over adding overlapping new ones.

**Never auto-apply.** All changes go through `skill-creator` and are reviewed before taking effect.

### 4. Reset the reconcile counter

After completing the reconcile pass, update the counter so the hook does not immediately re-trigger:

```bash
grep -c -x -F '<!-- learning -->' .claude/journal/LEARNINGS.md > .claude/.reconcile-state
```

Run this from the project root (the directory where `.claude/` lives). If `LEARNINGS.md` does not exist yet, write `0`:

```bash
echo 0 > .claude/.reconcile-state
```

## Sentinel

The exact sentinel string used throughout this loop is:

```
<!-- learning -->
```

Every learning block in `LEARNINGS.md` must begin with a line containing exactly this string. The SessionStart hook counts these with `grep -c -x -F '<!-- learning -->'`. Do not vary the sentinel.
