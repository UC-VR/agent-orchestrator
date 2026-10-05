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
- Execution done same day: ~30G reclaimed; 2 guards fired correctly (gemini-auth units, ~/tools on PATH) — guards earn their keep. Total session ≈ 1.1M tokens (plan ~650K, execute ~450K). Remote prompts written+verified for ix/lp.
- Wave 2 lesson: disabling `cloudflared-paperclip1.service` took chatwoot+uptime1 offline ~2h — it was the only tunnel. Rule: before disabling any cloudflared/proxy unit, grep its config for ALL hostnames. Also: a scout brief's "memory says X is live" is stale the moment the owner retires X in the same session — re-brief workers with current decisions, not memory.
- ~/inbox introduced (ACTION items); ~/archive is terminal.
- 2026-09-10: Wave 3 lesson: a worker auditing services flagged the live cloudflared unit as 'stale' from its NAME — same trap twice in one day. Any brief touching units must carry the current ingress facts. Secret lesson: `op item get --format json` leaks values into transcripts; workers must use `op read op://…` into an env var in one command, never `op item get` on secret items; invoke secret-hygiene skill in any brief that touches 1Password.

2026-09-10:
- Listener lesson: a host-network docker container's ports don't show in `docker ps` — audit with `ss -ltnp` + /proc/<pid>/cgroup, not docker port lists. Port-number guesses (Wyoming, RustDesk) were both wrong; only the owner's sudo ss settled it.

## 2026-09-10
- Firewall lesson: a rich rule's direction (source vs destination) is the whole rule — read `--list-all` literally, don't trust the report's paraphrase.

## 2026-09-10 — ix-claude1 declutter EXECUTED + VERIFIED
- Ran from `handovers/PROMPT-declutter-ix-claude1-2026-09-11.md` + `handovers/PLAN-declutter-ix-claude1-2026-09-10.md`; passed executed-state verifier. Disk 60G→54G used (65%→58%), du 43G→37G, top-level entries 154→97.
- Honcho on ix UNWIRED (5 containers down, unit disabled+archived, 4 volumes kept, dir → ~/archive/2026-09/infra/honcho); Multica on ix is LIVE+corporate — NOT retired (unlike vr-oc1). fde-wrg already fully pushed by owner. ~/.paperclip+backups (986M) → ~/archive/2026-09/paperclip/ after Cloudflare-history harvest; cron line removed. Cert relocated to ~/.local/share/tailscale-certs/ (expires 2026-10-09, no auto-renew, PENDING). buzz.ixfin.tech (HTTP 000) KEEP, not retired — PENDING investigate.
- Phase B: skills/cloudflare(partial, gate-blocked)/ai-dev/ai-mvp/buzz committed+pushed; agent-librarian+agent-multica committed but NOT pushed (rebase conflicts); retired-multica-config unpushable (GitHub repo archived) → sole copy in archive. Phase A: 29 heartbeat scripts archived (not rm'd, history kept), 8 junk files rm'd. Phase D: 4 empty project dirs deleted post-harvest, 310 empty session dirs; cleanupPeriodDays=90 confirmed via `chezmoi cat | jq` (line-diff false-positived once — modify-template reorders keys). Phase E: 3 auto-memory MEMORY.md files corrected append-only; ~/inbox/PENDING-2026-09.md has 21 items; sudo line composed, NOT run.
- Lessons: scout agent can't ssh (read-only gate allowlist) — use worker for remote censuses; chezmoi modify-template survival test is `chezmoi cat ~/.claude/settings.json | jq .cleanupPeriodDays`, not a line-diff; a prior scout's "15 timers active" was wrong (only 2 were); stale plan notes must be re-checked against current git state before acting on them.

## 2026-09-10 (later) — ix follow-ups
- agent-librarian + agent-multica pushed (0dc011a, fbfb048); agent-multica then archived to ~/archive/2026-09/multica/agent-multica; retired-multica-config accepted as sole copy there (repo archived upstream).
- cloudflare repo: 44 remaining files committed 8eff2cd via owner-approved `git -c core.hooksPath=/dev/null` bypass with `approved_by: vryckov` trailer.
- Lesson: the gate that blocked cloudflare writes is `runtime/githooks/pre-commit` (agent-only by design), NOT `runtime/gate.sh` (a Claude PreToolUse hook for live CF writes) — don't conflate the two.
- Lesson: `tailscale cert` works as user vr on ix with no sudo (vr has cert rights) — renewed, new notAfter 2026-12-08, old pair backed up.
- ix-readai-webhook.service killed (was Funnel :443→localhost:3003 target, now dangling → 502 on https://ix-claude1.dala-wage.ts.net/). Owner-pending: `tailscale funnel --https=443 off` + delete webhook in Read.ai dashboard. buzz.ixfin.tech HTTP 000 still uninvestigated; Phase F sudo line still not confirmed run.

## 2026-09-10 — Declutter lp-ryckov11 (Windows 11) — EXECUTED, Phase F VERIFIED (1 retry)
- Plan: handovers/PLAN-declutter-lp-ryckov11-2026-09-10.md (+ -appendix.md). Prompt: handovers/PROMPT-declutter-lp-ryckov11-2026-09-11.md. Logs on host: C:\Users\vr\archive\2026-09\declutter-log-{harvest,A,B,C,D,E}.txt. Pending: C:\Users\vr\inbox\PENDING-2026-09-10.md (17 items).
- Outcome: home root 133→88 entries; ≈6.45GB moved to archive\2026-09\ (.cache 1.7G, .vscode 2.0G, wix 2.0G, .codex 551M, tmp 293M, .multica, .honcho, 10 small AI dotdirs, 24 scratch files/dirs, Downloads→Downloads\Archive 361 items); deleted ≈130MB (node_modules 12.8M, honcho plugin cache+marketplace 96M, 5 orphan .claude project dirs 21M, .claude-archive). Honcho unwired (24 bun mcp-server procs killed, plugin+marketplace removed via CLI, settings clean), cleanupPeriodDays=90 added, funnel off (dangling public lp-ryckov11.dala-wage.ts.net→:3003), 2 disabled claude-* tasks exported+unregistered. Corporate hostname claude-proxy2-lp-ryckov.llm.infinox.io 403→403 throughout.
- Deferred (owner): .buzz 1.7G + second-hand moves wait on pushes; 4 pushes blocked by expired gh token on lp; 2 merge conflicts (agent-bugalteris accounts.beancount; .buzz\verify_scratch\agent-orchestrator plugin.json); TeamViewer zips not byte-identical; onepass has 6 journal files; .env.bak-2026-08-12-rotation kept.
- Lessons: (1) `scout` agent's read-only gate has no `ssh` — remote-host scouting must go to `worker`/`sysadmin`. (2) Remote pwsh: stdin `pwsh -Command -` silently no-ops multi-line blocks; use `-EncodedCommand <b64 UTF-16LE>`; login shell is pwsh WITH profile so escape `$` in the outer string. (3) "Honcho retired" ≠ "honcho dead": an enabled plugin spawns an MCP server per Claude session (24 bun.exe here) — enumerate by CommandLine, kill children only, then uninstall; parents (29 claude.exe) unaffected. (4) Scout size/emptiness claims must be re-checked as preconditions at apply time (onepass "empty" had 6 items; TeamViewer "dup" hashes differed; bin/data/project "empty" were not). (5) HARVEST.md coverage must include wrapper dirs (infra\honcho) and loose-file groups moved as dirs — verifier caught 9 gaps. (6) Plan-time Length-sum sizing lies under OneDrive Files-On-Demand (Excedo dir "1.5TB").
- Token cost: scouts ≈73K+109K+90K, planner ≈103K, plan verifier ≈91K, exec ≈123K+29K+184K+79K, Phase F ≈131K+65K+22K → ≈1.1M total (prompt estimated 600–800K; overage = honcho live-writer STOP/resume + HARVEST retry).

### 2026-09-10 (later) — lp-ryckov11 follow-up batch
- Owner decisions: .buzz → archived (47,061 files / 1.79GB, exact match, merge-sim conflicts dropped); root `buzz` kept live (holds .claude\journal from a running claude session); second-hand kept live (local commit 32727f2 still unpushed); TeamViewer zips stay in Downloads\Archive; .env.bak untouched.
- agent-bugalteris drift = ONE conflict hunk in accounts.beancount (lines 90–123, upstream 3 vs stashed 28 lines) from a `pull --rebase --autostash`; nothing lost; needs owner's ledger judgement then `git add … && git commit && git stash drop && git push`. vr-oc1 clone is ahead 8 on a separate line and lacks lp's 96705c4 — the two clones have forked; reconcile after lp pushes.
- orchestra-publish (lp, no remote, 12 commits, 2026-07-01) = stale ancestor of agents\agent-orchestrator (80% file overlap, all diverged except LICENSE); unique files `_skillgen.json`, `hooks/session-start-skill-review.sh` — eyeball then archive. Not on vr-oc1.
- GitHub auth on lp: gh tokens invalid for UC-VR and vr-ixfin; HTTPS remotes + GCM with nothing cached; SSH aliases github.com-vr / github.com-ix (1Password SSH agent, pubkey-only IdentityFile) need GUI approval → headless `ssh -T` hangs. Global `url.https://github.com/.insteadOf=git@github.com:` rewrites plain SSH remotes to HTTPS, bypassing identity routing. Nothing pushed; no config touched. Lesson: on lp, any git push must be done at the console (approve 1Password prompt) or after `gh auth refresh -h github.com -u UC-VR`; don't attempt headless.
- Lesson: "LOCKED" empty dirs on Windows are often a cwd of a live `claude --resume` session — check `.claude\journal` presence before treating as junk.
