# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

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

- Spawns the dedicated **`verifier`** subagent (agentType `agent-orchestrator:verifier`) — an independent, adversarial, **read-only** checker with its own fresh context. It tries to *falsify* the producer's work, re-deriving correctness from the actual artifact and ground truth (files, command output, sources) rather than the producer's summary, and returns a binary **`VERIFIED` / `ISSUES FOUND`** verdict grounded in evidence.
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

### 6. Self-learning journal (SessionEnd hook + manual reconciler)

The plugin ships a small journal loop. It records what happened, captures candidate learnings, and gives you a skill to consolidate them. It does not apply anything on its own, and nothing nudges you at session start.

Honest properties: the hooks are Python and shell (`session-journal.sh` is bash and uses `node` to parse the payload; `verify-reminder.sh` is POSIX `sh`; `model-tier-gate.py` and `scout-readonly-gate.py` are Python). `session-journal.sh` can invoke `claude -p`, which makes a network call to the model API, and it writes to `~/.claude/journal/LEARNINGS.md` outside the project.

#### SessionEnd: `hooks/session-journal.sh`

Registered in `hooks/hooks.json` (10s timeout). It always exits 0 (fail-open). On every session end it:

1. Appends a `session_end` stub to `.claude/journal/<YYYY-MM-DD>-<session_id>.md` in the project (`cwd`). The stub records the reason, the session ID, and the transcript path. When the transcript is readable it adds a `spawns: worker=N verifier=N judge=N scout=N` line, grepped from the `subagent_type` values in the transcript.
2. If the session was substantive (at least 12 `tool_use` blocks and at least 2 file-edit blocks: Edit, Write, MultiEdit, NotebookEdit), writes a capture prompt and launches a detached background `claude -p --permission-mode bypassPermissions --allowedTools Read Edit Write`. That run reads the transcript and either does nothing or appends one block to the **global** `~/.claude/journal/LEARNINGS.md` (not a per-project file). `bypassPermissions` is used because Claude Code's sensitive-path guard blocks non-interactive writes under `~/.claude/` otherwise; the allowed-tools list limits what the run can use.

Each captured block starts with the sentinel line `<!-- learning -->` (counted whole-line, fixed-string, case-sensitive), then a heading and four fields:

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

Searches `~/.claude/skills`, `~/.claude/plugins`, `.claude/skills`, and `.claude/recipes` for `.md` files matching candidate keywords (up to 20 hits per root per keyword). It needs only `bash`, `grep`, and `find`. It lives in `scripts/` because it is a manual helper called by the reconcile skill, not a hook.

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
>    The plugin ships the `orchestrator`, `worker`, `verifier`, `judge`, and `scout` agents plus the `PostToolUse:Agent` reminder hook (`hooks/hooks.json` → `hooks/verify-reminder.sh`); these load automatically once installed, with `${CLAUDE_PLUGIN_ROOT}` resolved for me — I do not need to copy files by hand.
> 2. Before changing any settings, back up my global settings: copy `~/.claude/settings.json` to `~/.claude/settings.json.bak` (skip if the file does not exist).
> 3. Apply the machine-local settings that do NOT travel in a plugin, merging into existing config rather than overwriting it — never drop my existing hooks, permissions, or other keys:
>    - Set the orchestrator thread to a strong model (e.g. Opus) via `/config`.
>    - Agent teams are disabled fleet-wide (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` since 2026-10-06): teammate tools are clamped to the lead's and hook payloads lose the agent type. Named spawns are plain subagents; track by returned ID. Do not enable them.
>    - If I want the orchestrator to be the main thread, point my `agent` setting at it (or note that I can launch with `claude --agent orchestrator`).
>    - Approve the tool/command permissions the orchestrator and its subagents need (Bash, file writes, network) when prompted.
> 4. Verify the install: confirm `agent-orchestrator` shows up via `/plugin` (installed), that `orchestrator`, `worker`, `verifier`, `judge`, and `scout` are listed as available agents, and that a `PostToolUse` hook with matcher `Agent|Task` running `verify-reminder.sh` is registered. Report exactly what you changed and anything you skipped.
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
