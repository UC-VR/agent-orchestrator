# agent-orchestrator

A Claude Code plugin that packages an **orchestrator-only** agent: a main thread that never does work itself, but decomposes every request and delegates it to subagents, agent teams, and workflows — then synthesizes the results for you.

## What it is

The orchestrator philosophy is **delegate everything**. The orchestrator's job is planning, routing, and judgement — not execution. All file edits, shell commands, builds, tests, and research are performed by subagents or teams it spawns. The orchestrator uses read-only tools (Read/Glob/Grep) solely to scope work and write good delegation prompts, then relays a clear synthesized answer to you.

This plugin adds two patterns on top of plain delegation:

### 1. Verification-gate pattern

Before delivering high-stakes output (code changes, multi-file edits, refactors, config changes), the orchestrator runs a verification gate:

- Spawns a **separate verifier agent** with independent context to adversarially check the producer's work — does it do what was asked, are there bugs/regressions, does it build and test cleanly?
- Uses **bounded retries** — on failure, the finding goes back to the producer or a fixer agent, capped at ~1–2 iterations to avoid infinite loops.
- **Escalates** the unresolved issue to the user after the cap instead of looping or shipping broken work.

Governing principle: **the bottleneck is verification, not generation.** Never deliver unverified high-stakes output.

### 2. Model-tiering guidance

The orchestrator matches model strength to task difficulty:

- Keep the **orchestrator itself on a strong model** (e.g. Opus) for planning, decomposition, and the review/verification gate.
- Delegate **well-scoped execution** (edits, mechanical refactors, searches, test runs) to **cheaper/faster models** (e.g. Haiku/Sonnet) via the Agent tool's `model` option or Workflow `opts.model` / `opts.effort`.
- Reserve the **strongest models for the hardest reasoning/verify/judge stages**.

This can cut cost substantially on well-scoped tasks — conditional on the review gate reliably catching cheap-model errors.

## Installation

Install directly from git:

```
/plugin install git+https://github.com/uc-vc/agent-orchestrator.git
```

Or via a marketplace (if you have added one that lists this plugin):

```
/plugin marketplace add uc-vc/agent-orchestrator
/plugin install agent-orchestrator
```

## Post-install manual steps (do NOT travel in a plugin)

A plugin ships the agent definition only. The following are machine-local settings that are **not** packaged and must be re-done on every machine where you install this plugin:

- [ ] **Approve permissions.** Grant the tool/command permissions the orchestrator and its subagents need (e.g. Bash, file writes, network) in your settings or when prompted.
- [ ] **Set the model.** Run `/config` and select a strong model (e.g. Opus) for the orchestrator thread, per the model-tiering guidance.
- [ ] **Enable agent teams.** Set the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` so the orchestrator can use agent teams.
- [ ] **Copy any status line script.** If you use a custom status line, copy the script over and re-point your settings at it.
- [ ] **Set voice / marketplaces / other local prefs.** Re-apply voice settings, re-add any plugin marketplaces, and any other per-machine configuration you rely on.

## Usage

Once installed, route your requests through the orchestrator agent. Hand it a goal rather than a single mechanical step — it will decompose the work, spawn subagents or teams (in parallel where possible), run the verification gate on high-stakes output, and return a synthesized answer. For trivial or conversational follow-ups it answers directly; everything else gets delegated.

## License

MIT — see [LICENSE](./LICENSE).
