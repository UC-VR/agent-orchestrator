---
name: reconcile-learnings
description: "Reconcile the self-learning journal: consolidate <!-- learning --> blocks from LEARNINGS.md, dedupe against existing skills/recipes, and PROPOSE updates via skill-creator. Triggers on: 'reconcile learnings', 'run a learnings reconcile', 'consolidate learnings', 'learning reconcile', 'reconcile my learnings'."
---

# reconcile-learnings

Consolidate accumulated learnings into skill/recipe improvements. This is
triggered by the **weekly scheduled task** (`claude-weekly-reconcile`, Sundays
09:00) or by **manual invocation** any time you want to reconcile.

**PROPOSE-not-apply throughout.** You never auto-apply changes. Every proposed
edit goes through the `skill-creator` skill and is reviewed before it takes
effect. "Nothing worth capturing" is a valid, expected outcome — do not force a
proposal when the learnings do not warrant one.

The global learnings file is:

```
~/.claude/journal/LEARNINGS.md
```

## Procedure

### 1. Read the learning journal

Open the GLOBAL file `~/.claude/journal/LEARNINGS.md` and locate every
block marked with the sentinel:

```
<!-- learning -->
```

Each block follows this structure:

```
<!-- learning -->
## YYYY-MM-DD · session <id>
**Learned:** ...
**Decided:** ...
**Candidate skill updates:** ...
**Dedupe check:** ...
```

If the file does not exist or contains no `<!-- learning -->` blocks, report
"nothing to reconcile" and stop.

### 2. Cross-reference candidates against existing skills (dedupe gate)

For each candidate update, run the dedupe helper:

```bash
bash ${CLAUDE_SKILL_DIR}/../../hooks/skill-overlap.sh <keywords>
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory
(`skills/reconcile-learnings/`), so `../../hooks/` points at the `hooks/`
directory shipped with the agent-orchestrator plugin. For a hand-copied install
where the plugin's hooks were not installed, use
`~/.claude/hooks/skill-overlap.sh` instead.

Replace `<keywords>` with 1-3 terms describing the candidate (e.g.,
`bash error-handling`, `google sheets append`). It searches `SKILL.md` and
`references/*.md` across the known skill roots and lists overlapping skills,
de-duplicated by skill.

Interpret the output:
- **Overlap found** — refine the existing skill; do NOT add a new one.
- **Contradiction found** — flag the conflict explicitly in your proposal.
- **No overlap** — a new reference or skill may be warranted, but still verify it
  isn't covered by a skill under a different name.

### 3. Decide the edit using the PATCH-OVER-CREATE hierarchy

Prefer the least-invasive change that fits. Work down this hierarchy and stop at
the first level that applies:

1. **Patch the most-relevant existing skill** — amend its `SKILL.md` in place.
2. **Patch an umbrella/parent skill** — if one skill already covers the area,
   extend it rather than creating a sibling.
3. **Add a `references/<topic>.md`** file under an existing skill — prefer this
   over a new top-level skill when the learning is a sub-topic of an existing
   capability.
4. **Create a brand-new skill** — last resort only, when none of the above fit.

### 4. Refusals (hard rules)

- **Refuse instance-specific skill names.** Do not propose skills named after a
  single session, project, ticket, or one-off task. A skill must name a
  generalizable, reusable capability.
- **Refuse duplicates.** Do not propose a skill that duplicates an
  already-installed skill. You MUST have run `skill-overlap.sh` (step 2) first;
  if it shows an overlap, patch the existing skill instead.

### 5. Backup → validate → rollback envelope (per proposed edit)

For every edit you draft against an existing skill file:

- **Backup / note pre-edit state.** Before drafting the change, record the
  pre-edit content or its exact location (path + the lines you would change) so
  the original can be restored if the proposal is rejected. Do not overwrite the
  only copy of the original.
- **Validate.** Confirm the proposed result is well-formed: valid YAML
  frontmatter (`name`, `description` present and intact), the sentinel/markdown
  structure is unbroken, and the change does not break the skill's triggering or
  contradict its existing guidance.
- **Rollback plan.** State explicitly how to undo the change (restore from the
  noted pre-edit content / backup path) if it is rejected downstream.

### 6. Provenance stamp (per proposed edit)

Every PROPOSED edit must carry provenance so reconciled changes are traceable:

```yaml
metadata:
  origin: reconciled
  date: <YYYY-MM-DD>
```

Add this to the target skill's frontmatter (or an equivalent metadata field the
skill format supports). New `references/*.md` files should note the same
`origin: reconciled` / `date` at the top.

### 7. PROPOSE the consolidated set of edits

Group related learnings from multiple sessions into coherent updates. For each
proposed change:

- Invoke the `skill-creator` skill to scaffold or update the target skill/recipe.
  **Never auto-apply** — proposals go through `skill-creator` and are reviewed
  before taking effect.
- State what changed and why, referencing the source learning blocks by
  date/session.
- Resolve contradictions between learnings explicitly — do not silently drop one
  side.
- Prefer refining existing skills over adding overlapping new ones (see the
  hierarchy in step 3).

If, after review, none of the learnings warrant a change, honestly report
**"nothing worth capturing"** and make no proposal. That is a correct outcome.

## Sentinel

The exact sentinel string used throughout this loop is:

```
<!-- learning -->
```

Every learning block in `LEARNINGS.md` begins with a line containing exactly this
string. Do not vary the sentinel.
