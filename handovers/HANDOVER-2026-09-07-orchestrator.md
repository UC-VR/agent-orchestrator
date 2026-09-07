# Handover: orchestrator, 2026-09-07

## Session Info
- Agent: orchestrator. Dates: 2026-09-02..07. User: vr.
- Branch(es): `main` (dotfiles repo); stray `fix/ix-settings-adopt` and `feat/parity` (already merged) also present.
- Repos in play: `UC-VR/dotfiles` [repo] `../../.local/share/chezmoi` (canonical, work repo for this session — see anchors), `UC-VR/oc-global` (retired, no further work).
- Purpose: chezmoi dotfiles drift reconciliation across three nodes — `lp-ryckov11` (Windows), `vr-oc1` (Linux, personal daily driver), `ix-claude1` (Linux, corporate).

## Completed (verified)
- Root cause diagnosed: two unrelated repos (`dotfiles` vs `oc-global`, no shared history) plus Windows-specific content baked into flat templates, plus a `Connections.db` credential vault present in git history.
- `Connections.db` purged from history via `git filter-repo`, then force-pushed (owner-approved). Pre-purge old `main` tip was `4b689c6` (not resolvable post-rewrite — expected, history was rewritten, not an anchor). Post-purge `main` tip `aa8c9829968e8e5646c65d5ae3377714ffb181fa`, tagged `pre-drift-fix-20260902-1856` (tag verified to point at this exact commit). A rollback mirror bundle was kept in this machine's local scratchpad (`dotfiles-mirror.git`) — machine-local, not a portable anchor.
- Wave 1 per-node capture branches pushed to origin: `capture/lp-ryckov11` @ `9f8c8f7410dcc2e0846da7c7400973ebdc13f4d3`, `capture/vr-oc1` @ `a47e3d9966a5b5790ce00821301023d0ed2de9ed`, `capture/ix-claude1` @ `b4ae5826eb90cd0a52e70ddf5cff8bdbb8ce21fe`.
- Wave 2/2.1 merge of `merge/templates` → `main` @ `53b317ab0f78fa0a9be5485d97cca85e7e602ca6`: `.chezmoi.toml.tmpl` derived data (`is_personal`, `git_email`, `agents_root`, `git_root`, `linux_distro`); `.chezmoiignore`; `dot_claude` settings template (later became `modify_` in Wave 3); `dot_gitconfig.tmpl` + `dot_config/git/identity-{vr,ix}.tmpl`; `dot_ssh/config.tmpl` (14 aliases, stat-guarded 1Password agent line); `dot_bashrc.tmpl`; `dot_bash_aliases.tmpl` (the `cc*` launcher family); Windows app templates; junk removed; `known_hosts` unmanaged; `BACKLOG.md` added (git-only, ignored so it never deploys); `.gitattributes` added.
- Wave 3 applied on all three nodes at `53b317a`; `vr-oc1` switched from `oc-global` to `dotfiles` (its old clone retired at `~/.local/share/chezmoi.oc-global-retired-2026-09-04`, per-node path, not anchored here).
- Wave 4 → `main` @ `5da03b9265cd4dfd7db61825a388c28d6b52045b`: includeIf glob fix (`:*/**`), Windows `core.sshCommand` switched to native OpenSSH, `dot_claude/modify_settings.json` introduced as a `chezmoi:modify-template` (managed keys: `permissions`/`hooks`/`env`/`enabledPlugins`/`extraKnownMarketplaces`; `model` and similar left host-owned). Applied on all three nodes.
- Wave 5 → `main` @ `34e9acf7c3d69f86291837eb7f10d3b3fae0fd61` (via now-merged `feat/parity`): `Documents/PowerShell/parity.ps1` + `parity.tests.ps1` + a PowerShell 5.1 stub + a `run_once` junction script (later retired, see In-Flight); bash-side mirror of the same shortcuts (`ll`/`la`/.../`mkcd`/`psg`); PowerToys Run `settings.json` unmanaged (runtime churn). Applied on both Linux nodes (`.bash_aliases` portion only there). NOT applied on `lp-ryckov11` — see In-Flight.
- ix-claude1's abandoned `pending/settings-bypass-review` branch archived as a bundle under a per-node backup dir on `ix` plus a scratchpad copy (machine-local, not anchored); its local branches were deleted and the ix clone was gc'd.
- Fleet convergence check run 2026-09-05: all three nodes on `main`, `chezmoi apply -v` returns rc=0 on both Linux nodes; `lp-ryckov11` returns rc=1, fully explained by two pre-accepted residual items (`Documents/PowerShell/*` dir-attr mismatch from OneDrive redirection, and PowerToys Run `settings.json` runtime churn) — no unaccounted drift found.

```anchors
commit 34e9acf7c3d69f86291837eb7f10d3b3fae0fd61 main ../../.local/share/chezmoi
commit 5da03b9265cd4dfd7db61825a388c28d6b52045b main ../../.local/share/chezmoi
commit 53b317ab0f78fa0a9be5485d97cca85e7e602ca6 main ../../.local/share/chezmoi
commit aa8c9829968e8e5646c65d5ae3377714ffb181fa main ../../.local/share/chezmoi
remote refs/heads/main 34e9acf7c3d69f86291837eb7f10d3b3fae0fd61 ../../.local/share/chezmoi
file ../../.local/share/chezmoi/dot_claude/modify_settings.json
file ../../.local/share/chezmoi/BACKLOG.md
file ../../.local/share/chezmoi/Documents/PowerShell/parity.ps1
file handovers/HANDOVER-2026-09-07-orchestrator.md
```

## In-Flight
- `main` = `34e9acf` on all three nodes and on origin (confirm with `git ls-remote origin refs/heads/main` in the dotfiles repo — matched at handover time). On `lp-ryckov11`: the Wave 5 junction-based Documents linking was rolled back (junctions broke chezmoi's Windows directory classifier — `unsupported file type 0o2000000`); `chezmoi status` there shows `DA Documents/PowerShell/*` plus the untouched `WindowsPowerShell` stub as pending, and a stale `run_once` state entry for the retired `10-link-documents` script remains recorded (harmless, no re-run risk).
- Wave 5.1 (owner-chosen redesign, replacing the junction approach): shared `.chezmoitemplates/pwsh/*` partials plus two thin wrapper trees — `Documents/PowerShell/*.tmpl` (generic Windows) and, for `lp` specifically, `OneDrive - Global Infinox/Documents/PowerShell/*.tmpl` + `.../WindowsPowerShell/*.tmpl`; a new `documents_rel` variable in `.chezmoi.toml.tmpl` derived from `[Environment]::GetFolderPath('MyDocuments')`; `.chezmoiignore` gated by `documents_rel`; and removal of `run_once_before_10-link-documents.ps1.tmpl`. The authoring agent died (auth error) before committing anything — checked for a branch or worktree named `fix/parity-onedrive` and found **none** (no local branch, no remote branch, no worktree, no commit anywhere in `git log --all`). This work has NOT been started in git; only the design above (from `PLAN-chezmoi-drift.md`/`parity-judge.md` in scratchpad) exists.
- ix settings adopt (owner decision: ADOPT the live drift into the template) — in `dot_claude/modify_settings.json`'s ix branch, set `enabledPlugins["vr-agent-creator@vr-orchestra"] = false` and `extraKnownMarketplaces.vr-orchestra.autoUpdate = true`. The worker agent died mid-edit; found a dangling worktree at the session scratchpad path (`wt-ixadopt`, checked out on local branch `fix/ix-settings-adopt`, tip = `main`'s `34e9acf`, so the branch itself carries no new commits) with an **uncommitted** working-tree diff: the `enabledPlugins` flip is present but the `extraKnownMarketplaces.vr-orchestra.autoUpdate` addition is still missing. Nothing has been committed or pushed for this change. Run `git worktree list` / `git worktree remove` (or `prune`) after finishing or discarding this edit.
- Remaining sequence once the two items above are resolved: verifier pass + a Linux dry-run, fast-forward `main`, apply to `lp` (new OneDrive-tree files) and to `ix` (settings no-op or adopt), run `parity.tests.ps1` under both pwsh7 and Windows PowerShell 5.1, then a fresh fleet convergence check.

## Decisions (OPEN/RESOLVED)
- RESOLVED: one canonical repo is `dotfiles`; `oc-global` is retired — avoids maintaining two unrelated histories for the same machines.
- RESOLVED: the `cc*` launcher family is canonical from `lp` — it was the most complete/maintained set.
- RESOLVED: `Connections.db` was purged from git history via filter-repo + force-push, an explicit exception to normal history-safety rules — it held a credential vault that should never have been committed (owner-approved).
- RESOLVED: reconciliation strategy = "Strategy B" (per-node capture branch → template merge) rather than picking one node's state as ground truth — preserves all three nodes' real config as the merge input.
- RESOLVED: `permissions.defaultMode: bypassPermissions` on all three nodes for now (BACKLOG item to train `auto` fleet-wide later).
- RESOLVED: git identity selection by hostname prefix, `includeIf` keyed by remote alias (`github.com-vr` → UC-VR, `github.com-ix` → the corporate remote alias).
- RESOLVED: Claude Code plugins/marketplaces are per-host snapshots, not force-synced — respects that each node may legitimately run different plugin state.
- RESOLVED: `known_hosts` is unmanaged (SSH-populated, not chezmoi's job).
- RESOLVED: the 14-alias SSH config set from Wave 2 is the standardized set across all nodes.
- RESOLVED: parity-layer strategy = "Strategy C" (judge-evaluated) with fixes D1–D8 and grafts G1–G7 applied from the judged comparison (see `parity-judge.md` in scratchpad for the itemized list — not reproduced here, file is machine-local).
- RESOLVED: Documents redirection handled via a host-gated OneDrive template tree, NOT NTFS junctions — junctions break chezmoi's Windows directory-type classifier (upstream issue chezmoi#4228).
- RESOLVED: adopt ix's live plugin/marketplace state into the template rather than reverting it (owner call, since it could not be proven from logs whether the drift was a deliberate toggle or an update side-effect) — implementation still uncommitted, see In-Flight.
- OPEN: confirm ix git identity email/name — currently guessed as `vadim.ryckov@infinox.com` (already-public per repo config, not a secret) <!-- handover:allow already-public identity per repo config, whitelisted by task instructions -->.
- OPEN: cleanup of retired clones/backups on `vr-oc1` and `ix` (orphan capture clone + retired oc-global clone on `vr-oc1`; archived-branch bundle on `ix`).
- OPEN: credential rotation for whatever secrets were stored in the purged `Connections.db`.
- OPEN: installing the `vr` user's `authorized_keys` on two remote hosts referenced in BACKLOG.md, plus adding `ix-claude1`'s pubkey to `vr-oc1`'s `authorized_keys`.
- OPEN: Tailscale MagicDNS broken on `vr-oc1` (hostnames resolve to bogus IPv6; direct IP works).
- OPEN: Greenshot's `Commandline.MS Paint` dead path needs an in-app fix before recapture.
- OPEN: chezmoi binary version not converged across the fleet (`lp`/`ix` on v2.70.0, `vr-oc1` on v2.69.4; latest available is v2.72.1 on all).
- OPEN: 1Password SSH agent not yet provisioned on the Linux nodes (`.ssh/config` already stat-guards for it and will auto-enable once the socket appears).

## Resume Instructions
1. Read this file fully, including the `anchors` block, before touching the dotfiles repo.
2. Run handover-open's anchor check to confirm nothing has drifted since this was written.
3. Skills to use next: `infra-network:chezmoi` (apply/template mechanics), `agent-meta:handover-open` (to formally resume), the orchestrator's own verifier gate (before declaring Wave 5.1/ix-adopt done), `dotjez:verify-current` (chezmoi `modify-template`/`output` function semantics move fast — verify against current docs before writing more modify-template logic).
4. In the dotfiles repo (`../../.local/share/chezmoi` from this agent repo): run `git worktree list` and `git branch -a`; the `wt-ixadopt` worktree and `fix/ix-settings-adopt` branch are known-dangling with one real uncommitted change in them (the `enabledPlugins` flip) — either finish that edit (add the `autoUpdate` field), commit, and merge, or discard it and redo the change; `git worktree prune` afterward. Confirm there is still no `fix/parity-onedrive` branch/worktree before starting Wave 5.1 fresh.
5. Re-brief an authoring agent for Wave 5.1 using the design summarized in In-Flight above (shared `.chezmoitemplates/pwsh/*`, two wrapper trees, `documents_rel` var, `.chezmoiignore` gating, removal of the old `run_once` junction script).
6. Complete the ix-adopt commit (see step 4).
7. Rebase/merge both into one fast-forwardable line on top of current `main` (`34e9acf`), run the verifier plus a Linux dry-run.
8. Fast-forward `main`; apply on `lp` (new OneDrive-tree files) then on `ix` (settings change, should be a no-op on disk since it's adopting already-live state).
9. Run `parity.tests.ps1` under both PowerShell 7 and Windows PowerShell 5.1 on `lp`; re-run the fleet convergence check across all three nodes.
10. Update `BACKLOG.md` to check off whatever the above resolves, and leave the rest OPEN as listed above.
