# APPENDIX A — raw scout data for PLAN-declutter-lp-ryckov11-2026-09-10

Companion to `PLAN-declutter-lp-ryckov11-2026-09-10.md`. Verbatim scout output (2026-09-10),
kept separate so the plan stays under 500 lines. A verifier can check §2 coverage and Phase C
safety from this file alone.

---

## A.1 Scout (b) — plain listing of `C:\Users\vr` (133 top-level entries)

The coverage baseline. Every name below must appear as a row in plan §2.

| # | Name | Type | MB | LastWrite | note |
|---|---|---|---|---|---|
| 1 | .agents | D | 0.01 | 2026-06-10 | |
| 2 | .antigravity | D | 94.39 | 2026-02-11 | newest file 2026-07-06 |
| 3 | .antigravity-ide | D | 100.81 | 2026-06-30 | newest 2026-09-07 |
| 4 | .aws | D | 0 | 2026-07-19 | |
| 5 | .azure | D | 0 | 2026-07-19 | |
| 6 | .bash_history | F | 0.0013 | 2026-03-15 | |
| 7 | .bash_profile | F | — | 2026-08-28 | |
| 8 | .bashrc | F | — | 2026-08-28 | |
| 9 | .browseros | D | 0.04 | 2026-08-26 | newest 2026-03-24 |
| 10 | .bun | D | 188.18 | 2026-07-07 | RUNNING: bun.exe x22 from .bun\bin |
| 11 | .buzz | D | 1703.95 | 2026-08-12 | newest 2026-09-03; git clones: .scratch\buzz-src (block/buzz, no upstream); REPOS\agent-orchestrator (UC-VR, clean); REPOS\buzz (block/buzz, no upstream); REPOS\skills (UC-VR, clean); verify_scratch\agent-orchestrator (2 dirty); verify_scratch\vr-orchestra (2 UNPUSHED) |
| 12 | .cache | D | 1741.81 | 2026-09-03 | |
| 13 | .cagent | D | 0.0 | 2026-02-02 | |
| 14 | .chezmoi-backup-20260902-1856 | D | 0.68 | — | |
| 15 | .chezmoi-backup-20260903-wave3 | D | 0.04 | — | |
| 16 | .chezmoi-backup-20260905-wave4 | D | 0.0 | — | |
| 17 | .chezmoi-backup-20260905-wave5 | D | 0.02 | — | |
| 18 | .claude | D | 763.58 | 2026-09-10 | see A.2 |
| 19 | .claude-archive | D | 0.02 | 2026-08-21 | single dir agents-retired-20260821 |
| 20 | .claude.json | F | 0.13 | 2026-09-10 | mcpServers: google-workspace only |
| 21 | .claude.json.backup | F | — | 2026-03-15 | |
| 22 | .claude.json.bak | F | — | 2026-07-09 | |
| 23 | .claude.json.bak-2026-08-06 | F | — | — | |
| 24 | .claude.json.tmp.35324.dc1eef21df4e | F | — | 2026-07-15 | |
| 25 | .claude.json.tmp.60692.8bed132607dd | F | — | 2026-07-09 | |
| 26 | .cloudflared | D | 0.0 | 2026-09-02 | no config.yml |
| 27 | .codex | D | 551.46 | 2026-08-10 | contains .tmp\plugins git, no remote |
| 28 | .config | D | 0.97 | 2026-06-21 | |
| 29 | .copilot | D | 0.0 | 2026-08-15 | |
| 30 | .docker | D | 92.78 | 2026-09-09 | |
| 31 | .env | F | 0.0014 | 2026-08-12 | SECRET — never read/stage |
| 32 | .env.bak-2026-08-12-rotation | F | — | — | SECRET |
| 33 | .gemini | D | 63.04 | 2026-08-15 | newest 2026-09-09; has antigravity-backup 1.93MB |
| 34 | .gitconfig | F | — | 2026-09-07 | |
| 35 | .gitignore | F | — | — | |
| 36 | .google_workspace_mcp | D | 0.58 | 2026-06-10 | newest 2026-09-10; matches only live mcpServers entry |
| 37 | .graph-mcp | D | 0.0 | 2026-08-19 | |
| 38 | .herdr | D | 56.68 | 2026-07-15 | newest 2026-08-24 |
| 39 | .honcho | D | 7.04 | 2026-09-10 | newest 2026-09-10 |
| 40 | .lesshst | F | — | — | |
| 41 | .local | D | 311.63 | 2026-06-10 | .local\bin\uv(x).exe RUNNING; .local\share\chezmoi — DO NOT TOUCH |
| 42 | .mcp-auth | D | 0.0 | 2026-08-26 | |
| 43 | .multica | D | 14.29 | 2026-05-14 | newest 2026-05-17 |
| 44 | .node_repl_history | F | — | — | |
| 45 | .OpenCluely | D | 0.01 | 2026-07-29 | |
| 46 | .optmp | D | 0.0 | 2026-06-10 | |
| 47 | .ssh | D | 0.03 | — | |
| 48 | .swt | D | 0.87 | 2026-05-13 | |
| 49 | .vite-plus | D | 34.78 | 2026-08-27 | |
| 50 | .vivaldi_reporting_data | F | — | — | |
| 51 | .vscode | D | 2007.0 | 2026-07-14 | newest 2026-08-19; 46 extensions |
| 52 | .vscode-shared | D | 0.04 | — | |
| 53 | ag-browser | D | 0 | 2026-08-26 | |
| 54 | agents | D | 199.18 | 2026-08-15 | agent-bugalteris main 60 DIRTY 1 UNPUSHED 1 STASH; agent-keth clean; agent-lawyer 1 dirty; agent-librarian clean; agent-netadmin clean; agent-orchestrator 1 dirty; agent-sysadmin clean; skills 2 UNPUSHED; vr-orchestra clean |
| 55 | ai-dev.infinox.io | D | 1303.97 | 2026-09-05 | UC-VR repo, 1 dirty; sub-repo cloudflare-os 1 dirty; CORPORATE |
| 56 | ai-mvp.infinox.io | D | 2.79 | 2026-09-07 | UC-VR clean; CORPORATE |
| 57 | AppData | D | 113076.9 | — | OS — out of scope except Local\Temp git scraps |
| 58 | Application Data | junction | — | — | -> AppData\Roaming |
| 59 | bin | D | 0.0 | 2026-08-15 | |
| 60 | buzz | D | 0.0 | 2026-08-04 | |
| 61 | cf-builder | D | 4.44 | 2026-09-08 | UC-VR clean, vendor\cloudflare-skills detached; CORPORATE |
| 62 | claude-code-proxy | D | 0.43 | 2026-09-03 | UC-VR clean; LIVE — docker bind mount |
| 63 | cloudflare | D | 25.89 | 2026-09-10 | no .git; CORPORATE |
| 64 | Contacts | D | — | — | shell folder |
| 65 | Cookies | junction | — | — | |
| 66 | data | D | 0.0 | 2026-07-15 | |
| 67 | Documents | D | 0 | — | OneDrive-redirected |
| 68 | Downloads | D | 3536.43 | 2026-09-09 | TeamViewerPortable.zip + " (2).zip" 77MB dup pair; a paperclip release bundle; Obsidian starter vault; exiftool; GenPatcher |
| 69 | Excedo Support Services Ltd | D | 1,575,338 reported | — | implausible; OneDrive Files-On-Demand placeholder inflation suspected; CORPORATE; needs on-disk re-measure |
| 70 | Favorites | D | — | — | shell folder |
| 71 | fde | D | 0.18 | 2026-09-02 | CORPORATE |
| 72 | fde-wrg4 | D | 0.18 | 2026-09-07 | CORPORATE |
| 73 | filt.ts | F | — | 2026-08-05 | |
| 74 | fxbo-mcp-bridges | D | 0.67 | 2026-08-26 | CORPORATE |
| 75 | fxbo-mcp1 | D | 187.35 | 2026-08-15 | CORPORATE |
| 76 | gbip.ts | F | — | — | |
| 77 | guide.ts | F | — | — | |
| 78 | ix-ai-azure-rds | D | 0.07 | 2026-07-15 | CORPORATE |
| 79 | ix-buzz | D | 0 | 2026-07-31 | CORPORATE |
| 80 | Links | D | — | — | shell folder |
| 81 | Local Settings | junction | — | — | -> AppData\Local |
| 82 | mercurial.ini | F | — | 2026-09-07 | |
| 83 | Music | D | — | — | shell folder |
| 84 | My Documents | junction | — | — | |
| 85 | NetHood | junction | — | — | |
| 86 | node_modules | D | 12.82 | 2026-08-31 | root package.json has NO name, NO deps -> stray |
| 87 | npm_latest.json | F | — | — | |
| 88 | NTUSER.DAT | F | — | — | OS registry hive |
| 89 | ntuser.dat.LOG1 | F | — | — | OS |
| 90 | ntuser.dat.LOG2 | F | — | — | OS |
| 91 | NTUSER.DAT{...}.TM.blf | F | — | — | OS |
| 92 | NTUSER.DAT{...}.regtrans-ms (1 of 2) | F | — | — | OS |
| 93 | NTUSER.DAT{...}.regtrans-ms (2 of 2) | F | — | — | OS |
| 94 | ntuser.ini | F | — | — | OS |
| 95 | Obsidian | junction | 4100 | — | -> V:\Obsidian, 15 vaults, IX-Global repo 31 DIRTY 98d |
| 96 | omnigagent | D | 2.13 | 2026-09-09 | UC-VR/omnigent clean |
| 97 | OneDrive | D | 0.0 | — | |
| 98 | OneDrive - Global Infinox | D | 326.43 | — | reparse; Documents/Desktop/Pictures redirected here |
| 99 | onepass | D | 0.0 | 2026-09-02 | EMPTY, not a git repo |
| 100 | orchestra-publish | D | 0.11 | 2026-07-15 | git, no remote, 1 dirty |
| 101 | package-lock.json | F | — | 2026-03-01 | |
| 102 | package.json | F | — | 2026-03-01 | no name, no deps |
| 103 | prevail-test | D | 0.01 | 2026-08-24 | CORPORATE |
| 104 | PrintHood | junction | — | — | |
| 105 | project | D | 0.1 | 2026-08-19 | has glu |
| 106 | projects | D | 319.81 | 2026-08-26 | fxbo-mcps InfinoxMngmt clean; CORPORATE |
| 107 | readme.md | F | — | 2026-08-05 | |
| 108 | Recent | junction | — | — | |
| 109 | Saved Games | D | — | — | shell folder |
| 110 | scoop | D | 11510.89 | 2026-07-15 | package manager — LIVE |
| 111 | scratch_all_rulesets.json | F | — | 2026-09-09 | |
| 112 | scratch_op | D | 0.03 | 2026-08-28 | |
| 113 | scratch_ruleset.json | F | — | — | |
| 114 | scratch_versions.json | F | — | — | |
| 115 | Searches | D | — | — | shell folder |
| 116 | second-hand | D | 0.73 | 2026-07-19 | UC-VR/second-hand master 08195ec 11 DIRTY 0 unpushed; also on vr-oc1 |
| 117 | SendTo | junction | — | — | |
| 118 | squad-orchestra-handover.md | F | — | 2026-06-23 | |
| 119 | Start Menu | junction | — | — | |
| 120 | start-and-verify.ps1 | F | — | 2026-02-14 | |
| 121 | Sync | junction | 11400 | — | -> V:\Sync |
| 122 | syncthing-config-new.xml | F | — | 2026-02-14 | |
| 123 | Templates | junction | — | — | |
| 124 | tm.ts | F | — | — | |
| 125 | tmp | D | 292.79 | 2026-07-15 | openclaw-purge\openclaw-personal-inspect UC-VR clean |
| 126 | top50_abs.txt | F | — | — | |
| 127 | top50_win.txt | F | — | — | |
| 128 | verify-devices.ps1 | F | — | — | |
| 129 | vhost_probe_results.txt | F | — | — | |
| 130 | Videos | D | — | — | shell folder |
| 131 | Windows-Setuper | D | 1.56 | 2026-07-09 | UC-VR, 3 dirty, 7 UNPUSHED |
| 132 | wix | D | 1960.1 | 2026-07-19 | git, NO remote, 1 dirty; CORPORATE per prompt |
| 133 | x_fxbo-mcp_claude | D | 307.85 | 2026-08-18 | InfinoxMngmt/mcp-fxbo2, 1 dirty; CORPORATE |

**Duplicate remotes:** UC-VR/agent-orchestrator x3 (`.buzz\REPOS`, `.buzz\verify_scratch` [2 dirty], `agents\`);
UC-VR/skills x2; UC-VR/vr-orchestra x2 (`.buzz\verify_scratch` has 2 unpushed); block/buzz x2.

**OneDrive:** Documents, Desktop, Pictures redirected to `OneDrive - Global Infinox`. No git/project dirs
under OneDrive/Documents. No `.crt/.key/.pem/.sql` files in the home root.

**AppData\Local\Temp git scraps** (leave — OS temp): `buzz-pr5410-work`, `gitglobtest`, `gitglobtest2`,
`uc-vr-skills`, `upstream-humanizer` — all remote-less.

---

## A.2 Scout (a) — `~/.claude` census (763.6MB)

Top-level: `projects` 534.3MB (26 dirs, 113 jsonl) · `plugins` 219.1MB (cache 141MB, marketplaces 77.6MB) ·
everything else <4MB. `settings.json.bak` present. **Zero `session_*` files anywhere** (no heartbeat spam).

| project dir | jsonl | MB | memory files | decoded path exists |
|---|---|---|---|---|
| C-- | 6 | 30.0 | 0 | T |
| C--Users-vr | 16 | 45.4 | 0 (memory\ exists but EMPTY, no MEMORY.md) | T |
| C--Users-vr--buzz | 3 | 0.69 | 3 | T |
| C--Users-vr--local-share-chezmoi | 1 | 0.18 | 0 | T |
| agents-agent-bugalteris | 7 | 15.1 | 0 | T |
| agents-agent-lawyer | 1 | 1.83 | 0 | T |
| agents-agent-orchestrator | 1 | 2.43 | 0 | T |
| agents-agent-sysadmin | 9 | 40.7 | 4 | T |
| agents-vr-orchestra | 1 | 7.0 | 0 | T |
| ai-dev-infinox-io | 7 | 34.2 | 0 | T |
| ai-mvp-infinox-io | 1 | 7.3 | 0 | T |
| AppData-Local-Packages-Claude-...-Roaming-Claude | 1 | 0.11 | 0 | F (Claude-internal path) |
| AppData-Local-Temp-claude-...-scratchpad-herdr-pane-topic-sync | 1 | 0.16 | 0 | F (transient) |
| cf-builder | 8 | 84.1 | 0 | T |
| claude-code-proxy | 2 | 8.1 | 0 | T |
| cloudflare | 35 | 117.9 | 10 | T |
| fde | 2 | 64.9 | 0 | T |
| **fxbo-mcp** | 7 | 19.8 | 0 | **F — ORPHAN** (real dirs: fxbo-mcp1, fxbo-mcp-bridges, projects\fxbo-mcps, x_fxbo-mcp_claude) |
| omnigagent | 2 | 48.3 | 0 | T |
| onepass | 1 | 0.0 | 0 | T |
| project-glu | 1 | 6.05 | 0 | T |
| V--Obsidian-claude-ix-Claude | 0 | 0.01 | 3 | T |
| V--Obsidian-claude-td-Claude | 0 | 0 | 2 | T |
| **V--Obsidian-Ideaverse-Pro-2-sample** | 0 | 0 | 1 | **F — ORPHAN** |
| V--Obsidian-IX-Global | 0 | 0.01 | 6 | T |
| **V--Obsidian-vrLYT---Crypton-Payments** | 0 | 0 | 1 | **F — ORPHAN** |

`settings.json` top keys: env, permissions, model(sonnet), hooks, statusLine(node ~/.claude/statusline.js),
enabledPlugins, extraKnownMarketplaces, outputStyle, advisorModel, tui, skipDangerousModePermissionPrompt,
theme, autoScrollEnabled, agentPushNotifEnabled, voiceEnabled. **`cleanupPeriodDays` is ABSENT.**

`enabledPlugins` includes **`honcho@honcho: true`**, plus agent-librarian, agent-meta, agent-orchestrator,
agent-sysadmin, brainstrust:false, claude-code-setup, claude-md-management, cloudflare, commit-commands,
comms-ops, document-skills, dotjez, frontend-design:false, hookify, i-have-adhd, infra-network,
mcp-server-dev:false, plugin-dev:false, ralph-loop, secret-management, skill-creator, vr-agent-creator.
`extraKnownMarketplaces` keys include **honcho**. `permissions`: **no honcho entries**.
`.claude.json` `mcpServers`: only `google-workspace` — no honcho/multica/paperclip anywhere.

`plugins\marketplaces\honcho` 53.97MB + `plugins\cache\honcho` 42.22MB = ~96MB honcho.
No paperclip/multica plugin traces. `.claude-archive` = one dir `agents-retired-20260821` (0.02MB,
0 jsonl, no overlap with `projects\`) — an agent-retirement folder, not a session archive.

---

## A.3 Scout (c) — dependency map (the Phase C move guard)

| dependency | path on C:\Users\vr | detail |
|---|---|---|
| docker compose project `claude-code-proxy` | `C:\Users\vr\claude-code-proxy` | bind mount -> /app; volume `claude-code-proxy_claude_proxy_tokens`; override `docker-compose.lp-ryckov11.yml`; `start.ps1` injects TUNNEL_TOKEN from 1Password |
| container `claude-code-proxy` | (as above) | node:22-alpine, 127.0.0.1:3456 -> 42069 |
| container `claude-code-proxy-cloudflared-1` | (as above) | token-mode tunnel `lp-ryckov11-claude-proxy2`, **no local config.yml** |
| `bun.exe` x22 | `.bun\bin` | running |
| `uv.exe` / `uvx.exe` | `.local\bin` | running; caches under AppData |
| `claude.exe` | `scoop\persist\fnm` | fnm-managed node |
| startup items | AppData / scoop only | none under the home root |

### Served hostnames (rule 1.5 table)

| hostname | backend | verdict |
|---|---|---|
| `claude-proxy2-lp-ryckov.llm.infinox.io` | cloudflared token tunnel -> container :42069 | **CORPORATE-PROD (`*.infinox.io`) — OWNER-DECIDES, never batch-touch, NOT TOUCHED in this plan** |
| `lp-ryckov11.dala-wage.ts.net` | Tailscale **Funnel** (public internet) -> localhost:3003 | **NOTHING LISTENING on 3003 — dangling public funnel; OWNER-DECIDES** |

A comment in the compose file documents a cross-host `wiki-tunnel` network-connect that a
`compose down` / `up` would drop — do not cycle the compose project in this pass.

### Scheduled tasks

- Enabled non-Microsoft: Edge, OneDrive, Vivaldi, Google, HP, PowerToys, enrollment, SoftLanding —
  **none** depend on `C:\Users\vr` outside AppData.
- Stale: `GoogleUpdaterTaskSystem152.0.7933.0` (versioned exe gone; self-heals; **not ours — leave**).
- **DISABLED:** `claude-watchdog-chaser` (`C:\Users\vr\.claude\hooks\watchdog-chaser.ps1` — exists),
  `claude-weekly-reconcile` (`.claude\hooks\weekly-reconcile.cmd` — exists),
  `syncthing start` (`V:\Sync\...` — exists).

### Services / Docker / WSL

- Services: **no** honcho/multica/paperclip/chatwoot/openclaw. Running: sshd, tailscaled,
  syncthing (8384 GUI, 22000 tailnet), TeamViewer, Docker.
- Docker: 2 containers (above), 1 volume, 3 images (cloudflared 96.8MB, node:22-alpine 232MB,
  hello-world) — **25.87 kB reclaimable. Nothing to prune.**
- WSL: Debian (v2, default) + docker-desktop. Debian: user `vr`, **no `~/.claude`**, no user services,
  no crontab, nothing referencing `/mnt/c/Users/vr`; vhdx 1.15GB. Fourth mini-host is effectively empty.
