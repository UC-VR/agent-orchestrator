# PROMPT — Declutter `lp-ryckov11` (Windows 11, user `lp-ryckov11\vr`)

You are the orchestrator. **Delegate everything**; you read nothing large yourself.

## 1. Context

- Repeat, on `lp-ryckov11`, the declutter planned+executed on `vr-oc1` on 2026-09-10.
- Precedent plan (read it first, for SHAPE only — its contents are vr-oc1-specific):
  `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-vr-oc1-2026-09-10.md`
- Rules that carry over **verbatim**:
  1. **Two states only: LIVE or `archive\2026-09\<domain>\`.** No "maybe". Minimal-move: LIVE stays where it is; the archive tree is the only new structure.
  2. **`HARVEST.md` written BEFORE any move**, in the dir being moved:
     ```
     What it was:   <one line>
     What worked:   <one line>
     What to steal: <file paths / patterns worth reusing>
     Why stopped:   <one line>
     Successor:     <repo or "none">
     ```
  3. **Delete allowlist** (everything else is a move): orphan `~/.claude/projects` state dirs; heartbeat `session_*` memory spam; `*.old` / `*-backup-*` dirs older than 90d **after owner OK**; retired clones; exact duplicates of a canonical repo; re-downloadable binaries; `node_modules`.
  4. **Never move a dir a running service / scheduled task / container maps to.** Disable first, or leave it LIVE.
  5. **No admin elevation.** If Administrator is genuinely needed, hand VR one vetted elevated line; do not attempt it.
  6. `cleanupPeriodDays` → **90** (owner's fleet-wide choice, 2026-09-10).
  7. `memory/` dirs are exempt from Claude's transcript sweep — bloat lives there; census it explicitly.

## 2. Access

```bash
ssh vr@100.102.239.39 'pwsh -NoProfile -Command "<command>"'
```
- **No ssh alias exists.** Use the Tailscale IPv4 above; re-derive with `tailscale ip -4 lp-ryckov11` if it fails.
- Default shell is PowerShell 7. The PS profile throws **non-fatal PSReadLine/fnm errors on every connection** — ignore that stderr noise; always pass `-NoProfile`.
- Tools: `jq` (scoop), `git`. **No `rg`, no `fd`** — use `Get-ChildItem -Recurse`, `Select-String`, `Measure-Object`.
- Claude Code v2.1.258 at `C:\Users\vr\AppData\Roaming\npm\claude.cmd`.
- If unreachable: check `tailscale status`, then from the box's own console `Get-Service sshd` (expect Running/Automatic). If still dead, STOP and tell VR.
- **Windows path encoding** in `~/.claude/projects` is `C--Users-vr-...` (not `-home-vr-...`) — decode accordingly.
- `Documents` is redirected into OneDrive (`"OneDrive - Global Infinox"`). **Never put `archive\` inside OneDrive or Documents** — it would sync corporate storage full.

## 3. Phase 1 — three read-only scout briefs (sonnet, parallel, ≤50K tokens each)

Scouts are **read-only**: no file writes on either host, no service/task mutations. They return **inline markdown tables** in their final message. Use `worker` for scout (c) since it needs service/process reads.

### Scout (a) — `~/.claude` census
```
Over `ssh vr@100.102.239.39 'pwsh -NoProfile -Command "..."'`, read-only.
~/.claude is 746MB with 26 project dirs. For EVERY dir in C:\Users\vr\.claude\projects\ one row:
  dir name | .jsonl count | total MB | first jsonl date | last jsonl date |
  memory\ file count | memory\session_* count | decoded path exists?
  (decode C--Users-vr-foo-bar -> C:\Users\vr\foo\bar, Test-Path)
Use: Get-ChildItem -Recurse -Filter *.jsonl | Measure-Object -Property Length -Sum
Then: size of every top-level .claude subdir, and
  (Get-Content C:\Users\vr\.claude\settings.json | ConvertFrom-Json).cleanupPeriodDays
  -- currently 26, which is odd (likely a typo of 60/90): FLAG it, do not silently fix.
Flag orphan dirs, memory-only dirs, and any memory\ holding >20 session_* files.
Inline tables only. No file writes. Budget <=50K tokens.
```

### Scout (b) — project / home census
```
Over `ssh vr@100.102.239.39 'pwsh -NoProfile -Command "..."'`, read-only.
1. PLAIN LISTING FIRST (today's lesson: marker-only scanning missed 5 dirs): every top-level entry of
   C:\Users\vr -- ALL ~80 entries including dotdirs and loose files -- with size and LastWriteTime.
   Size dirs with: Get-ChildItem -Recurse -Force -EA SilentlyContinue | Measure-Object Length -Sum
2. Then depth<=3 scan for dirs containing .git, README*, docker-compose*.y*ml, package.json,
   pyproject.toml, or .obsidian.
3. Per git repo: branch, remotes, last-commit date + days-since, dirty count, unpushed count.
4. Duplicates: group repos by remote URL; report any URL appearing >1x.
5. Backup-ish: *.old, *backup*, .chezmoi-backup-*, .claude-archive, *.sql.gz -- sizes + mtimes.
6. Loose files in the home root (scripts, *.crt/*.key, *.sql.gz) -- flag. NEVER print key/.env contents.
7. Report whether OneDrive redirection covers anything besides Documents.
Inline tables. No file writes. Budget <=50K tokens.
```

### Scout (c) — running services (use `worker`)
```
Over `ssh vr@100.102.239.39 'pwsh -NoProfile -Command "..."'`, READ-ONLY only:
  Get-Process node,python,pwsh -EA SilentlyContinue | Select Name,Id,Path
  Get-ScheduledTask | ? State -ne Disabled | Select TaskName,TaskPath,State
    (+ (Get-ScheduledTask X).Actions for any whose action touches C:\Users\vr)
  Get-Service | ? Status -eq Running | ? {$_.DisplayName -notmatch 'Microsoft|Windows'}
  docker ps  (only if Docker Desktop is installed -- check first, do not start it)
  wsl -l -v   -- and if any distro exists, check whether its home hosts more Claude state:
    Test-Path \\wsl$\<distro>\home\<user>\.claude   (report size; do NOT plan changes there this pass)
Report: process/task/service -> the C:\Users\vr path it depends on. That map is the Phase C move guard.
No Start/Stop/Enable/Disable. Inline table. Budget <=50K tokens.
```

## 4. Phase 2 — plan (one **opus** planner, then verifier gate)

Planner writes `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-lp-ryckov11-2026-09-11.md`
with the **same 7 sections** as the vr-oc1 plan:

| § | content |
|---|---|
| 1 | Target structure — minimal-move; `C:\Users\vr\archive\2026-09\<domain>\`; HARVEST.md template |
| 2 | Triage sheet — KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES, grouped by domain |
| 3 | Harvest list — knowledge to pull before any delete/move, with destinations |
| 4 | Phases A–F, dry-run-first, every mutating step preceded by a preview step |
| 5 | Owner decisions needed |
| 6 | Rules going forward |
| 7 | Sessions: resume / abandon (26 project dirs) |

**Host-specific items the planner MUST address:**
- **`node_modules` in the home root** — on the delete allowlist, but confirm no `package.json` in `~` depends on it before removing.
- **~15 AI-tool dotdirs**: `.antigravity` (+ide) `.codex` `.copilot` `.gemini` `.OpenCluely` `.cagent` `.swt` `.optmp` `.browseros` `.bun` `.herdr` `.graph-mcp` `.google_workspace_mcp` `.mcp-auth` `.vite-plus` `.buzz` `.agents`. Produce an **OWNER-DECIDES list**: which tools are still used? Report each one's size + last-write so VR can answer fast. Do not guess.
- **`.claude-archive`** — someone already started archiving. **Inspect it first**: what is in it, when, does it duplicate `~/.claude/projects`? It may be the seed of the archive tree or dead weight.
- **OneDrive redirection**: Documents-based state syncs to corporate storage. `archive\` goes at `C:\Users\vr\archive\` — **never** under OneDrive/Documents. Flag any project dir currently living under OneDrive.
- **chezmoi Windows quirks**: no junctions/symlinks — chezmoi behaves differently here. `UC-VR/dotfiles` Wave 5.1 is in flight; **do not edit chezmoi source**. `3× .chezmoi-backup-*` dirs: candidates once Wave 5.1 lands, not before.
- **`second-hand` and `onepass`** duplicate repos that also exist on vr-oc1 — **which clone is canonical?** Compare remotes, last-commit, unpushed. OWNER-DECIDES; never delete the side with unpushed commits.
- **`cleanupPeriodDays = 26`** — odd value, likely a typo. FIX row → 90.
- Corporate content (`ai-dev`/`ai-mvp.infinox.io`, `fxbo-mcp`, `x_fxbo-mcp_claude`, `ix-*`, `cf-builder`, `cloudflare`, `"Excedo Support Services Ltd"`, `fde`, `fde-wrg4`, `prevail-test`, `wix`) → **LIVE / OWNER-DECIDES by default**, never RUBBISH-DELETE.

**Verifier gate** (`verifier`, sonnet) — binary VERIFIED / ISSUES FOUND:
1. Coverage: **every** top-level home entry from scout (b)'s plain listing appears in the §2 triage sheet. Any omission = ISSUES FOUND.
2. Safety: no item tagged for move/delete appears in scout (c)'s process/task/service→path map without a preceding disable step.
3. Spot-check 6 facts in the plan against raw ssh re-queries.
Max **2 retries**; if still failing, present the failures to VR rather than a third retry.

## 5. Phase 3 — owner Q&A, then execution

**STOP after the verifier passes.** Present the plan summary + owner questions via `AskUserQuestion`.
Execute **only** what VR approves, in this fixed order:

```
harvest (§3)  →  A deletes  →  B commits  →  C moves  →  D ~/.claude hygiene  →  E fixes
```
- Every phase: **dry-run preview first, then apply.** PowerShell: use `-WhatIf` on `Move-Item`/`Remove-Item` for the preview pass.
- Log every action, line for line, to `C:\Users\vr\archive\2026-09\declutter-log-<phase>.txt` — **NOT under OneDrive or Documents.**
- D must not run before the §3 harvest is verified complete (transcript deletes are irreversible).
- Commits: message `chore: land in-flight work before 2026-09 declutter`. **No `Co-Authored-By` trailer** unless that repo's `.claude/settings.json` sets `attribution.commit`.
- **Secrets guard:** never stage `.env*`, `*.key`, `*.crt`, tokens, `*.db`, or backup archives. `git status` before every `add`; prefer explicit paths over `add -A` in corporate repos.
- Watch for Windows locks: a `Move-Item` fails if a process holds the dir — the scout (c) map is the pre-check, a failed move is a STOP, not a retry-with-force.

After execution: run `verifier` again against the **executed** state (paths that should exist/not exist, services still running, no repo left dirty that was supposed to be committed). Then a worker appends dated, append-only entries to
`/home/vr/agents/agent-orchestrator/memory/MEMORY.md` and `/home/vr/agents/agent-orchestrator/BACKLOG.md`,
plus a **PENDING** list for VR (owner-deferred items, any elevated hand-off line, anything unresolved).

## 6. Token budget

Expect **≈600–800K total** (vr-oc1 today: ~650K plan + ~300K execute).
Model tiering: scouts **sonnet** · planner and any prompt-writing **opus** · everything else **sonnet**. **Never haiku.**

## 7. Carry-over from vr-oc1 — *precedent, confirm, don't assume*

- Paperclip **and** Multica: retired fleet-wide → trash (harvest first) — applies to `.multica`, `.honcho`, `multica`-flavoured dirs here.
- OpenClaw dashboards: trash/archive. OpenClaw backup trees: prune, don't keep whole.
- `gstack`/`tools`-style utility repos: **harvest** the scripts, then archive.
- `cleanupPeriodDays` → **90**.
- Archive-first for everything not on the §1.3 delete allowlist.
- Big backup trees get a scheduled eyeball, never a bulk delete.
- chezmoi manages dotfiles on all 3 nodes (`UC-VR/dotfiles`); **Wave 5.1 is in flight — do not edit chezmoi source during this declutter.**
