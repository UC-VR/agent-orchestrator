# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents, agent teams, and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents or teams it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

This plugin adds six patterns on top of plain delegation.

### 1. Dispatch protocol (skill & agent matching)

Before spawning any worker, the orchestrator runs a routing step:

1. **Enumerate** what is actually available *this session* — the skills exposed via the Skill tool and the agent types available to the Agent tool, read from the live list injected into context (never a hardcoded/remembered list, which goes stale).
2. **Match** the task against them — does a specific skill or specialized agent fit better than a generic subagent?
3. **Prefer the specific over the generic** — invoke the matching skill or specialized agent when there is a clear fit.
4. **Log the choice** in one line: `Routing via <skill/agent> because <reason>.` If nothing specific fits, it picks the generic agent by task shape — the `worker`-vs-`general-purpose` tie-breaker. It **defaults to the `worker`** agent for any task whose path is already known: well-scoped, mechanical execution — applying a specified edit, a routine refactor, running a command/test, gathering named files (`worker` is the more specific tool here, carrying the craftsmanship principles and a cheaper tier, so it wins these ties). It **reserves `general-purpose`** for open-ended, exploratory, or multi-step research where the path is *not* known up front — locating something when you're unsure of the first hit, or work whose steps only emerge as you go. Tie-breaker question: *is the what-and-where already specified?* If yes → `worker`; if it still needs discovery → `general-purpose`.

This keeps routing **current** (reads the live list) and **auditable** (logs the why).

The repo also ships a **`worker`** agent: the default leaf executor for minor, well-scoped tasks, running on a cheaper model tier with built-in craftsmanship principles (think-before-coding, simplicity, surgical changes, goal-driven verification).

#### Scout (bulk input pre-analysis)

Bulk input (>~10 files or >~2K lines) feeding one downstream agent gets pre-analyzed by the **`scout`** agent first, so the planner reads a compact, priority-tagged briefing instead of the raw files. Scout runs the same model tier as `worker` — its value is an enforced read-only toolbelt (Read/Glob/Grep/Bash, Bash gated to inspection commands only by the `scout-readonly-gate.py` `PreToolUse` hook) and context isolation, not a cheaper model. Its briefing is capped (≤20% of source lines, ~8K chars). It never fixes, decides, or audits (a correctness check against a spec is `verifier` work) — it is not a verifier.

### 2. Tournament Trigger + comparative gate (offer, don't impose)

Some tasks are decisions, not executions — a design, a plan, a wording, an approach — where two competent producers would reasonably differ. The orchestrator flags these but never forces a tournament on its own: it asks via AskUserQuestion ("Tournament — N producers + judge, or a single producer?", defaulting to single) and only fans out unprompted when the user's own words already asked to compare or rank options.

Once a tournament runs: name 2–3 materially different approaches, spawn one producer per approach in parallel (each emits one de-identified candidate, no self-ranking), spawn the **`judge`** subagent with explicit criteria to score, rank, declare a winner, and list grafts from the losers, then run the normal verifier gate on the grafted winner only — never on every candidate.

The comparative gate itself has three tiers: **invariant** (never present a producer's own ranking as your conclusion — label it "producer-ranked, unjudged"), **offer** (default: when a report contains ≥2 ranked options, offer the judge pass via AskUserQuestion), and **mandatory** (only when the ranking will be acted on unreviewed in the same session, or the user explicitly asked for a ranking as the deliverable).

The `judge` is shipped as its own agent (`agents/judge.md`, `model: opus`): read-only, evidence-grounded per-criterion scoring, honest tie-flagging, and a graft list — it ranks, it does not fix or merge.

### 3. Verification gate (backed by the `verifier` subagent)

Before delivering high-stakes output (code changes, multi-file edits, refactors, config changes), the orchestrator runs a verification gate:

- Spawns the dedicated **`verifier`** subagent (agentType `verifier`) — an independent, adversarial, **read-only** checker with its own fresh context. It tries to *falsify* the producer's work, re-deriving correctness from the actual artifact and ground truth (files, command output, sources) rather than the producer's summary, and returns a binary **`VERIFIED` / `ISSUES FOUND`** verdict grounded in evidence.
- Uses **bounded retries** — on `ISSUES FOUND`, the blocking findings go back to the producer or a fixer agent, capped at ~1–2 iterations to avoid infinite loops.
- **Escalates** the unresolved issue to the user after the cap instead of looping or shipping broken work.

Governing principle: **for mechanical work the bottleneck is verification, not generation** — a plausible change is cheap, confirming it is the hard part. **For decision-shaped work the bottleneck is comparison** — a single draft has nothing to be better than. Comparison is offered by default and imposed only when the choice will be acted on unreviewed.

The `verifier` is shipped as its own agent (`agents/verifier.md`): it checks, it does not fix (no Write/Edit tools by design), it never delegates, and it never rubber-stamps.

### 4. Model-tiering guidance (enforced)

The orchestrator matches model strength to task difficulty — and since v1.6.0 this is mechanically enforced, not just prose:

- The **orchestrator main thread stays on the strongest tier (Fable/Opus)**; it never spawns a subagent on that tier.
- Every Agent-tool spawn must carry an **explicit `model` param** — no inheritance.
- **`model: opus`** for reasoning-heavy work (planning, verification, judging); **`model: sonnet`** for execution/mechanical work (the `worker` default); **Haiku is never used**.
- A `PreToolUse` **`model-tier-gate`** hook denies any spawn with `haiku`/`fable`, and denies unpinned built-in types (e.g. `general-purpose`, `Explore`, `Plan`, `claude-code-guide`) spawned with no explicit model — while letting pinned agents (`worker`, `verifier`) resolve their own frontmatter tier. It fails open on any internal error, so it never bricks spawning.
- The same hook (since v1.7.2) also denies any Agent/Task spawn that passes a `name` param: Claude Code's in-process teammate path (anthropics/claude-code#81746, #78234, #31977) silently drops the requested agent definition and degrades the spawn to a fixed reduced tool profile when `name` is set. Track agents by the ID the tool call returns and use it with `SendMessage` for follow-ups. Escape hatch for tmux-mode experiments: `ORCHESTRATOR_ALLOW_NAMED_SPAWNS=1`.
- (Since v1.7.3) That named-spawn check only runs when the incoming call's `tool_name` is `Agent` or `Task` — any other tool (e.g. `Bash`, which also accepts a `name`-shaped argument for unrelated reasons) is allowed through untouched. This keeps the gate scoped to spawns even though its `hooks.json` matcher already restricts it to `Agent|Task`, so the script enforces the same scope it claims.

This can cut cost substantially on well-scoped tasks — conditional on the review gate reliably catching cheap-model errors.

### 5. Reminder hook (soft nudge, not enforcement)

The plugin registers a `PostToolUse` hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`) on the subagent-spawning tool (`Agent`, with its legacy alias `Task`). After a producer is spawned, the hook injects a **non-blocking** `additionalContext` reminder naming both gates: verifier for mechanical output, judge-then-verifier for decision-shaped output or a report with ≥2 ranked options. It is a **soft reminder only** — it never blocks or fails a tool call, and the orchestrator is free to skip it for trivial/read-only work. The hook emits a no-op (`{}`) when the spawned agent *is* the `verifier`, `judge`, or `scout` — matched on the bare role name after stripping any `agent-orchestrator:` namespace prefix, so it never nags you to verify the verifier (which would invite an infinite loop). The script depends only on POSIX `sh` + `grep`/`sed` (no `jq` requirement) and defensively reads several possible agent-type field names.

### 6. Self-learning journal loop (SessionEnd + SessionStart + reconciler)

The plugin ships a v2 self-learning loop that accumulates session knowledge, surfaces it for review at the next session start, and periodically triggers a deeper consolidation into skill/recipe improvements — all without touching the network, without extra dependencies, and without auto-applying anything.

#### The two-hook cycle

**SessionEnd (`hooks/session-journal.sh`):** at the end of every session, this hook reads `cwd`, `session_id`, `reason`, and `transcript_path` from the hook payload and appends a timestamped entry to `.claude/journal/<YYYY-MM-DD>-<session_id>.md` inside the project root, plus a `spawns: worker=N verifier=N judge=N scout=N` line grepped from the transcript when it's available. It also appends a line to `.claude/.skill-update-pending` — a simple counter file that records how many sessions have passed since the last review. Both writes are append-only and non-blocking (always exit 0).

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
3. **(Tournament)** for decision-shaped work, offer N competing producers + a `judge` pass rather than impose one,
4. **Judge** the candidates when a tournament ran, or when the offer to rank ≥2 options is accepted,
5. **Verify** high-stakes output (the winner, or the sole producer's output) through the `verifier` gate with bounded retries,
6. **Synthesize** and return a clear answer.

For trivial or conversational follow-ups it answers directly; everything else gets delegated.

## Changelog

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
