# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

One narrow exception (since v1.9.0): the orchestrator may call the corp Projektor MCP tools (`mcp__plugin_projektor-corp_projektor__*`, from the vr-orchestra `projektor-corp` plugin) directly for lightweight task tracking. Heavier Projektor work is still delegated; if the tools are absent it delegates instead.

This plugin adds six patterns on top of plain delegation.

### 1. Dispatch protocol (skill & agent matching)

Before spawning any worker, the orchestrator runs a routing step:

1. **Enumerate** what is actually available *this session* — the skills exposed via the Skill tool and the agent types available to the Agent tool, read from the live list injected into context (never a hardcoded/remembered list, which goes stale).
2. **Match** the task against them — does a specific skill or specialized agent fit better than a generic subagent?
3. **Prefer the specific over the generic** — invoke the matching skill or specialized agent when there is a clear fit.
4. **Log the choice** in one line: `Routing via <skill/agent> because <reason>.` If nothing specific fits, it picks the generic agent by task shape — the `worker`-vs-`general-purpose` tie-breaker. It **defaults to the `worker`** agent for any task whose path is already known: well-scoped, mechanical execution — applying a specified edit, a routine refactor, running a command/test, gathering named files (`worker` is the more specific tool here, carrying the craftsmanship principles and a cheaper tier, so it wins these ties). It **reserves `general-purpose`** for open-ended, exploratory, or multi-step research where the path is *not* known up front — locating something when you're unsure of the first hit, or work whose steps only emerge as you go. Tie-breaker question: *is the what-and-where already specified?* If yes → `worker`; if it still needs discovery → `general-purpose`.

This keeps routing **current** (reads the live list) and **auditable** (logs the why).

The repo also ships a **`planner`** agent (`agents/planner.md`, `model: pool-fable`, tools Read/Glob/Grep only): the orchestrator's planning step. It returns a plan (goal, subtasks with deliverable, acceptance check and suggested agent, ordering, risks, open questions) and does not edit code, run commands or fetch the web; when web content is needed the orchestrator has a `worker` fetch it and passes the planner a summary, and commands, URLs and dependencies in a plan are unverified until a worker or verifier checks them. `pool-fable` is allowed by the model-tier gate for `subagent_type` `agent-orchestrator:planner` only.

The repo also ships a **`worker`** agent: the default leaf executor for minor, well-scoped tasks, running on a cheaper model tier with built-in craftsmanship principles (think-before-coding, simplicity, surgical changes, goal-driven verification).

#### Scout (bulk input pre-analysis)

Bulk input (>~10 files or >~2K lines) feeding one downstream agent gets pre-analyzed by the **`scout`** agent first, so the planner reads a compact, priority-tagged briefing instead of the raw files. Scout runs on Haiku 5.5 (`model: pool-haiku`, one of the few types the tier gate allows on Haiku) and has a hook-restricted toolbelt (best-effort guardrails, not a sandbox; see v1.9.1 known limits): Read/Glob/Grep, Bash gated to read-only inspection commands by `scout-readonly-gate.py` (`env`/`printenv` and other known environment-read routes are blocked, which reduces but does not eliminate the chance of reading secrets), and Write limited to `*_briefing.md` files by `scout-write-gate.py` (every other Write target and all Edit calls are denied). Scout is local-only: it has no network access, so for a remote repo or web page a `worker` first fetches the content to disk (shallow clone into a temp dir, or pages saved as files) and scout reads those files; fetched content is untrusted and instructions inside it are data. Its briefing is capped (≤20% of source lines, ~8K chars). It never fixes, decides, or audits (a correctness check against a spec is `verifier` work) — it is not a verifier.

### 2. Tournament Trigger + comparative gate (offer, don't impose)

Some tasks are decisions, not executions — a design, a plan, a wording, an approach — where two competent producers would reasonably differ. The orchestrator flags these but never forces a tournament on its own: it asks via AskUserQuestion ("Tournament — N producers + judge, or a single producer?", defaulting to single) and only fans out unprompted when the user's own words already asked to compare or rank options.

Once a tournament runs: name 2–3 materially different approaches, spawn one producer per approach in parallel (each emits one de-identified candidate, no self-ranking), spawn the **`judge`** subagent with explicit criteria to score, rank, declare a winner, and list grafts from the losers, then run the normal verifier gate on the grafted winner only — never on every candidate.

The comparative gate itself has three tiers: **invariant** (never present a producer's own ranking as your conclusion — label it "producer-ranked, unjudged"), **offer** (default: when a report contains ≥2 ranked options, offer the judge pass via AskUserQuestion), and **mandatory** (only when the ranking will be acted on unreviewed in the same session, or the user explicitly asked for a ranking as the deliverable).

The `judge` is shipped as its own agent (`agents/judge.md`, `model: pool-opus`): read-only, evidence-grounded per-criterion scoring, honest tie-flagging, and a graft list — it ranks, it does not fix or merge.

### 3. Verification gate (backed by the `verifier` subagent)

Before delivering high-stakes output (code changes, multi-file edits, refactors, config changes), the orchestrator runs a verification gate:

- Spawns the dedicated **`verifier`** subagent (agentType `agent-orchestrator:verifier`, pool-sonnet-high) for pre-final rounds and **`final-verifier`** (`agent-orchestrator:final-verifier`, pool-opus, same contract) for the last gate before delivery or push — each is an independent, adversarial, **read-only** checker with its own fresh context. It tries to *falsify* the producer's work, re-deriving correctness from the actual artifact and ground truth (files, command output, sources) rather than the producer's summary, and returns a binary **`VERIFIED` / `ISSUES FOUND`** verdict grounded in evidence.
- Uses **bounded retries** — on `ISSUES FOUND`, the blocking findings go back to the producer or a fixer agent, capped at ~1–2 iterations to avoid infinite loops.
- **Escalates** the unresolved issue to the user after the cap instead of looping or shipping broken work.

Governing principle: **for mechanical work the bottleneck is verification, not generation** — a plausible change is cheap, confirming it is the hard part. **For decision-shaped work the bottleneck is comparison** — a single draft has nothing to be better than. Comparison is offered by default and imposed only when the choice will be acted on unreviewed.

The `verifier` is shipped as its own agent (`agents/verifier.md`, `model: pool-sonnet-high`, used for pre-final rounds): it checks, it does not fix (no Write/Edit tools by design), it never delegates, and it never rubber-stamps.

### 4. Model-tiering guidance (enforced)

The orchestrator matches model strength to task difficulty — and since v1.6.0 this is mechanically enforced, not just prose:

- The orchestrator is pinned to `pool-opus`; no subagent may run on the orchestrator-reserved `fable` tier (`pool-fable`, `pool-fable-high`), with one exception: the `planner` agent is pinned to `pool-fable` (exact id, and only when `subagent_type` is exactly `agent-orchestrator:planner`).
- Every Agent-tool spawn must carry an **explicit `model` param** — no inheritance.
- **Pool map** (frontmatter `model:` is a 9router pool id, passed through verbatim; only live pools are used; `pool-sonnet-high` and `pool-haiku-high` are live as of 2026-10-15):

  | Agent / use | Pool |
  |---|---|
  | `orchestrator` | `pool-opus` |
  | `planner` | `pool-fable` |
  | `worker`, `general-purpose` | `pool-sonnet` |
  | `scout`, `Explore`, summaries | `pool-haiku` (`scout` may also use `pool-haiku-high`) |
  | `judge` | `pool-opus` |
  | `security-reviewer` | `pool-opus-high` |
  | `verifier` (pre-final rounds) | `pool-sonnet-high` |
  | `final-verifier` (last gate before delivery or push) | `pool-opus` |
  | lint-style checks | `pool-sonnet-low` |

  **Haiku only for `scout`/`Explore`/`claude-code-guide`/`statusline-setup`**, and `pool-haiku-high` for `scout` only (never verification, judgement, planning, code edits or security review; Haiku 4.x/3.x denied).
- **Why `final-verifier` is a separate agent.** The Agent tool's `model` parameter is an enum (`sonnet|opus|haiku|fable`) and cannot carry a pool id, so a per-call override to `pool-opus` is not possible. `agents/final-verifier.md` is the `verifier` contract pinned to `pool-opus`; the orchestrator uses `verifier` for bounded pre-final rounds and `final-verifier` for the last pass.
- **Gap (built-ins).** `general-purpose` and `Explore` can only be given an alias (`sonnet`/`haiku`); it routes to `pool-sonnet`/`pool-haiku` only if the host maps aliases to pools (e.g. `ANTHROPIC_DEFAULT_SONNET_MODEL=pool-sonnet`, `ANTHROPIC_DEFAULT_HAIKU_MODEL=pool-haiku`). This plugin does not edit host settings.
- A `PreToolUse` **`model-tier-gate`** hook denies any `fable` spawn (sole exception: exactly `pool-fable` with `subagent_type` `agent-orchestrator:planner`), denies `haiku` for every agent type outside the allowlist above (and Haiku 4.x/3.x ids everywhere), and denies unpinned built-in types (e.g. `general-purpose`, `Explore`, `Plan`, `claude-code-guide`) spawned with no explicit model — while letting pinned agents (`worker`, `planner`, `verifier`, `final-verifier`, `judge`, `scout`, `security-reviewer`) resolve their own frontmatter pool. Matching is by substring, so pool ids behave like aliases (`pool-fable*` denied except `pool-fable` for `agent-orchestrator:planner`, `pool-haiku` allowlisted types only, `pool-haiku-high` `scout` only). It fails open on any internal error, so it never bricks spawning.
- The same hook (since v1.7.2) handles Agent/Task spawns that pass a `name` param: Claude Code's in-process teammate path (anthropics/claude-code#81746, #78234, #31977) silently drops the requested agent definition and degrades the spawn to a fixed reduced tool profile when `name` is set. Since v1.8.6 the hook strips `name` (plus teammate-only `team_name`/`teamName`/`mode`) via `updatedInput` and lets the spawn proceed as a plain subagent when the CLI is ≥ 2.1.290 (the other tier rules still apply to the stripped input); on an older or undetectable CLI it denies instead. Track agents by the ID the tool call returns and use it with `SendMessage` for follow-ups. Escape hatch for tmux-mode experiments: `ORCHESTRATOR_ALLOW_NAMED_SPAWNS=1` (keeps `name`, no strip).
- (Since v1.7.3) That named-spawn check only runs when the incoming call's `tool_name` is `Agent` or `Task` — any other tool (e.g. `Bash`, which also accepts a `name`-shaped argument for unrelated reasons) is allowed through untouched. This keeps the gate scoped to spawns even though its `hooks.json` matcher already restricts it to `Agent|Task`, so the script enforces the same scope it claims.

This can cut cost substantially on well-scoped tasks — conditional on the review gate reliably catching cheap-model errors.

### 4b. Loop guard (no polling loops, subagent lifetime limit)

`hooks/loop-guard.py` (PreToolUse, matcher `*`, best-effort, **fails open** on any internal error) answers an observed incident: one orchestrator made 142 status checks (37 identical in a row), 28 `TaskStop` and 26 respawns. It denies the 5th identical consecutive status-check call (`ListAgents`, `TaskOutput`, `TaskGet`, `TaskList`, `BashOutput`, `TaskStop`, `SendMessage`, Bash where the whole command is `sleep N`, or a `sleep`/`tail`/`cat` on one of Claude Code's task output files, and Read of such a file; task output files are `.../tasks/<id>.output` or `.output` files under a `/claude-<uid>/` tmp tree, so ordinary files in a `tasks/` directory such as Ansible roles and `sleep 5 && curl ...` health checks are never watched), or the 8th within 5 minutes, with an exponential backoff (30s, 60s, 120s, cap 10m; the deny message states the exact wait, and denied retries do not extend it), and caps `TaskStop` at 6 per hour. For subagents it also counts tool calls: at ~150 calls or 4 hours it warns (compact or return a handoff summary), and denies at 1.5x. State is per session and agent under `${XDG_CACHE_HOME:-~/.cache}/agent-orchestrator/`; the `$TMPDIR` fallback is used only if that directory is a real (non-symlink) directory owned by the current user with mode 0700, the state file is opened with `O_NOFOLLOW`, watched Bash commands and Read paths are stored only as hashes (no plaintext), the number of stored signatures is capped (oldest dropped first), and whitespace is collapsed before matching, so padding cannot hide a repeated call: the signature hashes the full normalised command, but the regexes only see at most 4096 characters of it (head and tail), which bounds their cost. A trailing `# comment` does not hide a bare `sleep N`. Overrides: `LOOP_GUARD_MAX_IDENTICAL`, `_WINDOW_MAX`, `_WINDOW_SECS`, `_MAX_STOPS`, `_MAX_TURNS`, `_MAX_HOURS`, `_HARD_FACTOR`, `LOOP_GUARD_DISABLE=1`. Known limit: alternating two different watched calls evades the streak rule (the window rule still applies).

### 5. Reminder hook (soft nudge, not enforcement)

The plugin registers a `PostToolUse` hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`) on the subagent-spawning tool (`Agent`, with its legacy alias `Task`). After a producer is spawned, the hook injects a **non-blocking** `additionalContext` reminder naming both gates: verifier for mechanical output, judge-then-verifier for decision-shaped output or a report with ≥2 ranked options. It is a **soft reminder only** — it never blocks or fails a tool call, and the orchestrator is free to skip it for trivial/read-only work. The hook emits a no-op (`{}`) when the spawned agent *is* the `verifier`, `final-verifier`, `judge`, or `scout` — matched on the bare role name after stripping any `agent-orchestrator:` namespace prefix, so it never nags you to verify the verifier (which would invite an infinite loop). The script depends only on POSIX `sh` + `grep`/`sed` (no `jq` requirement) and defensively reads several possible agent-type field names.

### 6. Self-learning journal (SessionEnd hook + manual reconciler)

The plugin ships a small journal loop. It records what happened, captures candidate learnings, and gives you a skill to consolidate them. It does not apply anything on its own, and nothing nudges you at session start.

Honest properties: the hooks are Python and shell (`session-journal.sh` is bash and uses `node` to parse the payload; `verify-reminder.sh` is POSIX `sh`; `model-tier-gate.py`, `loop-guard.py`, `scout-readonly-gate.py`, `scout-write-gate.py` and `security-reviewer-gate.py` are Python). `session-journal.sh` can invoke `claude -p`, which makes a network call to the model API, and it writes to `~/.claude/journal/LEARNINGS.md` outside the project.

#### SessionEnd: `hooks/session-journal.sh`

Registered in `hooks/hooks.json` (10s timeout). It always exits 0 (fail-open). On every session end it:

1. Appends a `session_end` stub to `.claude/journal/<YYYY-MM-DD>-<session_id>.md` in the project (`cwd`). The stub records the reason, the session ID, and the transcript path. When the transcript is readable it adds a `spawns: worker=N verifier=N judge=N scout=N` line, grepped from the `subagent_type` values in the transcript.
2. If the session was substantive (at least 12 `tool_use` blocks and at least 2 file-edit blocks: Edit, Write, MultiEdit, NotebookEdit), writes a capture prompt and launches a detached background `claude -p --permission-mode bypassPermissions --tools Read,Edit,Write`. That run reads the transcript and either does nothing or appends one block to the **global** `~/.claude/journal/LEARNINGS.md` (not a per-project file). `--tools Read,Edit,Write` restricts the run to those three tools; `--permission-mode bypassPermissions` avoids the prompt (Claude Code's sensitive-path guard blocks non-interactive writes under `~/.claude/` otherwise). Note that `--allowedTools` would not do this restricting: it only pre-approves tools.

Each captured block starts with the sentinel line `<!-- learning -->`, then a heading and four fields:

```
<!-- learning -->
## YYYY-MM-DD · session <id>
**Learned:** ...
**Decided:** ...
**Candidate skill updates:** ...
**Dedupe check:** ...
```

#### Manual reconcile: `skills/reconcile-learnings`

A skill you invoke on demand ("reconcile learnings", "consolidate learnings"). It reads the `<!-- learning -->` blocks in `~/.claude/journal/LEARNINGS.md`, runs `scripts/skill-overlap.sh` for each candidate, and proposes consolidated edits through `skill-creator` (PROPOSE-not-apply: you review before anything changes). It is intended to run weekly; no scheduler is shipped with this plugin, so run it yourself or wire your own timer.

#### `scripts/skill-overlap.sh` dedupe helper

Searches `SKILL.md` and `references/*.md` files (only those; `_archived`, `node_modules` and `.git` directories are skipped) for the candidate keywords. Roots, in order: any colon-separated paths in the `SKILL_OVERLAP_ROOTS` environment variable (prepended), then `~/.claude/skills`, `~/.claude/plugins`, `~/agents/skills`, `.claude/skills` and `.claude/recipes` under the current directory; roots that do not exist are skipped and the same directory is not scanned twice. Hits are de-duplicated per skill directory (each skill is listed once per keyword, with the file that matched); there is no hit-count cap. It needs only `bash`, `grep`, and `find`. It lives in `scripts/` because it is a manual helper called by the reconcile skill, not a hook.

#### What does not exist

There is no `SessionStart` journal hook, no pending-marker or reconcile-counter file, no reconcile threshold, and no compaction handling. The only `SessionStart` hook is `version-check.sh`, which compares installed plugin versions against the marketplace pins.

## How to add it

> **Preferred install:** via the `vr-orchestra` marketplace (`UC-VR/vr-orchestra`). The standalone marketplace here remains for backwards compatibility.

Install directly from git:

```
/plugin install git+https://github.com/uc-vr/agent-orchestrator.git
```

Or via a marketplace:

```
/plugin marketplace add https://github.com/UC-VR/agent-orchestrator.git
/plugin install agent-orchestrator@agent-orchestrator
```

## Install via Claude

Prefer to let Claude Code do the install for you? Paste the prompt below into a Claude Code session. It uses the plugin mechanism (the repo's intended install path) and then wires up the machine-local settings that a plugin can't carry.

> Install the `agent-orchestrator` Claude Code plugin for me and wire it into my global config. Do this carefully and do not clobber anything:
>
> 1. Add the marketplace and install the plugin:
>    - Run `/plugin marketplace add https://github.com/UC-VR/agent-orchestrator.git`
>    - Run `/plugin install agent-orchestrator@agent-orchestrator`
>    The plugin ships the `orchestrator`, `worker`, `planner`, `verifier`, `final-verifier`, `judge`, `scout`, and `security-reviewer` agents plus the `PostToolUse:Agent` reminder hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`); these load automatically once installed, with `${CLAUDE_PLUGIN_ROOT}` resolved for me — I do not need to copy files by hand.
> 2. Before changing any settings, back up my global settings: copy `~/.claude/settings.json` to `~/.claude/settings.json.bak` (skip if the file does not exist).
> 3. Apply the machine-local settings that do NOT travel in a plugin, merging into existing config rather than overwriting it — never drop my existing hooks, permissions, or other keys:
>    - Set the orchestrator thread to a strong model (e.g. Opus) via `/config`.
>    - Agent teams are disabled fleet-wide (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` since 2026-10-06): teammate tools are clamped to the lead's and hook payloads lose the agent type. Named spawns are plain subagents; track by returned ID. Do not enable them.
>    - If I want the orchestrator to be the main thread, point my `agent` setting at it (or note that I can launch with `claude --agent orchestrator`).
>    - Approve the tool/command permissions the orchestrator and its subagents need (Bash, file writes, network) when prompted.
> 4. Verify the install: confirm `agent-orchestrator` shows up via `/plugin` (installed), that `orchestrator`, `worker`, `planner`, `verifier`, `final-verifier`, `judge`, `scout`, and `security-reviewer` are listed as available agents, and that a `PostToolUse` hook with matcher `Agent|Task` running `verify-reminder.sh` is registered. Report exactly what you changed and anything you skipped.
>
> Prerequisite: the reminder hook is a POSIX shell script, so on Windows make sure an `sh` (e.g. Git Bash) is available to Claude Code. `jq` is not required.

## Post-install manual checklist (these do NOT travel in a plugin)

A plugin ships the agent/hook definitions only. The following are machine-local settings that are **not** packaged and must be re-done on every machine where you install this plugin:

- [ ] **Approve permissions.** Grant the tool/command permissions the orchestrator and its subagents need (e.g. Bash, file writes, network) in your settings or when prompted.
- [ ] **Set the model.** Run `/config` and select a strong model (e.g. Opus) for the orchestrator thread, per the model-tiering guidance.
- [ ] **Leave agent teams off.** Agent teams are disabled fleet-wide (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` since 2026-10-06): teammate tools are clamped to the lead's and hook payloads lose the agent type. Named spawns are plain subagents; track by returned ID.
- [ ] **Make the orchestrator the active agent.** Point your `agent` setting (or `claude --agent orchestrator`) at it if you want it to run as the main thread.
- [ ] **Copy any status line script.** If you use a custom status line, copy the script over and re-point your settings at it.
- [ ] **Set voice / marketplaces / other local prefs.** Re-apply voice settings, re-add any plugin marketplaces, and any other per-machine configuration you rely on.
- [ ] **(Hook prerequisite)** The reminder hook runs a POSIX shell script. On Windows, ensure a `sh` (e.g. Git Bash) is available to Claude Code so the hook can execute. `jq` is **not** required.
- [ ] **(Self-learning: gitignore entry)** The SessionEnd journal writes a directory that should not be committed to version control: `.claude/journal/` (per-project session stubs). A plugin cannot set git config, so you must add it to your global gitignore yourself: run `git config --global core.excludesFile ~/.gitignore_global` (if not already set), then append `.claude/journal/` to that file.
- [ ] **(Self-learning: avoid double-registration)** If you already have `SessionStart` or `SessionEnd` hooks hand-wired in `~/.claude/settings.json` pointing at the same scripts (e.g. from a prior hand-copy install), installing this plugin will double-register them — Claude Code will run the hook twice per event. When migrating from a hand-wired install to the plugin, remove the hand-wired `SessionStart`/`SessionEnd` entries from `~/.claude/settings.json` before or immediately after installing the plugin.
- [ ] **Version stamp check.** Version stamp in every `agents/*.md` first body line MUST equal `plugin.json` version — grep-check before tagging.

## Usage

Once installed, route your requests through the orchestrator agent. Hand it a goal rather than a single mechanical step — it will:

1. **Route** the task via the dispatch protocol (matching it to the best available skill or specialized agent),
2. **Decompose** and spawn subagents (in parallel where possible) or run a Workflow,
3. **(Tournament)** for decision-shaped work, offer N competing producers + a `judge` pass rather than impose one,
4. **Judge** the candidates when a tournament ran, or when the offer to rank ≥2 options is accepted,
5. **Verify** high-stakes output (the winner, or the sole producer's output) through the `verifier` gate with bounded retries,
6. **Synthesize** and return a clear answer.

For trivial or conversational follow-ups it answers directly; everything else gets delegated.

## Changelog

### v1.10.1

- **1.10.1: role map update (`planner`, new pins), model-tier-gate rules, loop-guard P2 hardening.**
  - **New 9router pools** `pool-sonnet-high` and `pool-haiku-high` (created on vr-omni1, live as of 2026-10-15). The 1.10.0 note that `pool-sonnet-high` does not exist is superseded.
  - **New `planner` agent** (`agents/planner.md`, `model: pool-fable`, tools Read/Glob/Grep, read-only): the orchestrator's planning step. It returns a plan with per-subtask acceptance checks and suggested agents; it does not edit code or run commands. The orchestrator's dispatch protocol now routes planning to it. It has no WebFetch or shell (a worker fetches web content for it), and commands, URLs and dependencies in its plans are unverified until a worker or verifier checks them.
  - **New pins.** `verifier` `pool-sonnet-high` (was `pool-sonnet`), `final-verifier` `pool-opus` (was `pool-opus-high`), `judge` `pool-opus` (was `pool-opus-high`). Unchanged: `orchestrator` `pool-opus`, `worker` `pool-sonnet`, `scout` `pool-haiku`, `security-reviewer` `pool-opus-high`. The orchestrator tier map, dispatch step 5 and Verification-Gate text follow the new map.
  - **`model-tier-gate` rules.** `pool-fable` is allowed only when `subagent_type` is exactly `agent-orchestrator:planner` (exact model id; never granted from `agentType`, never for a bare `planner` since bare names do not resolve to this plugin's agents, and denied when `subagent_type` and `agentType` disagree); `pool-fable-high`, `fable` and every other type stay denied. `planner` stays in the Haiku-never set in both bare and prefixed forms. `pool-haiku-high` is allowed for `scout` only (the other Haiku-allowlisted types keep plain Haiku). `planner` joins the Haiku-never set. Pinned agents dispatched with no model still pass. New tests cover each rule with negative cases.
  - **`loop-guard` P2 hardening** (the three items left open in 1.10.0): (a) the `$TMPDIR` fallback state dir is used only if it is a real, non-symlink directory owned by the current user with mode 0700 (it is created 0700 and `fchmod`ed so umask cannot break it), otherwise the hook fails open; the state file is opened with `O_NOFOLLOW` and `fchmod`ed 0600; (b) watched Bash commands and Read paths are stored as sha256 digests, never plaintext; (c) state keys are capped at 200 (oldest dropped first), and commands are whitespace-normalised before matching, with the regexes seeing at most 4096 characters (head and tail) while the signature hashes the full normalised string, so padding cannot evade the polling rule. A trailing `# comment` does not hide a bare `sleep N`. New tests in `hooks/tests/test_loop_guard_hardening.py`. State files written by 1.10.0 may still contain plaintext commands until they are pruned (3 days); they can be removed manually with `rm ~/.cache/agent-orchestrator/loopguard-*.json` (nothing deletes them for you).
  - **Scope note.** A built-in-replacement pair (`explorer`, `generalist` plugin agents) was considered and dropped: no such agents ship. The built-ins `Explore` and `general-purpose` are unchanged and keep their existing guidance (`model: sonnet` / `model: haiku` aliases). `cf-builder` has no agent file in this repo, so it is not pinned here.
  - **Known residual evasions (accepted, best-effort guardrails).** The polling guard is not a sandbox. These still go unwatched: `sleep 5;`, `sleep 5#c` (no space before `#`), zero-width or other non-whitespace padding, multi-line sleeps, and a task `.output` path in the middle of a command longer than 4096 characters (only the head and tail are scanned).

### v1.10.0

- **1.10.0: pool pins, `final-verifier`, loop-guard (no polling loops, subagent lifetime limit).**
  - **Pool pins.** Frontmatter `model:` is a 9router pool id passed through verbatim: `orchestrator` `pool-opus`; `worker` and `verifier` `pool-sonnet`; `final-verifier`, `judge` and `security-reviewer` `pool-opus-high`; `scout` `pool-haiku`. Built-ins (`general-purpose`, `Explore`) can only take the aliases `sonnet`/`haiku`. `pool-sonnet-high` does not exist, so it is not used.
  - **New `final-verifier` agent** (`agents/final-verifier.md`, `pool-opus-high`): the `verifier` contract run as the last gate before delivery or push. It is a separate agent because the Agent tool's `model` parameter is an enum (`sonnet|opus|haiku|fable`) and cannot carry a pool id. Gate order: producer, `verifier`, `final-verifier`, (offer) `security-reviewer`.
  - **New `hooks/loop-guard.py`** (PreToolUse, matcher `*`, best-effort, fails open). Status-poll repeat guard: denies the 5th identical consecutive status check (or the 8th in 5 minutes) with exponential backoff (30s, 60s, 120s, cap 10m); `TaskStop` capped at 6 per hour; subagent lifetime counter warns at ~150 tool calls or 4 hours and denies at 1.5x. See section 4b. Tests in `hooks/tests/test_loop_guard.py`; `model-tier-gate` tests extended.
  - **orchestrator "Waiting & Lifetime" instructions:** after dispatching background subagents, end the turn and wait for completion notifications; never poll in a loop; unavoidable checks use exponential backoff and a bounded count; never stop and respawn a subagent that is still progressing; subagents at the lifetime limit are compacted or restarted with a handoff summary.
  - Version stamps in plugin.json, marketplace.json and all agents/*.md (now including `final-verifier`).

### v1.9.1

- **1.9.1: lands the never-pushed 1.8.7 work on top of 1.9.0, plus worker/verifier/judge discipline edits.**
  - **Includes all of 1.8.7** (see below): Haiku 5.5 allowlist, scout on Haiku, scout write/read-only gate hardening, `security-reviewer` agent + gate, worktree isolation strip, journal model pin. 1.8.7 was never released on its own.
  - **Projektor:** the "Projektor Routing" section now defers to the 1.9.0 Rules exception: lightweight tracking is direct; heavier issue work (or absent tools) is delegated to a worker.
  - **worker:** Simplicity never removes trust-boundary validation, data-loss error handling, security, accessibility or stated requirements; reuse-before-writing order; `shortcut: <limit>; upgrade when <trigger>` comments, which never cut anything in the never-removes list; Surgical is not partial; report every `shortcut:` left.
  - **verifier:** checks `shortcut:` comments (Blocking if one cuts a protected category, Minor if it lacks a limit or trigger).
  - **judge:** length is not quality.
  - **Gate hardening (verifier B1/B2).** The gates are **best-effort guardrails, not guarantees**: they block the known routes below and fail closed on what they cannot parse, but they are not a sandbox and have known open holes (see Known limits). Scout's gate blocks these environment-read routes (`/proc/*/environ` incl. globs, `jq`/`yq` `env`/`$ENV`/`strenv`/`envsubst`, `awk` `ENVIRON`/`PROCINFO`, `less` removed, chezmoi template-rendering verbs `cat`/`diff`/`status`/`data`/`dump`/`verify` removed, `git remote show` needs `-n`), blocks direct reads of secret-bearing files (shared `hooks/_secret_paths.py`: `.env*`, keys, `~/.config/op`, gh `hosts.yml`, docker `config.json`, `.netrc`, `.git-credentials`, `~/.aws`, glob spellings), and `scout-write-gate` now denies briefings whose content looks like a literal secret and scout Read/Grep on secret paths. `security-reviewer-gate` is now a default-deny allowlist: `gh`, `git credential`, `git -c`/`--config-env`/`--exec-path`, `--output=`, `--ext-diff`, `git grep -O`, mutating `remote`/`tag`/`update-ref`/`notes`/..., interpreters (`python3`, `node`, ...), shells, `curl`/`wget` and other network tools are refused; Read/Grep of secret paths too. Every case from the verifier report has a test.
  - **Second verifier round (NB1/NB2).** security-reviewer: `xargs` removed (it hid file operands from the gate), `declare`/`typeset`/`export`/`readonly` with any `-p` flag or no names denied. Both gates: commands that read a file through a list/format flag are denied (`date -f`, `file -f`, `wc`/`du`/`sort --files0-from`, `du -X`, `tree --fromfile`, `find -files0-from`, `hostname -F`, `*sum -c`), checksum tools are secret-path checked, `.git/config` counts as secret-bearing, and only bare `git remote` is allowed (`-v`/`get-url`/`show` can print token-bearing URLs). Scout: awk `getline` denied. `scout-readonly-gate.py` split into the gate plus `hooks/_scout_checks.py` (per-command checks) to stay under 500 lines.
  - **Known limits and open holes (documented, not closed).** The gates reduce accidental secret exposure and mutation; do not rely on them as a security boundary. Open holes found by the last verifier round (tracked for a follow-up release): **H1** a `<` redirect glued to another word (`cat -<.netrc`, `head -n1<.netrc`, `grep F<.netrc`) skips the secret-path check in both gates; **H2** changing directory defeats the relative-path check (`env -C ~/.docker cat config.json` on the reviewer gate; `git -C .git diff --no-index /dev/null config` on both); **H3** glob operands containing `..` are not normalised (`cat ~/.config/gh/../o?/config`); **H4** security-reviewer: environment-variable prefixes (`GIT_CONFIG_COUNT/KEY/VALUE_*`, `GIT_EXTERNAL_DIFF=...`) re-enable git code execution. Other limits: (1) recursive reads (`grep -r`/`rg` over a tree, `grep -r '' dir`, `diff -r`) print file contents found inside a directory tree, including secret-named files such as `.env` or `.netrc` below the named directory, and secrets inside normal files; the agent prompts require `-l`/`-c` and scout briefings are content-scanned as a backstop. (2) `git show`/`log -p`/`diff` print committed blobs, which may contain secrets under normal names. (3) Repo-config-driven git textconv/diff drivers can run a program if `.git/config` is hostile. (4) The briefing content scan is pattern-based; unknown token formats pass. (5) The Read tool is only blocked on secret-named paths. (6) Both gates are no-ops for every other agent by design.
  - **Third verifier round (F1-F5).** Shared helpers now normalise non-glob paths (`//`, `/./`, `..`; globs with `..` are H3), strip leading fd-prefixed stdin redirects (`0<.netrc`; other glued forms are H1), and match any GNU long-option prefix of file-list flags (`date --f=`, `wc --files0=`, `file --files=`, `tree --fromtabfile`). security-reviewer: `declare`/`typeset +p` denied. Both gates: jq `import`/`include`/`-L`/`-f`/`--rawfile`/`--slurpfile` denied. Scout: `awk` and `yq` removed from the allowlist (awk `ARGV` and yq `load`/`load_str` read arbitrary files). Scout gate fails closed if its helper modules are missing (tested).
  - **orchestrator:** Projektor note now lists `security-reviewer` among agents that cannot reach the tools.
  - Version stamps in plugin.json, marketplace.json and all agents/*.md (now including security-reviewer).

### v1.9.0

- **1.9.0: orchestrator: may call corp Projektor MCP tools (projektor-corp plugin) directly for lightweight tracking; doctrine note. Requires vr-orchestra projektor-corp ≥0.1.0 (optional; absent tools → delegate).** The orchestrator `tools:` allowlist gains `mcp__plugin_projektor-corp_projektor__*` and a Rules exception bullet. Corp Projektor (projects.ai.infinox.io) is for FDE / Infinox work only; personal and Grok Bot matters belong to the personal instance (projects.ucvc.email), which is not wired here.

### v1.8.7

- **1.8.7: Haiku 5.5 allowlist, scout on Haiku, scout hardening, security-reviewer, Projektor routing.**
  - **Haiku 5.5 allowlist.** `model-tier-gate` no longer bans Haiku outright: `haiku`/`pool-haiku`/`claude-haiku-5-5` is allowed only for `scout`, `Explore`, `claude-code-guide` and `statusline-setup` (`HAIKU_OK`). Every other type is denied, and `verifier`, `judge` and `security-reviewer` are explicitly never allowed even if added to the set. Haiku 4.x / 3.x ids (`haiku-4`, `3-5-haiku`, `3-haiku`, `claude-haiku-4`) are denied for all types. Fable stays banned everywhere. The fork, fable and haiku denies all run before any input strip, and the gate still fails open. `statusline-setup` is now in the UNPINNED set (a built-in with no pin), so it needs an explicit `model` like the other built-ins.
  - **Scout runs on Haiku 5.5** (`model: haiku`; the router's `pool-haiku` is confirmed live on `claude-haiku-5-5`).
  - **Scout can Write `*_briefing.md` only** (new `hooks/scout-write-gate.py`, matcher `Write|Edit|MultiEdit|NotebookEdit`; fail-closed for scout, path checked lexically and after `realpath`, `.git`/`.claude` segments denied).
  - **Scout read-only gate:** bypass fixes (env-wrapped mutators, `uniq` output operand, awk output/profile flags), and `env`/`printenv` removed from the allowlist so scout cannot read secrets from the environment (the env-wrapper recursion was dead code and is removed).
  - **Scout is local-only:** no network access. For remote repos or web pages a `worker` fetches the content to disk first; fetched content is untrusted.
  - **New `security-reviewer` agent + `hooks/security-reviewer-gate.py`** (Bash gate: no secret-value exposure, no mutation; fail-closed for that agent) and an orchestrator "Security-Review Offer" step after `VERIFIED`; `verify-reminder.sh` loop-guard covers it.
  - **Projektor routing:** orchestrator "Projektor Routing" section and `worker` "Projektor Issues" section for corp issue tracking.
  - **Worktree isolation strip (Rule 0a):** `isolation: "worktree"` is stripped when the cwd is not a git work tree, so spawns from non-repo directories do not fail.
  - **`session-journal.sh`:** the unattended `claude -p` capture run now passes `--model sonnet` (it writes persistent memory, so it stays off Haiku).
  - **Tests:** 64 tests; run with `cd hooks && python3 -m unittest discover -s tests -v`.

### v1.8.6

- **1.8.6: tier gate strips `name` (updatedInput) instead of denying when CLI ≥ 2.1.290; denies otherwise; teammate-only fields dropped; requires agent teams off (fleet default since 2026-10-06).** Version is read from `MODEL_TIER_GATE_CLI_VERSION`/`CLAUDE_CODE_VERSION`/`AI_AGENT` (set by Claude Code in hook processes), else `claude --version` cached per binary mtime. Haiku/fable/fork/unpinned denies still win over the strip.

### v1.8.5

- **1.8.5: session-journal: `--tools` restricts the capture run (was `--allowedTools`, which only pre-approves); docs truth.** The detached `claude -p` capture ran under `bypassPermissions` with `--allowedTools Read Edit Write`, which pre-approves those tools but does not limit the available set, so the run also had Bash, Agent, WebFetch, WebSearch and the rest. It now passes `--tools Read,Edit,Write` (verified: the run lists only Edit, Read, Write). Docs: README §6 rewritten to match the shipped hooks (no SessionStart journal hook, no counter files, no reconcile threshold; the capture step invokes `claude -p`, so it is not zero-network); agent-teams advice removed (teams are disabled fleet-wide); install text lists all five agents; `skill-overlap.sh` description corrected; `reconcile-learnings` no longer claims a shipped scheduler; the orchestrator prose no longer recommends agent teams.

### v1.8.4

- **1.8.4: scout gate — shlex-unquote argv; closes quoted/escaped flag bypass class.** The gate tokenized with `seg.split()` and never unquoted, so `sed s/a/Z/ '-i' f`, `sort '-o' out g`, `git log '--output=lo'`, `find . -exe\c rm` etc. slipped past every flag check. Segments are now split quote-aware and parsed with `shlex.split` (unparseable quoting is denied), and all per-command checks run on the unquoted argv. Unquoted `$`/backtick expansion and brace expansion are rejected (they can synthesize flags the gate cannot see), and `env -S`, `awk -f/-i/-l/@load/pipes` and `yq -s` are denied. Raw-string checks (redirects, `<(`/`>(`, `$(`, backticks, `eval`) still run first on the raw (pre-unquoting) segment.

### v1.8.3

- **1.8.3: scout gate — close sed/sort/git-remote option-order bypasses.** `sed` options are now validated anywhere in argv (GNU permutation made `sed s/a/b/ -i f`, `... f -i.bak`, `--in-place`, `-ibak`, `-ni` write in place); `sort` denies any short-option cluster containing `o` (`-of`, `-oout`, `-k2 -of`) and abbreviated `--output`/`--compress-program`; `git remote` takes its verb from the first non-flag argument (`git remote -v add x y` was a bypass). Also closed: `yq --inplace`, `tree -o`, `rg --pre`. Known residual (documented in the script header of the jq/yq rule): `less +!cmd`, `awk -f file`, `git diff --ext-diff`. README: namespaced `agent-orchestrator:verifier` in the verification-gate bullet.

### v1.8.2

- **`model-tier-gate` leaks closed.** A spawn with no `subagent_type` (Claude Code defaults it to `general-purpose`), `model: "inherit"`, or `subagent_type: "fork"` could land a subagent on the orchestrator's fable tier. Missing/empty type is now treated as `general-purpose`, `inherit` as no model, and `fork` is denied outright (forks ignore `model`); escape hatch `ORCHESTRATOR_ALLOW_FORK=1`.
- **`scout-readonly-gate` hardened.** Now denies `find -fprint*/-fls/-okdir`, `git --output`, `sort -o`, process substitution, single `&` chaining, `awk system (`, `chezmoi execute-template`, mutating `git branch`/`git remote` forms; `sed` is allowed only for simple print/`s///` scripts (fixes the `sed -n 1,5p` false positive). Header comment corrected: plugin agents ignore frontmatter hooks, so plugin-level `hooks.json` is the only mechanism.
- **`verifier` now pins opus** (was sonnet), matching the adversarial-verification tier in the orchestrator prose.
- **Prose/frontmatter:** namespaced agent names in the scout example and orchestrator verifier reference; orchestrator `tools` list trimmed to the 5-series set (dropped TaskCreate/TaskList/TaskGet/TaskUpdate/TodoWrite/TaskOutput, added ListAgents).
- **Tests:** `hooks/tests/test_model_tier_gate.py` added; scout gate tests extended. Run with `cd hooks && python3 -m unittest discover -s tests -v`.

### v1.8.1

- **`hooks.json`: removed the `"//"` comment key.** Claude Code does not recognize `"//"` and warned on every load (`agent-orchestrator: hooks.json: unknown key "//" ignored`). It is replaced by the documented optional top-level `description` field (a one-line summary of all registered hooks). The detailed rationale that lived in the comment was already in `hooks/verify-reminder.sh`'s header; the one missing fact (tool renamed Task → Agent in CC 2.1.63, hence the `Agent|Task` matcher) was added there. Hook behaviour is unchanged.

### v1.8.0

- **Tournament Trigger.** New pattern: decision-shaped work (design, plan, wording, approach) is flagged and *offered* as a tournament via `AskUserQuestion` — never imposed — defaulting to a single producer. Fan-out runs unprompted only when the user's own words asked to compare/rank/which-is-best.
- **Comparative gate, three tiers.** Invariant (never present a producer's own ranking as your conclusion), offer (default: offer `judge` when a report carries ≥2 ranked options), mandatory (only when the ranking will be acted on unreviewed, or the user asked for a ranking as the deliverable).
- **Candidates-only producer contract.** Tournament producers emit one de-identified candidate each — no self-ranking, no recommendation.
- **Blind judging.** Candidates reach `judge` de-identified (Candidate A/B/C, no producer names or confidence framing).
- **`Candidates: N` routing line.** The dispatch protocol's routing line is now two mandatory lines, the second stating candidate count and which gate follows.
- **`verify-reminder.sh` namespace fix.** The loop-guard compared the bare agent name against a namespaced `subagent_type` (e.g. `agent-orchestrator:verifier`), so it never matched and the hook always fired on verifier/judge/scout spawns too. It now strips the `namespace:` prefix before comparing. The reminder text now names both gates (verifier for mechanical output, judge-then-verifier for decision-shaped output).
- **`scout` gets Bash + a read-only gate.** Scout drops the "cheap model" framing — it runs the same tier as `worker`; its value is the enforced read-only toolbelt (new `Bash`, gated to inspection commands by a `PreToolUse` hook) and context isolation. Added an output ceiling (≤20% of source lines, ~8K char cap) and an explicit non-goal: scout is not a verifier or auditor.
- **Marketplace version drift fixed.** `.claude-plugin/marketplace.json` was still pinned at 1.4.5 (stale since 1.5.0); both it and the `vr-orchestra` marketplace pin now track 1.8.0.

### v1.7.3

- **`model-tier-gate` now checks `tool_name` before applying any rule.** A verifier check found that the named-spawn guard added in v1.7.2 keyed only on `tool_input.name`, so any tool call carrying a `name`-shaped field (e.g. `Bash`) was denied even though the hook is only wired to `Agent|Task` in `hooks.json` — the script's own logic didn't match its stated scope. `main()` now exits allow immediately when `tool_name` isn't `"Agent"` or `"Task"`, before Rule 0 runs. Fail-open wrapper unchanged.

### v1.7.2

- **`model-tier-gate` now blocks named Agent/Task spawns.** Claude Code's in-process teammate path (anthropics/claude-code#81746, #78234, #31977) silently drops the requested agent definition and degrades the spawn to a fixed reduced tool profile whenever `name` is set, regardless of `subagent_type`. The gate now denies any Agent/Task call carrying a non-empty `name`, evaluated before the existing model-tier checks, with an `ORCHESTRATOR_ALLOW_NAMED_SPAWNS=1` escape hatch for tmux-mode experiments.
- **Removed `TeamCreate`/`TeamDelete` from the orchestrator's tool grant** — these tools were removed from the CLI in 2.1.178 and were dead weight in the frontmatter.
- **`orchestrator.md`** now carries an explicit "never pass `name`" rule in the spawning guidance, and points at the returned agent ID (not a name) for `SendMessage` follow-ups.
- **`hooks.json`** pins `"shell": "bash"` on the `model-tier-gate` PreToolUse hook, so its `command -v python3 ... || python ...` fallback can't be interpreted by PowerShell on Windows hosts without Git Bash.

## License

MIT — see [LICENSE](./LICENSE).
