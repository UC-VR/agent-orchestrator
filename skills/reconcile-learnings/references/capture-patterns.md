---
origin: harvested
source: self-improving-agent (peterskoett/self-improving-agent)
harvested: 2026-07-02
note: Harvested from self-improving-agent during skills consolidation Phase 4.
---

# Capture patterns

Advisory vocabulary for the learning loop: what counts as a transferable lesson
worth capturing, and what warrants promotion at reconcile time. Harvested from
the `self-improving-agent` skill during skills consolidation (Phase 4); adapted
to this loop's append-only, single-file, PROPOSE-only design.

These fill the two things the loop was previously silent on:

1. The SessionEnd capture prompt asks the background agent to decide whether a
   session holds a "genuinely transferable lesson" but gives no signal taxonomy.
2. This reconcile skill decides what warrants a change but states no positive
   promotion criteria (only refusals: instance-specific names, duplicates).

## Signals that a session holds a transferable lesson

When judging whether a session (or a `<!-- learning -->` block) is worth
capturing or promoting, look for these concrete signals:

- **User correction.** The user pushed back on an approach or fact — "no, that's
  not right", "actually it should be...", "that's outdated". The corrected
  understanding is the lesson.
- **Knowledge gap closed.** The user supplied information you did not have, or a
  referenced doc/API behaved differently than expected.
- **Capability gap.** The user wanted something that does not exist — "can you
  also...", "is there a way to..." — pointing at a missing skill or tool.
- **Tool or command failure.** A command, API, or tool failed and the diagnosis
  was non-obvious; the fix or diagnostic sequence is the lesson.
- **Better approach found.** A superior method for a recurring task emerged.

Use these as *kinds* of lesson (tags in prose), not as separate files or a
required field: `correction`, `knowledge_gap`, `capability_gap`, `tool_failure`,
`best_practice`.

## Promotion signals (reconcile time)

A captured learning warrants a proposed skill/recipe change when one or more of
these holds — beyond the existing refusals:

- **Recurring.** The same lesson appears across 2+ sessions/blocks. Recurrence
  is the strongest promote signal.
- **Non-obvious.** It required real debugging/investigation to discover; a
  future agent would not derive it unaided.
- **Verified.** The fix or approach was actually confirmed to work, not just
  hypothesized.
- **Broadly applicable.** Reusable across projects, not a one-off detail. (This
  restates the loop's existing "not instance-specific" rule — keep enforcing it.)

## Deliberately NOT adopted

These parts of `self-improving-agent` were reviewed and rejected because they
conflict with this loop's design (recorded here so they are not re-harvested):

- Structured entry schema (ID `LRN/ERR/FEAT-YYYYMMDD-XXX`, Priority, Status,
  Area) — conflicts with the append-only, freeform, background-captured block.
- Status lifecycle (`pending → resolved → promoted`) — blocks here are
  append-only and consumed by reconcile, never mutated in place.
- Three-file split (`LEARNINGS.md` / `ERRORS.md` / `FEATURE_REQUESTS.md`) — this
  loop uses one unified `LEARNINGS.md`.
- OpenClaw / generic UserPromptSubmit + PostToolUse capture hooks — this loop
  already captures via its own gated SessionEnd hook.
