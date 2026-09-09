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

## 2026-09-10 declutter planning session
- Scout agents (agent-orchestrator:scout) cannot write files: the scout-readonly-gate blocks redirects, `docker`, `systemctl`, and complex jq (pipes, `as`, `$()`). Brief scouts to return inline tables, and use a `worker` for docker/systemctl checks. The jq restriction made the session-content scout cost ~98K tokens; a worker with a one-off script would be cheaper next time.
- The projects scout only detects dirs with .git/README/compose markers — it missed 5 plain dirs (~1 GB) under ~/claw-services; verifier caught it. Always add a plain `ls` of container dirs to project scouts.
- Corrections to auto-memory claims: ~/skills has 50 SKILL.md (not ~195); honcho@honcho plugin is DISABLED in settings.json (memory says "active"). ~/.claude/todos and plans do not exist; journal/ is a live learning-capture pipeline.
- Declutter plan (verified, 377 lines): handovers/PLAN-declutter-vr-oc1-2026-09-10.md. Key decisions: minimal-move (live repos stay put, only new tree is ~/archive/2026-09/<domain>/), cleanupPeriodDays=60, crash-loops (paperclip, multica-backend) diagnose-only, agent-comms-1 dirty+unpushed is the first FINISH item. Execution not started.
- Phase-1 cost: 3 scouts + 1 researcher + 1 services worker ≈ 260K tokens; planner (opus) 3 calls ≈ 160K; 2 verifier passes ≈ 80K.
