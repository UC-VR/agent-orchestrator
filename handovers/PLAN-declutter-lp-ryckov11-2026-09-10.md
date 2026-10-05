# PLAN — Declutter `lp-ryckov11` (Windows 11, user `lp-ryckov11\vr`) — 2026-09-10

## 0. STATUS — **PLANNED, not executed**

Nothing in this plan has been run. No mutation has touched `lp-ryckov11`; the three inputs are
**read-only scouts taken 2026-09-10** (token cost: a ~73K, b ~109K, c ~90K). Execution is a later
session, dry-run first, and only for what VR approves in §5.

**Appendix A lives in a second file:** `PLAN-declutter-lp-ryckov11-2026-09-10-appendix.md`
(raw 133-entry home listing, the `~/.claude` census, and the dependency + served-hostname map).

**Access recipe.** Reachable at `100.102.239.39`; PowerShell 7.6.5. Single commands:
```bash
ssh vr@100.102.239.39 'pwsh -NoProfile -Command "<one-liner>"'
```
**Multi-line scripts MUST use EncodedCommand** — stdin `-Command -` silently no-ops multi-line blocks:
```bash
B64=$(printf '%s' "$SCRIPT" | iconv -f UTF-8 -t UTF-16LE | base64 -w0)
ssh vr@100.102.239.39 "pwsh -NoProfile -EncodedCommand $B64"
```
The login shell is pwsh **with** profile (profile lives under OneDrive:
`C:\Users\vr\OneDrive - Global Infinox\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`) and
throws non-fatal PSReadLine/fnm noise on every connection — always pass `-NoProfile`, ignore that stderr.

**Frozen this pass:** anything under `C:\Users\vr\.local\share\chezmoi` — Wave 5.1 is IN-FLIGHT
(design only, no commits). Honcho lines were already removed from chezmoi source (dotfiles `5cc210d`),
so `chezmoi apply` will **not** re-add honcho here. vr-oc1 PENDING #9 ("lp ssh alias") is a
chezmoi/Wave-5.1 item — **out of scope**.

**Corrections to the governing prompt's guesses:** `cleanupPeriodDays` is **absent** from
settings.json (not 26) → FIX = *add* it as 90. Docker Desktop **is** running (it was not started by
us). `.claude-archive` exists; `inbox\` and `archive\` do **not** exist yet. There are **no**
`session_*` heartbeat files on this host, and **no MEMORY.md drift** — the home project dir's
`memory\` is empty (see §7).

---

## 1. Target structure

**Minimal-move**, same as vr-oc1: LIVE stays exactly where it is (moving a repo orphans its
path-encoded `~/.claude/projects\C--Users-vr-...` dir and breaks compose bind mounts and launchers).
The only new structure is the archive tree plus the inbox.

```
C:\Users\vr\archive\2026-09\        NEW — terminal. Nothing here is ever looked at again.
  ├─ infra\honcho\                  .honcho dotdir + settings backup evidence
  ├─ infra\multica\                 .multica dotdir
  ├─ ai-tools\                      dead AI-tool dotdirs VR retires in §5
  ├─ scratch\                       loose root files (*.ts, scratch_*.json, top50_*, probes, scripts)
  ├─ backups\                       .claude.json.* backups/tmp, settings.json.bak, task XMLs
  ├─ agents\                        merged content of .claude-archive\agents-retired-20260821
  ├─ repos-dupes\                   any duplicate clone VR retires (only after push, §3)
  └─ declutter-log-<phase>.txt      A..F, one file per phase, line-for-line
C:\Users\vr\inbox\                  NEW — ACTION location.
  ├─ README.md                      carries the rule: THIS DIR MUST BE EMPTY BY THE 2026-12 PASS
  ├─ sessions-for-omnigent\         resumable transcripts + MANIFEST.md
  └─ PENDING-lp-ryckov11.md         owner-deferred items after execution
```

**Hard placement rule:** `archive\` and `inbox\` sit at `C:\Users\vr\` and **NEVER** under
`OneDrive`, `OneDrive - Global Infinox`, or `Documents` (Documents/Desktop/Pictures are redirected
into corporate OneDrive — archiving there would sync corporate storage full).

**`HARVEST.md` is written INSIDE the dir being moved, BEFORE the move**, verbatim template:
```
What it was:   <one line>
What worked:   <one line>
What to steal: <file paths / patterns worth reusing>
Why stopped:   <one line>
Successor:     <repo or "none">
```

---

## 2. Triage sheet

Tags: **KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES.**
Every one of the 133 top-level entries in Appendix A.1 appears below exactly once.
Delete allowlist (D1 orphan `.claude/projects` state dirs · D2 heartbeat `session_*` spam · D3
`*.old`/`*-backup-*` >90d after owner OK · D4 retired clones · D5 exact duplicates of a canonical
repo · D6 re-downloadable binaries · D7 `node_modules`) — every RUBBISH-DELETE row cites its item.

### 2.1 OS / shell-folder / junction rows (never touched)
| item | tag | note |
|---|---|---|
| NTUSER.DAT, ntuser.dat.LOG1, ntuser.dat.LOG2, NTUSER.DAT{...}.TM.blf, NTUSER.DAT{...}.regtrans-ms (x2), ntuser.ini | KEEP-LIVE (OS) | live registry hive — never touch |
| Application Data, Cookies, Local Settings, My Documents, NetHood, PrintHood, Recent, SendTo, Start Menu, Templates | KEEP-LIVE (OS) | legacy junctions |
| Contacts, Favorites, Links, Music, Saved Games, Searches, Videos | KEEP-LIVE (OS) | shell folders |
| Documents | KEEP-LIVE (OS) | 0MB, redirected into OneDrive — never a target |
| AppData | KEEP-LIVE (OS) | 113GB, out of scope; `Local\Temp` git scraps (buzz-pr5410-work, gitglobtest, gitglobtest2, uc-vr-skills, upstream-humanizer) left as OS temp |
| OneDrive | KEEP-LIVE | 0MB stub |
| OneDrive - Global Infinox | KEEP-LIVE | 326MB, corporate sync root + the pwsh profile |
| Obsidian (junction -> V:\Obsidian) | KEEP-LIVE | 4.1GB, 15 vaults, off C: — see §5.13 |
| Sync (junction -> V:\Sync) | KEEP-LIVE | 11.4GB, off C:; `syncthing start` task points here |
| scoop | KEEP-LIVE | 11.5GB package manager; `scoop\persist\fnm` supplies claude.exe (dep map) |
| .ssh, .gitconfig, .gitignore, .bashrc, .bash_profile, .config | KEEP-LIVE | shell/git config |
| .bash_history, .lesshst, .node_repl_history, .vivaldi_reporting_data | KEEP-LIVE | shell/app history, bytes |

### 2.2 Live dependencies (dep map — never move; Phase C guard)
| item | tag | note |
|---|---|---|
| claude-code-proxy | **KEEP-LIVE** | UC-VR, clean. Docker bind mount -> /app; serves `claude-proxy2-lp-ryckov.llm.infinox.io` (CORPORATE-PROD). **Not touched.** |
| .bun | KEEP-LIVE | 188MB; **22 running bun.exe** out of `.bun\bin`. Listed in §5.1 for a keep/retire answer only — no move while running |
| .local | KEEP-LIVE | 311MB; `uv.exe`/`uvx.exe` running; contains `.local\share\chezmoi` — **DO NOT TOUCH** |
| .docker | KEEP-LIVE | 92.8MB; Docker Desktop is running |
| .cloudflared | KEEP-LIVE | 0MB, no config.yml (tunnel is token-mode, config is remote) |
| .google_workspace_mcp | KEEP-LIVE | 0.58MB, written 2026-09-10; backs the only live `mcpServers` entry |
| .claude | KEEP-LIVE + FIX | 763.6MB — hygiene in Phase D (§2.7) |
| .claude.json | KEEP-LIVE | live; `mcpServers` = google-workspace only, no honcho |

### 2.3 Retired-fleet dotdirs (Honcho / Multica / dead tooling)
| item | tag | note |
|---|---|---|
| .honcho | HARVEST→ARCHIVE | 7.04MB, **written 2026-09-10** — check for live procs in the Phase-D preview; HARVEST.md then -> `archive\2026-09\infra\honcho` |
| .multica | HARVEST→ARCHIVE | 14.29MB, newest 2026-05-17, multica retired fleet-wide -> `archive\2026-09\infra\multica` |
| .browseros | HARVEST→ARCHIVE | 0.04MB config only (no AppImage here, unlike vr-oc1), newest 2026-03-24 -> `archive\2026-09\ai-tools` |
| `.claude\plugins\marketplaces\honcho` (53.97MB) + `.claude\plugins\cache\honcho` (42.22MB) | **RUBBISH-DELETE** | allowlist **D4 retired clones** + **D6 re-downloadable** — removed by the §4D honcho checklist after the plugin uninstall |

### 2.4 AI-tool dotdirs — OWNER-DECIDES (facts in §5.1; none are in the dep map)
| item | MB | last-write | tag |
|---|---|---|---|
| .agents | 0.01 | 2026-06-10 | OWNER-DECIDES |
| .antigravity | 94.39 | 2026-02-11 (newest file 2026-07-06) | OWNER-DECIDES |
| .antigravity-ide | 100.81 | 2026-06-30 (newest 2026-09-07) | OWNER-DECIDES |
| .cagent | 0.0 | 2026-02-02 | OWNER-DECIDES |
| .codex | 551.46 | 2026-08-10 | OWNER-DECIDES (holds a remote-less git at `.tmp\plugins`) |
| .copilot | 0.0 | 2026-08-15 | OWNER-DECIDES |
| .gemini | 63.04 | 2026-08-15 (newest 2026-09-09) | OWNER-DECIDES (1.93MB `antigravity-backup` inside) |
| .graph-mcp | 0.0 | 2026-08-19 | OWNER-DECIDES |
| .herdr | 56.68 | 2026-07-15 (newest 2026-08-24) | OWNER-DECIDES |
| .mcp-auth | 0.0 | 2026-08-26 | OWNER-DECIDES (auth tokens — do not print) |
| .OpenCluely | 0.01 | 2026-07-29 | OWNER-DECIDES |
| .optmp | 0.0 | 2026-06-10 | OWNER-DECIDES |
| .swt | 0.87 | 2026-05-13 | OWNER-DECIDES |
| .vite-plus | 34.78 | 2026-08-27 | OWNER-DECIDES |
| .buzz | 1703.95 | 2026-08-12 (newest 2026-09-03) | OWNER-DECIDES + FINISH (see §2.5 — holds unpushed work) |
| .vscode | 2007.0 | 2026-07-14 (newest 2026-08-19) | OWNER-DECIDES — 46 extensions, likely live IDE |
| .vscode-shared | 0.04 | — | OWNER-DECIDES (rides with `.vscode`) |
| .cache | 1741.81 | 2026-09-03 | OWNER-DECIDES — generic; **inspect subdirs, never blanket-delete** |
| .aws | 0 | 2026-07-19 | OWNER-DECIDES (creds dir, 0MB) |
| .azure | 0 | 2026-07-19 | OWNER-DECIDES (creds dir, 0MB) |
| ag-browser | 0 | 2026-08-26 | OWNER-DECIDES (empty) |
| .browseros | 0.04 | — | see §2.3 |

### 2.5 Repos and project dirs
| item | tag | note |
|---|---|---|
| agents\ (agent-keth, agent-librarian, agent-netadmin, agent-sysadmin, vr-orchestra — clean) | KEEP-LIVE | 199MB total tree |
| agents\agent-bugalteris | **FINISH** | main, **60 dirty, 1 unpushed, 1 stash** — biggest loss risk on this host; commit+push in Phase B (§5.6) |
| agents\agent-lawyer | FINISH | 1 dirty — commit |
| agents\agent-orchestrator | FINISH | 1 dirty — commit |
| agents\skills | FINISH | **2 unpushed** — push |
| .buzz\verify_scratch\vr-orchestra | **FINISH** | **2 UNPUSHED** — push BEFORE any `.buzz` decision (§3) |
| .buzz\verify_scratch\agent-orchestrator | FINISH | 2 dirty — commit or discard (dup of `agents\agent-orchestrator`) |
| .buzz\REPOS\{agent-orchestrator, skills} | OWNER-DECIDES | clean duplicate clones of UC-VR canonicals (§5.4) |
| .buzz\REPOS\buzz, .buzz\.scratch\buzz-src | OWNER-DECIDES | block/buzz, no upstream, x2 |
| omnigagent | KEEP-LIVE | UC-VR/omnigent, clean, 2026-09-09 |
| second-hand | FINISH + OWNER-DECIDES | 0.73MB, **11 dirty**, 0 unpushed; a clone also exists on vr-oc1 — which is canonical? (§5.5) |
| Windows-Setuper | **FINISH** | 1.56MB, 3 dirty, **7 UNPUSHED** — push (§5.7) |
| orchestra-publish | OWNER-DECIDES | 0.11MB, git with **no remote**, 1 dirty, 2026-07-15 |
| onepass | OWNER-DECIDES | **empty dir, not a git repo** — delete or keep as a placeholder (§5.8) |
| buzz | OWNER-DECIDES | 0MB empty dir, 2026-08-04 |
| bin | OWNER-DECIDES | 0MB, 2026-08-15 |
| data | OWNER-DECIDES | 0MB, 2026-07-15 |
| project | OWNER-DECIDES | 0.1MB, holds `glu` (matches `.claude` project dir `project-glu`) |
| tmp | OWNER-DECIDES | 292.79MB; holds `openclaw-purge\openclaw-personal-inspect` (UC-VR, clean) |
| scratch_op | OWNER-DECIDES | 0.03MB, 2026-08-28 |
| node_modules | **RUBBISH-DELETE** | allowlist **D7 node_modules**; guard first: root `package.json` has **no name and no dependencies**, so nothing in `~` needs it — re-confirm with `Get-Content package.json` in the Phase-A preview |
| package.json, package-lock.json | OWNER-DECIDES | 2026-03-01, empty manifest; delete with `node_modules` or keep — owner call |
| npm_latest.json | HARVEST→ARCHIVE | loose scratch -> `archive\2026-09\scratch` |

### 2.6 Corporate (default KEEP-LIVE / OWNER-DECIDES — **never** RUBBISH-DELETE)
| item | tag | note |
|---|---|---|
| ai-dev.infinox.io | KEEP-LIVE + FINISH | 1304MB, UC-VR, 1 dirty; sub-repo `cloudflare-os` 1 dirty — owner reviews the diff before any commit (corporate: explicit paths, never `add -A`) |
| ai-mvp.infinox.io | KEEP-LIVE | 2.79MB, clean |
| cf-builder | KEEP-LIVE | 4.44MB, clean; `vendor\cloudflare-skills` detached HEAD (cosmetic, leave) |
| cloudflare | KEEP-LIVE | 25.89MB, no `.git`, written 2026-09-10 — live docs |
| fde | KEEP-LIVE | 0.18MB |
| fde-wrg4 | KEEP-LIVE | 0.18MB |
| fxbo-mcp1 | KEEP-LIVE | 187.35MB |
| fxbo-mcp-bridges | KEEP-LIVE | 0.67MB |
| x_fxbo-mcp_claude | KEEP-LIVE | 307.85MB, InfinoxMngmt/mcp-fxbo2, 1 dirty — owner reviews |
| projects (holds `fxbo-mcps`, InfinoxMngmt, clean) | KEEP-LIVE | 319.81MB |
| ix-ai-azure-rds | KEEP-LIVE | 0.07MB |
| ix-buzz | KEEP-LIVE | 0MB |
| prevail-test | KEEP-LIVE | 0.01MB |
| wix | OWNER-DECIDES | 1960.1MB, git with **no remote**, 1 dirty — corporate, biggest single owner-dependent reclaim (§5.10) |
| Excedo Support Services Ltd | **OWNER-DECIDES — NEVER MOVE** | reported 1,575,338MB, implausible; OneDrive Files-On-Demand placeholder inflation suspected. Re-measure only (§5.11) |

### 2.7 `~/.claude` internals (Phase D)
| item | tag | note |
|---|---|---|
| `projects\` 21 dirs with existing decoded paths | KEEP-LIVE | see §7 |
| `projects\fxbo-mcp` (7 jsonl, 19.8MB) | **RUBBISH-DELETE** | allowlist **D1 orphan project dir** — decoded path does not exist; harvest transcripts first (§3) |
| `projects\V--Obsidian-Ideaverse-Pro-2-sample` (1 memory file) | **RUBBISH-DELETE** | allowlist **D1** — harvest the 1 memory file first |
| `projects\V--Obsidian-vrLYT---Crypton-Payments` (1 memory file) | **RUBBISH-DELETE** | allowlist **D1** — harvest the 1 memory file first |
| `projects\AppData-Local-Packages-Claude-...` + `...Temp-claude-...scratchpad-...` | RUBBISH-DELETE | allowlist **D1** — framework-internal/transient paths, regenerate harmlessly; 0.27MB combined |
| heartbeat `session_*` files | n/a | **none exist on this host** (allowlist D2 does not fire) |
| `settings.json` — `cleanupPeriodDays` **absent** | **FIX** | ADD `"cleanupPeriodDays": 90` (owner's fleet-wide choice) |
| `settings.json` — `enabledPlugins["honcho@honcho"] = true`, `extraKnownMarketplaces.honcho` | **FIX** | remove via the §4D checklist. **No `permissions` entries exist** and **no `mcpServers.honcho`** — nothing to purge there |
| `settings.json.bak` | HARVEST→ARCHIVE | -> `archive\2026-09\backups` |
| `.claude\backups` | OWNER-DECIDES | contents UNKNOWN — verify in Phase F, review before archiving |
| `.claude\hooks\watchdog-chaser.ps1`, `weekly-reconcile.cmd` | KEEP-LIVE | referenced by two **disabled** scheduled tasks (§5.15) |
| .claude-archive | HARVEST→ARCHIVE | 0.02MB, one dir `agents-retired-20260821`, 0 jsonl, **no overlap with `projects\`** -> merge into `archive\2026-09\agents\`, then remove the third state |
| .claude.json.backup (2026-03-15), .claude.json.bak (2026-07-09), .claude.json.bak-2026-08-06 | HARVEST→ARCHIVE | -> `archive\2026-09\backups` (older than 90d but allowlist D3 needs owner OK — archive is the safe default) |
| .claude.json.tmp.35324.dc1eef21df4e, .claude.json.tmp.60692.8bed132607dd | HARVEST→ARCHIVE | orphaned atomic-write temps -> `archive\2026-09\backups` |

### 2.8 Backups, secrets, loose root files
| item | tag | note |
|---|---|---|
| .chezmoi-backup-20260902-1856 (0.68MB), -20260903-wave3 (0.04), -20260905-wave4 (0.0), -20260905-wave5 (0.02) | OWNER-DECIDES — **DEFERRED** | candidates only **after Wave 5.1 lands**; not this pass (§5.16) |
| .env | KEEP-LIVE | SECRET — never read, never stage, never move |
| .env.bak-2026-08-12-rotation | OWNER-DECIDES | SECRET backup; propose delete **after VR confirms the 2026-08-12 rotation completed**. Never print contents (§5.20) |
| Downloads (3536.43MB) | OWNER-DECIDES | eyeball. **Only** the duplicate `TeamViewerPortable (2).zip` is on the allowlist (**D5 exact duplicate** + **D6 re-downloadable**) -> RUBBISH-DELETE. paperclip release bundle, Obsidian starter vault, exiftool, GenPatcher: owner (§5.12) |
| filt.ts, gbip.ts, guide.ts, tm.ts | HARVEST→ARCHIVE | loose scratch scripts -> `archive\2026-09\scratch` |
| scratch_all_rulesets.json, scratch_ruleset.json, scratch_versions.json | HARVEST→ARCHIVE | -> `archive\2026-09\scratch` |
| top50_abs.txt, top50_win.txt, vhost_probe_results.txt | HARVEST→ARCHIVE | probe output -> `archive\2026-09\scratch` |
| start-and-verify.ps1, verify-devices.ps1, syncthing-config-new.xml | OWNER-DECIDES | 2026-02-14 ops scripts + a syncthing config draft; syncthing IS running -> confirm the xml is not the live config before moving (§5.19) |
| squad-orchestra-handover.md, readme.md | HARVEST→ARCHIVE | -> `inbox\` if still actionable, else `archive\2026-09\scratch` (owner glance) |
| mercurial.ini | KEEP-LIVE | 2026-09-07, hg config — recent, tiny |

---

## 3. Harvest list — everything here happens BEFORE any move or delete

| source | what to pull | destination |
|---|---|---|
| `.claude\projects\fxbo-mcp` (7 jsonl, 19.8MB, ORPHAN) | apply the §7(c) resumable test to each transcript; **if any passes** copy it out with a `MANIFEST.md`, else nothing | `inbox\sessions-for-omnigent\` (+ MANIFEST.md), then delete the dir |
| `.claude\projects\V--Obsidian-Ideaverse-Pro-2-sample` (1 memory file) | read the file; keep it only if it states a durable fact | `archive\2026-09\HARVEST-obsidian-memory.md`, then delete the dir |
| `.claude\projects\V--Obsidian-vrLYT---Crypton-Payments` (1 memory file) | same | same |
| `.buzz\verify_scratch\vr-orchestra` (**2 unpushed**) | `git push` — **never delete the side with unpushed commits** | remote UC-VR/vr-orchestra |
| `.buzz\verify_scratch\agent-orchestrator` (2 dirty) | `git diff` -> commit or explicitly discard (owner) | remote, or discard |
| `agents\agent-bugalteris` (60 dirty, 1 unpushed, 1 stash) | review diff + `git stash list`/`stash show -p`; commit+push, stash landed or dropped deliberately | remote |
| `agents\skills` (2 unpushed), `Windows-Setuper` (7 unpushed) | push | remotes |
| `.claude-archive\agents-retired-20260821` | inspect contents; write one `HARVEST.md` for the set | `archive\2026-09\agents\` |
| `.honcho` (7.04MB, written **today**) | list contents first; pull any non-regenerable config/notes into `HARVEST.md` — the rest is client cache | `archive\2026-09\infra\honcho\` |
| `.multica` (14.29MB) | `HARVEST.md` (what it was / what to steal) | `archive\2026-09\infra\multica\` |
| `.browseros`, and any AI-tool dotdir VR retires in §5 | one `HARVEST.md` per dir, written inside it before the move | `archive\2026-09\ai-tools\` |
| `orchestra-publish`, `.codex\.tmp\plugins`, `wix` (all remote-less git) | if VR retires any: `git bundle create <name>.bundle --all` first | `archive\2026-09\repos-dupes\` |

**No MEMORY.md harvest on this host.** The home project dir `C--Users-vr` has an **empty** `memory\`
(no MEMORY.md) — see §7. Nothing to correct locally; corrections go to the vr-oc1-side orchestrator
memory/BACKLOG instead.

---

## 4. Execution phases — dry-run first, always

Global rules: **every mutating step is immediately preceded by its own `-WhatIf` preview step**, and
every step appends line-for-line to `C:\Users\vr\archive\2026-09\declutter-log-<phase>.txt`.
Fixed order: **harvest (§3) → A → B → C → D → E → F.** D must not start until §3 is verified
complete (transcript deletes are irreversible). No admin elevation anywhere in this plan.

Create the trees first (this is the only non-previewed step, it creates nothing destructive):
```powershell
New-Item -ItemType Directory -Force C:\Users\vr\archive\2026-09\{infra\honcho,infra\multica,ai-tools,scratch,backups,agents,repos-dupes}
New-Item -ItemType Directory -Force C:\Users\vr\inbox\sessions-for-omnigent
Set-Content C:\Users\vr\inbox\README.md "inbox = ACTION. archive = terminal, never re-read.`nTHIS DIR MUST BE EMPTY BY THE 2026-12 PASS."
```

### Phase A — rubbish deletes (allowlist only)
```powershell
# PREVIEW
Get-Content C:\Users\vr\package.json                                   # guard: must show no name / no deps
Get-ChildItem C:\Users\vr\node_modules | Measure-Object                # ~12.82MB
Get-ChildItem 'C:\Users\vr\Downloads\TeamViewerPortable*.zip' | Select Name,Length,LastWriteTime
Get-FileHash 'C:\Users\vr\Downloads\TeamViewerPortable.zip','C:\Users\vr\Downloads\TeamViewerPortable (2).zip'
Remove-Item -Recurse -Force C:\Users\vr\node_modules -WhatIf
Remove-Item -Force 'C:\Users\vr\Downloads\TeamViewerPortable (2).zip' -WhatIf
# APPLY (only if the two hashes match, and only after owner OK on the zip)
```
Rollback: **none for a delete** — that is why only D5/D6/D7 items are here.
Honcho plugin dirs are deleted in Phase D (they must follow the plugin uninstall, not precede it).

### Phase B — commit / push FINISH items
```powershell
# PREVIEW (all repos, no writes)
'C:\Users\vr\agents\agent-bugalteris','C:\Users\vr\agents\agent-lawyer','C:\Users\vr\agents\agent-orchestrator',
'C:\Users\vr\agents\skills','C:\Users\vr\Windows-Setuper','C:\Users\vr\second-hand',
'C:\Users\vr\.buzz\verify_scratch\vr-orchestra','C:\Users\vr\.buzz\verify_scratch\agent-orchestrator' |
  % { "=== $_"; git -C $_ status -sb; git -C $_ diff --stat; git -C $_ log --branches --not --remotes --oneline }
```
Order: **agent-bugalteris first** (60 dirty + 1 unpushed + 1 stash = the largest loss risk).
Message: `chore: land in-flight work before 2026-09 declutter`. **No `Co-Authored-By` trailer** unless
that repo's `.claude\settings.json` sets `attribution.commit`.
**Secrets guard before every `add`:** `git status` first; never stage `.env*`, `*.key`, `*.crt`, `*.db`,
tokens or archives; in corporate repos (`ai-dev.infinox.io`, `x_fxbo-mcp_claude`) use explicit paths,
never `add -A`, and only with per-repo owner OK.

### Phase C — HARVEST.md, then moves
```powershell
# 1. HARVEST.md written INSIDE each dir first (§1 template, §3 sources)
# 2. GUARD — nothing running maps into a move target
docker ps --format '{{.Names}} {{.Mounts}}'          # expect only claude-code-proxy* -> C:\Users\vr\claude-code-proxy
Get-Process bun,uv,uvx,node,pwsh -EA SilentlyContinue | Select Name,Id,Path
# 3. PREVIEW every move
Move-Item C:\Users\vr\.honcho   C:\Users\vr\archive\2026-09\infra\honcho\   -WhatIf
Move-Item C:\Users\vr\.multica  C:\Users\vr\archive\2026-09\infra\multica\  -WhatIf
Move-Item C:\Users\vr\.browseros C:\Users\vr\archive\2026-09\ai-tools\      -WhatIf
Move-Item C:\Users\vr\filt.ts,C:\Users\vr\gbip.ts,C:\Users\vr\guide.ts,C:\Users\vr\tm.ts,`
          C:\Users\vr\scratch_*.json,C:\Users\vr\top50_*.txt,C:\Users\vr\vhost_probe_results.txt,`
          C:\Users\vr\npm_latest.json C:\Users\vr\archive\2026-09\scratch\ -WhatIf
Move-Item C:\Users\vr\.claude.json.backup,C:\Users\vr\.claude.json.bak,`
          C:\Users\vr\.claude.json.bak-2026-08-06,C:\Users\vr\.claude.json.tmp.* ,`
          C:\Users\vr\.claude\settings.json.bak C:\Users\vr\archive\2026-09\backups\ -WhatIf
Move-Item C:\Users\vr\.claude-archive\agents-retired-20260821 C:\Users\vr\archive\2026-09\agents\ -WhatIf
# 4. APPLY the same lines without -WhatIf, one at a time, each logged
```
**Windows-lock rule: a failed `Move-Item` is a STOP, not a retry-with-force.** If a move fails, a
process holds the dir — log it, leave the item LIVE, and raise it as an owner item. Never `-Force`
past a lock, never fall back to copy-then-delete.
After the merge, `Remove-Item C:\Users\vr\.claude-archive` (now empty) so no third state remains.

### Phase D — `~/.claude` hygiene

**Honcho unwiring checklist for THIS host** (no MCP entry, no permissions entries, no containers,
no volumes, no timers/tasks here — the fleet checklist collapses to six steps):
```powershell
# 1. back up settings.json to a location outside .claude
Copy-Item C:\Users\vr\.claude\settings.json C:\Users\vr\archive\2026-09\settings.json.bak-2026-09-<dd>
# 2. uninstall
claude plugin uninstall honcho@honcho
# 3. VERIFY both keys are gone
(Get-Content C:\Users\vr\.claude\settings.json | ConvertFrom-Json).enabledPlugins.PSObject.Properties.Name -match 'honcho'
(Get-Content C:\Users\vr\.claude\settings.json | ConvertFrom-Json).extraKnownMarketplaces.PSObject.Properties.Name -match 'honcho'
#    -> both must return nothing. (permissions: none exist. .claude.json mcpServers: google-workspace only.)
# 4. PREVIEW then delete the two plugin dirs (~96MB)
Remove-Item -Recurse -Force C:\Users\vr\.claude\plugins\marketplaces\honcho,C:\Users\vr\.claude\plugins\cache\honcho -WhatIf
# 5. move the dotdir (HARVEST.md written first, §3)
Move-Item C:\Users\vr\.honcho C:\Users\vr\archive\2026-09\infra\honcho\        # done in Phase C
# 6. NO chezmoi source edit — honcho lines were already removed upstream (dotfiles 5cc210d)
```

Orphan project dirs and settings:
```powershell
# PREVIEW
$o = 'fxbo-mcp','V--Obsidian-Ideaverse-Pro-2-sample','V--Obsidian-vrLYT---Crypton-Payments'
$o | % { Get-ChildItem -Recurse "C:\Users\vr\.claude\projects\$_" | Measure-Object Length -Sum }
Remove-Item -Recurse -Force ($o | % { "C:\Users\vr\.claude\projects\$_" }) -WhatIf
Get-ChildItem C:\Users\vr\.claude\backups -EA SilentlyContinue        # review before deciding
# APPLY (only after §3 harvest is verified) then:
# add "cleanupPeriodDays": 90  -- the key is ABSENT, so this is an ADD, not an edit
$s = Get-Content C:\Users\vr\.claude\settings.json -Raw | ConvertFrom-Json
$s | Add-Member -NotePropertyName cleanupPeriodDays -NotePropertyValue 90 -Force
$s | ConvertTo-Json -Depth 100 | Set-Content C:\Users\vr\.claude\settings.json
```
`plugins\cache` (141MB) and `plugins\marketplaces` (77.6MB) minus honcho are **left alone** —
regenerating costs more than it saves. No `session_*` sweep: **none exist**.

### Phase E — fixes
1. `cleanupPeriodDays` -> 90 (done in D; verify by re-reading the file).
2. `enabledPlugins.honcho@honcho` + `extraKnownMarketplaces.honcho` removed (done in D; verify).
3. `.claude-archive` third state eliminated (done in C; verify the dir is gone).
4. Duplicate remotes reconciled per VR's §5.4/§5.5 answers — **push before any delete**.
5. **Memory correction: N/A on this host.** `C--Users-vr\memory\` is empty, there is no MEMORY.md
   and therefore no stale Honcho/paperclip/multica claim to correct here. The dated, **append-only**
   corrections go to `/home/vr/agents/agent-orchestrator/memory/MEMORY.md` and `BACKLOG.md` instead.
6. **NO chezmoi source edits.** Wave 5.1 is in flight; `.local\share\chezmoi` is untouched.
7. **Docker: NO prune.** `docker system df` reports **25.87 kB** reclaimable; all 3 images
   (cloudflared, node:22-alpine, hello-world) back running containers or are trivial. Pruning would
   buy nothing and risks the corporate proxy. State this in the log and move on.
8. **Stale-task sweep: nothing actionable that is ours.** The only stale task is
   `GoogleUpdaterTaskSystem152.0.7933.0` (versioned exe gone) — it is Google's, it self-heals, and
   it does not touch `C:\Users\vr`. **Leave it.** The three disabled tasks (`claude-watchdog-chaser`,
   `claude-weekly-reconcile`, `syncthing start`) all have **existing** action paths, so none qualify
   as stale; the two `claude-*` ones are an owner question (§5.15).
9. **Tailscale funnel: OWNER-DECIDES, do not touch unprompted.** `lp-ryckov11.dala-wage.ts.net`
   is a **public** funnel to `localhost:3003` with **nothing listening**. Recommended, only with an
   explicit OK: `tailscale funnel off` (or `tailscale serve reset`). §5.14.
10. **`claude-proxy2-lp-ryckov.llm.infinox.io` is NOT TOUCHED by any step in this plan** (rule 1.5:
    `*.infinox.io` = corporate production). Do not `compose down`/`up` the proxy project — a comment
    in its compose file documents a cross-host `wiki-tunnel` network-connect that a cycle would drop.

**Pre/post hostname HTTP check — run BEFORE Phase A and again AFTER Phase E**, even though no tunnel
is planned to be touched. Any code that degrades = STOP + ISSUES FOUND:
```powershell
'https://claude-proxy2-lp-ryckov.llm.infinox.io','https://lp-ryckov11.dala-wage.ts.net' |
  % { "$_ -> " + (curl.exe -s -o NUL -w '%{http_code}' --max-time 10 $_) }
```
Record both codes in `declutter-log-pre.txt` and `declutter-log-post.txt`.

### Phase F — hand to VR / verify
Nothing in this plan needs Administrator; there is no elevated hand-off line. Phase F is the
executed-state verifier: the hostname pre/post table, `Get-Service | ? Status -ne 'Running'` for
anything previously running, `Get-ScheduledTask | ? LastTaskResult -ne 0`, an unchanged
running-container set, `inbox\README.md` present, no repo left dirty that was meant to be committed,
and resolution of every item this plan marked **UNKNOWN** (`.claude\backups` contents; the on-disk
size of `Excedo Support Services Ltd`; whether `.honcho`'s 2026-09-10 write has a live writer).

---

## 5. Owner decisions

1. **AI-tool dotdirs — which are still used?** One line each, all sizes MB, none in the dep map:
   `.antigravity` 94.4 (Feb, newest Jul-06) · `.antigravity-ide` 100.8 (newest Sep-07) ·
   `.codex` 551.5 (Aug-10) · `.copilot` 0.0 (Aug-15) · `.gemini` 63.0 (newest Sep-09) ·
   `.OpenCluely` 0.01 (Jul-29) · `.cagent` 0.0 (Feb-02) · `.swt` 0.87 (May-13) · `.optmp` 0.0 (Jun-10) ·
   `.herdr` 56.7 (newest Aug-24) · `.graph-mcp` 0.0 (Aug-19) · `.mcp-auth` 0.0 (Aug-26) ·
   `.vite-plus` 34.8 (Aug-27) · `.agents` 0.01 (Jun-10) · `.aws` 0 · `.azure` 0 · `ag-browser` 0 (empty).
   **Not on this list:** `.bun` (22 running procs — stays), `.google_workspace_mcp` (live MCP).
   Answer = keep, or archive to `archive\2026-09\ai-tools\` with a HARVEST.md.
2. **`.vscode` 2007MB + `.vscode-shared` 0.04MB** — 46 extensions, newest file 2026-08-19. Live IDE?
   If yes: KEEP-LIVE untouched. If VS Code is retired here, this is the single biggest tidy-up.
3. **`.cache` 1741.8MB (written 2026-09-03)** — generic. Proposal: **inspect subdirectories and
   decide per subdir**; no blanket delete. Which caches (npm/bun/uv/puppeteer/…) may be cleared?
4. **`.buzz` 1703.95MB** — holds 6 git clones, incl. **`verify_scratch\vr-orchestra` with 2 UNPUSHED**
   and `verify_scratch\agent-orchestrator` 2 dirty, plus clean duplicate clones of UC-VR
   agent-orchestrator and skills (canonicals live in `agents\`) and two `block/buzz` clones with no
   upstream. Push the 2 unpushed first, then: keep `.buzz`, or reduce it to the two `block/buzz` trees?
5. **`second-hand`** — 0.73MB here, master `08195ec`, **11 dirty, 0 unpushed**; a clone also exists on
   vr-oc1. Which is canonical? (Never delete the side with unpushed work; here the dirt is local.)
6. **`agents\agent-bugalteris`** — 60 dirty, 1 unpushed, 1 stash. Commit+push all of it, or does VR
   want to review the 60 first? This is the largest loss risk on the host.
7. **`Windows-Setuper`** — 1.56MB, 3 dirty, **7 unpushed**. Proposal: push. Confirm.
8. **`onepass`** — empty dir, not a git repo, 2026-09-02. Delete, or keep as a placeholder?
   (Same-named repo is LIVE on vr-oc1.) Also: `buzz`, `bin`, `data` — all 0MB empty dirs.
9. **`Obsidian\IX-Global` — 31 dirty, 98 days idle.** Lives on `V:\`, **out of C: scope** — flagged
   only. Corporate vault: reconcile or freeze?
10. **`wix` 1960.1MB** — git repo with **no remote**, 1 dirty, 2026-07-19, corporate. Keep, or
    `git bundle --all` into `archive\2026-09\repos-dupes\` and reclaim ~1.96GB?
11. **`Excedo Support Services Ltd` — size anomaly, NEVER MOVE.** Reported 1,575,338MB. Re-measure
    only: `Get-ChildItem -Recurse -Force -Attributes !Offline` (excludes OneDrive placeholders), or
    `(Get-Item '...').Attributes` / `fsutil reparsepoint query` to confirm Files-On-Demand.
    Corporate. Decision needed only on **who re-measures**, not on any move.
12. **`Downloads` 3536.4MB** — owner eyeball. Only the duplicate `TeamViewerPortable (2).zip`
    (~half of a 77MB pair) is allowlisted. Also inside: a paperclip release bundle (paperclip is
    retired fleet-wide), an Obsidian starter vault, exiftool, GenPatcher — delete any of these?
13. *(covered by 9)* — no other V: content is in scope this pass.
14. **Dangling public Tailscale Funnel.** `lp-ryckov11.dala-wage.ts.net` is exposed to the **public
    internet** and forwards to `localhost:3003`, where **nothing is listening**. Recommend
    `tailscale funnel off` / `tailscale serve reset` — **only with an explicit OK.**
    **`claude-proxy2-lp-ryckov.llm.infinox.io` is explicitly NOT TOUCHED** by this plan.
15. **Two disabled `claude-*` scheduled tasks** — `claude-watchdog-chaser` and
    `claude-weekly-reconcile`; both action paths still exist under `.claude\hooks\`. Delete the task
    definitions (`Export-ScheduledTask` the XML into `archive\2026-09\backups\` first), or leave them
    disabled? (`syncthing start` is disabled too but syncthing runs as a service — leave it.)
16. **The 4 `.chezmoi-backup-*` dirs (0.74MB total)** — **deferred**: candidates only once Wave 5.1
    lands. Nothing to decide today; noting it so it is not forgotten in December.
17. **WSL Debian** — scouted as a fourth mini-host: user `vr`, **no `~/.claude`**, no user services,
    no crontab, nothing referencing `/mnt/c/Users/vr`, vhdx 1.15GB. **Nothing to do**; explicitly out
    of scope for mutations this run.
18. **Loose root files** — `filt.ts`, `gbip.ts`, `guide.ts`, `tm.ts`, `scratch_all_rulesets.json`,
    `scratch_ruleset.json`, `scratch_versions.json`, `top50_abs.txt`, `top50_win.txt`,
    `vhost_probe_results.txt`, `npm_latest.json`, `readme.md`, `squad-orchestra-handover.md`.
    Proposal: all -> `archive\2026-09\scratch\`, except anything still actionable -> `inbox\`.
    Which (if any) is still actionable? `mercurial.ini` stays (2026-09-07, live hg config).
19. **`start-and-verify.ps1`, `verify-devices.ps1`, `syncthing-config-new.xml`** (all 2026-02-14) —
    syncthing **is running**; confirm the xml is not the live config, then archive all three?
20. **`.env.bak-2026-08-12-rotation`** — a **secret** backup. Propose: delete once VR confirms the
    2026-08-12 rotation completed. **Never printed, never staged, never moved into archive.**
    (`.env` itself stays LIVE and untouched.)
21. **`package.json` / `package-lock.json` (2026-03-01, empty manifest)** — delete along with
    `node_modules`, or keep the manifest?
22. **`tmp` 292.8MB / `project` 0.1MB / `scratch_op` 0.03MB / `orchestra-publish` 0.11MB** (the last
    is a remote-less git with 1 dirty file) — keep, or bundle + archive?

---

## 6. Rules going forward (Windows adaptation of the vr-oc1 §6)

1. **Staleness rule: 90 days.** No commit in 90d -> `HARVEST.md` + move to
   `C:\Users\vr\archive\YYYY-MM\<domain>\`. Two states only: LIVE or archived. No "maybe".
2. New projects at `C:\Users\vr\<name>`, agents at `C:\Users\vr\agents\agent-<name>`.
3. **Never move a dir a container, service or scheduled task maps to.** Disable first or leave LIVE.
   On Windows a lock makes `Move-Item` fail — **a failed move is a STOP, never a `-Force` retry.**
4. Never sync `.claude\projects` (sessions + memory are machine-local, and the Windows path encoding
   `C--Users-vr-...` differs from Linux `-home-vr-...`). Cross-machine state travels via chezmoi only.
5. Deletion is limited to the §2 allowlist (D1–D7). Everything else is a move.
6. **Nothing goes under `OneDrive`, `OneDrive - Global Infinox`, or `Documents`** — those are
   corporate-synced and `Documents`/`Desktop`/`Pictures` are redirected. `archive\` and `inbox\`
   live at `C:\Users\vr\`.
7. **chezmoi on Windows has no junctions/symlinks** — never plan a chezmoi-managed symlink here, and
   never edit chezmoi source while a wave is in flight (Wave 5.1 now).
8. **`inbox\` is for ACTION; `archive\` is terminal.** `inbox\` **must be empty by the 2026-12 pass.**
9. **Before disabling any service/task/tunnel, enumerate every hostname, port and path it serves**
   (rule 1.5). Names lie — on vr-oc1 a mis-named tunnel unit caused a ~2h public outage. Anything on
   `*.infinox.io` / `*.ixfin.tech` / `*.infinox.com` is corporate production: per-hostname owner OK,
   never batch-touch. Curl every served hostname before and after.
10. `cleanupPeriodDays = 90` fleet-wide; set it **explicitly** so a default change cannot surprise you.
11. Quarterly repeat (next **2026-12**): the same three read-only scouts, then this plan shape.
12. Retirement checklist for a tool: push local commits -> stop anything running -> uninstall
    plugin/marketplace/MCP/permissions entries -> delete the plugin+marketplace cache dirs ->
    `HARVEST.md` -> move the dotdir to archive -> note any chezmoi-template line to remove after the
    frozen wave lands.

---

## 7. Sessions: resume / abandon (26 project dirs)

**No MEMORY.md drift on this host.** `C--Users-vr\memory\` exists but is **empty** — there is no
MEMORY.md making stale Honcho/paperclip/multica claims, so the vr-oc1 memory-correction step is
**N/A here**. Append-only corrections go to `/home/vr/agents/agent-orchestrator/memory/MEMORY.md`
and `BACKLOG.md` instead. Also: **zero `session_*` heartbeat files** anywhere in `.claude`.

| # | project dir | jsonl / MB | verdict |
|---|---|---|---|
| 1 | C-- | 6 / 30.0 | **KEEP** — drive-root sessions, path exists |
| 2 | C--Users-vr | 16 / 45.4 | **KEEP** — this host's home sessions; memory\ empty (nothing to harvest) |
| 3 | C--Users-vr--buzz | 3 / 0.69 | **KEEP** — 3 memory files; keep with the `.buzz` decision (§5.4) |
| 4 | C--Users-vr--local-share-chezmoi | 1 / 0.18 | **KEEP** — Wave 5.1 in flight, frozen |
| 5 | agents-agent-bugalteris | 7 / 15.1 | **KEEP** — repo has 60 dirty + a stash (§5.6); may need resuming |
| 6 | agents-agent-lawyer | 1 / 1.83 | **KEEP** |
| 7 | agents-agent-orchestrator | 1 / 2.43 | **KEEP** |
| 8 | agents-agent-sysadmin | 9 / 40.7 | **KEEP** — 4 memory files, curated |
| 9 | agents-vr-orchestra | 1 / 7.0 | **KEEP** |
| 10 | ai-dev-infinox-io | 7 / 34.2 | **KEEP** — corporate, repo live |
| 11 | ai-mvp-infinox-io | 1 / 7.3 | **KEEP** — corporate |
| 12 | AppData-Local-Packages-Claude-...-Roaming-Claude | 1 / 0.11 | **DELETE** (allowlist D1) — Claude-internal path, does not exist; regenerates harmlessly |
| 13 | AppData-Local-Temp-claude-...-scratchpad-herdr-pane-topic-sync | 1 / 0.16 | **DELETE** (D1) — transient scratchpad path, gone |
| 14 | cf-builder | 8 / 84.1 | **KEEP** — corporate, >50MB but repo is live |
| 15 | claude-code-proxy | 2 / 8.1 | **KEEP** — backs a LIVE corporate-prod service |
| 16 | cloudflare | 35 / 117.9 | **KEEP** — largest dir; **10 memory files** = curated corporate knowledge, never sweep |
| 17 | fde | 2 / 64.9 | **KEEP** — corporate; 64.9MB from only 2 transcripts, will age out at 90d |
| 18 | **fxbo-mcp** | 7 / 19.8 | **ARCHIVE-then-DELETE** (D1 orphan) — no such dir; real dirs are fxbo-mcp1, fxbo-mcp-bridges, projects\fxbo-mcps, x_fxbo-mcp_claude. Apply the (c) resumable test; anything passing -> `inbox\sessions-for-omnigent\` + MANIFEST.md, then delete |
| 19 | omnigagent | 2 / 48.3 | **KEEP** — repo clean and recent (2026-09-09) |
| 20 | onepass | 1 / 0.0 | **KEEP** (0MB) — but the repo dir is empty (§5.8); delete together if `onepass` goes |
| 21 | project-glu | 1 / 6.05 | **KEEP** — `project\glu` exists |
| 22 | V--Obsidian-claude-ix-Claude | 0 / 0.01 | **KEEP (memory-only)** — 3 memory files, vault exists on V: |
| 23 | V--Obsidian-claude-td-Claude | 0 / 0 | **KEEP (memory-only)** — 2 memory files, vault exists |
| 24 | **V--Obsidian-Ideaverse-Pro-2-sample** | 0 / 0 | **HARVEST-then-DELETE** (D1 orphan) — 1 memory file; vault gone |
| 25 | V--Obsidian-IX-Global | 0 / 0.01 | **KEEP (memory-only)** — 6 memory files, corporate vault live |
| 26 | **V--Obsidian-vrLYT---Crypton-Payments** | 0 / 0 | **HARVEST-then-DELETE** (D1 orphan) — 1 memory file; vault gone |

**Memory-only dirs (5):** the five `V--Obsidian-*` entries hold memory files and **no transcripts**.
Three are backed by live vaults on `V:\` and are kept; two are orphans and are harvested then deleted.
`memory\` is exempt from Claude's transcript sweep, so curated knowledge is never at risk from
`cleanupPeriodDays`.

**Resumable test (unchanged from vr-oc1 §7c):** turns >= 8 **AND** the last assistant line names a
next step or an open question. Fails either -> dead; close it or let it age out under
`cleanupPeriodDays = 90`. Subagent fan-out transcripts are noise by construction — never harvested,
never resumed; the parent's handover is the record.

---

**Appendix A** — raw scout (b) plain listing (all 133 names), the `~/.claude` census, and the scout (c)
dependency map + served-hostname table: `PLAN-declutter-lp-ryckov11-2026-09-10-appendix.md`.
