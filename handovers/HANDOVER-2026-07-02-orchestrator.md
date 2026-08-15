# Handover: orchestrator (Fable) session, 2026-07-02

## Session Info

- **Agent:** orchestrator (Fable)
- **Date:** 2026-07-02
- **User:** VR
- **Purpose:** resume point — context nearly full.

## Completed Today (verified)

### agent-orchestrator repo
GitHub `uc-vr/agent-orchestrator`, all pushed:

- `dfee330` + `476a604` — plugin load fixes
- `ec87555` — model-tiering hard rule (fable=orchestrator only, every spawn explicit model, opus=reasoning, sonnet=execution, no haiku)
- `0590c17` — shipwright evidence disciplines in worker.md
- `5bb103c` — learning-loop v2 port = plugin v1.3.0 (SessionStart removed, gated detached SessionEnd capture, reconcile-learnings v2 w/ patch-over-create)
- doc-only commit re bypassPermissions necessity (empirically proven: sensitive-path guard beats scoped allow rules)
- `78dd7ae` — dispatch tie-in routing setup requests to librarian
- `50c3000` — hook/journal fix

Global `~/.claude/settings.json` hooks={} — plugin is sole hook source. Weekly schtasks `claude-weekly-reconcile` Sun 09:00. Global `LEARNINGS.md` at `~/.claude/journal/` (has first real block).

### agent-librarian repo
`C:/Users/vr/agents/agent-librarian`, LOCAL git only, 11 commits, user pushes later:

- Plugin `agent-librarian@uc-vr-agents` v0.1.0 installed
- `/librarian` command + spawnable opus agent
- Step 0 location-aware misroute correction (prescription field 0 = OK|REDIRECT)
- Modes: Consultant / Inventory / Acquisitions (only networked mode, appends to `catalog/EXTERNAL.md`) / Curator
- `catalog/SOURCES.md`
- `DECISION_MATRIX.md` final commit **GATED** on skills consolidation rename pass

### agent-keth repo
`C:/Users/vr/agents/agent-keth`, LOCAL git, 3 commits, user pushes later:

- Alena's PA
- insurance-ethniki matter in `keth/matters/` (TODOs: confirm Eurolife successor policy w/ HR; confirm Mar-2026 claim submitted)
- audit clean

### openclaw-personal purge
DONE + verified:

- Redaction commit `4c78934`
- `filter-repo` removed 8 files / 6 values
- All branches force-pushed
- Fresh-clone zero hits
- Caveat: `refs/pull/1/head` retains old blobs until GitHub GC
- Rotation checklist (7 items, `CLAUDE_CODE_OAUTH_TOKEN` top priority) in `agent-sysadmin/sysadmin/memory/BACKLOG.md` — **USER ACTION PENDING**
- User will archive repo after migration
- Salvage: memory archive at `agents/_archive/openclaw-main-memory/`; sysadmin `TOOLS.md` created; skillrouter/oc-global closed (scrap/ignore)

### External adopts
14 installed user-scope:

- document-skills docx/pdf/xlsx (via anthropic-agent-skills marketplace)
- ralph-loop
- hookify
- claude-md-management
- plugin-dev
- mcp-server-dev
- mcp-builder copy (manifest says delete-defer)
- dotjez
- brainstrust (manifest says drop later)
- obsidian trio + invoice-organizer + web-to-markdown (via davila7)

## Skills Consolidation (in flight)

Repo `C:/Users/vr/agents/skills`, branch `consolidation/v2`.

### Phase 0 — done
Unshallowed, 115 commits, `docs/` found on `skill-system-review-2026-06` branch = user's valid prior work: overlap clusters, deskpro/session-extractor name-collision bug, ~330 keyword-damage warnings.

### Phase 1 — done, MANIFEST.md VERIFIED
Commits `8442293`, `2147858`, `d772f5d` §10, `20fa0ff` (stats fix); effective totals: 46 keep / 22 merge / 54 delete / 4 defer / 1 salvage / 1 investigate of 128 rows.

### USER-APPROVED verdicts (including)
- weather: delete
- lobster: delete
- ixbob: `_TEMPLATE` drop + `snapshot/ixbob` branch delete at cutover
- dotjez: `orchestrate-agents` + `agent-delegation` disable at cutover
- mcporter: keep
- mcp-builder vs mcp-server-dev: needs NOT-for disambiguation in Phase 3
- **GWS split-by-provenance:**
  - 19 `gws-*`/`recipe-*` = regen artifacts of `@googleworkspace/cli` (`gws generate-skills`) → version-pinned regen step, don't own
  - `managing-google-workspace` → install `taylorwilsdon/google_workspace_mcp` upstream plugin, delete local
  - `google-workspace-recipes` = user-authored → fold in but **SCRUB PII** (infinox email, spreadsheet IDs, op refs) to local overlay
- **Obsidian:** kepano plugin wins formats; repo keeps personal overlay (obsidian-memory absorbs obsidian-kb; scrub `~/clawd` paths)
- **reconcile-learnings** global copy delete GATED: plugin v2 copy is canonical survivor (already done — safe to delete local at cutover)
- **finance skill** stays baked in agent-bugalteris

### Phase 2 — EXECUTING (agent may have been stopped — CHECK)
- Marketplace `uc-vr-skills` scaffold, 9 plugins: finance, google-workspace, infra-network, obsidian, research-content, career-legal, comms-ops, agent-meta, dev-tools
- `git mv` keeps, merge sources → `plugins/*/_merge-staging/`
- Deletions (skill-manager Python scripts salvaged to `scripts/salvaged-skill-manager/` first)
- `validate.py` (`--strict` flag) + CI + symlink guard
- Resume = continue from last commit on `consolidation/v2`

### Remaining phases
- **Phase 3** — description rewrite fan-out (8 batches by plugin, style guide: what-it-does + "Use when:" user phrasings + NOT-for siblings, ≤500 chars, explicit triggers per The Method; honor the keyword-damage warning list in `docs/`)
- **Phase 4** — merges (per manifest merge-into rows + gws provenance plan)
- **Phase 5** — tooling (README/CONTRIBUTING w/ style guide, issue templates, `overlap-report.py`, B9 handover skill pair into agent-meta)
- **Phase 6** — cutover (install marketplace, delete 25 `~/.claude` locals + brainstrust plugin + disable dotjez pair, `snapshot/ixbob` branch delete, consumer audit of agent CLAUDE.mds for renamed skill refs, PR `consolidation/v2`→`main`, THEN librarian `DECISION_MATRIX.md` final commit w/ new names)
- **Phase 7** — multica maintenance loop (labels, 3 issue templates, monthly dedupe/description audits, quarterly staleness)

## Backlog (patterns to port)

| ID | Pattern |
|----|---------|
| B1 | mbruhler resumable `state.json` → orchestrator workflows |
| B2 | @-gate fallbacks |
| B3 | shipwright→worker.md — **DONE** |
| B4 | ccpm PRD→Epic→Task |
| B5 | no-LLM status scripts |
| B6 | worktree-per-epic |
| B7 | issue-ID-filename sync |
| B8 | semantic routing/flow DSL |
| B9 | `/handover-close` + `/handover-open` skill pair (research agent evaluating existing external implementations first — alirezarezvani handoff skill, mbruhler state persistence, ccpm context commands, native `--resume`) |

## Open User Decisions (parked)

- bugalteris `CLAUDE.md` self-authorization clause (flagged by 2 independent agents) — keep/tighten/remove.
- git push allowlist audit (force-push executed without permission prompt during purge).

## Decision Matrix v2 (staged content)

Staged content — commit to `agent-librarian/librarian/DECISION_MATRIX.md` **AFTER** consolidation renames. Draft below.

Columns: task shape / agents / skills / methodology (TDD\|ralph-loop\|plan-first\|deep-research\|scheduled-routine\|document-pipeline) / team depth (solo\|orch+workers\|full team\|scheduled headless) + cost note / model tier / verification.

| # | Task shape | → |
|---|-----------|---|
| 1 | research | → deep-research skill / solo / opus-lead |
| 2 | doc drafting | → document-pipeline / gws skills / verifier-before-external |
| 3 | cloud admin | → sysadmin\|network-engineer / plan-first / gate hooks |
| 4 | windows bugfix | → sysadmin / plan-first / dry-run |
| 5 | greenfield coding | → orchestrator+claude-automation-recommender sub-step / plan-first→TDD-or-ralph / multica task list |
| 6 | TDD build | → full team w/ verifier / TDD+ralph option |
| 7 | new domain agent | → vr-agent-creator/new-agent + folder-doctrine check first |
| 8 | recurring job | → schedule skill / scheduled-routine / haiku-sonnet body |
| 9 | finance | → bugalteris / verifier on money output |
| 10 | legal | → lawyer / document-pipeline / human review always |
| 11 | new skill | → skill-creator evals as TDD |
| 12 | gws ops | → google-workspace-recipes / sonnet |
| 13 | networking | → network-engineer / lockout-guard |
| 14 | fleet maintenance | → reconcile-learnings / scheduled monthly / PROPOSE-only |

(A fully expanded 7-column version of this matrix has been drafted separately as `agent-librarian/librarian/DECISION_MATRIX.draft.md`.)

## Resume Instructions (for next orchestrator session)

1. Read this file fully.
2. Check `agents/skills` `consolidation/v2` git log for Phase 2+ progress; verify with a verifier agent against `MANIFEST.md` before proceeding to next phase.
3. Model tiering hard rule applies (in orchestrator.md).
4. Wave pattern: each phase = commit + verifier gate + user checkpoint where destructive.
5. User's manual queue: key rotation, HR confirmations, GitHub pushes for agent-keth/agent-librarian, archive openclaw-personal.

## ADDENDUM — session close (this doc is now final)

### 1. Phase 2 status: COMPLETE and VERIFIED
- 6 commits, range `32837e5..3cf48c2`, pushed to `origin/consolidation/v2`.
- Result: 44 skills now live under `plugins/*/skills`, 21 still in `_merge-staging`.
- Validator is green, with 11 "Use when" warnings deferred to Phase 3. The 11 skills:
  - onepassword
  - nano-banana-pro
  - academic-deep-research
  - defuddle
  - cloudflare
  - coolify
  - mcporter
  - deskpro
  - portable-agent-builder
  - invoice-organizer
  - jules
- Verification note: the verifier agent initially counted only 10 of these, but reconciliation confirmed the producer's count of 11 was correct — the verifier had missed `jules`.
- Judgment calls accepted during this phase: frontmatter normalization (commit `3cf48c2`, provenance preserved as nested field), namespace README removals, and removal of a dangling `.agents/skills` symlink.

### 2. Phase 2 content follow-ups carried forward into Phase 3/Phase 4 (flagged by the producer agent, must not be lost)
- Confirm op-read keyword-damage risk on the `onepassword` skill
- Description rewrites needed for: coolify, uptime-kuma, skill-vetting, voice-command
- PII scrub needed for: `google-workspace-recipes`, and `obsidian-kb`/`obsidian-memory` (contains `~/clawd` paths)
- OpenClaw-strip needed for: agent-teams, memory-manager, self-improving-agent
- NOT-for disambiguation lines needed for: mcporter, mcp-builder, mcp-server-dev
- All 21 items currently in `_merge-staging` must be resolved during Phase 4

### 3. B9 (handover skill pair) spec finalized — verdict: EXTEND
- Design: steal the alirezarezvani `handoff` skill's 5-section skeleton plus its redaction approach; keep VR's existing OPEN/RESOLVED tagging convention.
- The net-new contribution beyond both sources is a durable synced storage location plus a verify-on-open step (re-checks verification anchors from the prior handover and stops if drift is detected, rather than blindly trusting stale state).
- To be built inside the `agent-meta` plugin during Phase 5.

### 4. Next session starting point
- Phase 3, the description rewrite fan-out (8 batches, one per plugin; style guide is documented earlier in this same handover doc's Skills Consolidation section; the strict validator run is the gate before moving on), followed by Phase 4 (resolving the merges).
- Reiterate the wave pattern this whole consolidation effort follows: commit, then verify, then a checkpoint before continuing.
