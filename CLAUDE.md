# CLAUDE.md

## Working on this repo

This is the `vr-orchestra` **orchestrator** plugin source (`agent-orchestrator`). The
orchestrator persona lives in `agents/orchestrator.md`; `worker`, `verifier`, `judge`,
and `scout` are its sibling agents. Editing an `agents/*.md` file here does not change
what's live — plugin installs read from the plugin cache, so run `claude plugin update`
(or reinstall) after any edit to reach it. Version stamp in every `agents/*.md` first
body line must equal `plugin.json`'s version (grep-check before tagging).

## Memory overlay (cco+/cco-)

When this repo is the launch dir or add-dir'd (the CoS launcher family), the orchestrator
should, before planning: read `memory/MEMORY.md`, `BACKLOG.md`, and the most recent files
under `handovers/`. After the session, append learnings — append-only, dated entries,
via a worker (never rewrite history, never edit in place).

This section does **not** redefine the persona — that's `agents/orchestrator.md`'s job,
and this overlay must not touch it. The CoS role here is **execution-time delegation +
outcome memory** (what got delegated, what worked, what to remember next time) — it is
not the fleet's planning-time stack advisor. For "what agent/skill/stack should I use,"
consult `agent-librarian` instead of duplicating that here.
