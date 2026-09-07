# Orchestrator Memory (append-only, dated entries)

## 2026-08-28
- Rolled out the launcher-family memory scaffold across the fleet (agent-orchestrator,
  agent-sysadmin, agent-lawyer, agent-bugalteris): every domain launcher now add-dirs its
  home repo, personas read MEMORY/JOURNAL/BACKLOG (+ domain dirs) at session start when
  home is reachable, and append learnings back at session end (append-only, dated,
  commit+push ff-only). Memory files are `merge=union` in `.gitattributes` so appends
  from all 3 machines auto-merge without conflicts.

## 2026-09-05
- 45-day census: worker 311 / verifier 91 / scout 7 / judge 1 spawns — judge fired once, only on a user-pre-shaped A/B/C prompt.
- Root cause: judge had no input by construction — no fan-out rule, line 18 forbade splitting one deliverable, judge trigger was one Example bullet, gate was verifier-only; verify-reminder.sh loop-guard was dead (bare vs namespaced compare) so verifier nudge fired on every spawn.
- Fix shipped in 1.8.0: Tournament Trigger (offer, don't impose — AskUserQuestion, default single producer), three-tier comparative gate (invariant / offer / mandatory-only-when-acted-on-unreviewed), producers emit candidates not rankings, blind judging, "Candidates: N" routing line, hook fixes, SessionEnd spawn counts.
- Scout: same model tier as worker (haiku banned) so "cheap eyes" premise was false; value is enforced read-only + context isolation. 2/7 uses were verifier work; 1/7 net loss (below threshold). Now has Bash behind fail-closed allowlist gate.
- Learning: a mandatory gate that names one agent (verifier) mechanically starves siblings; symmetric reminders + an explicit candidate-count field make omission visible.
- Learning: cross-session peer report caught two improvements (output-shape trigger, blind judging) but got the hook mechanism wrong — always re-verify peer diagnoses against files.
- Open validation: confirm real PreToolUse payloads carry agent_id/agent_type for scout Bash calls (gate no-ops silently if absent).

## 2026-09-07
- Handover claims about "rolled back" changes must be checked against `git ls-files` of the source repo — a junction-creator script the handover said was rolled back was still present in `main`.
- "Byte-identical" capture claims go stale once later commits touch the same file — verify against current git history, not the commit that made the original claim.
- Herdr #3269 (Shift+Enter flattened to bare CR under modifyOtherKeys negotiation) — Ctrl+J is the working substitute until a fix is chosen.
- A producer's plausible mtime-based timeline was overturned by a verifier using git history + the upstream issue tracker — always check the source repo's history and vendor issue trackers before blaming the last-changed layer.
