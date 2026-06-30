# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents, agent teams, and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents or teams it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

This plugin adds four patterns on top of plain delegation.

### 1. Dispatch protocol (skill & agent matching)

Before spawning any worker, the orchestrator runs a routing step:

1. **Enumerate** what is actually available *this session* — the skills exposed via the Skill tool and the agent types available to the Agent tool, read from the live list injected into context (never a hardcoded/remembered list, which goes stale).
2. **Match** the task against them — does a specific skill or specialized agent fit better than a generic subagent?
3. **Prefer the specific over the generic** — invoke the matching skill or specialized agent when there is a clear fit.
4. **Log the choice** in one line: `Routing via <skill/agent> because <reason>.` If nothing specific fits, it defaults to the **`worker`** agent (the catch-all for minor, well-scoped tasks) and falls back to a general-purpose agent only when `worker` is unsuitable.

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

## How to add it

Install directly from git:

```
/plugin install git+https://github.com/uc-vr/agent-orchestrator.git
```

Or via a marketplace:

```
/plugin marketplace add uc-vr/agent-orchestrator
/plugin install agent-orchestrator
```

## Post-install manual checklist (these do NOT travel in a plugin)

A plugin ships the agent/hook definitions only. The following are machine-local settings that are **not** packaged and must be re-done on every machine where you install this plugin:

- [ ] **Approve permissions.** Grant the tool/command permissions the orchestrator and its subagents need (e.g. Bash, file writes, network) in your settings or when prompted.
- [ ] **Set the model.** Run `/config` and select a strong model (e.g. Opus) for the orchestrator thread, per the model-tiering guidance.
- [ ] **Enable agent teams.** Set the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` so the orchestrator can use agent teams.
- [ ] **Make the orchestrator the active agent.** Point your `agent` setting (or `claude --agent orchestrator`) at it if you want it to run as the main thread.
- [ ] **Copy any status line script.** If you use a custom status line, copy the script over and re-point your settings at it.
- [ ] **Set voice / marketplaces / other local prefs.** Re-apply voice settings, re-add any plugin marketplaces, and any other per-machine configuration you rely on.
- [ ] **(Hook prerequisite)** The reminder hook runs a POSIX shell script. On Windows, ensure a `sh` (e.g. Git Bash) is available to Claude Code so the hook can execute. `jq` is **not** required.

## Usage

Once installed, route your requests through the orchestrator agent. Hand it a goal rather than a single mechanical step — it will:

1. **Route** the task via the dispatch protocol (matching it to the best available skill or specialized agent),
2. **Decompose** and spawn subagents or teams (in parallel where possible),
3. **Verify** high-stakes output through the `verifier` gate with bounded retries,
4. **Synthesize** and return a clear answer.

For trivial or conversational follow-ups it answers directly; everything else gets delegated.

## License

MIT — see [LICENSE](./LICENSE).
