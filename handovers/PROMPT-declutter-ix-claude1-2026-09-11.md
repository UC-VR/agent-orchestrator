# PROMPT — Declutter `ix-claude1` (Linux, corporate Infinox box, user `vr`)

## 0. Re-validate before starting (this prompt runs whenever it is pasted — no fixed date)

1. Re-derive reachability yourself: `ssh ix-claude1 hostname`; if that fails, `tailscale status | grep ix-claude1`, then `tailscale ip -4 ix-claude1` and `ssh vr@<ip> hostname`. If still dead, STOP and tell VR.
2. Re-read **§0 STATUS (incl. Wave 2 + the PENDING list)** of `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-vr-oc1-2026-09-10.md` — it is the live precedent and may have moved on since this prompt was written; §7 below is a snapshot, §0 wins.
3. Re-check whether chezmoi Wave 5.1 has landed (it gates every dotfile/settings fix here).

You are the orchestrator. **Delegate everything**; you read nothing large yourself.

## 1. Context

- Repeat, on `ix-claude1`, the declutter planned+executed on `vr-oc1` on 2026-09-10.
- Precedent plan (read it first, for SHAPE only — its contents are vr-oc1-specific):
  `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-vr-oc1-2026-09-10.md`
- Rules that carry over **verbatim**:
  1. **Two states only: LIVE or `~/archive/2026-09/<domain>/`.** No "maybe". Minimal-move: LIVE stays where it is; the archive tree is the only new structure.
  2. **`HARVEST.md` written BEFORE any `mv`**, in the dir being moved:
     ```
     What it was:   <one line>
     What worked:   <one line>
     What to steal: <file paths / patterns worth reusing>
     Why stopped:   <one line>
     Successor:     <repo or "none">
     ```
  3. **Delete allowlist** (everything else is `mv`): orphan `~/.claude/projects` state dirs; heartbeat `session_*` memory spam; `*.old` / `*-backup-*` dirs older than 90d **after owner OK**; retired clones; exact duplicates of a canonical repo; re-downloadable binaries; `node_modules`.
  4. **Never move a dir a running container / service / timer maps to.** Disable first, or leave it LIVE.
  5. **HARD RULE — read what a unit actually serves before touching it.** Before disabling/stopping ANY unit, service, timer, container or tunnel, read its config and enumerate **every hostname, port and path it serves**: `cloudflared` `config.yml` ingress blocks, nginx/caddy site files, `docker-compose*.y*ml` ports/labels, unit `ExecStart` args. Names lie. On vr-oc1 (2026-09-10) disabling `cloudflared-paperclip1.service` silently took **chatwoot + uptime-kuma offline for ~2h** because it was the *single* tunnel (0efd55e7) for three hostnames despite its name. **On ix-claude1 this is CRITICAL:** `cloudflare-os`, `cloudflared`, the `buzz` / `cfos` / `ai-dev` / `ai-mvp` tunnels and `ix-readai-webhook.service` are **corporate production**. Every unit/tunnel change on ix is **OWNER-DECIDES per item** — never batch-disable, and **never touch anything serving `*.infinox.io` / `*.ixfin.tech` / `*.infinox.com` without an explicit per-hostname OK from VR.**
  6. **No sudo / elevation.** If root is genuinely needed, hand VR one vetted `sudo bash -c '...'` line; do not attempt it.
  7. `cleanupPeriodDays` → **90** (owner's fleet-wide choice, 2026-09-10).
  8. `memory/` dirs are exempt from Claude's transcript sweep — bloat lives there; census it explicitly.
  9. **`~/inbox` is the ACTION location; `~/archive/` is terminal.** Anything that still needs a human decision or a follow-up goes to `~/inbox/`, never into archive — nothing in archive is ever looked at again. Session transcripts worth resuming are copied to `~/inbox/sessions-for-omnigent/` with a `MANIFEST.md` in the same format as vr-oc1's. Write `~/inbox/README.md` carrying the rule: **this dir must be empty by the 2026-12 pass.**

## 2. Access

```bash
ssh ix-claude1 'bash -lc "<command>"'      # alias exists in ~/.ssh/config; Tailscale hostname
```
- Shell: bash. Tools present: `jq rg git du`. **No `fd`** — use `find`.
- All scouting runs FROM vr-oc1 over ssh.
- `claude` is NOT on the non-login PATH. That is a **Phase E finding to confirm**, not a blocker — have a scout check `~/.local/bin/claude`, `~/.npm-global/bin/claude`, `npx claude -v`, and report which exists.
- Corporate git identity (`github.com-ix` host alias) is in use. **Respect it** — never rewrite remotes or user.email.

## 3. Phase 1 — three read-only scout briefs (sonnet, parallel, ≤50K tokens each)

Scouts are **read-only**: no file writes on either host, no `docker`/`systemctl` mutations. They return **inline markdown tables** in their final message. Use `worker` for scout (c) since it needs docker/systemctl reads.

### Scout (a) — `~/.claude` census
```
Over `ssh ix-claude1 'bash -lc "..."'`, read-only. ~/.claude is 467M, projects/ 436M, 85 project dirs.
For EVERY dir in ~/.claude/projects/ report one table row:
  dir name | .jsonl count | total MB | first jsonl date | last jsonl date |
  memory/ file count | memory/session_* count | decoded path exists? (decode -home-vr-x-y -> /home/vr/x/y, test -d)
Then: du -sh of every top-level ~/.claude subdir (projects plugins journal sessions teams tasks
session-env todos plans skills commands agents ...), and `jq '.cleanupPeriodDays' ~/.claude/settings.json`
(report "unset" if null). Flag: orphan dirs (decoded path missing), memory-only dirs (0 jsonl but
memory files), dirs whose memory/ holds >20 session_* files.
Also dump, verbatim: any `enabledPlugins`, `permissions` entries matching mcp__honcho__*, and
`extraKnownMarketplaces` keys in ~/.claude/settings.json; `mcpServers` keys in ~/.claude.json.
And read ~/.claude/projects/<this host's home>/memory/MEMORY.md: list every claim that a retired
system (Honcho / paperclip / multica / OpenClaw) is still live. Quote the stale lines.
Return inline tables only. No file writes. Budget <=50K tokens.
```

### Scout (b) — project / home census
```
Over `ssh ix-claude1 'bash -lc "..."'`, read-only.
1. PLAIN LISTING FIRST (vr-oc1 lesson: marker-only scanning missed 5 dirs): every top-level entry of
   ~ with size (du -sh) and mtime -- ALL ~60+ entries, none omitted, including loose files and dotdirs
   (call out `.honcho` if present).
2. Then depth<=3 scan for dirs containing .git, README*, docker-compose*.y*ml, package.json,
   pyproject.toml, or .obsidian.
3. Per git repo: current branch, remotes, last-commit date + days-since, dirty file count,
   unpushed commit count (`git log --branches --not --remotes --oneline | wc -l`).
4. Duplicates: group repos by remote URL; report any URL appearing >1x.
5. Backup-ish dirs: */backups, *.old, *backup*, *-backups, *.sql.gz -- with sizes and mtimes.
6. Loose files in ~ root: scripts (*.py *.sh *.ts), *.crt/*.key, *.sql.gz, *.txt, *.html -- flag them.
   NEVER print the contents of any .key/.crt/.env.
Return inline tables. No file writes. Budget <=50K tokens.
```

### Scout (c) — running services (use `worker`)
```
Over `ssh ix-claude1 'bash -lc "..."'`, READ-ONLY commands only:
  docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' ; docker ps -q | xargs -r docker inspect \
    --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}'
  systemctl --user list-units --all --no-pager ; systemctl --user list-timers --all --no-pager
  systemctl list-units --no-pager | grep -i vr ; grep -rl '/home/vr' /etc/systemd/system 2>/dev/null
  crontab -l 2>/dev/null
  For EVERY unit/container found: cat its ExecStart/compose file and, for any cloudflared instance,
  its config.yml -- and list EVERY hostname in the ingress block. Same for nginx/caddy sites.
  Then: for each unit, does its WorkingDirectory / ExecStart path still exist? (stale-unit sweep input)
Report two tables: (1) unit/container -> the /home/vr path it depends on (the Phase C move guard);
(2) unit/tunnel -> every public hostname + port it serves (the rule-1.5 guard).
No systemctl start/stop/enable. No docker run/restart. Budget <=50K tokens.
```

## 4. Phase 2 — plan (one **opus** planner, then verifier gate)

Planner writes `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-ix-claude1-<today>.md`
with the **same 7 sections** as the vr-oc1 plan:

| § | content |
|---|---|
| 1 | Target structure — minimal-move; `~/archive/2026-09/<domain>/`; `~/inbox/`; HARVEST.md template |
| 2 | Triage sheet — KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES, grouped by domain |
| 3 | Harvest list — knowledge to pull before any delete/move, with destinations |
| 4 | Phases A–F, dry-run-first, every mutating step preceded by a preview step |
| 5 | Owner decisions needed |
| 6 | Rules going forward |
| 7 | Sessions: resume / abandon (85 project dirs — expect a long tail) |

**Host-specific items the planner MUST address:**
- The 12 loose heartbeat scripts in `~` (`ceo_hb*.py` ×7, `ceo_test_comment.py`, `eng_*.py` ×5, `comment_vre33.txt`) — Paperclip-era heartbeat scripts. Paperclip was **retired fleet-wide**, so precedent = **trash** — but only after proving nothing runs them: `crontab -l`, `systemctl --user list-units`, and a grep of unit files / task actions for each filename. Confirm, don't assume.
- `ix-claude1.dala-wage.ts.net.crt` + `.key` **in home root** — **OWNER-DECIDES**, almost certainly a Tailscale cert. Proposal: relocate to `~/.local/share/tailscale-certs/` with `chmod 600`. **Never delete. Never print contents.** Check whether any service references the current path before moving.
- Backup dirs `cfos-backups`, `metabase-backups`, `multica-backup-*.sql.gz`, `cloudflare-os-backup-*`, `Backups`/`backup`/`archives`, `cfos-restore-kit`, `buzz` — **list sizes + dates, tag OWNER-DECIDES (corporate). Never bulk delete.**
- **Honcho unwiring** (see §7) — full checklist, per rule 1.5 for its containers, and archive (never delete) volumes list.
- 85 `~/.claude/projects` dirs — expect many orphans; harvest memory before deleting any.
- **Corporate vs personal separation.** `~/cloudflare`, `cloudflare-os`, `ai-dev.infinox.io`, `ai-mvp.infinox.io`, `buzz` / `buzz.ixfin.tech`, `cfos*`, `deskpro`, `fxbo-mcp`, `infinox-year1-report`, `ix-readai-webhook.service`, `corma`, `fde-wrg` are **corporate → LIVE**. Default tag **OWNER-DECIDES**, never RUBBISH-DELETE, and every unit/tunnel among them is per-item owner-approved (rule 1.5).
- **Memory drift.** `~/.claude/projects/<home>/memory/MEMORY.md` on ix is **machine-local** and will still claim Honcho / paperclip / multica are live. The planner must **list the stale claims verbatim**; **Phase E appends dated corrections (append-only, never rewrite)** exactly as vr-oc1 did.
- `claude` missing from non-login PATH → a **Phase E finding / FIX row** in §2.

**Verifier gate** (`verifier`, sonnet) — binary VERIFIED / ISSUES FOUND. Acceptance criteria are **facts to check**, not claims to confirm:
1. Coverage: **every** top-level home entry from scout (b)'s plain listing appears in the §2 triage sheet. Any omission = ISSUES FOUND.
2. Safety: no item tagged for move/delete appears in scout (c)'s service→path map without a preceding disable step.
3. Every unit/tunnel the plan disables has, in the plan, the full list of hostnames it serves plus a recorded owner OK per hostname (rule 1.5).
4. Re-derive 6 facts in the plan by raw ssh re-query; a mismatch is ISSUES FOUND.
Max **2 retries**; if still failing, present the failures to VR rather than a third retry.

## 5. Phase 3 — owner Q&A, then execution

**STOP after the verifier passes.** Present the plan summary + owner questions via `AskUserQuestion`.
Execute **only** what VR approves, in this fixed order:

```
harvest (§3)  →  A deletes  →  B commits  →  C moves  →  D ~/.claude hygiene  →  E fixes
```
- Every phase: **dry-run preview first, then apply.** Scripts default `--dry-run`; mutate only on `--apply`.
- Log every action, line for line, to `~/archive/2026-09/declutter-log-<phase>.txt` on ix-claude1.
- D must not run before the §3 harvest is verified complete (transcript deletes are irreversible).
- Commits: message `chore: land in-flight work before 2026-09 declutter`. **No `Co-Authored-By` trailer** unless that repo's `.claude/settings.json` sets `attribution.commit`.
- **Secrets guard:** never stage `.env*`, `*.key`, `*.crt`, tokens, `*.db`, or backup archives. `git status` before every `add`; prefer explicit paths over `add -A` in corporate repos.
- Crash-looping services: **diagnose only** (capture logs, file an item in `~/inbox/`). A declutter is the worst context to debug a service in.

**Executed-state verifier** (after execution) — checks facts, not claims:
1. `curl -s -o /dev/null -w '%{http_code}'` **every public hostname** from scout (c)'s hostname table, recorded **BEFORE and AFTER** any unit change; any hostname whose code degraded = ISSUES FOUND.
2. `systemctl --user --failed` and `systemctl --user list-units --all` — no new failed units.
3. Running-container set identical to the pre-run set **except** the explicitly approved removals.
4. Paths that should exist / not exist; no repo left dirty that was supposed to be committed; `~/inbox/README.md` present.
Then a worker appends dated, append-only entries to
`/home/vr/agents/agent-orchestrator/memory/MEMORY.md` and `/home/vr/agents/agent-orchestrator/BACKLOG.md`,
plus a **PENDING** list into `~/inbox/` for VR (owner-deferred items, the sudo hand-off line if any, anything unresolved).

## 6. Token budget

Expect **≈600–800K total** (vr-oc1: ~650K plan + ~300K execute).
Model tiering: scouts **sonnet** · planner and any prompt-writing **opus** · everything else **sonnet**. **Never haiku.**

## 7. Carry-over from vr-oc1 — *precedent, confirm, don't assume*

- **Paperclip and Multica: retired fleet-wide → trash** (harvest first; **push before delete** for anything with unpushed commits).
- **OpenClaw dashboards** (mission-control, command-center, kanban, tenacitos, lobsterboard): **trash**. **OpenClaw backup trees: prune to newest 1.**
- **`gemini-auth-manager`: deleted** (plus its 4 units).
- **Honcho: unwired completely, fleet-wide.** On each host: stop containers (**keep the volumes; list them** for a later `docker volume rm`), disable its timers, `claude plugin uninstall honcho@honcho`, purge from `~/.claude/settings.json` the `enabledPlugins` entry, the `permissions` entries matching `mcp__honcho__*`, and `extraKnownMarketplaces.honcho`; purge `mcpServers.honcho` from `~/.claude.json`; remove the marketplace + plugin cache dirs; move the honcho dir and any `.honcho` dotdir (**lp has one**) → `archive/2026-09/infra/honcho`. Back up settings.json first. **Note:** the chezmoi template `dot_claude/modify_settings.json` still carries honcho lines — a `chezmoi apply` re-adds the plugin; **fix after Wave 5.1, do not edit chezmoi source during this declutter.**
- **Docker prune approved** (`docker image prune -a`, `docker builder prune -a`) — only **after** confirming every running container's image survives.
- **Stale-unit sweep approved.** Linux: any user unit whose `WorkingDirectory`/`ExecStart` path no longer exists → disable + move the unit file to archive. (Windows: scheduled tasks whose action path is missing → disable + export XML to archive.)
- **`~/tools`-style ACESx memory tooling** (`mem-recall`, `mem-write`, `obs-search`, `migrate-memory-v2`, PATH via `.bashrc`) = **OWNER-DECIDES — do not move it if it is on PATH.**
- **`~/backups` → archive**, after confirming no unit or script writes there.
- `cleanupPeriodDays` → **90**.
- Heartbeat `session_*` memory spam → **delete**. Orphan project-state dirs → **delete after harvest**.
- Archive-first for everything not on the §1.3 delete allowlist. Big backup trees get a scheduled eyeball, never a bulk delete.
- chezmoi manages dotfiles on all 3 nodes (`UC-VR/dotfiles`); **Wave 5.1 is in flight — do not edit chezmoi source during this declutter.**
