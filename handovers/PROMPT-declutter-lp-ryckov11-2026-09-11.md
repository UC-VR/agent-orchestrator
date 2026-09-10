# PROMPT — Declutter `lp-ryckov11` (Windows 11, user `lp-ryckov11\vr`)

## 0. Re-validate before starting (this prompt runs whenever it is pasted — no fixed date)

1. Re-derive reachability yourself: `tailscale ip -4 lp-ryckov11`, then `ssh vr@<ip> hostname` (the IP below may be stale; no ssh alias exists yet). If it fails: `tailscale status`, then from the box's own console `Get-Service sshd` (expect Running/Automatic). If still dead, STOP and tell VR.
2. Re-read **§0 STATUS (incl. Wave 2 + the PENDING list)** of `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-vr-oc1-2026-09-10.md` — it is the live precedent and may have moved on since this prompt was written; §7 below is a snapshot, §0 wins.
3. Re-check whether chezmoi Wave 5.1 has landed (it gates every dotfile/settings fix here).

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
  5. **HARD RULE — read what a unit actually serves before touching it.** Before disabling/stopping ANY service, scheduled task, container or tunnel, read its config and enumerate **every hostname, port and path it serves**: `cloudflared` `config.yml` ingress blocks, nginx/caddy site files, `docker-compose*.y*ml` ports/labels, and `(Get-ScheduledTask X).Actions` for task action paths + arguments. Names lie. On vr-oc1 (2026-09-10) disabling `cloudflared-paperclip1.service` silently took **chatwoot + uptime-kuma offline for ~2h** because it was the *single* tunnel for three hostnames despite its name. Any tunnel/service here that serves `*.infinox.io` / `*.ixfin.tech` / `*.infinox.com` is **corporate production**: **OWNER-DECIDES per item, never batch-disable, never touch without an explicit per-hostname OK from VR.**
  6. **No admin elevation.** If Administrator is genuinely needed, hand VR one vetted elevated line; do not attempt it.
  7. `cleanupPeriodDays` → **90** (owner's fleet-wide choice, 2026-09-10).
  8. `memory/` dirs are exempt from Claude's transcript sweep — bloat lives there; census it explicitly.
  9. **`inbox` is the ACTION location; `archive\` is terminal.** Anything that still needs a human decision or a follow-up goes to `C:\Users\vr\inbox\` — **NOT under OneDrive or Documents** — never into archive; nothing in archive is ever looked at again. Session transcripts worth resuming are copied to `inbox\sessions-for-omnigent\` with a `MANIFEST.md` in the same format as vr-oc1's. Write `inbox\README.md` carrying the rule: **this dir must be empty by the 2026-12 pass.**

## 2. Access

```bash
ssh vr@100.102.239.39 'pwsh -NoProfile -Command "<command>"'
```
- **No ssh alias exists.** Re-derive the IP with `tailscale ip -4 lp-ryckov11` before trusting the one above (§0.1).
- Default shell is PowerShell 7. The PS profile throws **non-fatal PSReadLine/fnm errors on every connection** — ignore that stderr noise; always pass `-NoProfile`.
- Tools: `jq` (scoop), `git`. **No `rg`, no `fd`** — use `Get-ChildItem -Recurse`, `Select-String`, `Measure-Object`.
- Claude Code v2.1.258 at `C:\Users\vr\AppData\Roaming\npm\claude.cmd`.
- **Windows path encoding** in `~/.claude/projects` is `C--Users-vr-...` (not `-home-vr-...`) — decode accordingly.
- `Documents` is redirected into OneDrive (`"OneDrive - Global Infinox"`). **Never put `archive\` or `inbox\` inside OneDrive or Documents** — it would sync corporate storage full.
- **Docker Desktop may not be running.** Every `docker` command is conditional: check installed + running first; **do not start it** to satisfy a scout.

## 3. Phase 1 — three read-only scout briefs (sonnet, parallel, ≤50K tokens each)

Scouts are **read-only**: no file writes on either host, no service/task mutations. They return **inline markdown tables** in their final message. Use `worker` for scout (c) since it needs service/process reads.

### Scout (a) — `~/.claude` census
```
Over `ssh vr@<ip> 'pwsh -NoProfile -Command "..."'`, read-only.
~/.claude is 746MB with 26 project dirs. For EVERY dir in C:\Users\vr\.claude\projects\ one row:
  dir name | .jsonl count | total MB | first jsonl date | last jsonl date |
  memory\ file count | memory\session_* count | decoded path exists?
  (decode C--Users-vr-foo-bar -> C:\Users\vr\foo\bar, Test-Path)
Use: Get-ChildItem -Recurse -Filter *.jsonl | Measure-Object -Property Length -Sum
Then: size of every top-level .claude subdir, and
  (Get-Content C:\Users\vr\.claude\settings.json | ConvertFrom-Json).cleanupPeriodDays
  -- currently 26, which is odd (likely a typo of 60/90): FLAG it, do not silently fix.
Also dump, verbatim: any `enabledPlugins`, `permissions` entries matching mcp__honcho__*, and
`extraKnownMarketplaces` keys in settings.json; `mcpServers` keys in C:\Users\vr\.claude.json.
And read the memory\MEMORY.md under this host's own home project dir: list every claim that a retired
system (Honcho / paperclip / multica / OpenClaw) is still live. Quote the stale lines.
Flag orphan dirs, memory-only dirs, and any memory\ holding >20 session_* files.
Inline tables only. No file writes. Budget <=50K tokens.
```

### Scout (b) — project / home census
```
Over `ssh vr@<ip> 'pwsh -NoProfile -Command "..."'`, read-only.
1. PLAIN LISTING FIRST (vr-oc1 lesson: marker-only scanning missed 5 dirs): every top-level entry of
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
Over `ssh vr@<ip> 'pwsh -NoProfile -Command "..."'`, READ-ONLY only:
  Get-Process node,python,pwsh -EA SilentlyContinue | Select Name,Id,Path
  Get-ScheduledTask | ? State -ne Disabled | Select TaskName,TaskPath,State
    (+ (Get-ScheduledTask X).Actions for EVERY task whose action touches C:\Users\vr -- record the
     full action path + arguments, and whether that path still exists: stale-task sweep input)
  Get-Service | ? Status -eq Running | ? {$_.DisplayName -notmatch 'Microsoft|Windows'}
  docker ps  -- ONLY if Docker Desktop is installed AND already running (check first, never start it);
    otherwise report "Docker not running" and skip. For any container/tunnel found, cat its compose
    file / cloudflared config.yml and list EVERY hostname + port it serves (the rule-1.5 guard).
  wsl -l -v   -- and for EVERY distro found: Test-Path \\wsl$\<distro>\home\*\.claude
    Report size, project-dir count and last-write. Treat each WSL distro as a FOURTH mini-host:
    SCOUT it only -- do NOT plan or execute any declutter inside it this run unless VR says so.
Report: process/task/service -> the C:\Users\vr path it depends on. That map is the Phase C move guard.
No Start/Stop/Enable/Disable. Inline table. Budget <=50K tokens.
```

## 4. Phase 2 — plan (one **opus** planner, then verifier gate)

Planner writes `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-lp-ryckov11-<today>.md`
with the **same 7 sections** as the vr-oc1 plan:

| § | content |
|---|---|
| 1 | Target structure — minimal-move; `C:\Users\vr\archive\2026-09\<domain>\`; `C:\Users\vr\inbox\`; HARVEST.md template |
| 2 | Triage sheet — KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES, grouped by domain |
| 3 | Harvest list — knowledge to pull before any delete/move, with destinations |
| 4 | Phases A–F, dry-run-first, every mutating step preceded by a preview step |
| 5 | Owner decisions needed |
| 6 | Rules going forward |
| 7 | Sessions: resume / abandon (26 project dirs) |

**Host-specific items the planner MUST address:**
- **`node_modules` in the home root** — on the delete allowlist, but confirm no `package.json` in `~` depends on it before removing.
- **`.honcho`, `.multica`, `.browseros` dotdirs** — precedent says **trash** (honcho/multica retired fleet-wide; browseros dead tooling). **Confirm per-item** (size, last-write, any process referencing it) before acting; run the full Honcho unwiring checklist in §7, not just the dotdir move.
- **~15 AI-tool dotdirs**: `.antigravity` (+ide) `.codex` `.copilot` `.gemini` `.OpenCluely` `.cagent` `.swt` `.optmp` `.bun` `.herdr` `.graph-mcp` `.google_workspace_mcp` `.mcp-auth` `.vite-plus` `.buzz` `.agents`. Produce an **OWNER-DECIDES list**: which tools are still used? Report each one's size + last-write so VR can answer fast. Do not guess.
- **`.claude-archive`** — someone already started archiving. **Inspect it first**: what is in it, when, does it duplicate `~/.claude/projects`? Then either **merge it into `archive\2026-09\`** or **delete it** — decide on the inspection, do not leave a third state.
- **WSL distros** — if scout (c) found Claude state under `\\wsl$\<distro>\home\*\.claude`, list it as a **fourth mini-host** in §5 with its own sizes; explicitly out of scope for this run's mutations unless VR opts in.
- **OneDrive redirection**: Documents-based state syncs to corporate storage. `archive\` and `inbox\` go at `C:\Users\vr\` — **never** under OneDrive/Documents. Flag any project dir currently living under OneDrive.
- **chezmoi Windows quirks**: no junctions/symlinks — chezmoi behaves differently here. `UC-VR/dotfiles` Wave 5.1 is in flight; **do not edit chezmoi source** (its `dot_claude/modify_settings.json` still carries honcho lines — see §7). `3× .chezmoi-backup-*` dirs: candidates once Wave 5.1 lands, not before.
- **`second-hand` and `onepass`** duplicate repos that also exist on vr-oc1 — **which clone is canonical?** Compare remotes, last-commit, unpushed. OWNER-DECIDES; never delete the side with unpushed commits (**push before delete**).
- **`cleanupPeriodDays = 26`** — odd value, likely a typo. FIX row → 90.
- **Memory drift.** This host's `.claude\projects\<home>\memory\MEMORY.md` is **machine-local** and will still claim Honcho / paperclip / multica are live. The planner must **list the stale claims verbatim**; **Phase E appends dated corrections (append-only, never rewrite)** exactly as vr-oc1 did.
- Corporate content (`ai-dev`/`ai-mvp.infinox.io`, `fxbo-mcp`, `x_fxbo-mcp_claude`, `ix-*`, `cf-builder`, `cloudflare`, `"Excedo Support Services Ltd"`, `fde`, `fde-wrg4`, `prevail-test`, `wix`) → **LIVE / OWNER-DECIDES by default**, never RUBBISH-DELETE.

**Verifier gate** (`verifier`, sonnet) — binary VERIFIED / ISSUES FOUND. Acceptance criteria are **facts to check**, not claims to confirm:
1. Coverage: **every** top-level home entry from scout (b)'s plain listing appears in the §2 triage sheet. Any omission = ISSUES FOUND.
2. Safety: no item tagged for move/delete appears in scout (c)'s process/task/service→path map without a preceding disable step.
3. Every service/task/tunnel the plan disables has, in the plan, the full list of hostnames/ports it serves plus a recorded owner OK per hostname (rule 1.5).
4. Re-derive 6 facts in the plan by raw ssh re-query; a mismatch is ISSUES FOUND.
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

**Executed-state verifier** (after execution) — checks facts, not claims:
1. `curl.exe -s -o NUL -w "%{http_code}"` (or `Invoke-WebRequest`) against **every public hostname** from scout (c)'s hostname table, recorded **BEFORE and AFTER** any service/task/tunnel change; any hostname whose code degraded = ISSUES FOUND.
2. `Get-Service | ? Status -ne 'Running'` for anything previously running, and `Get-ScheduledTask | ? LastTaskResult -ne 0` — no new failures.
3. Running-container set identical to the pre-run set **except** the explicitly approved removals (skip only if Docker was not running before and after).
4. Paths that should exist / not exist; no repo left dirty that was supposed to be committed; `inbox\README.md` present.
Then a worker appends dated, append-only entries to
`/home/vr/agents/agent-orchestrator/memory/MEMORY.md` and `/home/vr/agents/agent-orchestrator/BACKLOG.md`,
plus a **PENDING** list into `C:\Users\vr\inbox\` for VR (owner-deferred items, any elevated hand-off line, anything unresolved).

## 6. Token budget

Expect **≈600–800K total** (vr-oc1: ~650K plan + ~300K execute).
Model tiering: scouts **sonnet** · planner and any prompt-writing **opus** · everything else **sonnet**. **Never haiku.**

## 7. Carry-over from vr-oc1 — *precedent, confirm, don't assume*

- **Paperclip and Multica: retired fleet-wide → trash** (harvest first; **push before delete** for anything with unpushed commits) — applies to `.multica` and any `multica`/`paperclip`-flavoured dir here.
- **OpenClaw dashboards** (mission-control, command-center, kanban, tenacitos, lobsterboard): **trash**. **OpenClaw backup trees: prune to newest 1.**
- **`gemini-auth-manager`: deleted.**
- **Honcho: unwired completely, fleet-wide.** On each host: stop containers (**keep the volumes; list them** for a later `docker volume rm`), disable its timers/tasks, `claude plugin uninstall honcho@honcho`, purge from `settings.json` the `enabledPlugins` entry, the `permissions` entries matching `mcp__honcho__*`, and `extraKnownMarketplaces.honcho`; purge `mcpServers.honcho` from `~/.claude.json`; remove the marketplace + plugin cache dirs; move the honcho dir and the **`.honcho` dotdir (lp has one)** → `archive\2026-09\infra\honcho`. Back up settings.json first. **Note:** the chezmoi template `dot_claude/modify_settings.json` still carries honcho lines — a `chezmoi apply` re-adds the plugin; **fix after Wave 5.1, do not edit chezmoi source during this declutter.**
- **Docker prune approved** (`docker image prune -a`, `docker builder prune -a`) — only if Docker is running, and only **after** confirming every running container's image survives.
- **Stale-task sweep approved.** Windows: any scheduled task whose action path no longer exists → disable + `Export-ScheduledTask` the XML into archive. (Linux equivalent: user units with missing `WorkingDirectory`/`ExecStart`.)
- **`~/tools`-style ACESx memory tooling** (`mem-recall`, `mem-write`, `obs-search`, `migrate-memory-v2`, on PATH) = **OWNER-DECIDES — do not move it if it is on PATH.**
- **`backups` dirs → archive**, after confirming no service/task/script writes there.
- `cleanupPeriodDays` → **90**.
- Heartbeat `session_*` memory spam → **delete**. Orphan project-state dirs → **delete after harvest**.
- Archive-first for everything not on the §1.3 delete allowlist. Big backup trees get a scheduled eyeball, never a bulk delete.
- chezmoi manages dotfiles on all 3 nodes (`UC-VR/dotfiles`); **Wave 5.1 is in flight — do not edit chezmoi source during this declutter.**
