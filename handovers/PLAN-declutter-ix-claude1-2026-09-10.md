# PLAN — Declutter `ix-claude1` (Linux, corporate Infinox box, user `vr`) — 2026-09-10

> **PLANNED, NOT EXECUTED.** Nothing in this document has been run. No mutating command was
> issued on ix-claude1 during planning; all checks were read-only `ssh ix-claude1 'bash -lc "..."'`.
> Execution is a later session, dry-run-first, owner-gated per §5.

---

## 6 facts for the verifier

| # | Fact asserted in this plan | Re-derive with |
|---|---|---|
| 1 | 19 running containers, 5 of them honcho (`honcho-api-1 -database-1 -deriver-1 -grafana-honcho-1 -prometheus-1`) | `ssh ix-claude1 'bash -lc "docker ps -q \| wc -l; docker ps --format {{.Names}} \| sort"'` |
| 2 | `fde-wrg` has **104** unpushed commits | `ssh ix-claude1 'bash -lc "git -C ~/fde-wrg log --branches --not --remotes --oneline \| wc -l"'` |
| 3 | Cert `~/ix-claude1.dala-wage.ts.net.crt` expires **Oct 9 18:47:08 2026 GMT** | `ssh ix-claude1 'bash -lc "openssl x509 -enddate -noout -in ~/ix-claude1.dala-wage.ts.net.crt"'` |
| 4 | `cleanupPeriodDays` is **null (unset)**; `~/.claude/projects` holds **88** dirs; `~/.claude/settings.json` is chezmoi-managed by a **modify-template** at `~/.local/share/chezmoi/dot_claude/modify_settings.json` | `ssh ix-claude1 'bash -lc "jq .cleanupPeriodDays ~/.claude/settings.json; ls ~/.claude/projects \| wc -l; chezmoi managed \| grep -x .claude/settings.json; chezmoi source-path ~/.claude/settings.json"'` |
| 5 | Exactly **2** orphan project dirs: `-home-vr-ai-infinox-io`, `-home-vr-multica-workspaces` | `ssh ix-claude1 'bash -lc "ls -d ~/ai.infinox.io ~/multica-workspaces 2>&1; ls -d ~/multica_workspaces ~/multica_workspaces_ixfin"'` (both targets missing; underscore variants exist) |
| 6 | Honcho unit is `~/.config/systemd/user/honcho.service`, WorkingDirectory `/home/vr/claw-services/honcho`, 4 volumes | `ssh ix-claude1 'bash -lc "systemctl --user cat honcho.service \| head -20; docker volume ls --format {{.Name}} \| grep honcho"'` |

---

## 0. STATUS — EXECUTED + VERIFIED 2026-09-10

### Execution record 2026-09-10 (VERIFIED)

Ran from `handovers/PROMPT-declutter-ix-claude1-2026-09-11.md`; passed the executed-state verifier.

**Owner decisions (verbatim-intent):** Honcho UNWIRED (containers down, unit disabled+archived, 4 volumes kept, dir archived); fde-wrg already fully pushed by owner; buzz.ixfin.tech (HTTP 000) KEEP, not retired — investigate; cert relocated to ~/.local/share/tailscale-certs/, no auto-renew; ~/.paperclip + backups → ~/archive/2026-09/paperclip/ after Cloudflare-history harvest (92% already in ~/cloudflare, GoDaddy→CF gap extracted); its cron line removed; deskpro gmail identity left+flagged; 67 aged multica_workspaces_ixfin dirs age out via cleanupPeriodDays=90; .cache pruned (kept chezmoi-status+uv), .vscode-server removed; .antigravity-* archived; Sync/.hermes/Obsidian/archives DEFER to 2026-12. Multica on ix is LIVE+corporate — NOT retired (unlike vr-oc1).

**Executed per phase:** Phase A — 29 heartbeat scripts moved (not rm'd) to ~/archive/2026-09/paperclip/heartbeat-scripts/, 8 junk files rm'd. Phase B — skills/cloudflare(1/45, gate-blocked)/ai-dev.infinox.io/ai-mvp.infinox.io/buzz.ixfin.tech committed+pushed; agent-librarian+agent-multica committed NOT pushed (rebase conflicts); retired-multica-config unpushable (repo archived) → sole copy in archive; 4 forks stashed. Phase D — 4 empty project dirs deleted post-diff-verified harvest, 310 empty session dirs removed; cleanupPeriodDays=90 confirmed via `chezmoi cat | jq` (a line-diff guard false-positived first). Phase E — 3 auto-memory MEMORY.md files corrected append-only; ~/inbox/PENDING-2026-09.md consolidated to 21 items; Phase F sudo line composed, NOT run.

**Disk:** 60G→54G used (65%→58%), du ~43G→37G, top-level entries 154→97. Logs + baselines: ~/archive/2026-09/{declutter-log-*.txt, HTTP/container/unit baselines} on ix.

**PENDING location on ix:** ~/inbox/PENDING-2026-09.md (21 items).

### Follow-ups 2026-09-10 (later session, verification pending)

Executed after the main declutter above; independent verification in progress — not yet marked VERIFIED.

- Tailscale cert renewed as user vr, no sudo (vr has cert rights): new notAfter 2026-12-08, at ~/.local/share/tailscale-certs/; old pair backed up ~/archive/2026-09/tailscale-certs-pre-renew/. Nothing on the host consumes the file cert (Serve/Funnel use Tailscale's internal store) — could be allowed to lapse.
- agent-librarian: merged origin/main (union-resolved EXTERNAL.md/BACKLOG.md/MEMORY.md), commit 0dc011a, pushed, 0 unpushed.
- agent-multica: merged+pushed fbfb048, then archived → ~/archive/2026-09/multica/agent-multica (+ ~/multica symlink); retired-multica-config accepted by owner as sole copy in ~/archive/2026-09/multica/ (GitHub repo archived).
- ~/cloudflare: 4 junk files removed+gitignored; 41 files (39 journal stubs, tool-fixer-instructions.md, .gitignore) committed 8eff2cd via `git -c core.hooksPath=/dev/null` with `approved_by: vryckov` trailer (owner-approved bypass). Lesson: the gate is `runtime/githooks/pre-commit` (agent-only by design), not `runtime/gate.sh` (Claude PreToolUse hook for live CF writes).
- ix-readai-webhook.service: killed by owner decision — disabled/stopped, unit+env → ~/archive/2026-09/infra/ix-readai-webhook/systemd/, code → .../readai/ with HARVEST.md. It was the Funnel :443→localhost:3003 target; https://ix-claude1.dala-wage.ts.net/ now 502 (dangling funnel). Owner-pending: `tailscale funnel --https=443 off`, delete webhook in Read.ai dashboard.
- buzz.ixfin.tech: owner said keep (HTTP 000 still uninvestigated). Phase F sudo enumeration line handed to owner, not yet confirmed run.

§0 execution record is authoritative; §1–§7 below are the pre-execution plan kept as history.

**Scout reports (ground truth):**
- `/tmp/claude-1000/-home-vr/0fddf1d0-254d-439e-9cc5-126a0b49a252/scratchpad/scout-a-claude-census.md`
- `/tmp/claude-1000/-home-vr/0fddf1d0-254d-439e-9cc5-126a0b49a252/scratchpad/scout-b-home-census.md`
- `/tmp/claude-1000/-home-vr/0fddf1d0-254d-439e-9cc5-126a0b49a252/scratchpad/scout-c-services.md`

**§0 findings carried in (established, do not re-derive):**
1. ix-claude1 reachable via `ssh ix-claude1`.
2. chezmoi **Wave 5.1 IN FLIGHT, design-only, nothing in git** → **no edit to chezmoi source in this declutter.** The honcho lines in `dot_claude/modify_settings.json` are **already removed** (dotfiles commit `5cc210d`) — the governing prompt's §7 note about them is **stale**.
3. vr-oc1 precedent §0 PENDING list is unchanged (CF token roll, OP token leak, `~/claw-services`→`~/services` rename, etc.). None of it blocks ix.
4. Coverage baseline correction: scout b's plain listing says "159 entries"; the actual count re-derived on 2026-09-10 is **154** (`ls -A ~ | wc -l`). The delta is scout arithmetic over its own grouped rows — **every one of the 154 real names appears in §2.**

**Disk before:** `/dev/sda2 99G total, 60G used, 34G avail, 65%` (home is on `/`). `du -sh ~` = **43G**.
`~/inbox` and `~/archive` **do not exist** on ix yet.

**HTTP baseline (scout c Table 4, from vr-oc1, 2026-09-10 ~10:22:53 UTC) — the before-row of the executed-state verifier:**

| Hostname | HTTP code |
|---|---|
| wiki.ixfin.tech | 302 |
| ix-buzz.dala-wage.ts.net | 200 |
| ix-claude1.dala-wage.ts.net | 404 (root not routed; Funnel target is a specific app) |
| multica.ixfin.tech | 302 |
| buzz.ixfin.tech | **000** (unreachable — DNS or connection failure) |
| ai-dev.infinox.io | 302 |

**New findings from this planner's own read-only spot-checks (not in the scout reports):**
- **Honcho consumers on ix: none at runtime.** `rg` over `~/.config/systemd/user`, `~/.bashrc`, `~/.bash_aliases`, `~/.profile`, `~/.omnigent`, `~/bin`, `~/.claude/settings.json`, `~/.claude.json` found honcho only in: `honcho.service` itself, `honcho.service.bak.20260706-163907`, a *comment* in `~/bin/backup-metabase-db.sh` ("the honcho backup script already on this host"), and `~/.claude/settings.json:66` `"agent-meta:honcho": "off"`. `~/.hermes/hermes-agent` ships a `honcho_integration/` + `plugins/memory/honcho` + tests — but it is a **source checkout with no systemd unit and no running process**, not a live consumer. No fleet node points at it: `rg 'ix-claude1.dala-wage.ts.net:3000'` over vr-oc1's `~/.claude`, `~/agents`, `~/.config` → 0 hits.
- **Honcho is tailnet-reachable**: `honcho-api-1` binds `127.0.0.1:3000` and `100.90.137.7:3000`; `tailscale serve` proxies `https://ix-claude1.dala-wage.ts.net:3000` (tailnet-only) → `127.0.0.1:3000`. `honcho-database-1` exposes **`0.0.0.0:15432`** (not localhost-bound — a security item regardless of the unwire decision).
- **3 dangling `tailscale serve` entries**: `:3111`, `:3112`, `:3113` proxy to `127.0.0.1:311x` where **no process listens**. Only `:3000` (honcho) and the Funnel `:443→localhost:3003` (`cloudflare-os.service`, pid 2402) have live backends.
- **No service references the cert path.** `rg 'dala-wage.ts.net.(crt|key)'` over `~/.config`, `~/bin`, `~/wikijs`, `~/buzz.ixfin.tech`, `~/claude-code-proxy`, `~/multica.ixfin.tech` → **0 hits**. Relocation is therefore safe from a references standpoint (still OWNER-DECIDES, §5.3).
- Honcho volumes: **4**, not 5 — `honcho_venv`, `honcho_pgdata`, `honcho_prometheus-data`, `honcho_grafana-honcho-data`.

---

## 1. Target structure

**Decision: minimal-move**, same reasoning as vr-oc1 — moving a LIVE repo orphans its
`~/.claude/projects/-home-vr-<path>` dir (path-encoded → session + memory continuity lost) and
breaks compose files, units and chezmoi paths. **LIVE stays exactly where it is; the archive tree
is the only new structure.** On ix this bites harder: ~2.6G of corporate project dirs and 19
containers are path-bound.

```
~/<corporate dirs>      unchanged: ai-dev.infinox.io ai-mvp.infinox.io cfos.ixfin.tech
                        ito.ixfin.tech itops.ixfin.tech itsupport.ixfin.tech buzz.ixfin.tech
                        multica.ixfin.tech cloudflare cloudflare-os corma deskpro fde-wrg
                        fxbo-mcp infinox-year1-report wikijs wrg4-ops cf-builder
                        claude-code-proxy uptime-kuma
~/agents/*              4 agent repos (agent-sysadmin agent-librarian agent-multica vr-orchestra)
~/skills                unchanged
~/Obsidian/*            9 vaults (unchanged — ix-tl@ timers + ix-readai-webhook depend on paths)
~/Sync/*                unchanged (ix-tl@ agent-runner + QuoteStream container live here)
~/archive/2026-09/      NEW — the only structural change
  ├─ paperclip/         retired-paperclip, .paperclip, paperclip-backups, heartbeat-script
  │                     patterns, ceo_/eng_/sec_/sysadmin_ harvest
  ├─ multica/           retired-multica-config, multica-backup-*.sql.gz, multica_workspaces
  ├─ infra/             honcho (ONLY if §5.1 approves), .honcho, claw, claw-logs, .lobster,
  │                     .agentmemory, .iii, recovery-staging, cloudflare-os-starter-upstream
  ├─ backups/           (only what §5.4 approves — nothing bulk)
  ├─ declutter-log-<phase>.txt   ← one per phase, line-for-line
  └─ HARVEST.md per archived item (in the moved dir root, written BEFORE the mv)
~/inbox/                NEW — the ACTION location
  ├─ README.md          rule: this dir must be EMPTY by the 2026-12 pass. Archive is terminal;
  │                     anything needing a human decision lives here, never in archive.
  ├─ PENDING-2026-09.md owner-deferred items + the sudo hand-off line
  └─ sessions-for-omnigent/MANIFEST.md   (format copied verbatim from vr-oc1's, §7)
```

**HARVEST.md template** (≤5 lines, written *before* the `mv`):
```
What it was:   <one line>
What worked:   <one line>
What to steal: <file paths / patterns worth reusing>
Why stopped:   <one line>
Successor:     <repo or "none">
```

**`~/inbox/README.md` content (verbatim):**
```
This directory is the ACTION location. ~/archive/ is terminal — nothing there is ever read again.
Anything that still needs a human decision or a follow-up goes here, never into archive.
RULE: this directory must be EMPTY by the 2026-12 quarterly pass.
```

**`~/inbox/sessions-for-omnigent/MANIFEST.md` format** (columns copied from vr-oc1's):
`sid8 | project dir (decoded path) | original jsonl path | lines | size | what it was doing | intended action`
plus the same three trailing notes (JSONL record shape; originals stay until `cleanupPeriodDays=90`
ages them out — copies not moves; `claude --resume <full-session-id>` from the original cwd still works).

---

## 2. Triage sheet

Tags: **KEEP-LIVE / FINISH / HARVEST→ARCHIVE / RUBBISH-DELETE / FIX / OWNER-DECIDES**
All 154 top-level entries appear below. **Corporate default = OWNER-DECIDES or KEEP-LIVE, never RUBBISH-DELETE.**
Rows marked **[SVC-GUARD]** appear in scout c Table 1 (service→path map): the disable step cited in
the row **must precede** any move/delete. No row in this sheet moves or deletes a **[SVC-GUARD]** path
without that citation.

### 2.1 Corporate — live services & their dirs (KEEP-LIVE, path-bound)

| entry | tag | note |
|---|---|---|
| `wikijs` | KEEP-LIVE **[SVC-GUARD]** | compose dir for `wiki`, `wiki-db`, **`wiki-tunnel`**. DO-NOT-DISABLE (§6). Never moved this pass. |
| `multica.ixfin.tech` | KEEP-LIVE **[SVC-GUARD]** | compose dir for `multica-web/-backend/-db`. **Multica on ix is LIVE and CORPORATE** — serves `multica.ixfin.tech` via `wiki-tunnel`/multica-net. Precedent ("multica retired fleet-wide") **does not apply here**; that was vr-oc1's own instance. |
| `buzz.ixfin.tech` | KEEP-LIVE + FINISH **[SVC-GUARD]** | 5 containers (`buzz-prod-{relay,tailscale,postgres,redis,minio}-1`). Outer repo 2 dirty → commit Phase B. Serves `ix-buzz.dala-wage.ts.net` (200). |
| `buzz` (symlink→buzz.ixfin.tech) | KEEP-LIVE | 0-byte symlink; harmless. |
| `claude-code-proxy` | KEEP-LIVE **[SVC-GUARD]** | container bind-mounts `/home/vr/claude-code-proxy:/app`. **Note the fragility**: `wiki-tunnel` is attached to `claude-code-proxy_default` by a manual `docker network connect`, NOT in compose → lost on `--force-recreate`. Do not recreate it this pass. |
| `uptime-kuma` | KEEP-LIVE **[SVC-GUARD]** | compose dir, 127.0.0.1:3001 only. |
| `cloudflare-os` | KEEP-LIVE **[SVC-GUARD]** | `cloudflare-os.service` ACTIVE, WorkingDirectory here, listens 127.0.0.1:3003 = the **public Funnel target**. 17 dirty → §5.6 (upstream fork; propose no commit). DO-NOT-DISABLE (§6). |
| `Obsidian` (4.4G, 9 vaults) | KEEP-LIVE **[SVC-GUARD]** | `ix-readai-webhook.service` WorkingDirectory = `Obsidian/claude-ix/Claude-services/pipelines/readai`; 13 `ix-tl@*` timers WorkingDirectory = `Obsidian/claude-ix/Claude`. DO-NOT-DISABLE. Vault retention → §5.10. |
| `Sync` (8.0G) | KEEP-LIVE **[SVC-GUARD]** | `quotestream-app-1` compose dir = `Sync/Projects/IXTech/QuoteStream`; `ix-tl@` runner = `Sync/claude-ix/Claude-tools/bin/agent-runner.sh`. Biggest dir on box → §5.10 eyeball only. |
| `claw-services` (27M) | KEEP-LIVE **[SVC-GUARD]** | contains only `honcho/` (the compose dir for `honcho.service`). Fate is §5.1. |
| `ai-dev.infinox.io` (1.3G) | KEEP-LIVE + FINISH **[SVC-GUARD]** | `ai-dev-blueprints-backup.timer` runs `ops/backup-blueprints.py` daily 03:20 from here. 1 dirty → commit Phase B (explicit path). |
| `ai-mvp.infinox.io` (1.3G) | FINISH | 3 unpushed → push Phase B. No running service. Corporate. |
| `cfos.ixfin.tech` | OWNER-DECIDES | 176K, no running service, no git repo listed. Corporate → keep in place, decide 2026-12. |
| `ito.ixfin.tech` / `itops.ixfin.tech` | OWNER-DECIDES | compose files present, **no containers running**. Corporate → leave in place; do not `compose up` to test. |
| `itsupport.ixfin.tech` | OWNER-DECIDES | git repo, clean, 65d. Corporate → leave. |
| `cloudflare` | FINISH | UC-VR/ix-ai-cloudflare, 7 dirty, commit today's date → commit Phase B. |
| `cf-builder` | KEEP-LIVE | 1d, clean, vendored `cloudflare-skills` submodule. |
| `fde-wrg` (336M) | **FINISH — owner-gated** | **104 unpushed commits** on `git@github.com-ix:InfinoxMngmt/fde-ix-wrg.git`, identity `vr-ixfin@users.noreply.github.com`. Corporate. Push only on explicit §5.7 yes. **Never rewrite remote or identity.** |
| `deskpro` | FIX (flag only) | 4 dirty; `user.email = vadim.r00@gmail.com` (personal) while every other repo uses `github@uc.email`. **Flag, do not change** — changing identity on a corporate repo is not a declutter action. §5.8. |
| `corma` (99M) | OWNER-DECIDES | corporate, 43d idle, no service. Leave in place. |
| `fxbo-mcp` | OWNER-DECIDES | 16K corporate stub, 27d. Leave. |
| `infinox-year1-report` | OWNER-DECIDES | 96K corporate. Leave. |
| `wrg4-ops` | KEEP-LIVE | 28K, 1d old, README only. Companion to fde-wrg. |
| `cloudflare-os-backups` (17M) | OWNER-DECIDES | §5.4 |
| `cloudflare-os-starter-upstream` (1.5M) | HARVEST→ARCHIVE | upstream template clone, re-clonable (`cloudflare/cloudflare-os-starter`), 22d, clean → `archive/2026-09/infra/`. Not a delete: it is a corporate-adjacent reference. |
| `ops` (68K) | KEEP-LIVE | `ops/backup/README.md`; small. |
| `ix-readai-webhook.service` (loose file in `~`) | FIX (INFO) | This is a **copy** of the unit; the installed unit is a **USER unit** at `~/.config/systemd/user/ix-readai-webhook.service` (scout c Table 1 — confirmed user-level, NOT system-level). The loose home-root copy is a stray editing artifact. **Do not delete this pass** — it is 4K and the risk of touching a corporate unit file is worse than the clutter. → `~/inbox/PENDING`. |

### 2.2 Honcho (LIVE on ix — the biggest owner decision)

Per rule 1.5, enumerate before proposing a stop.

| entry | tag | note |
|---|---|---|
| `claw-services/honcho` | **OWNER-DECIDES** **[SVC-GUARD]** | See §5.1. **Serves:** `honcho-api-1` → `127.0.0.1:3000` + `100.90.137.7:3000`, reachable at `https://ix-claude1.dala-wage.ts.net:3000` (**tailnet-only**, not Funnel); `honcho-database-1` → **`0.0.0.0:15432`**; grafana + prometheus containers (no serve entry). **Public hostnames served: NONE.** **Consumers found: none at runtime** (see §0 spot-checks). `~/.claude` on ix has **no** honcho plugin, marketplace, MCP server or `mcp__honcho__*` permission — the vr-oc1 unwire checklist is 90% a no-op here. **Volumes to KEEP (never delete):** `honcho_venv`, `honcho_pgdata`, `honcho_prometheus-data`, `honcho_grafana-honcho-data`. **Disable step (only if §5.1 = yes):** `systemctl --user disable --now honcho.service` → `docker compose -f ~/claw-services/honcho/docker-compose.yml down` (**no `-v`**) → then and only then `mv ~/claw-services/honcho ~/archive/2026-09/infra/honcho`. 5 dirty files + repo is a plastic-labs upstream fork → discard dirt, do not commit. |
| `~/.config/systemd/user/honcho.service` | OWNER-DECIDES | disabled+moved to `archive/2026-09/infra/systemd-units/` only under §5.1 = yes. |
| `~/.config/systemd/user/honcho.service.bak.20260706-163907` | RUBBISH-DELETE | `.bak` of a unit file, 66d old, superseded. Delete regardless of §5.1 (not in Table 1). |
| `.honcho` (8.0K) | HARVEST→ARCHIVE | contains only `config.json`. Harvest (§3) then → `archive/2026-09/infra/`. **Do not print its contents** (may hold an API key). |
| `~/bin/backup-metabase-db.sh` honcho mention | INFO | a *comment* only, no dependency. No action. |
| `~/.claude/settings.json:66` `"agent-meta:honcho": "off"` | INFO | already off. No action. |
| `.hermes/hermes-agent/honcho_integration` + `plugins/memory/honcho` | INFO | source checkout, no unit, no process. Not a consumer. No action. |

### 2.3 Paperclip legacy (retired fleet-wide → RUBBISH-DELETE, after proof)

**Confirm-step commands are in Phase A's preview and must all pass before any `rm`.**

| entry | tag | note |
|---|---|---|
| `ceo_hb.py ceo_hb2.py ceo_hb3.py ceo_hb4.py ceo_hb5.py ceo_hb6.py ceo_hb7.py` (7) | RUBBISH-DELETE | Paperclip heartbeat scripts, all `http://localhost:3100/api`. Nothing runs them (scout b §7). Harvest the pattern first (§3). |
| `ceo_test_comment.py` | RUBBISH-DELETE | same family. |
| `eng_check.py eng_check2.py eng_dep.py eng_details.py eng_heartbeat.py eng_heartbeat2.py` (6) | RUBBISH-DELETE | same family; these additionally read `~/.paperclip/instances/default/.env` in binary for HMAC. |
| `sec_check2.py sec_check3.py sec_check4.py sec_check5.py sec_check6.py sec_check7.py sec_hb.py sec_proactive.py` (8) | RUBBISH-DELETE | same family, undocumented in the prompt — scout b found them. |
| `sysadmin_check.py sysadmin_comments.py sysadmin_unassigned.py sysadmin_v113.py sysadmin_v48.py sysadmin_v48b.py` (6) | RUBBISH-DELETE | same family. |
| `comment_vre33.txt` | RUBBISH-DELETE | 4K Paperclip comment payload. |
| `retired-paperclip` (1.1G) | HARVEST→ARCHIVE | 15 dirty + **2 stashes**, `master`, origin `paperclipai/paperclip.git`, 156d. Harvest stashes + dirty diff to a patch (§3), then → `archive/2026-09/paperclip/`. **Not a delete** — 2 stashes are unrecoverable knowledge. |
| `.paperclip` (809M) | **OWNER-DECIDES** **[SVC-GUARD-adjacent]** | **A crontab entry writes here daily**: `0 3 * * * find /home/vr/.paperclip/instances/default/data/backups -name "paperclip-*.sql" -mtime +7 -delete`. No Paperclip container runs. **Disable step before any move: remove that crontab line** (`crontab -l > ~/archive/2026-09/crontab.bak && crontab -l | grep -v '.paperclip/instances' | crontab -`). Then → `archive/2026-09/paperclip/`. Contains `.env` → **never staged, never printed**. |
| `paperclip-backups` (177M) | OWNER-DECIDES | §5.4. Precedent = prune to newest 1; owner OK required (>90d, 2026-04-08). |
| `.agentmemory` (16K) | HARVEST→ARCHIVE | Paperclip-era agent memory, 112d. Harvest then `archive/2026-09/paperclip/`. |
| `.lobster` (56K) | HARVEST→ARCHIVE | OpenClaw/lobsterboard-era state, 168d → `archive/2026-09/infra/`. |
| `.iii` (8.0K) | HARVEST→ARCHIVE | 112d, unidentified dotdir → `archive/2026-09/infra/`; if empty on preview, RUBBISH-DELETE. |
| `claw` (56K) | HARVEST→ARCHIVE | OpenClaw remnant, 161d → `archive/2026-09/infra/`. |
| `claw-logs` (16K) | HARVEST→ARCHIVE | precedent: vr-oc1 archived the same dir → `archive/2026-09/infra/`. |
| `.claude-archive` (12K) | HARVEST→ARCHIVE | 20d, prior `.claude` salvage → `archive/2026-09/infra/`. |
| `recovery-staging` (44M) | OWNER-DECIDES | 17d, unexplained. §5.4. |

### 2.4 Multica on ix (LIVE — split from the retired artifacts)

| entry | tag | note |
|---|---|---|
| `multica.ixfin.tech` | KEEP-LIVE | see §2.1. |
| `multica-daemon.service` (unit) | KEEP-LIVE **[SVC-GUARD]** | `/usr/local/bin/multica --profile ixfin daemon start --foreground`; binary is outside `/home/vr` so no move-guard, but DO-NOT-DISABLE (§6). |
| `.multica` (17M) | KEEP-LIVE | live daemon profile state for the `ixfin` profile. Never move. |
| `multica` (symlink→`~/agents/agent-multica`) | KEEP-LIVE | resolves; agent repo is live. |
| `multica_workspaces_ixfin` (27M) | KEEP-LIVE | the real base dir for the 67 `~/.claude/projects` workspace dirs (§2.7). |
| `multica_workspaces` (940K) | HARVEST→ARCHIVE | underscore dir, 90d, superseded by `multica_workspaces_ixfin`. Its orphaned project dir carries 2 memory files (§2.7) → harvest first. |
| `retired-multica-config` (1.4M) | FINISH→ARCHIVE | 1 dirty + **2 unpushed** on `UC-VR/multica-config.git`. **Push first** (precedent: push before archive), then `archive/2026-09/multica/`. §5.6. |
| `multica-backup-2026-07-07-pre-upgrade.sql.gz` (3.1M) | OWNER-DECIDES | pre-upgrade DB dump of a **still-live** Multica → keeping it is cheap insurance. Propose: → `archive/2026-09/multica/`, keep. §5.4. |

### 2.5 Personal / fleet infra

| entry | tag | note |
|---|---|---|
| `agents` (19M) | KEEP-LIVE + FINISH | 4 repos: `agent-sysadmin` (clean), `agent-librarian` (9 dirty + 1 unpushed → FINISH), `agent-multica` (5 dirty + 1 unpushed → FINISH), `vr-orchestra` (clean). |
| `.agents` (12K) | HARVEST→ARCHIVE | 92d stub, superseded by `~/agents` → `archive/2026-09/infra/`. |
| `skills` (64M) | KEEP-LIVE + FINISH | `UC-VR/skills`, 2 dirty → commit Phase B. |
| `claude-skills` (488K) | HARVEST→ARCHIVE | **no remote configured**, 1 unpushed, 176d. Cannot push. Bundle the commit as a patch (§3) then → `archive/2026-09/infra/`. |
| `.claude` (498M) | KEEP-LIVE + FIX | see §2.7. |
| `.claude.json` (124K) | KEEP-LIVE | live config. `mcpServers` = `["google-workspace"]` only. |
| `.claude.json.tmp.88913.285fa708c393` | RUBBISH-DELETE | 0-byte temp, 63d. |
| `.omnigent` (256K) | KEEP-LIVE **[SVC-GUARD]** | `omni-host.service` reads `~/.omnigent/config.yaml`; `omnigent-reaper.timer` reaps it daily 04:40. |
| `dotfiles` (symlink→`.local/share/chezmoi`) | KEEP-LIVE | **DO NOT TOUCH** — Wave 5.1 in flight. |
| `.local` (5.0G) | KEEP-LIVE | holds `.local/bin/claude`, `.local/share/chezmoi`, `.local/bin/omni`, `.local/bin/syncthing`. Never bulk-touched. |
| `bin` (72K) | KEEP-LIVE **[SVC-GUARD]** | 4 crontab entries + `omnigent-reaper` live here (`sync-hermes-token.sh`, `backup-buzz.sh`, `backup-metabase-db.sh`). |
| `home` (1.4M) | OWNER-DECIDES | 171d, literal `~/home` dir — almost certainly a bad-`$HOME` artifact. Propose HARVEST→ARCHIVE `infra/`; needs one look. |
| `data` (24K) | OWNER-DECIDES | 112d, unidentified. Propose HARVEST→ARCHIVE `infra/`. |
| `ws` (4.0K) | OWNER-DECIDES | 3d, empty-ish scratch. Propose leave. |
| `.hermes` (7.7G) | OWNER-DECIDES | `hermes-agent` checkout (1 dirty, 160d) + 7.7G of model/data cache. **`sync-hermes-token.sh` runs every 6h from crontab** → do not move. §5.10. |
| `.gemini` (22M) / `.copilot` (8K) / `.azure` (3.2M) / `.dotnet` (264K) / `.google_workspace_mcp` (284K) | KEEP-LIVE | tool state; `google-workspace` is the one live MCP server. |
| `.vite-plus` (38M) / `.bun` (78M) / `.nvm` (493M) / `.npm` (1.2G) / `.npm-global` (271M) | KEEP-LIVE | toolchain caches. `.npm` 1.2G is prunable but is a cache, not clutter — not this pass. |
| `.antigravity-ide-server` (376M) / `.antigravity-server` (385M) | OWNER-DECIDES | 761M combined; `.antigravity-server` untouched since 2026-04-08 (155d). Likely a dead IDE remote-server pair. §5.10. |
| `.vscode-server` (4.0G) | OWNER-DECIDES → likely prune | §5.10. |
| `.cache` (5.8G) | OWNER-DECIDES → likely prune | §5.10. Note `.cache/chezmoi-status` is a git checkout of `UC-VR/dotfiles` — **exclude it from any prune**. |
| `.config` (614M) | KEEP-LIVE | all user units live here. |
| `.mozilla` (62M) / `.pki` (76K) / `.gnupg` (8K) / `.ssh` (48K) / `.docker` (112K) | KEEP-LIVE | credentials/browser state. Never touched. |
| `install.sh` (8K) / `bootstrap-debian.sh` (4K) | HARVEST→ARCHIVE | 182d provisioning scripts → `archive/2026-09/infra/`. Genuinely reusable — harvest into the infra HARVEST.md. |
| `download.html` | RUBBISH-DELETE | 0 bytes, 92d. |

### 2.6 Backups, dotfile cruft, and the "everything else" table

**Backup-ish (all OWNER-DECIDES per §5.4 — never bulk-deleted):**

| entry | size | mtime | proposal |
|---|---|---|---|
| `archives` | 1.3G | 2026-07-06 | eyeball, then archive-in-place or off-box |
| `Backups` | 51M | 2026-08-24 | 17d — recent; keep, decide 2026-12 |
| `backup` | 12K | 2026-08-28 | trivial; identify then delete or keep |
| `cfos-backups` | 12M | 2026-08-25 | **written daily by `ai-dev-blueprints-backup.timer`** — KEEP-LIVE, never move |
| `cfos-restore-kit` | 3.4M | 2026-08-24 | corporate restore kit — keep |
| `metabase-backups` | 34M | 2026-07-31 | written by `~/bin/backup-metabase-db.sh` — check crontab wiring before any move (not in current crontab) |
| `cloudflare-os-backups` | 17M | 2026-08-24 | keep |
| `paperclip-backups` | 177M | 2026-04-08 | prune to newest 1 (owner OK) |
| `recovery-staging` | 44M | 2026-08-24 | identify |
| `multica-backup-2026-07-07-pre-upgrade.sql.gz` | 3.1M | 2026-07-07 | → archive/multica/ |

**Everything else (trivial dotfiles/system entries — all KEEP-LIVE / no action, except as tagged):**

| entry | tag | entry | tag |
|---|---|---|---|
| `.bash_aliases` | KEEP-LIVE (chezmoi) | `.bash_history` | KEEP-LIVE |
| `.bash_logout` | KEEP-LIVE | `.bashrc` | KEEP-LIVE (chezmoi) — see FIX below |
| `.bashrc.bak.1787602002` | RUBBISH-DELETE (`.bak`, 17d, chezmoi is the source of truth) | `.bashrc.bak-cco-rollout` | RUBBISH-DELETE (41d) |
| `.bashrc.bak-cco-wrapper-update` | RUBBISH-DELETE (41d) | `.profile` | KEEP-LIVE |
| `.chezmoi-backup-20260902-1856` | KEEP-LIVE until Wave 5.1 lands, then delete | `.chezmoi-backup-20260903-wave3` | same |
| `.chezmoi-backup-20260905-wave4` | same | `.chezmoi-backup-20260905-wave5` | same |
| `.npmrc` (0 bytes) | KEEP-LIVE | `.npmrc.bak-20260723-151334` | RUBBISH-DELETE (`.bak`, 155d) |
| `.env` | KEEP-LIVE — **never staged, never printed** | `.gitconfig` | KEEP-LIVE |
| `.dmrc` | KEEP-LIVE | `.face` / `.face.icon` | KEEP-LIVE |
| `.ICEauthority` (0 bytes) | KEEP-LIVE | `.Xauthority` | KEEP-LIVE |
| `.lesshst` | KEEP-LIVE | `.wget-hsts` | KEEP-LIVE |
| `.sudo_as_admin_successful` (0 bytes) | KEEP-LIVE | `.xsession-errors` | KEEP-LIVE |
| `.xsession-errors.old` | RUBBISH-DELETE (`.old`, 177d) | `Desktop` `Documents` `Downloads` `Music` `Pictures` `Public` `Templates` `Videos` | KEEP-LIVE (empty XDG dirs, 4.0K each) |
| `ix-claude1.dala-wage.ts.net.crt` | **OWNER-DECIDES** §5.3 — 644, expires **2026-10-09** | `ix-claude1.dala-wage.ts.net.key` | **OWNER-DECIDES** §5.3 — 600 (correct). **Never delete, never print.** |

### 2.7 `~/.claude` sub-sheet (498M; projects/ 467M, 88 dirs)

| item | tag | note |
|---|---|---|
| `cleanupPeriodDays` = `null` | FIX | → **90** (Phase D). Fleet-wide owner choice 2026-09-10. **`~/.claude/settings.json` IS chezmoi-managed** (`chezmoi managed` lists `.claude` and `.claude/settings.json`) — but its source is a **modify-template**, `~/.local/share/chezmoi/dot_claude/modify_settings.json`, not a full-file template. Its own header states it "overwrite[s] ONLY the fleet-managed top-level keys" (`permissions`, `hooks`, `env`, `enabledPlugins`, `extraKnownMarketplaces`) and keeps every host-owned key "and anything else Claude Code invents later". `cleanupPeriodDays` is an unmanaged top-level key → **a local edit survives `chezmoi apply`**; this is exactly how vr-oc1 set it on 2026-09-10 without reversion. **No chezmoi source edit is required or permitted.** Phase D still proves it with a post-edit `chezmoi diff` check and reverts if the proof fails. |
| orphan `-home-vr-ai-infinox-io` (8K, 1 jsonl) | RUBBISH-DELETE | decoded `/home/vr/ai.infinox.io` absent; no `ai-infinox-io` dir either. 0 memory files → nothing to harvest. |
| orphan `-home-vr-multica-workspaces` (20K, 0 jsonl, **2 memory files**) | HARVEST→then-DELETE | orphan **and** memory-only. **Harvest §3 first** — contains the stale Multica claim below. |
| memory-only `-home-vr-cloudflare` (2 files) | HARVEST→then-DELETE | corporate memory → harvest into `~/cloudflare` repo docs or `-home-vr` memory. |
| memory-only `-home-vr-ito-ixfin-tech` (5 files) | HARVEST→then-DELETE | corporate. |
| memory-only `-home-vr-Obsidian-claude-ix-Claude` (10 files) | **KEEP** | decoded path **exists** and is the WorkingDirectory of `ix-readai-webhook.service` + 13 `ix-tl@` timers. Live corporate memory — do not delete; only correct the stale claims. |
| memory-only `-home-vr-Sync-Projects-IXTech-VRExecutiveOperations` (6 files) | **KEEP** | decoded path exists, live. Correct the stale claim. |
| **67-dir `multica_workspaces_ixfin` cluster** | OWNER-DECIDES → **recommend DELETE as one batch** | pattern `-home-vr-multica-workspaces-ixfin-a06e6801-356d-4baf-bcc2-d74b4661893e-<8hex>-workdir`. 1 jsonl each, 36K–772K, ≈**24M** total, **0 memory files, 0 session_\***, 2026-08-11→2026-09-10. These are ephemeral Multica per-workspace agent runs, not human sessions. Base dir `~/multica_workspaces_ixfin` **exists** → they are not orphans; they will age out on their own once `cleanupPeriodDays=90` is set. **Recommendation: set 90 and let them age out — do not hand-delete.** §5.9. |
| `-home-vr` (22 jsonl, 45M, memory 8 files, 0 session_*) | KEEP-LIVE | host-home; **no stale claims** (scout a: clean). |
| 9 dirs >20MB (fde-wrg 93M, ai-dev 70M, cf-builder 48M, cfos 46M, agent-sysadmin 45M, -home-vr 45M, deskpro 43M, corma 28M, ai-mvp 23M) | KEEP-LIVE | all decode to live dirs; aged out by `cleanupPeriodDays=90`. |
| heartbeat `session_*` memory spam | **NONE** | 0 across all 88 dirs — the vr-oc1 cleanup step does not apply here. |
| `plugins/` 25M cache | KEEP-LIVE | do not `rm` — regenerating costs more than it saves. |
| `settings.json.doctor-bak` | KEEP-LIVE | leave; Phase D takes its own dated backup. |
| honcho plugin/marketplace/MCP/permissions | **N/A** | `find ~/.claude -iname '*honcho*'` → 0 results. The vr-oc1 unwire steps are a no-op on ix. |

**Stale memory claims — quoted verbatim (corrections are APPEND-ONLY and dated, Phase E):**

1. `/home/vr/.claude/projects/-home-vr-multica-workspaces/memory/MEMORY.md:3`
   > `- [Multica local deployment](multica-local-deployment.md) — vr-oc1 down for maintenance; local Multica server deployed at multica.ixfin.tech, workspace IX-Global, Resend auth; claudfred skipped`
   **Correction to append:** the `multica.ixfin.tech` claim is **still TRUE on ix** (live, corporate); the "vr-oc1 down for maintenance" framing is stale — vr-oc1's Multica was retired 2026-09-10, ix's is independent and live.
2. `/home/vr/.claude/projects/-home-vr-Obsidian-claude-ix-Claude/memory/MEMORY.md:7`
   > `- [feedback_paperclip_agents.md](feedback_paperclip_agents.md) — Critical agent setup: dangerouslySkipPermissions, adapter_type, defaultProjectId, timeouts, DISPLAY`
3. `…/-home-vr-Obsidian-claude-ix-Claude/memory/MEMORY.md:14`
   > `- [project_ix_production_status.md](project_ix_production_status.md) — Deployment state, Paperclip managing agents, integrations`
4. `…/-home-vr-Obsidian-claude-ix-Claude/memory/MEMORY.md:16`
   > `- [project_paperclip_integration.md](project_paperclip_integration.md) — Paperclip architecture, admin setup, key IDs, skills installed`
5. `/home/vr/.claude/projects/-home-vr-Sync-Projects-IXTech-VRExecutiveOperations/memory/MEMORY.md:5`
   > `- [feedback_plugin_runtime.md](feedback_plugin_runtime.md) — Plugins run on Paperclip SDK (Node.js 20), NOT Cloudflare Workers`

   **Correction to append to 2–5:** Paperclip is retired fleet-wide (vr-oc1 2026-09-10); **no Paperclip container runs on ix-claude1** (19 containers, none Paperclip). `ix-readai-webhook.env` still sets `PAPERCLIP_API_URL=http://localhost:3100` and `PAPERCLIP_COMPANY_ID` — **that webhook may be pointing at a dead backend** → `~/inbox` item, diagnose-only.
6. Scout a could not read the sub-files (budget) — whether ix ran a *separate* Paperclip is unresolved. The correction must say "no Paperclip process on ix as of 2026-09-10", not "Paperclip never existed here".

### 2.8 Non-defects (FIX/INFO rows — evidence, not problems)

| item | tag | evidence |
|---|---|---|
| "`claude` not on PATH" (prompt premise) | **INFO — not a defect** | `command -v claude` → `/home/vr/.local/bin/claude` → symlink to `/home/vr/.local/share/claude/versions/2.1.267` (native installer). `~/.npm-global/bin/claude` absent; `npx --no-install claude -v` fails (expected). `.bashrc` has `export PATH="$HOME/.local/bin:$PATH"`, `.profile` prepends the same. **Login and interactive shells are correct.** Only a *non-login non-interactive* shell (e.g. a bare `ssh host 'claude'`) misses it — which is why every command in this plan is wrapped in `bash -lc`. **No action.** |
| `~/tools` absent, `.bashrc` references it | **INFO — inert** | `[ -d "$HOME/tools/bin" ] && export PATH=…` and `[ -f "$HOME/.tools-config" ] && . …` — both `-d`/`-f` guarded, no-ops. `.bashrc` is **chezmoi-managed** → **do not edit**; queue the template line removal for after Wave 5.1 (`~/inbox`). |
| 3 dangling `tailscale serve` entries `:3111 :3112 :3113` | FIX (deferred) | serve proxies bind on `100.90.137.7:311x` → `127.0.0.1:311x`, where **nothing listens**. Cosmetic; removing them is `tailscale serve --https=3111 off` ×3. Not this pass → `~/inbox`. |
| `honcho-database-1` on `0.0.0.0:15432` | **SECURITY — inbox** | not localhost-bound. Independent of §5.1: even if honcho stays, this should be rebound (vr-oc1 precedent: Honcho/Uptime-Kuma rebound to 127.0.0.1 in the 2026-06 hardening pass). |
| `wiki-tunnel` ↔ `claude-code-proxy_default` manual network attach | **FRAGILITY — inbox** | not in compose; lost on `--force-recreate`. Document in SERVICES.md (§6). |

---

## 3. Harvest list

Knowledge pulled **before** any delete/move. Destination is a HARVEST.md, a repo, or `-home-vr` memory.

| source | what | destination |
|---|---|---|
| `~/retired-paperclip` 2 stashes | `git -C ~/retired-paperclip stash show -p stash@{0} > ~/archive/2026-09/paperclip/retired-paperclip-stash0.patch` (and `{1}`) | `archive/2026-09/paperclip/` |
| `~/retired-paperclip` 15 dirty | `git -C ~/retired-paperclip diff > …/retired-paperclip-dirty.patch` + `git status --porcelain` for untracked list | same |
| 27 heartbeat scripts (`ceo_*` `eng_*` `sec_*` `sysadmin_*` `comment_vre33.txt`) | **one representative of each family** (`ceo_hb.py`, `eng_heartbeat.py`, `sec_hb.py`, `sysadmin_check.py`) copied whole + a 5-line note on the HMAC-over-`.env` pattern against `localhost:3100/api` | `archive/2026-09/paperclip/heartbeat-scripts/` + a line in its HARVEST.md. **Copy, then delete all 27.** |
| `~/.honcho/config.json` | copy as-is (**do not print**) | `archive/2026-09/infra/honcho-dotdir/` |
| `~/claw-services/honcho` | volume names, compose service list, the op-injected env var name (`LLM_GEMINI_API_KEY`), and the `0.0.0.0:15432` finding | `archive/2026-09/infra/honcho/HARVEST.md` (only if §5.1 = yes) |
| `~/claude-skills` 1 unpushed commit (no remote) | `git -C ~/claude-skills format-patch -1 -o ~/archive/2026-09/infra/claude-skills-patches/` | `archive/2026-09/infra/` |
| `~/.claude/projects/-home-vr-multica-workspaces/memory/` (2 files) | the Multica-local-deployment note | `-home-vr` memory as a dated, corrected entry (§2.7 claim 1) |
| `~/.claude/projects/-home-vr-cloudflare/memory/` (2 files) | corporate CF notes | `~/cloudflare` repo `docs/` or `-home-vr` memory |
| `~/.claude/projects/-home-vr-ito-ixfin-tech/memory/` (5 files) | corporate ITO notes | `-home-vr` memory index |
| `~/install.sh`, `~/bootstrap-debian.sh` | provisioning steps worth reusing | `archive/2026-09/infra/HARVEST.md` |
| `~/multica_workspaces` (940K) | one line on what the underscore dir was vs `_ixfin` | `archive/2026-09/multica/HARVEST.md` |
| stale memory claims 1–6 (§2.7) | dated append-only corrections | the 3 MEMORY.md files, in place (Phase E) |

---

## 4. Execution phases

**Global rules.** Every mutating step is preceded by a preview step. Scripts take `--dry-run`
(**default ON**) and mutate only on `--apply`. Every action is logged line-for-line to
`~/archive/2026-09/declutter-log-<phase>.txt` on ix. **Order is fixed:**
`harvest (§3) → A deletes → B commits → C moves → D ~/.claude hygiene → E fixes → F sudo hand-off`.
**D must not run before the §3 harvest is verified complete** (transcript deletes are irreversible).

### Phase A — rubbish deletes

```bash
# ---------- PREVIEW (must all pass) ----------
mkdir -p ~/archive/2026-09 ~/inbox                    # only mkdir in the preview
LOG=~/archive/2026-09/declutter-log-A.txt

# GUARD 1 — nothing runs the 27 heartbeat scripts
crontab -l | grep -E 'ceo_|eng_|sec_|sysadmin_|comment_vre33' || echo "GUARD1a OK: no crontab ref"
systemctl --user list-units --all --no-pager | grep -Ei 'ceo|heartbeat|paperclip' || echo "GUARD1b OK: no unit"
rg -l -e 'ceo_hb' -e 'eng_heartbeat' -e 'sec_hb' -e 'sysadmin_check' -e 'comment_vre33' \
   ~/.config/systemd/user ~/bin ~/.bashrc ~/.bash_aliases ~/.profile 2>/dev/null || echo "GUARD1c OK: no refs"
# GUARD 2 — no Paperclip container
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i paperclip || echo "GUARD2 OK: no paperclip container"
# GUARD 3 — sizes of every delete target
du -sh ~/download.html ~/.claude.json.tmp.88913.285fa708c393 ~/.xsession-errors.old \
       ~/.npmrc.bak-20260723-151334 ~/.bashrc.bak.1787602002 ~/.bashrc.bak-cco-rollout \
       ~/.bashrc.bak-cco-wrapper-update ~/.config/systemd/user/honcho.service.bak.20260706-163907
ls -la ~/ceo_hb*.py ~/ceo_test_comment.py ~/eng_*.py ~/sec_*.py ~/sysadmin_*.py ~/comment_vre33.txt | wc -l   # expect 28

# ---------- APPLY (only after §3 harvest of the 4 representative scripts) ----------
rm -f ~/ceo_hb.py ~/ceo_hb{2,3,4,5,6,7}.py ~/ceo_test_comment.py
rm -f ~/eng_check.py ~/eng_check2.py ~/eng_dep.py ~/eng_details.py ~/eng_heartbeat.py ~/eng_heartbeat2.py
rm -f ~/sec_check{2,3,4,5,6,7}.py ~/sec_hb.py ~/sec_proactive.py
rm -f ~/sysadmin_check.py ~/sysadmin_comments.py ~/sysadmin_unassigned.py \
      ~/sysadmin_v113.py ~/sysadmin_v48.py ~/sysadmin_v48b.py
rm -f ~/comment_vre33.txt ~/download.html ~/.claude.json.tmp.88913.285fa708c393 \
      ~/.xsession-errors.old ~/.npmrc.bak-20260723-151334 \
      ~/.bashrc.bak.1787602002 ~/.bashrc.bak-cco-rollout ~/.bashrc.bak-cco-wrapper-update \
      ~/.config/systemd/user/honcho.service.bak.20260706-163907
```
Reclaimed: ~150K. **This phase is deliberately tiny** — on a corporate box the delete allowlist is
narrow and everything of size is OWNER-DECIDES. Rollback: **none for `rm`** — hence the guards.
Agents/tokens: 1 worker, ~15k.

### Phase B — commit/push FINISH items

```bash
# ---------- PREVIEW ----------
for r in ~/skills ~/cloudflare ~/ai-dev.infinox.io ~/ai-mvp.infinox.io ~/buzz.ixfin.tech \
         ~/agents/agent-librarian ~/agents/agent-multica ~/retired-multica-config; do
  echo "=== $r"; git -C "$r" status -sb; git -C "$r" diff --stat
  git -C "$r" status --porcelain | grep -Ei '\.env|\.key|\.crt|token|\.db|\.sql\.gz|backup' \
    && echo "!!! SECRET-GUARD HIT — do not add these paths"
done
# ---------- APPLY (per repo, individually reviewed) ----------
git -C "$r" add <explicit paths>            # NEVER add -A in a corporate repo
git -C "$r" commit -m "chore: land in-flight work before 2026-09 declutter"
git -C "$r" push
```
- **No `Co-Authored-By` trailer** unless that repo's `.claude/settings.json` sets `attribution.commit`.
- **Secrets guard:** never stage `.env*`, `*.key`, `*.crt`, tokens, `*.db`, backup archives. `git status` before **every** `add`.
- **Not committed:** `cloudflare-os` (17 dirty — upstream `cloudflare/cloudflare-os` fork, dirt is local run artifacts → discard, §5.6); `claw-services/honcho` (5 dirty — upstream fork → discard); `.hermes/hermes-agent` (1 dirty — upstream fork → discard); `deskpro` (4 dirty — **blocked on the identity question, §5.8**); `retired-paperclip` (15 dirty + 2 stashes → **harvested as patches, never committed**).
- **`fde-wrg` (104 unpushed) is a separate, explicitly owner-gated step (§5.7).** It runs alone, last, with `git -C ~/fde-wrg log --oneline origin/main..HEAD | head -40` reviewed first. Never `--force`, never touch the remote or `user.email`.
Rollback: everything is a commit. Agents/tokens: 1 worker, ~40k.

### Phase C — harvest + archive moves

```bash
mkdir -p ~/archive/2026-09/{paperclip,multica,infra,backups}
# ---------- 1. HARVEST.md written FIRST in each dir to be moved (§1 template, §3 sources) ----------
# ---------- 2. PREVIEW every move ----------
for d in ~/retired-paperclip ~/retired-multica-config ~/multica_workspaces ~/.agentmemory \
         ~/.agents ~/.iii ~/.lobster ~/claw ~/claw-logs ~/.claude-archive ~/.honcho \
         ~/cloudflare-os-starter-upstream ~/claude-skills ~/install.sh ~/bootstrap-debian.sh; do
  echo "MOVE $d"; ls -d "$d" && test -f "$d/HARVEST.md" && echo "  HARVEST.md present" || echo "  !! no HARVEST.md"
done
# ---------- 3. GUARD: nothing running maps to any of these (scout c Table 1 cross-check) ----------
docker ps -q | xargs -r docker inspect --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}' \
  | grep -Ei 'retired-paperclip|multica_workspaces|claw-logs|/home/vr/claw($| )|\.honcho|claude-skills' \
  || echo "GUARD OK: no container maps to a move target"
systemctl --user list-units --all --no-pager | grep -Ei 'paperclip|lobster|agentmemory' || echo "GUARD OK: no unit"
# ---------- 4. APPLY (mv only, never cp+rm) ----------
mv ~/retired-paperclip           ~/archive/2026-09/paperclip/
mv ~/.agentmemory                ~/archive/2026-09/paperclip/
mv ~/retired-multica-config      ~/archive/2026-09/multica/       # AFTER its 2 commits are pushed (Phase B)
mv ~/multica_workspaces          ~/archive/2026-09/multica/
mv ~/multica-backup-2026-07-07-pre-upgrade.sql.gz ~/archive/2026-09/multica/
mv ~/.agents ~/.iii ~/.lobster ~/claw ~/claw-logs ~/.claude-archive ~/.honcho \
   ~/cloudflare-os-starter-upstream ~/claude-skills ~/install.sh ~/bootstrap-debian.sh \
                                 ~/archive/2026-09/infra/
```

**`~/.paperclip` (809M) — disable-before-move, only on §5.5 approval:**
```bash
crontab -l > ~/archive/2026-09/crontab.bak-2026-09-10                    # DISABLE STEP (preview)
crontab -l | grep '.paperclip/instances'                                  # confirm the one line
crontab -l | grep -v '.paperclip/instances' | crontab -                   # DISABLE STEP (apply)
crontab -l | grep -c '.paperclip' && echo "!! still referenced" || echo "OK"
mv ~/.paperclip ~/archive/2026-09/paperclip/                              # only after the above
```
**Rule-1.5 note on this cron line:** it **serves no hostname and no port** — it is a local
backup-prune (`find … -name "paperclip-*.sql" -mtime +7 -delete`) against a directory whose
service is already gone. Removing it cannot degrade any hostname in the §0 baseline; the other
three crontab entries (`sync-hermes-token.sh`, `backup-buzz.sh`, the weekly reconcile) are untouched.

**Honcho (`~/claw-services/honcho`) — disable-before-move, ONLY on §5.1 = yes:**
```bash
curl -s -o /dev/null -w '%{http_code}\n' https://ix-claude1.dala-wage.ts.net:3000/   # BEFORE
systemctl --user disable --now honcho.service                                        # DISABLE STEP 1
docker compose -f ~/claw-services/honcho/docker-compose.yml down                     # DISABLE STEP 2 (NO -v)
docker volume ls --format '{{.Name}}' | grep honcho    # must still print all 4 — volumes are KEPT
mv ~/.config/systemd/user/honcho.service ~/archive/2026-09/infra/systemd-units/
systemctl --user daemon-reload
mv ~/claw-services/honcho ~/archive/2026-09/infra/                                   # MOVE (last)
```
**Never touched in Phase C:** `wikijs`, `multica.ixfin.tech`, `buzz.ixfin.tech`, `claude-code-proxy`,
`uptime-kuma`, `cloudflare-os`, `Obsidian`, `Sync`, `.omnigent`, `bin`, `.multica`,
`multica_workspaces_ixfin`, `cfos-backups`, `.hermes`, `.local`, `.config` (§6 DO-NOT-DISABLE).
Rollback: `mv` back — the target path is in the phase log. Agents/tokens: 1 worker, ~60k.

### Phase D — `~/.claude` hygiene

```bash
# ---------- PREVIEW ----------
# settings.json is CHEZMOI-MANAGED. Establish HOW before touching it.
chezmoi managed | grep -x '.claude/settings.json'          # expect: .claude/settings.json
chezmoi source-path ~/.claude/settings.json                # expect: .../dot_claude/modify_settings.json
head -1 "$(chezmoi source-path ~/.claude/settings.json)"   # expect: {{- /* chezmoi:modify-template */ -}}
#   -> a MODIFY template: it rewrites only permissions/hooks/env/enabledPlugins/
#      extraKnownMarketplaces and prints every other key back untouched. An unmanaged
#      top-level key such as cleanupPeriodDays therefore SURVIVES `chezmoi apply`.
#      If head -1 does NOT show chezmoi:modify-template, STOP: do not edit the file;
#      route "set cleanupPeriodDays=90 after Wave 5.1" to ~/inbox/PENDING-2026-09.md instead.
chezmoi diff ~/.claude/settings.json > ~/archive/2026-09/chezmoi-diff-settings.BEFORE.txt
grep -c cleanupPeriodDays ~/archive/2026-09/chezmoi-diff-settings.BEFORE.txt   # expect 0
#   NOTE: this diff is NOT empty on ix and is not expected to be. The template's own header
#   documents a one-off alphabetical re-ordering diff with no semantic change on first apply
#   per node. The ONLY thing that matters here is that cleanupPeriodDays never appears in it.

cp ~/.claude/settings.json ~/archive/2026-09/settings.json.bak-2026-09-10   # BACKUP FIRST
jq '.cleanupPeriodDays' ~/.claude/settings.json                              # expect null
ls -d ~/.claude/projects/-home-vr-ai-infinox-io ~/.claude/projects/-home-vr-multica-workspaces \
      ~/.claude/projects/-home-vr-cloudflare ~/.claude/projects/-home-vr-ito-ixfin-tech
ls ~/.claude/projects | grep -c 'multica-workspaces-ixfin'                   # expect 67
find ~/.claude/session-env ~/.claude/tasks -type d -empty 2>/dev/null | wc -l
# HARVEST GATE — must be true before any rm below:
test -s ~/archive/2026-09/multica/HARVEST.md && \
  ls ~/archive/2026-09/harvested-memory/ && echo "HARVEST VERIFIED" || echo "STOP — harvest incomplete"

# ---------- APPLY ----------
jq '.cleanupPeriodDays = 90' ~/.claude/settings.json > /tmp/s.json && mv /tmp/s.json ~/.claude/settings.json
# PROOF the chezmoi modify-template preserves the new key (never run `chezmoi apply` to test):
chezmoi diff ~/.claude/settings.json > ~/archive/2026-09/chezmoi-diff-settings.AFTER.txt
if grep -q '^-.*cleanupPeriodDays' ~/archive/2026-09/chezmoi-diff-settings.AFTER.txt; then
  echo "FAIL: chezmoi would strip cleanupPeriodDays — reverting"
  cp ~/archive/2026-09/settings.json.bak-2026-09-10 ~/.claude/settings.json
  echo "- cleanupPeriodDays=90 DEFERRED: chezmoi modify-template would strip it; set after Wave 5.1" \
    >> ~/inbox/PENDING-2026-09.md
else
  echo "OK: cleanupPeriodDays=90 survives chezmoi (absent from the pending diff)"
fi
rm -rf ~/.claude/projects/-home-vr-ai-infinox-io                 # orphan, 0 memory files
rm -rf ~/.claude/projects/-home-vr-multica-workspaces            # orphan + memory-only, HARVESTED
rm -rf ~/.claude/projects/-home-vr-cloudflare                    # memory-only, HARVESTED
rm -rf ~/.claude/projects/-home-vr-ito-ixfin-tech                # memory-only, HARVESTED
find ~/.claude/session-env ~/.claude/tasks -type d -empty -delete
# NOT deleted: -home-vr-Obsidian-claude-ix-Claude and -home-vr-Sync-...-VRExecutiveOperations
#   (memory-only but decoded paths are LIVE and unit-bound)
# NOT deleted: the 67 multica_workspaces_ixfin dirs — they age out under cleanupPeriodDays=90 (§5.9)
# NOT touched: plugins/ (25M cache), settings.json.doctor-bak, journal/, sessions/, teams/
```
**`cleanupPeriodDays = 90`** — the fleet-wide owner choice of 2026-09-10. `memory/` is exempt from
the sweep, so curated knowledge is never at risk; 90 also disposes of the 67-dir Multica workspace
cluster (24M) without a hand-delete. Rollback: transcript deletes are **irreversible** → the harvest
gate above is mandatory; the settings key is trivially revertible from the backup.
Agents/tokens: 1 worker, ~25k.

### Phase E — fixes

```bash
# 1. Memory corrections — APPEND-ONLY, dated. Never rewrite a line.
#    Append to each of the 3 MEMORY.md files (§2.7 claims 1–6):
cat >> ~/.claude/projects/-home-vr-Obsidian-claude-ix-Claude/memory/MEMORY.md <<'EOF'

<!-- correction 2026-09-10 (declutter pass) -->
- CORRECTION 2026-09-10: Paperclip is retired fleet-wide (vr-oc1 2026-09-10). No Paperclip
  container runs on ix-claude1 as of 2026-09-10 (19 containers, none Paperclip). The
  feedback_paperclip_agents / project_ix_production_status / project_paperclip_integration
  entries above describe a system that is no longer running here. NOTE: ix-readai-webhook.env
  still sets PAPERCLIP_API_URL=http://localhost:3100 — that backend is dead; see ~/inbox.
EOF
# (analogous dated blocks for -home-vr-Sync-...-VRExecutiveOperations and, if not deleted in D,
#  -home-vr-multica-workspaces; the Multica correction states multica.ixfin.tech is LIVE on ix.)

# 2. Cert relocation — ONLY on §5.3 approval. Never delete, never print contents.
rg -l 'dala-wage.ts.net.(crt|key)' ~/.config ~/bin ~/wikijs ~/buzz.ixfin.tech \
     ~/claude-code-proxy ~/multica.ixfin.tech 2>/dev/null || echo "GUARD OK: 0 references"  # PREVIEW
mkdir -p ~/.local/share/tailscale-certs
mv ~/ix-claude1.dala-wage.ts.net.crt ~/ix-claude1.dala-wage.ts.net.key ~/.local/share/tailscale-certs/
chmod 600 ~/.local/share/tailscale-certs/ix-claude1.dala-wage.ts.net.key
chmod 644 ~/.local/share/tailscale-certs/ix-claude1.dala-wage.ts.net.crt

# 3. inbox README + PENDING
cat > ~/inbox/README.md <<'EOF'
This directory is the ACTION location. ~/archive/ is terminal — nothing there is ever read again.
Anything that still needs a human decision or a follow-up goes here, never into archive.
RULE: this directory must be EMPTY by the 2026-12 quarterly pass.
EOF
# ~/inbox/PENDING-2026-09.md gets: cert expiry 2026-10-09; honcho-database 0.0.0.0:15432;
#   3 dangling tailscale serve entries; wiki-tunnel<->claude-code-proxy manual network attach;
#   ix-readai-webhook PAPERCLIP_API_URL dead backend; ~/tools .bashrc template line (post-Wave-5.1);
#   stray ~/ix-readai-webhook.service home-root copy; deskpro identity; every deferred §5 item.

# 4. INFO rows — NO ACTION, recorded only: claude-on-PATH (§2.8), ~/tools (§2.8).
#    .bashrc is chezmoi-managed — DO NOT EDIT IT.
```
**Cert expiry is an inbox item, not a fix**: the cert expires **2026-10-09 (~29 days)**. Tailscale
does **not** auto-renew file-based certs written by `tailscale cert` — someone must re-run
`tailscale cert ix-claude1.dala-wage.ts.net`. Nothing on the host currently reads these files
(0 references), so the *expiry itself* may be harmless — but that unknown is exactly why it goes
to `~/inbox` and not to a script. Agents/tokens: 1 worker, ~30k.

### Phase F — hand to VR (sudo)

No passwordless sudo on ix; `/etc/systemd/system` could not be enumerated (scout c Table 3).
**Exactly one read-only hand-off line.** Nothing in this plan requires root to execute.

```bash
sudo bash -c 'echo "== units referencing /home/vr =="; grep -rl "/home/vr" /etc/systemd/system 2>/dev/null; \
echo "== vr/cloudflare/readai system units =="; systemctl list-units --type=service --all --no-pager | grep -i -E "cloudflare|readai|vr|honcho|multica"; \
echo "== cfos-backup =="; systemctl cat cfos-backup.service cfos-backup.timer 2>&1 | head -20; \
echo "== 0.0.0.0 listeners =="; ss -ltnp | grep "0.0.0.0"'
```
**Read-only only** — no `systemctl disable`, no `daemon-reload`, no writes. Paste the output into
`~/inbox/PENDING-2026-09.md`. Rationale: scout c found `ix-readai-webhook.service` as a **USER**
unit (`~/.config/systemd/user/`), and a comment in `ai-dev-blueprints-backup.service` references a
`cfos-backup.service`/`.timer` that `systemctl cat` says does not exist — both need a system-level
confirmation before the 2026-12 pass. Also settles the `0.0.0.0:15432` and `0.0.0.0:*` listeners.

### Executed-state verifier checklist

1. **`curl -s -o /dev/null -w '%{http_code}'` every hostname in the §0 baseline table, BEFORE and AFTER any unit change**: `wiki.ixfin.tech` (302), `multica.ixfin.tech` (302), `ix-buzz.dala-wage.ts.net` (200), `ix-claude1.dala-wage.ts.net` (404), `ai-dev.infinox.io` (302), `buzz.ixfin.tech` (000). **Any degradation = ISSUES FOUND.** Plus the tailnet-only `https://ix-claude1.dala-wage.ts.net:3000` if §5.1 was answered either way.
2. `systemctl --user --failed` → **0 units** (baseline: 0). `systemctl --user list-units --all` → no new failed unit.
3. `docker ps -q | wc -l` → **19**, or **14** if §5.1 approved the honcho stop. Container name set identical to the §0 list except the 5 approved honcho removals. `docker volume ls | grep honcho` → **still 4** (volumes kept).
4. Paths that must EXIST: `~/inbox/README.md`, `~/inbox/PENDING-2026-09.md`, `~/archive/2026-09/declutter-log-{A,B,C,D,E}.txt`, `~/archive/2026-09/settings.json.bak-2026-09-10`, a `HARVEST.md` inside every moved dir, all 4 honcho volumes.
5. Paths that must NOT exist: the 27 heartbeat scripts, `~/comment_vre33.txt`, `~/download.html`, the 3 `.bashrc.bak*`, `~/.npmrc.bak-*`, `~/.xsession-errors.old`, `~/.claude.json.tmp.*`, the 4 deleted project dirs.
6. `jq '.cleanupPeriodDays' ~/.claude/settings.json` → **90** — **and** `chezmoi diff ~/.claude/settings.json | grep '^-.*cleanupPeriodDays'` → **no output** (proves the chezmoi modify-template preserves the key and no `chezmoi apply` will strip it). Both `~/archive/2026-09/chezmoi-diff-settings.{BEFORE,AFTER}.txt` must exist. If the key was deferred instead, `jq` returns `null` **and** `~/inbox/PENDING-2026-09.md` must carry the deferral line — no third outcome is acceptable. `~/.local/share/chezmoi` must be byte-identical to its pre-run state (`git -C ~/.local/share/chezmoi status --porcelain` → empty): this plan never edits chezmoi source.
7. No repo left dirty that Phase B was supposed to commit: re-run the Phase B preview loop; every listed repo → clean or explicitly excluded above.
8. `crontab -l` → 3 entries if §5.5 approved (`.paperclip` line gone), else 4; `~/bin/sync-hermes-token.sh`, `backup-buzz.sh` and the weekly reconcile line **must survive** either way.
9. `git -C ~/fde-wrg log --branches --not --remotes --oneline | wc -l` → **0** if §5.7 approved, **104** if not. No other value is acceptable.

---

## 5. Owner decisions needed

Each is a yes/no or A/B. **Recommended default in bold.** Every unit/tunnel/container touched carries
its full hostname list with a per-hostname OK slot (rule 1.5).

**5.1 — Unwire Honcho on ix-claude1 (stop 5 containers + disable `honcho.service`, keep all 4 volumes, archive the dir)? y/n**
Recommended default: **NO — leave it LIVE this pass, and instead rebind `honcho-database-1` off `0.0.0.0:15432`.**
Consumers enumerated: **none at runtime** (§0). Public hostnames served: **NONE**. Tailnet-only surface: `https://ix-claude1.dala-wage.ts.net:3000` → `127.0.0.1:3000`. Volumes kept: `honcho_venv`, `honcho_pgdata`, `honcho_prometheus-data`, `honcho_grafana-honcho-data`.
Risk of YES: low but non-zero — `~/.hermes/hermes-agent` ships a honcho memory plugin, and the fleet-wide retirement was decided *for vr-oc1's instance*; ix's is a separate deployment nobody has audited for corporate use. Risk of NO: 5 idle containers keep running and `:15432` stays world-open.
Per-hostname OK: `ix-claude1.dala-wage.ts.net:3000` (tailnet) → OK? ☐   `:15432` rebind → OK? ☐

**5.2 — `buzz.ixfin.tech` returns HTTP 000. Is that hostname retired (A) or broken and needing a fix (B)?**
Recommended default: **A — retired, superseded by `ix-buzz.dala-wage.ts.net` (200).** Do not touch the 5 `buzz-prod-*` containers either way; the compose `edge` cloudflared profile is not started (`BUZZ_TUNNEL_TOKEN` unset). Risk: if B, a corporate hostname is silently down and this declutter would record it as intentional.
Per-hostname OK: `buzz.ixfin.tech` (currently 000) → OK to record as retired? ☐   `ix-buzz.dala-wage.ts.net` (200, must stay 200) → ☐

**5.3 — Relocate `ix-claude1.dala-wage.ts.net.crt/.key` from `~` to `~/.local/share/tailscale-certs/`? y/n**
Recommended default: **YES.** Verified **0 references** to the current path across `~/.config`, `~/bin`, and all four live compose dirs. *Footnote (widened re-scan, 2026-09-10):* two incidental string hits exist outside live config — `~/recovery-staging/recover/manifest/journal-strings.txt` (2 hits; a forensic filesystem-journal string dump, not a config file) and `~/agents/agent-sysadmin/sysadmin/memory/BACKLOG.md` (a prose backlog note). **Neither is read by any service; neither blocks the relocation.** Risk: near-zero; the `.key` is already 600. **Never delete, never print.** Separately: the cert **expires 2026-10-09 (~29 days)** and file-based Tailscale certs do not auto-renew → `~/inbox` item regardless of the answer.

**5.4 — Backup dirs, one fate each (KEEP in place / → `archive/2026-09/backups/` / PRUNE to newest 1):**
`cfos-backups` (12M) → **KEEP-LIVE, do not move** (written daily by `ai-dev-blueprints-backup.timer`). `metabase-backups` (34M) → **KEEP**. `cloudflare-os-backups` (17M) → **KEEP**. `cfos-restore-kit` (3.4M) → **KEEP** (corporate restore path). `Backups` (51M, 17d) → **KEEP**. `backup` (12K) → **identify, then delete**. `archives` (1.3G, 66d) → **KEEP, scheduled eyeball 2026-12** (largest; never bulk-delete). `paperclip-backups` (177M, 155d) → **PRUNE to newest 1** (Paperclip retired). `recovery-staging` (44M) → **identify**. `multica-backup-2026-07-07-pre-upgrade.sql.gz` (3.1M) → **→ archive/multica/, keep** (insurance for a still-live service). Risk of any delete here: corporate data loss with no second copy.

**5.5 — `~/.paperclip` (809M): remove the daily crontab line and archive the dir? y/n**
Recommended default: **YES.** No Paperclip container runs; the only thing keeping the dir warm is a cron job pruning its own backups. **That cron line serves no hostname and no port — it is a local backup-prune only**, so removing it cannot degrade anything in the §0 HTTP baseline. Crontab is backed up to `~/archive/2026-09/crontab.bak-2026-09-10` first. Risk: it holds `.env` files — archived, never staged, never printed; if anything corporate still calls `localhost:3100` this makes that failure visible (it is already dead).

**5.6 — Dirty upstream forks: discard the dirt in `cloudflare-os` (17), `claw-services/honcho` (5), `.hermes/hermes-agent` (1)? y/n. And push `retired-multica-config`'s 2 unpushed commits before archiving? y/n**
Recommended default: **discard the fork dirt = YES** (local run artifacts in vendored upstreams; committing them to an upstream fork is worse than losing them) / **push retired-multica-config = YES** (precedent: push before archive; 2 commits, UC-VR remote, low risk).

**5.7 — Push `fde-wrg`'s 104 unpushed commits to `InfinoxMngmt/fde-ix-wrg`? y/n**
Recommended default: **YES, as an isolated, reviewed step** — review `git log --oneline origin/main..HEAD` first, `git push` only, **never `--force`, never rewrite the `github.com-ix` remote or `vr-ixfin@users.noreply.github.com` identity.** Risk of YES: 104 commits land on a corporate repo in one push — if any carry secrets or half-work, that is now public to the org. Risk of NO: 104 commits (336M repo, touched today) live on one laptop with no second copy.

**5.8 — `deskpro` uses `vadim.r00@gmail.com` while every other repo uses `github@uc.email`. Change it (A) or leave and flag (B)?**
Recommended default: **B — leave and flag.** Its 4 dirty files stay uncommitted until this is answered. Risk of A: rewriting identity on a corporate repo is out of scope for a declutter and may break org attribution rules.

**5.9 — The 67-dir `multica_workspaces_ixfin` project cluster (24M): hand-delete now (A) or let `cleanupPeriodDays=90` age them out (B)?**
Recommended default: **B — age out.** They are not orphans (base dir exists), hold 0 memory files, and Multica is **live** on ix — a workspace could still be resumed. Risk of A: deleting the transcript of a live corporate workspace run. Risk of B: 24M lingers up to 90 days.

**5.10 — Big-dir eyeballs (each: prune / keep / defer):**
`.cache` 5.8G → **PRUNE, likely safe** — it is by definition regenerable; the only thing in it worth protecting is `.cache/chezmoi-status` (a `UC-VR/dotfiles` checkout), so any prune must exclude that path. `.vscode-server` 4.0G → **PRUNE, likely safe** — VS Code Server re-downloads its server + extensions on next connect; nothing else reads it (untouched since 2026-07-19). `Sync` 8.0G → **DEFER, do not touch** — QuoteStream's compose dir and the `ix-tl@` agent-runner live inside it. `.hermes` 7.7G → **DEFER** — `sync-hermes-token.sh` runs every 6h from crontab; model/data cache, needs a look not a script. `.antigravity-server` + `.antigravity-ide-server` 761M → **OWNER-DECIDES** (the `-server` half untouched 155d; likely a dead IDE remote pair). `Obsidian` 4.4G / 9 vaults → **DEFER to 2026-12** — two vaults are unit-bound.

**5.11 — Run the Phase F read-only `sudo bash -c '...'` enumeration line? y/n**
Recommended default: **YES.** It is strictly read-only (`grep -rl`, `systemctl list-units`, `systemctl cat`, `ss -ltnp`) and is the only way to close the `/etc/systemd/system` gap, confirm whether `cfos-backup.service`/`.timer` exists, and identify the `0.0.0.0` listeners. Risk: none beyond VR pasting one line.

---

## 6. Rules going forward

Rules 1–12 of the vr-oc1 plan §6 carry over verbatim. ix-specific additions:

**Rule 1.5 — DO-NOT-DISABLE list for ix-claude1.** Never stopped, disabled, moved or recreated in any declutter pass without a per-hostname owner OK:

| Never touch | Because it serves |
|---|---|
| `wiki-tunnel` (docker, `~/wikijs`) | `wiki.ixfin.tech`, `multica.ixfin.tech`, **and a CF-Access-gated `claude-code-proxy` hostname**. It is **token-based** — ingress lives in the Cloudflare Zero Trust dashboard and **cannot be enumerated locally** (no `cloudflared` binary on host, no `~/.cloudflared/`, no shell in the image). You therefore **cannot prove what it serves before stopping it** — which is precisely the vr-oc1 outage failure mode. **Treat as untouchable.** |
| `cloudflare-os.service` | the **public Tailscale Funnel** target `https://ix-claude1.dala-wage.ts.net` → `localhost:3003` |
| `ix-readai-webhook.service` (**USER** unit, `~/.config/systemd/user/`) | corporate Read.ai → Obsidian pipeline |
| `multica-daemon.service` | live corporate Multica `ixfin` profile |
| Tailscale Funnel + serve (`ix-claude1.dala-wage.ts.net`, `ix-buzz.dala-wage.ts.net`) | host-level ingress for cloudflare-os and the buzz relay |
| `buzz-prod-tailscale-1` | `ix-buzz.dala-wage.ts.net` (200) |
| the 13 `ix-tl@*` timers | corporate agent schedule, WorkingDirectory in `~/Obsidian` and `~/Sync` |

**Rule 13 — write `~/claw-services/SERVICES.md` on ix** (the vr-oc1 precedent registry). One row per unit/container: name → compose dir → every hostname/port served → tunnel mechanism → DO-NOT-DISABLE flag. It must record the two facts SSH cannot re-derive: (a) `wiki-tunnel` is token-based, so its ingress is dashboard-only; (b) `wiki-tunnel` is attached to `claude-code-proxy_default` by a manual `docker network connect` that is **not in any compose file and is lost on `--force-recreate`**.

**Rule 14 — corporate default.** On ix, anything matching `*.infinox.io`, `*.ixfin.tech`, `*.infinox.com`, or a corporate git remote is **OWNER-DECIDES or KEEP-LIVE by default, never RUBBISH-DELETE**, and never batch-anything.

**Rule 15 — Multica is not fleet-uniform.** vr-oc1's Multica was retired; **ix's is live corporate production.** Never apply a fleet-wide retirement to a per-host deployment without re-deriving that host's state. The same caution now applies to Honcho (§5.1).

---

## 7. Sessions: resume / abandon

Staging destination: `~/inbox/sessions-for-omnigent/` on ix, `MANIFEST.md` in the vr-oc1 format (§1).
**Copies, not moves** — originals age out under `cleanupPeriodDays=90`.

### (a) Stage to `~/inbox/sessions-for-omnigent/` — recent, large, real projects

| project dir | jsonl | size | last | why stage |
|---|---|---|---|---|
| `-home-vr-fde-wrg` | 3 | 93M | 2026-09-10 | largest, touched today, and the repo with 104 unpushed commits — the §5.7 decision needs this context |
| `-home-vr-ai-dev-infinox-io` | 16 | 70M | 2026-09-09 | most-worked corporate project, **10 memory files** |
| `-home-vr-cf-builder` | 6 | 48M | 2026-09-10 | active, 1d old |
| `-home-vr-cfos-ixfin-tech` | 12 | 46M | 2026-09-09 | active corporate |
| `-home-vr-agents-agent-sysadmin` | 12 | 45M | 2026-09-09 | fleet agent, active |
| `-home-vr` (host home) | 22 | 45M | 2026-09-10 | host-level thread incl. this declutter; 8 memory files, **no stale claims** |
| `-home-vr-ai-mvp-infinox-io` | 2 | 23M | 2026-09-09 | 3 unpushed commits ride on it |

### (b) Abandon / let age out

| project dir | verdict |
|---|---|
| **the 67-dir `multica_workspaces_ixfin` cluster** | **ABANDON as one line** — ephemeral per-workspace Multica agent runs, 1 jsonl each, ≈24M total, 0 memory files, 0 `session_*`. Never resumed by a human. Age out under `cleanupPeriodDays=90` (§5.9). |
| `-home-vr-ai-infinox-io` (1 jsonl, 8K) | ABANDON — orphan, deleted in Phase D |
| `-home-vr-multica-workspaces` (0 jsonl, 2 memory) | ABANDON the dir; **harvest the 2 memory files** (§3) |
| `-home-vr-buzz` (1 jsonl, 2.4M, 29d) | ABANDON — one-shot; the buzz question is answered by §5.2, not by replaying it |
| `-home-vr-corma` (3 jsonl, 28M, 29d) | ABANDON — idle 29d, no next step recorded |
| `-home-vr-deskpro` (7 jsonl, 43M, 17d) | ABANDON — blocked on the §5.8 identity question, not on a thread |
| `-home-vr-cloudflare-os` / `-claude-code-proxy` / `--local-share-chezmoi` (1 jsonl each) | ABANDON — one-shots; chezmoi work is frozen behind Wave 5.1 anyway |
| `-home-vr-cfos-ixfin-tech-builder` (2, 12M) | ABANDON — superseded by the parent `cfos.ixfin.tech` thread |
| `-home-vr-fde-wrg-public`, `-home-vr-ito-ixfin-tech`, `-home-vr-cloudflare`, `-home-vr-Obsidian-claude-ix-Claude`, `-home-vr-Sync-...-VRExecutiveOperations` | 0 jsonl — nothing to stage; memory handled in §2.7/§3 |

### (c) Session hygiene rule (carried from vr-oc1 §7c)
1. Subagent fan-out transcripts are noise by construction — never harvest, never resume; the parent's handover is the record.
2. The unit of memory is a HANDOVER or a HARVEST.md, not a transcript.
3. 10-second resumable test: **turns ≥8** AND **the last assistant line names a next step or an open question**. Fails either → dead; close it or let it age out.
