# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents, agent teams, and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents or teams it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

This plugin adds five patterns on top of plain delegation.

### 1. Dispatch protocol (skill & agent matching)

Before spawning any worker, the orchestrator runs a routing step:

1. **Enumerate** what is actually available *this session* — the skills exposed via the Skill tool and the agent types available to the Agent tool, read from the live list injected into context (never a hardcoded/remembered list, which goes stale).
2. **Match** the task against them — does a specific skill or specialized agent fit better than a generic subagent?
3. **Prefer the specific over the generic** — invoke the matching skill or specialized agent when there is a clear fit.
4. **Log the choice** in one line: `Routing via <skill/agent> because <reason>.` If nothing specific fits, it picks the generic agent by task shape — the `worker`-vs-`general-purpose` tie-breaker. It **defaults to the `worker`** agent for any task whose path is already known: well-scoped, mechanical execution — applying a specified edit, a routine refactor, running a command/test, gathering named files (`worker` is the more specific tool here, carrying the craftsmanship principles and a cheaper tier, so it wins these ties). It **reserves `general-purpose`** for open-ended, exploratory, or multi-step research where the path is *not* known up front — locating something when you're unsure of the first hit, or work whose steps only emerge as you go. Tie-breaker question: *is the what-and-where already specified?* If yes → `worker`; if it still needs discovery → `general-purpose`.

This keeps routing **current** (reads the live list) and **auditable** (logs the why).

The repo also ships a **`worker`** agent: the default leaf executor for minor, well-scoped tasks, running on a cheaper model tier with built-in craftsmanship principles (think-before-coding, simplicity, surgical changes, goal-driven verification).

### 2. Verification gate (backed by the `verifier` subagent)

Before delivering high-stakes output (code changes, multi-file edits, refactors, config changes), the orchestrator runs a verification gate:

- Spawns the dedicated **`verifier`** subagent (agentType `verifier`) — an independent, adversarial, **read-only** checker with its own fresh context. It tries to *falsify* the producer's work, re-deriving correctness from the actual artifact and ground truth (files, command output, sources) rather than the producer's summary, and returns a binary **`VERIFIED` / `ISSUES FOUND`** verdict grounded in evidence.
- Uses **bounded retries** — on `ISSUES FOUND`, the blocking findings go back to the producer or a fixer agent, capped at ~1–2 iterations to avoid infinite loops.
- **Escalates** the unresolved issue to the user after the cap instead of looping or shipping broken work.

Governing principle: **the bottleneck is verification, not generation.** Never deliver unverified high-stakes output.

The `verifier` is shipped as its own agent (`agents/verifier.md`): it checks, it does not fix (no Write/Edit tools by design), it never delegates, and it never rubber-stamps.

### 3. Model-tiering guidance

The orchestrator matches model strength to task difficulty:

- Keep the **orchestrator itself on a strong model** (e.g. Opus) for planning, decomposition, and the review/verification gate.
- Delegate **well-scoped execution** (edits, mechanical refactors, searches, test runs) to **cheaper/faster models** (e.g. Haiku/Sonnet) via the Agent tool's `model` option or Workflow `opts.model` / `opts.effort`. (The `verifier` itself runs on Sonnet.)
- Reserve the **strongest models for the hardest reasoning/verify/judge stages**.

This can cut cost substantially on well-scoped tasks — conditional on the review gate reliably catching cheap-model errors.

### 4. Reminder hook (soft nudge, not enforcement)

The plugin registers a `PostToolUse` hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`) on the subagent-spawning tool (`Agent`, with its legacy alias `Task`). After a worker is spawned, the hook injects a **non-blocking** `additionalContext` reminder to run the verification gate for high-stakes work. It is a **soft reminder only** — it never blocks or fails a tool call, and the orchestrator is free to skip it for trivial/read-only work. The hook emits a no-op (`{}`) when the spawned agent *is* the `verifier`, so it never nags you to verify the verifier (which would invite an infinite loop). The script depends only on POSIX `sh` + `grep`/`sed` (no `jq` requirement) and defensively reads several possible agent-type field names.

### 5. Self-learning journal loop (SessionEnd + SessionStart + reconciler)

The plugin ships a v2 self-learning loop that accumulates session knowledge, surfaces it for review at the next session start, and periodically triggers a deeper consolidation into skill/recipe improvements — all without touching the network, without extra dependencies, and without auto-applying anything.

#### The two-hook cycle

**SessionEnd (`hooks/session-journal.sh`):** at the end of every session, this hook reads `cwd`, `session_id`, `reason`, and `transcript_path` from the hook payload and appends a timestamped entry to `.claude/journal/<YYYY-MM-DD>-<session_id>.md` inside the project root. It also appends a line to `.claude/.skill-update-pending` — a simple counter file that records how many sessions have passed since the last review. Both writes are append-only and non-blocking (always exit 0).

**SessionStart (`hooks/session-start-skill-review.sh`):** at the start of the next session, this hook reads the pending-marker and counts the `<!-- learning -->` sentinel lines in `.claude/journal/LEARNINGS.md`. It then chooses one of three branches:

- **Branch A — reconcile pass due:** the delta between the current learning count and the last-reconciled count has reached or exceeded the threshold (`SELF_LEARNING_RECONCILE_THRESHOLD`, default 10). The hook resets the counter and emits an escalated `additionalContext` nudge asking Claude to do a full consolidation pass via the `reconcile-learnings` skill.
- **Branch B — normal review:** `.skill-update-pending` exists (one or more sessions recorded since the last review). The hook consumes the marker and emits a PROPOSE-not-apply debrief nudge asking Claude to read the recent journal entries, synthesise learnings, append a `<!-- learning -->` block to `LEARNINGS.md`, and run the dedupe gate before proposing any skill change.
- **Branch C — silent:** no marker and no threshold breach; the hook exits without output.

The hook is suppressed when `SessionStart` fires due to context compaction (`source == "compact"`), so compaction restarts do not generate spurious nudges.

#### Enriched LEARNINGS.md capture

Each learning block appended to `.claude/journal/LEARNINGS.md` must begin with a line containing exactly `<!-- learning -->` (the sentinel the loop counts), followed by a heading and four fields:

```
<!-- learning -->
## YYYY-MM-DD · session <id>
**Learned:** ...
**Decided:** ...
**Candidate skill/recipe updates:** ...
**Dedupe check:** ...
```

The sentinel is counted with `grep -c -x -F '<!-- learning -->'` (whole-line, fixed-string, case-sensitive). Do not vary it.

#### `skill-overlap.sh` dedupe gate

Before any skill or recipe is added or updated, `scripts/skill-overlap.sh` searches `~/.claude/skills`, `~/.claude/plugins`, `.claude/skills`, and `.claude/recipes` for `.md` files matching the candidate keywords. It prints hits (up to 20 per root per keyword) and reminds Claude to PROPOSE-not-apply rather than auto-edit. The script depends only on `bash`+`grep`+`find` (no network, no `jq`).

It lives in `scripts/`, not `hooks/`, because it's a manual CLI helper invoked by the reconcile-learnings skill — it is deliberately not wired into `hooks.json`.

#### Reconciler threshold and env knob

The reconcile threshold defaults to 10 new `<!-- learning -->` sentinels since the last pass. Override it per-project or globally by setting `SELF_LEARNING_RECONCILE_THRESHOLD` in your environment (e.g. `export SELF_LEARNING_RECONCILE_THRESHOLD=5`). Non-numeric values fall back to 10.

#### Manual `reconcile-learnings` skill

The `skills/reconcile-learnings/SKILL.md` skill ships a step-by-step reconcile procedure you can invoke on demand (trigger phrases: "reconcile learnings", "consolidate learnings", etc.). It walks through reading the journal, running `skill-overlap.sh` for each candidate, proposing consolidated edits via `skill-creator`, and resetting the reconcile counter.

#### PROPOSE-not-apply / zero-network / zero-dep properties

- **PROPOSE-not-apply:** no hook or skill auto-edits any file. All proposed changes go through `skill-creator` and require explicit review.
- **Zero network calls:** every script uses only local file I/O, `grep`, `wc`, `date`, `node` (for JSON parsing the hook payload), and `find`. No outbound requests.
- **Zero extra dependencies beyond `bash` and `node`:** `node` is assumed present because Claude Code itself requires it. No `jq`, no Python, no curl.

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
>    The plugin ships the `orchestrator`, `worker`, and `verifier` agents plus the `PostToolUse:Agent` reminder hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`); these load automatically once installed, with `${CLAUDE_PLUGIN_ROOT}` resolved for me — I do not need to copy files by hand.
> 2. Before changing any settings, back up my global settings: copy `~/.claude/settings.json` to `~/.claude/settings.json.bak` (skip if the file does not exist).
> 3. Apply the machine-local settings that do NOT travel in a plugin, merging into existing config rather than overwriting it — never drop my existing hooks, permissions, or other keys:
>    - Set the orchestrator thread to a strong model (e.g. Opus) via `/config`.
>    - Set the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` so agent teams work.
>    - If I want the orchestrator to be the main thread, point my `agent` setting at it (or note that I can launch with `claude --agent orchestrator`).
>    - Approve the tool/command permissions the orchestrator and its subagents need (Bash, file writes, network) when prompted.
> 4. Verify the install: confirm `agent-orchestrator` shows up via `/plugin` (installed), that `orchestrator`, `worker`, and `verifier` are listed as available agents, and that a `PostToolUse` hook with matcher `Agent|Task` running `verify-reminder.sh` is registered. Report exactly what you changed and anything you skipped.
>
> Prerequisite: the reminder hook is a POSIX shell script, so on Windows make sure an `sh` (e.g. Git Bash) is available to Claude Code. `jq` is not required.

## Post-install manual checklist (these do NOT travel in a plugin)

A plugin ships the agent/hook definitions only. The following are machine-local settings that are **not** packaged and must be re-done on every machine where you install this plugin:

- [ ] **Approve permissions.** Grant the tool/command permissions the orchestrator and its subagents need (e.g. Bash, file writes, network) in your settings or when prompted.
- [ ] **Set the model.** Run `/config` and select a strong model (e.g. Opus) for the orchestrator thread, per the model-tiering guidance.
- [ ] **Enable agent teams.** Set the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` so the orchestrator can use agent teams.
- [ ] **Make the orchestrator the active agent.** Point your `agent` setting (or `claude --agent orchestrator`) at it if you want it to run as the main thread.
- [ ] **Copy any status line script.** If you use a custom status line, copy the script over and re-point your settings at it.
- [ ] **Set voice / marketplaces / other local prefs.** Re-apply voice settings, re-add any plugin marketplaces, and any other per-machine configuration you rely on.
- [ ] **(Hook prerequisite)** The reminder hook runs a POSIX shell script. On Windows, ensure a `sh` (e.g. Git Bash) is available to Claude Code so the hook can execute. `jq` is **not** required.
- [ ] **(Self-learning: gitignore entries)** The self-learning loop writes files that should not be committed to version control: `.claude/journal/`, `.claude/.skill-update-pending`, and `.claude/.reconcile-state`. A plugin cannot set git config, so you must add these to your global gitignore yourself. Add them via `core.excludesFile`: run `git config --global core.excludesFile ~/.gitignore_global` (if not already set), then append `.claude/journal/`, `.claude/.skill-update-pending`, and `.claude/.reconcile-state` to that file.
- [ ] **(Self-learning: avoid double-registration)** If you already have `SessionStart` or `SessionEnd` hooks hand-wired in `~/.claude/settings.json` pointing at the same scripts (e.g. from a prior hand-copy install), installing this plugin will double-register them — Claude Code will run the hook twice per event. When migrating from a hand-wired install to the plugin, remove the hand-wired `SessionStart`/`SessionEnd` entries from `~/.claude/settings.json` before or immediately after installing the plugin.
- [ ] **Version stamp check.** Version stamp in every `agents/*.md` first body line MUST equal `plugin.json` version — grep-check before tagging.

## Usage

Once installed, route your requests through the orchestrator agent. Hand it a goal rather than a single mechanical step — it will:

1. **Route** the task via the dispatch protocol (matching it to the best available skill or specialized agent),
2. **Decompose** and spawn subagents or teams (in parallel where possible),
3. **Verify** high-stakes output through the `verifier` gate with bounded retries,
4. **Synthesize** and return a clear answer.

For trivial or conversational follow-ups it answers directly; everything else gets delegated.

## License

MIT — see [LICENSE](./LICENSE).
