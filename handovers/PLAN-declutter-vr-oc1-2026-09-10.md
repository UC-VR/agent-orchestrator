# PLAN — Declutter vr-oc1 (Arch, user `vr`) — 2026-09-10

Planning only. Execution is a later session, dry-run-first. No sudo in this plan except the
explicit hand-to-VR block (§4F). Nothing under `~/.local/share/chezmoi` is touched (Wave 5.1 in flight).

---

## 0. STATUS 2026-09-10 — EXECUTED

**Owner decisions taken (verbatim intent):** approved rubbish list; OpenClaw dashboards ×5 → deleted;
paperclip (repo, deployed copy, containers, ~/.paperclip*, cloudflared unit) → retired+deleted;
multica (service, containers, symlink, agent-multica repo — pushed to GitHub first) → retired+deleted;
gemini-auth-manager → delete (blocked by guard, see pending); tenacitos → deleted; lobsterboard +
lobster-healthcheck timer → deleted; claw-backups → pruned to newest 1 (`pre-auth-swap-20260315-0244`);
the rest → harvest wave; cleanupPeriodDays → 90; finish-first commits done.

**Executed:** Phase B (9 repos committed/pushed; librarian + skills fast-forwarded and pushed),
harvest (3 HARVEST.md + paperclip patch + preserved customs under archive/2026-09/paperclip/untracked/
+ 3 habits promoted to -home-vr memory + 2 memory corrections), Phase A deletes (20 targets), service
teardown (compose down -v for paperclip & multica; 5 user units disabled and moved to
archive/2026-09/openclaw/systemd-units/), Phase C moves (gstack, claw-logs, emergency-bot, tasks, zoe),
Phase D (~/.claude: cleanupPeriodDays=90, 87 heartbeat files, 12 orphan/memory-only project dirs, 431
empty leaves). Disk: 172G→142G used (~30G reclaimed). Log: ~/archive/2026-09/declutter-log-2026-09-10.txt.
Settings backup: ~/archive/2026-09/settings.json.bak-2026-09-10.

### Wave 2 — 2026-09-10 (later same day), VERIFIED

**Owner decisions:** gemini delete + stale units removed; ~/tools = ACESx memory tooling,
still undecided; Honcho unwired completely; cloudflared checked; docker prune done; convex
vars were URLs/paths not secrets — nothing to rotate; ~/backups archived; honcho plugin
uninstalled; sessions staged for omnigent; ~/inbox introduced as the ACTION location — rule:
empty by 2026-12 pass; archive = never look again.

**Executed:** cloudflared-paperclip1 unit restored — it was the single tunnel (0efd55e7) for
chatwoot+uptime1+multica1; disabling it caused a ~2h public outage of chatwoot/uptime1, fixed;
multica1 ingress stripped, config backed up. gemini-auth-manager + 4 units removed. Stale
slack-backup unit swept. Honcho: 23 MCP procs killed, compose down (5 volumes kept), timer
off, plugin/marketplace/MCP/permissions removed, ~/CLAUDE.md memory line updated, dir →
archive/2026-09/infra/honcho, skill removed from ~/skills (source repo + marketplace cache +
plugin cache; commit 51b2192). Docker prune +35G. ~/backups → archive/2026-09/backups. Disk
172G→101G used total today.

**PENDING — owner decisions/actions:**
1. ~/tools: ACESx memory scripts (mem-recall/mem-write/obs-search/migrate-memory-v2) on PATH via ~/.bashrc:46 — archive + drop PATH line (chezmoi, after Wave 5.1)?
2. Honcho leftovers: 5 docker volumes honcho_{pgdata,redis-data,prometheus-data,grafana-honcho-data,venv} → `docker volume rm` when sure; chezmoi template dot_claude/modify_settings.json lines 117/159/180/213/221 still reference honcho → remove after Wave 5.1 or chezmoi apply re-adds the plugin; archive/2026-09/infra/honcho 6.6G incl. backups/ → delete later.
3. Cloudflare dashboard: delete DNS CNAMEs + Zero Trust Access apps for multica1.ucvc.email and paperclip1.ucvc.email; keep tunnel 0efd55e7 (chatwoot+uptime1). Cosmetic: rename unit cloudflared-paperclip1.service → cloudflared.service.
4. OP service-account token leak — still UNRESOLVED; only VR can rotate (1Password admin → new token → ~/.env).
5. Obsidian: claw (git 366↑/372↓ dirty), claw-lp-cb1 2.3G, vrLYT 882M, Basic_template_2026-Q3 — later.
6. ~/backup 1.7M unnamed — later.
7. skills/qb-cli + ccy* launchers; ccl* broken launchers → chezmoi after Wave 5.1 — later.
8. Sessions: 6 transcripts in ~/inbox/sessions-for-omnigent/ — omnigent needs an importer (none exists); resume omnigent WSL2 + bugalteris Cablenet threads.
9. lp-ryckov11 ssh alias → chezmoi ssh template after Wave 5.1. ix-claude1: claude not on non-login PATH.
10. uptime-kuma repo detached HEAD; remove its monitors for paperclip/multica/honcho.
11. Remote runs: handovers/PROMPT-declutter-{ix-claude1,lp-ryckov11}-2026-09-11.md.
12. Chezmoi Wave 5.1 + ix-adopt still in flight (unchanged today).

---
## 1. Target structure

**Decision: minimal-move.** I am NOT creating `~/work/<domain>/`. Reason: moving a LIVE repo
orphans its `~/.claude/projects/-home-vr-<path>` dir (path-encoded → session + memory continuity
lost), and breaks launchers, compose files, timers and chezmoi-managed paths. The value of tidier
paths is cosmetic; the breakage is real. So: **LIVE stays exactly where it is; the only new tree is
the archive.** Grouping happens inside `~/archive/2026-09/<domain>/` where nothing depends on paths.

```
~/agents/*              7 agent repos (unchanged — launchers depend on paths)
~/skills                50 SKILL.md (unchanged; add _archived/ only if needed)
~/claw-services/*       LIVE set, explicitly: honcho multica chatwoot grafana uptime-kuma
                        (+ gemini-auth-manager until Phase C archives it). Everything else under
                        claw-services moves to ~/archive/2026-09/openclaw/ or is deleted per §2.
~/Obsidian/*            vaults (unchanged)
~/<repo>                active + warm project repos stay top-level: omnigent vr-orchestra
                        bazaraki bazaraki-scraper fb-x second-hand marketplace-monitor
                        zipline-cyprus onepass tools
~/archive/2026-09/      NEW — the only structural change
  ├─ openclaw/          mission-control command-center tenacitos lobsterboard kanban
  │                     emergency-bot tasks zoe
  ├─ paperclip/         paperclip claw-services-paperclip gstack
  ├─ infra/             gemini-auth-manager teamviewer oc-global
  └─ HARVEST.md per archived item (in the moved dir root)
~/backups ~/claw-backups   untouched this pass (§5 owner eyeball)
```

**HARVEST.md template** (≤5 lines, written *before* the `mv`):
```
What it was:   <one line>
What worked:   <one line>
What to steal: <file paths / patterns worth reusing>
Why stopped:   <one line>
Successor:     <repo or "none">
```

---

## 2. Triage sheet

Tags: KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES

### 2.1 Agent fleet & skills
| item | tag | note |
|---|---|---|
| ~/agents/agent-orchestrator | KEEP-LIVE | 3d; dirty = 2 untracked (`.claude/` and this plan file — the plan file is expected). Commit in Phase B |
| ~/agents/agent-sysadmin | KEEP-LIVE | clean; 143 backlog lines need triage (§3) |
| ~/vr-orchestra | KEEP-LIVE | marketplace source for all plugins |
| ~/agents/agent-bugalteris | KEEP-LIVE | 22d, clean; 112 backlog lines need triage (§3) |
| ~/agents/agent-multica | FINISH | 1 dirty file; commit, then KEEP-LIVE (~/multica symlink) |
| ~/agents/agent-comms-1 | FINISH | 23 dirty + 1 unpushed — biggest loose-work risk; commit or discard before anything else |
| ~/agents/agent-librarian | FINISH | 3 dirty + 1 unpushed; commit+push, stays live (plugin v0.2.0) |
| ~/skills | KEEP-LIVE | 50 skills, none >120d stale |
| ~/skills/qb-cli (untracked) | FINISH | never committed — commit or delete; owner call in §5 |
| launchers cco/cco+/cco- ccа* ccb* | KEEP-LIVE | map to existing repos |
| launchers ccl/ccl+/ccl- | FIX | point at nonexistent ~/agents/agent-lawyer — remove from chezmoi template AND live file |
| launcher ccy/ccy+ | OWNER-DECIDES | bare profile with no agent — keep as scratch profile or drop? |
| plugin honcho@honcho (disabled) | FIX | either enable or uninstall; disabled-but-installed is drift (memory says "active") |
| plugins: librarian, agent-meta, orchestrator, sysadmin, karpathy, adhd, secret-mgmt, vr-agent-creator | KEEP-LIVE | all enabled and used |

### 2.2 Marketplace scrapers
| item | tag | note |
|---|---|---|
| ~/bazaraki | FINISH | 37d, 3 dirty — commit, KEEP-LIVE |
| ~/bazaraki-scraper | KEEP-LIVE | linked worktree of same remote; do NOT rm -rf (use `git worktree remove`) |
| ~/fb-x | FINISH | 4 unpushed commits — push, KEEP-LIVE |
| ~/marketplace-monitor | FINISH | 1 unpushed + 5 dirty — commit+push, KEEP-LIVE |
| ~/second-hand | FINISH | 1 dirty — commit, KEEP-LIVE |
| ~/claw-services/deal-watcher | KEEP-LIVE | 4 containers up + 3 timers |
| NOTE | — | the running `aimm` and `deal-watcher` containers are built from `~/marketplace-monitor` and `~/second-hand` (compose/source lives there, not in claw-services subdirs) — those two are live service repos: never archive |

### 2.3 Fleet infra
| item | tag | note |
|---|---|---|
| ~/.local/share/chezmoi | KEEP-LIVE | Wave 5.1 + ix-adopt in flight — DO NOT TOUCH |
| ~/.local/share/chezmoi.oc-global-retired-2026-09-04 | RUBBISH-DELETE | retired clone, superseded |
| ~/oc-global | RUBBISH-DELETE | retired per handover, canonical = dotfiles; verify no unpushed first |
| ~/tools | HARVEST→ARCHIVE | 172d fleet scripts, 1 dirty — commit, harvest scripts, archive/infra/ |
| ~/zipline-cyprus | KEEP-LIVE | 50d warm, 5 dirty → FINISH commit first |
| ~/onepass | KEEP-LIVE | active session dir; secret tooling |
| ~/claw-services/gemini-auth-manager | HARVEST→ARCHIVE | 186d, 1 dirty; commit then archive/2026-09/infra/ |
| ~/teamviewer | RUBBISH-DELETE | AUR package clone, re-clonable, 221d |

Status 2026-09-10: see §0.

### 2.4 OpenClaw legacy (decommissioned 2026-06-22)
| item | tag | note |
|---|---|---|
| ~/claw-services/mission-control | HARVEST→ARCHIVE | 193d fork, behind 184 |
| ~/claw-services/command-center | HARVEST→ARCHIVE | 198d, dirty — commit or discard (propose discard: dead) |
| ~/claw-services/kanban | HARVEST→ARCHIVE | 217d, 3 dirty → discard dirty |
| ~/claw-services/tenacitos | HARVEST→ARCHIVE | 201d, ~30 dirty → OWNER-DECIDES: commit the 30 or discard? |
| ~/claw-services/lobsterboard | HARVEST→ARCHIVE | 207d, behind 99 — BUT `lobster-healthcheck.timer` exists → §2.7 FIX first |
| ~/Obsidian/claw | OWNER-DECIDES | git vault ahead 366/behind 372 + dirty — reconcile or freeze as-is? Do not move until answered |
| ~/claw-backups 6.6G | OWNER-DECIDES | later eyeball, not this pass |
| ~/claw-logs 708K | HARVEST→ARCHIVE | move to archive/openclaw/ |
| ~/.openclaw-backups.old 420K | RUBBISH-DELETE | `.old` backup dir |
| ~/claw-services/mission-control-convex-backup 774M | RUBBISH-DELETE | Feb backup of the archived OpenClaw dashboard; **contains `.env` + `.env.local` — grep for live creds and rotate before rm** (ties to the UNRESOLVED secret-leak item) |
| ~/claw-services/emergency-bot 36M | HARVEST→ARCHIVE | Feb Telegram/PM2 bot (bot.js + README + GEMINI.md); 36M is node_modules — `rm -rf node_modules` then archive/openclaw/ |
| ~/claw-services/tasks 24K | HARVEST→ARCHIVE | OpenClaw file-based task board (active/backlog/archive/attachments); tiny — archive/openclaw/ after checking `active/` and `backlog/` are empty |
| ~/claw-services/zoe 40K | HARVEST→ARCHIVE | Mar scaffold, never built (PROJECT-PLAN.md + README + prisma + empty worktrees) — harvest PROJECT-PLAN.md, archive/openclaw/ |
| ~/claw-services/browseros 225M | RUBBISH-DELETE | single `BrowserOS.AppImage` (Feb), re-downloadable, no config beside it |

Status 2026-09-10: see §0.

### 2.5 Paperclip / ACES / Trading Desk
| item | tag | note |
|---|---|---|
| docker `paperclip` (crash-loop 5d) | FIX | diagnose-only this pass (§4E); config ~/.paperclip |
| ~/.paperclip, ~/.paperclip-worktrees | KEEP-LIVE | live container config — never move |
| ~/paperclip (repo, 151d) | HARVEST→ARCHIVE | branch fix/3586, NO upstream, 2 dirty + 8 untracked. Push branch to a fork OR harvest the diff into HARVEST.md, then archive/paperclip/ |
| ~/claw-services/paperclip | RUBBISH-DELETE | stale deployed snapshot, same origin, behind 2299, no process references it — confirm no compose mount first |
| ~/gstack | HARVEST→ARCHIVE | 157d, clean → archive/paperclip/ |
| ~/Obsidian/ACES, fund-manager, claude-td | KEEP-LIVE | vaults |
| ~/Obsidian/Basic_template_2026-Q3 123M | OWNER-DECIDES | template vault — still seeding new vaults? |

Status 2026-09-10: see §0.

### 2.6 Infinox corporate
| item | tag | note |
|---|---|---|
| ~/Obsidian/IX-Global 124M, ~/Obsidian/claude-ix | KEEP-LIVE | live corporate |
| ~/cloudflare | KEEP-LIVE | live docs |

### 2.7 Services (running — never move)
| item | tag | note |
|---|---|---|
| ~/claw-services/honcho (6.6G, 156d, ahead 5, dirty) | KEEP-LIVE + FIX | 6 containers up (api, deriver, database, redis, prometheus, grafana-honcho). Push the 5 ahead commits or note them; backups/ subdir → §5 eyeball |
| ~/claw-services/multica (80d, detached HEAD, 3 dirty, 2 remotes) | KEEP-LIVE + FIX | backend CRASH-LOOPING; detached HEAD → pin to a branch; drop the redundant remote |
| ~/claw-services/chatwoot, aimm, grafana | KEEP-LIVE | up + healthy |
| ~/claw-services/uptime-kuma (102d, detached HEAD, 1 dirty) | KEEP-LIVE + FIX | systemd user unit; pin branch |
| timer `lobster-healthcheck` | FIX | points at archived lobsterboard → disable timer BEFORE archiving that dir |
| ~/omnigent | KEEP-LIVE | 1d, 3 dirty → FINISH commit; `omnigent-reaper.timer` + `omni-host` unit live |

Status 2026-09-10: see §0.

### 2.8 Backups / trash / misc
| item | size | tag |
|---|---|---|
| ~/backups | 15G | OWNER-DECIDES (later eyeball, keep) |
| ~/claw-backups | 6.6G | OWNER-DECIDES (later eyeball, keep) |
| ~/backups.old | 559M | RUBBISH-DELETE (`.old`) |
| ~/.openclaw-backups.old | 420K | RUBBISH-DELETE (`.old`) |
| ~/.config-backups (ruflo-wire) | 520K | RUBBISH-DELETE (ruflo fully scrapped) |
| ~/.trash (multica-predraft) | 40K | RUBBISH-DELETE |
| ~/.chezmoi-backup-20260902 / 0905-wave3/4/5 | ~250K | KEEP-LIVE until Wave 5.1 lands, then delete |
| ~/.claude-journal-backup-2026-09-09 | 20K | KEEP-LIVE (1 day old) |
| ~/backup (2026-09-04) | 1.7M | OWNER-DECIDES — what is it? unnamed, 6 days old |
| ~/Obsidian/claw-lp-cb1 | 2.3G | OWNER-DECIDES — unexplained, largest vault |
| ~/Obsidian/vrLYT | 882M | OWNER-DECIDES — active or archive? |

Status 2026-09-10: see §0.

### 2.9 ~/.claude (521M)
| item | tag | note |
|---|---|---|
| projects/ 13 ACTIVE dirs | KEEP-LIVE | -home-vr, agent-*, vr-orchestra, bazaraki, dotfiles, fb-x, local-share-chezmoi, omnigent, onepass, zipline-cyprus |
| projects/agent-multica (25d) | KEEP-LIVE | warm |
| 5 ORPHAN dirs (ACESx-boiler, ComplianceCore, 3e1347f5 project, 2 workspaces) | RUBBISH-DELETE | decoded paths gone — harvest ComplianceCore memory first (§3) |
| ComplianceCore memory: 87 `session_*-hb*.md` | RUBBISH-DELETE | heartbeat spam |
| ComplianceCore memory: 3 real files | HARVEST→ARCHIVE | into archive/paperclip/HARVEST.md |
| memory-only dirs: claw-services-honcho, claw-services-paperclip, Obsidian-* ×4, paperclip, 3 paperclip-instances | HARVEST→ARCHIVE | harvest listed files (§3) then delete the dirs |
| projects/-home-vr memory (26 curated) | KEEP-LIVE + FIX | 2 stale claims to correct (§4E) |
| session-env/ + tasks/ ~430 empty leaves | RUBBISH-DELETE | empty dirs only |
| plugins/ 149M cache | KEEP-LIVE | do NOT rm — regenerating costs more than it saves |
| ~/.claude/skills, ~/.claude/commands (empty) | RUBBISH-DELETE | empty; plugins supply both |
| ~/.claude/agents/_retired/ (empty) | RUBBISH-DELETE | empty |
| cleanupPeriodDays unset | FIX | set explicitly (§4D) |

---

## 3. Harvest list

Knowledge to pull **before** any delete/move. Target: `-home-vr` MEMORY index, or the domain HARVEST.md.

| source | destination |
|---|---|
| ComplianceCore memory: project_compliancecore.md, feedback_api_patterns.md, MEMORY.md | archive/paperclip/HARVEST.md + 1 memory entry |
| Obsidian-paperclip memory: acex-systema-architecture, paperclip-harness-plan, kb-guide-decision, feedback chezmoi-deployment | archive/paperclip/HARVEST.md; chezmoi feedback → `-home-vr` memory |
| Obsidian-claw memory: project_openclaw_gateway_revival.md | archive/openclaw/HARVEST.md |
| Obsidian-paperclip-aces-admin: project_vault_state.md | archive/paperclip/HARVEST.md |
| -home-vr-paperclip: project_companies.md, feedback_docs_before_code.md | archive/paperclip/HARVEST.md; docs-before-code → `-home-vr` memory (durable habit) |
| agent-orchestrator handovers ×2, agent-bugalteris handovers ×3 | stay in repo; index one line each in that repo's MEMORY |
| ~/paperclip fix/3586 diff (2 dirty + 8 untracked) | `git diff > archive/paperclip/paperclip-fix3586.patch` before archiving |
| ~/tools fleet scripts | list reusable scripts in archive/infra/HARVEST.md |

**Backlog triage (separate, parallel):** two workers, one each.
- Worker A: `~/agents/agent-sysadmin` BACKLOG 143 open lines → collapse to ≤15 lines (dedupe, group by theme, drop anything done/obsolete, keep only actionable items with a verb). Writes back in place, commits.
- Worker B: same brief for `~/agents/agent-bugalteris` 112 lines → ≤15.
- Both: read-only elsewhere, no code changes, output = the rewritten BACKLOG + a 5-line summary.
- Also small: agent-comms-1 (26), agent-multica (12), orchestrator (7), librarian (4), vr-orchestra (1) — leave as-is.

---

## 4. Execution phases

Global rule: every mutating step is preceded by a preview step. Scripts take `--dry-run` (default ON)
and only mutate with `--apply`. Log every action to `~/archive/2026-09/declutter-log-<phase>.txt`.

### Phase A — rubbish deletes
```bash
# PREVIEW
du -sh ~/backups.old ~/.openclaw-backups.old ~/.config-backups ~/.trash \
       ~/teamviewer ~/oc-global ~/.local/share/chezmoi.oc-global-retired-2026-09-04 \
       ~/claw-services/paperclip ~/claw-services/browseros \
       ~/claw-services/mission-control-convex-backup
# GUARDS (must all pass)
git -C ~/oc-global status -sb; git -C ~/oc-global log --branches --not --remotes   # must be empty
grep -rl "claw-services/paperclip" ~/claw-services/*/docker-compose*.y*ml || echo "no mount refs"
# APPLY
rm -rf ~/backups.old ~/.openclaw-backups.old ~/.config-backups ~/.trash
rm -rf ~/teamviewer ~/oc-global ~/.local/share/chezmoi.oc-global-retired-2026-09-04
rm -rf ~/claw-services/paperclip ~/claw-services/browseros
# secrets guard BEFORE the convex backup goes:
grep -rIE '=[A-Za-z0-9_-]{16,}' ~/claw-services/mission-control-convex-backup/.env* || true
rm -rf ~/claw-services/mission-control-convex-backup       # +774M
```
Reclaimed: ~560M (backups.old) + 774M (mission-control-convex-backup) + 225M (browseros) + ~1M (small dirs) + teamviewer/oc-global/retired-clone/claw-services-paperclip
(sizes unmeasured — the preview `du` prints them; expect ~1–2G total).
Agents/tokens: 1 worker, ~15k. Rollback: **none for rm** — that is why the guards are mandatory and
why only re-clonable / superseded / `.old` items are in this phase.

### Phase B — commit/push FINISH items
```bash
for r in ~/agents/agent-comms-1 ~/agents/agent-librarian ~/agents/agent-multica \
         ~/agents/agent-orchestrator ~/omnigent ~/bazaraki ~/second-hand \
         ~/marketplace-monitor ~/zipline-cyprus ~/fb-x ~/tools \
         ~/claw-services/gemini-auth-manager; do
  echo "=== $r"; git -C "$r" status -sb; git -C "$r" diff --stat; done   # PREVIEW
# then per repo, reviewed individually:
git -C "$r" add -A && git -C "$r" commit -m "chore: land in-flight work before 2026-09 declutter" && git -C "$r" push
```
Order: agent-comms-1 first (23 dirty + 1 unpushed = largest loss risk). Dead-repo dirt
(command-center, kanban, tenacitos) is **discarded**, not committed — except tenacitos' ~30 files,
which is an owner question (§5). Agents/tokens: 1 worker, ~40k (needs to read diffs).
Rollback: everything is a commit; `git reset --hard <sha>` / unpush via force is available.

### Phase C — harvest + archive moves
```bash
mkdir -p ~/archive/2026-09/{openclaw,paperclip,infra}
# 1. HARVEST.md written FIRST for each item (see §1 template, §3 sources)
# 2. PREVIEW every move
for d in ~/claw-services/{mission-control,command-center,kanban,tenacitos,lobsterboard,emergency-bot,tasks,zoe} \
         ~/paperclip ~/gstack ~/tools ~/claw-services/gemini-auth-manager ~/claw-logs; do
  echo "MOVE $d"; ls -d "$d"; done
# 3. GUARD: nothing running maps here
docker ps --format '{{.Names}} {{.Mounts}}' | grep -Ei 'mission-control|kanban|tenacitos|lobster|gstack|/home/vr/paperclip' || echo OK
systemctl --user list-units --all | grep -i lobster    # disable BEFORE moving lobsterboard
# 4. APPLY (mv only, never cp+rm)
systemctl --user disable --now lobster-healthcheck.timer
mv ~/claw-services/mission-control ~/archive/2026-09/openclaw/   # ...etc per table
```
Agents/tokens: 1 worker + 2 backlog workers in parallel, ~60k.
Rollback: `mv` back — path is recorded in the phase log line-for-line.

### Phase D — ~/.claude hygiene
```bash
# PREVIEW
jq '.cleanupPeriodDays' ~/.claude/settings.json
ls -d ~/.claude/projects/-home-vr-Obsidian-paperclip-ACESx-boiler \
      ~/.claude/projects/*ComplianceCore* ~/.claude/projects/*paperclip-instances*
ls ~/.claude/projects/*ComplianceCore*/memory/session_*-hb*.md | wc -l    # expect 87
find ~/.claude/session-env ~/.claude/tasks -type d -empty | wc -l         # expect ~430
# APPLY (harvest §3 files FIRST)
# cleanupPeriodDays: set to 60
rm -f ~/.claude/projects/*ComplianceCore*/memory/session_*-hb*.md
rm -rf <the 5 orphan project dirs> <the memory-only dirs, post-harvest>
find ~/.claude/session-env ~/.claude/tasks -type d -empty -delete
rmdir ~/.claude/skills ~/.claude/commands ~/.claude/agents/_retired
# plugins/ 149M cache: LEFT ALONE
```
**cleanupPeriodDays = 60.** Why: the default 30 is shorter than the observed working rhythm
(agent-multica went 25d idle and is still warm; several repos are touched on a ~40d cycle), so 30
silently eats transcripts of repos you are about to come back to. 60 covers the warm band, still
bounds growth, and `memory/` is exempt from the sweep either way so curated knowledge is never at risk.
Setting it *explicitly* also stops a future default change from surprising you.
Agents/tokens: 1 worker, ~25k. Rollback: transcript deletes are irreversible → the harvest step
(§3) must be verified complete before this phase runs; the settings key is trivially revertible.

### Phase E — fixes (diagnose-only where noted)
```bash
# 1. paperclip crash-loop — DIAGNOSE ONLY, first command:
docker logs --tail 100 paperclip 2>&1 | tail -60
# 2. multica-backend crash-loop — DIAGNOSE ONLY, first command:
docker logs --tail 100 multica-backend 2>&1 | tail -60
# 3. broken ccl/ccl+/ccl- launchers
grep -rn "agent-lawyer" ~/.local/share/chezmoi/ ~/.bashrc ~/.zshrc 2>/dev/null   # PREVIEW
#    edit the chezmoi source template, then `chezmoi apply` — do NOT just edit the live file
# 4. detached HEADs
git -C ~/claw-services/multica status -sb; git -C ~/claw-services/uptime-kuma status -sb
git -C ~/claw-services/multica checkout <intended-branch>    # after confirming the sha
# 5. multica duplicate remote: git -C ~/claw-services/multica remote -v  → drop the unused one
# 6. honcho plugin drift: claude plugin list | grep honcho  → enable or uninstall
# 7. stale memory claims in ~/.claude/projects/-home-vr/memory/
#    project_skills_cleanup.md: "195 skills" → 50 skills (verified 2026-09-10)
#    project_honcho.md: add "honcho@honcho plugin DISABLED in settings as of 2026-09-10"
```
Crash-loops are **not** fixed in this pass — capture logs, file two items, stop. Do not restart or
recreate containers during a declutter; a decluttering session is the worst context to debug a service in.
Agents/tokens: 1 worker, ~30k. Rollback: chezmoi edit is a commit; git checkout is reversible;
memory edits are text.

### Phase F — hand to VR (sudo)
**Nothing in this plan requires root.** Deletes, moves, `systemctl --user`, docker and chezmoi all
run as `vr`. If Phase C's guard finds a *system* (not user) unit pointing at a dir being archived,
that single unit disable becomes the one hand-off line:
```
sudo bash -c 'systemctl disable --now <unit> && systemctl daemon-reload'
```
Otherwise this phase is empty. Do not invent sudo work.

**Phase order is fixed:** harvest (§3) → A → B → C → D → E. D must not run before §3 harvest is verified.

---

## 5. Owner decisions needed

- `~/backups` 15G + `~/claw-backups` 6.6G + `~/claw-services/honcho/backups`: keep, prune, or move off-box? (deferred, but growing)
- `~/Obsidian/claw-lp-cb1` 2.3G — what is it, and is it live?
- `~/Obsidian/vrLYT` 882M and `Basic_template_2026-Q3` 123M — live, or archive?
- `~/Obsidian/claw` — git vault ahead 366 / behind 372 + dirty: reconcile with remote, or freeze as a read-only archive?
- `~/claw-services/tenacitos` ~30 dirty files — commit them before archiving, or discard?
- `~/paperclip` branch `fix/3586` has no upstream — push to a fork, or keep only the patch file?
- `~/backup` (1.7M, 2026-09-04) — what is it? Nothing identifies it.
- `~/skills/qb-cli` SKILL.md never committed, and `ccy/ccy+` launchers (bare profile, no agent) — commit/keep, or delete both?
- agent-multica session `fbe01be7` has been waiting on your `/start` for 48d — resume it, or abandon the thread?
- fb-x relay + bazaraki agents: are those two ops incidents still live, or already fixed? (decides RESUME vs CLOSE)
- honcho plugin installed-but-disabled — enable, or uninstall and rely on the MCP server directly?

---

## 6. Rules going forward

1. **Staleness rule: 90 days.** A repo with no commit in 90d gets a HARVEST.md and moves to `~/archive/YYYY-MM/<domain>/`. Two states only: LIVE or archived. No "maybe".
2. New projects start at `~/<name>` (top level) or `~/agents/agent-<name>` for agents. Nothing new under `~/claw-services` unless it is an actually-running service dir.
3. Never archive a dir a docker container or systemd unit maps to — disable the unit first, or leave it live.
4. Never sync `~/.claude/projects` (sessions + memory are machine-local by design). Cross-machine state travels only via chezmoi dotfiles.
5. Deletion is limited to: orphan project-state dirs, heartbeat spam, `*.old` dirs, retired clones, exact duplicates of a canonical repo. Everything else is `mv`.
6. Big backup trees get a scheduled eyeball, never a bulk delete.
7. **Quarterly repeat (next: 2026-12).** Same three read-only scout briefs — (a) `~/.claude` state + memory census, (b) repo census with days-since-commit / dirty / unpushed, (c) running services (docker + systemd) — then this same plan shape. Run on `lp-ryckov11` (Windows: swap `systemctl --user` for scheduled tasks/services, `du` for `Get-ChildItem`) and `ix-claude1` (Linux: identical).
8. Every quarter, re-check the memory index for stale claims (this pass found 2 of 26 wrong) — treat MEMORY.md as code that rots.

---

## 7. Sessions: resume / abandon

Scope note: no `summary` records exist in any transcript, so nothing here is recoverable from a
summary index — a thread is either resumed from its jsonl or closed with a handover. `~/.claude/todos`
and `~/.claude/plans` are absent from disk — nothing to do, and Phase D must not reference them. `journal/` (188 files, still writing today) is a LIVE
learning-capture pipeline — **keep, never prune**. `sessions/` (65 .json/.key pairs) is process
state, not transcripts — **leave alone**. `teams/` (108 session-id subdirs) mirrors sessions —
prune each subdir together with its session, never independently.

### (a) Resumable threads
| project | sid8 | turns | what it was doing | verdict |
|---|---|---|---|---|
| omnigent | 9a08e66e | 98 | WSL2 runner plan §4 step 2b in progress | **RESUME** — genuine mid-task, most-active repo (1d) |
| omnigent | e8a8d0c4 | 20 | reading a handover | **ABANDON** — its content lives in the handover it was reading |
| agent-sysadmin | ccb90efa | 89 | "elegant answer already ranked #1" — mid-analysis | **RESUME-AFTER-backlog-triage** — §3 Worker A rewrites that repo's BACKLOG; resume after, or it re-litigates |
| agent-bugalteris | eef759e4 | 58 | filing Cablenet PDFs, then a dry-run | **RESUME** — concrete unfinished ops task with a defined next step |
| agent-multica | fbe01be7 | 65 | waiting on user `/start` | **OWNER-DECIDES** — blocked 48d on you, not on the agent (§5) |
| fb-x | 6e6715ba | 80 | relay down after reboot | **CLOSE-WITH-HANDOVER** — an ops incident, not a thread; check if relay is up, then close |
| bazaraki | 14888df1 | 51 | re-verifying after a restart wiped agents | **CLOSE-WITH-HANDOVER** — same: incident, verify current state fresh rather than replay 51 turns |
| root | c2b2c2bd | 11 | cc* launcher adoption | **CLOSE** — already ended in a full HANDOVER (09-04); point §2.1 launcher FIX at that doc |
| root | 68ddaf9b | 6 | cc* launcher adoption, earlier | **ABANDON** — superseded by c2b2c2bd and its handover |
| agent-orchestrator | c1e432f9 | 4 | resume chezmoi drift; doc-note worker mid-push | **RESUME-AFTER-chezmoi-Wave-5.1** — touches `~/.local/share/chezmoi`, which is frozen this pass |
| root | 0769a176 | — | this declutter session | **RESUME** — closes with this plan's execution session |
| root | 1321938f + d627e8f1 | — | secret-leak discussion (duplicate prompts) | **CLOSE** — the live item is the UNRESOLVED secret-leak remediation (token still unrotated); track it there, not in a transcript |

Rule for the RESUME rows: resume once, land a handover, then let the transcript age out. Do not keep
a thread alive as a filing cabinet.

### (b) Throwaways
~20 one-shot fan-outs (09-07 investigation, 09-09 gate/hooks verify, chezmoi/sysadmin/bugalteris
probes, several 401-OAuth dead ends) plus the ~45-session Jul19–Aug21 batch (bugalteris finance/ops
loop, sysadmin learning-capture, duplicate secret-leak prompts): **no action** — they age out on
their own under `cleanupPeriodDays = 60` (§4D). Their `teams/` subdirs go with them.

### (c) Session hygiene rule (going forward)
1. Subagent fan-out transcripts are noise by construction — never harvest them, never resume them; the parent's handover is the record.
2. The unit of memory is a HANDOVER or a HARVEST.md, not a transcript. If a thread matters, it must end in a written artifact before it goes idle.
3. 10-second resumable test: **turns ≥8** AND **the last assistant line names a next step or an open question**. Fails either → dead; close it or let it age out.
