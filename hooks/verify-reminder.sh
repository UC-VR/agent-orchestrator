#!/usr/bin/env sh
# verify-reminder.sh — SOFT reminder, NOT enforcement.
#
# Registered as a PostToolUse hook on the subagent-spawning tool (Agent, alias Task).
# After the orchestrator spawns a worker, this prints an `additionalContext` reminder
# nudging it to run the verification gate (spawn the `verifier` subagent) for
# high-stakes work. It does NOT block, fail, or force anything — Claude is free to
# ignore the nudge. The orchestrator's own judgement still decides whether to verify.
#
# Loop-guard: if the spawned agent IS the verifier, judge, or scout, we emit `{}`
# (no reminder) so we never nag the model to verify the verifier — which would
# invite an infinite loop.
#
# Input: the PostToolUse hook JSON arrives on stdin.
# Output (stdout): either
#   {}                                              (no-op / verifier case)
# or
#   {"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"..."}}
#
# This script intentionally does NOT depend on `jq` (it is not installed everywhere).
# It extracts the spawned agent type with a portable grep/sed pass, defensively
# trying several field names because the exact key varies by Claude Code version
# (subagent_type / agentType / agent_type / task_type).

input="$(cat)"

# Pull the first value for any of the likely agent-type keys.
# Matches:  "subagent_type": "verifier"   (any of the key spellings, any spacing)
agent_type="$(printf '%s' "$input" \
  | grep -oE '"(subagent_type|agentType|agent_type|task_type)"[[:space:]]*:[[:space:]]*"[^"]*"' \
  | head -n 1 \
  | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/')"

# Normalize to lowercase for the comparison.
agent_type_lc="$(printf '%s' "$agent_type" | tr '[:upper:]' '[:lower:]')"

# Loop-guard: spawning verifier/judge/scout -> no reminder (all three are
# read-only checking/advisory roles; nagging them to "go verify" recreates
# the verify-the-verifier loop).
if [ "$agent_type_lc" = "verifier" ] || [ "$agent_type_lc" = "judge" ] || [ "$agent_type_lc" = "scout" ]; then
  printf '%s\n' '{}'
  exit 0
fi

# Otherwise, inject the soft reminder.
reminder='Reminder (soft, non-blocking): a worker subagent was just spawned. For high-stakes output (code changes, multi-file edits, refactors, config changes, or anything with correctness risk), run the verification gate before delivering to the user — spawn the dedicated `verifier` subagent (agentType `verifier`) to adversarially check the result, with bounded 1-2 retries, then escalate rather than spin. Skip this for trivial or read-only work.'

# Emit valid JSON. Build it without jq; the reminder text contains no double quotes
# or backslashes, so direct interpolation is safe here.
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$reminder"
exit 0
