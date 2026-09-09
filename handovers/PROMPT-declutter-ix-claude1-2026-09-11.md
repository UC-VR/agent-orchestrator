# PROMPT — Declutter `ix-claude1` (Linux, corporate Infinox box, user `vr`)

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
  5. **No sudo / elevation.** If root is genuinely needed, hand VR one vetted `sudo bash -c '...'` line; do not attempt it.
  6. `cleanupPeriodDays` → **90** (owner's fleet-wide choice, 2026-09-10).
  7. `memory/` dirs are exempt from Claude's transcript sweep — bloat lives there; census it explicitly.

## 2. Access

```bash
ssh ix-claude1 'bash -lc "<command>"'      # alias exists in ~/.ssh/config; Tailscale hostname
```
- Shell: bash. Tools present: `jq rg git du`. **No `fd`** — use `find`.
- All scouting runs FROM vr-oc1 over ssh.
- `claude` is NOT on the non-login PATH. That is a **finding to confirm**, not a blocker — have a scout check `~/.local/bin/claude`, `~/.npm-global/bin/claude`, `npx claude -v`, and report which exists.
- If unreachable: `tailscale status | grep ix-claude1`, re-derive with `tailscale ip -4 ix-claude1` and ssh `vr@<ip>`. If still dead, STOP and tell VR.
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
Return inline tables only. No file writes. Budget <=50K tokens.
```

### Scout (b) — project / home census
```
Over `ssh ix-claude1 'bash -lc "..."'`, read-only.
1. PLAIN LISTING FIRST (today's lesson: marker-only scanning missed 5 dirs): every top-level entry of
   ~ with size (du -sh) and mtime -- ALL ~60+ entries, none omitted, including loose files.
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
Report: unit/container -> the /home/vr path it depends on. That map is the Phase C move guard.
No systemctl start/stop/enable. No docker run/restart. Inline table. Budget <=50K tokens.
```

## 4. Phase 2 — plan (one **opus** planner, then verifier gate)

Planner writes `/home/vr/agents/agent-orchestrator/handovers/PLAN-declutter-ix-claude1-2026-09-11.md`
with the **same 7 sections** as the vr-oc1 plan:

| § | content |
|---|---|
| 1 | Target structure — minimal-move; `~/archive/2026-09/<domain>/`; HARVEST.md template |
| 2 | Triage sheet — KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES, grouped by domain |
| 3 | Harvest list — knowledge to pull before any delete/move, with destinations |
| 4 | Phases A–F, dry-run-first, every mutating step preceded by a preview step |
| 5 | Owner decisions needed |
| 6 | Rules going forward |
| 7 | Sessions: resume / abandon (85 project dirs — expect a long tail) |

**Host-specific items the planner MUST address:**
- The 12 loose heartbeat scripts in `~` (`ceo_hb*.py` ×7, `ceo_test_comment.py`, `eng_*.py` ×5, `comment_vre33.txt`) — Paperclip-era? Paperclip was **retired fleet-wide** on vr-oc1 today. Propose a tag; do not assume.
- `ix-claude1.dala-wage.ts.net.crt` + `.key` **in home root** — flag for secure relocation (e.g. `~/.config/certs/` with 0600). **Never print key contents.** Check whether any service references the path before moving.
- Backup dirs `cfos-backups`, `metabase-backups`, `multica-backup-*.sql.gz`, `Backups`/`backup`/`archives`, `cloudflare-os` + its 2 backup dirs, `cfos-restore-kit`, `buzz` — **owner eyeball, never bulk delete**.
- 85 `~/.claude/projects` dirs — expect many orphans; harvest memory before deleting any.
- **Corporate vs personal separation.** `~/cloudflare`, `ai-dev.infinox.io`, `ai-mvp.infinox.io`, `buzz` / `buzz.ixfin.tech`, `cfos*`, `deskpro`, `fxbo-mcp`, `infinox-year1-report`, `ix-readai-webhook.service`, `corma`, `fde-wrg` are **corporate → LIVE**. Treat with extra care; default tag **OWNER-DECIDES**, never RUBBISH-DELETE.
- `claw*` / `multica` / `paperclip`-flavoured dirs: vr-oc1 precedent applies (see §7) — confirm per-item.
- `claude` missing from PATH → a FIX row in §2.

**Verifier gate** (`verifier`, sonnet) — binary VERIFIED / ISSUES FOUND:
1. Coverage: **every** top-level home entry from scout (b)'s plain listing appears in the §2 triage sheet. Any omission = ISSUES FOUND.
2. Safety: no item tagged for move/delete appears in scout (c)'s service→path map without a preceding disable step.
3. Spot-check 6 facts in the plan against raw ssh re-queries.
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
- Crash-looping services: **diagnose only** (capture logs, file an item). A declutter is the worst context to debug a service in.

After execution: run `verifier` again against the **executed** state (paths that should exist/not exist, services still up, no repo left dirty that was supposed to be committed). Then a worker appends dated, append-only entries to
`/home/vr/agents/agent-orchestrator/memory/MEMORY.md` and `/home/vr/agents/agent-orchestrator/BACKLOG.md`,
plus a **PENDING** list for VR (owner-deferred items, the sudo hand-off line if any, anything unresolved).

## 6. Token budget

Expect **≈600–800K total** (vr-oc1 today: ~650K plan + ~300K execute).
Model tiering: scouts **sonnet** · planner and any prompt-writing **opus** · everything else **sonnet**. **Never haiku.**

## 7. Carry-over from vr-oc1 — *precedent, confirm, don't assume*

- Paperclip **and** Multica: retired fleet-wide → trash (harvest first).
- OpenClaw dashboards (mission-control, command-center, kanban, tenacitos, lobsterboard): trash/archive.
- OpenClaw backup trees: prune, don't keep whole.
- `gstack`/`tools`-style utility repos: **harvest** the scripts, then archive.
- `cleanupPeriodDays` → **90**.
- Archive-first for everything not on the §1.3 delete allowlist.
- Big backup trees get a scheduled eyeball, never a bulk delete.
- chezmoi manages dotfiles on all 3 nodes (`UC-VR/dotfiles`); **Wave 5.1 is in flight — do not edit chezmoi source during this declutter.**
