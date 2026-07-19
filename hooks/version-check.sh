#!/usr/bin/env bash
# SessionStart hook: agent-orchestrator version-check
#
# Compares the installed plugin version (this repo's own
# .claude-plugin/plugin.json, or plugin.json at repo root as a fallback) against
# the version pinned for agent-orchestrator in the vr-orchestra marketplace
# manifest. Fail-open: any missing file, missing field, or parse failure is
# swallowed silently and the hook exits 0 with no output.
#
# Registered as a SessionStart hook in hooks/hooks.json.

set -uo pipefail

main() {
  local plugin_json="${CLAUDE_PLUGIN_ROOT:-}/.claude-plugin/plugin.json"
  [ -f "$plugin_json" ] || plugin_json="${CLAUDE_PLUGIN_ROOT:-}/plugin.json"
  [ -f "$plugin_json" ] || return 0

  local marketplace_json="${HOME:-}/agents/vr-orchestra/.claude-plugin/marketplace.json"
  [ -f "$marketplace_json" ] || return 0

  local installed
  installed=$(grep -m1 '"version"' "$plugin_json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  [ -n "$installed" ] || return 0

  local pinned
  pinned=$(grep -A 10 '"name"[[:space:]]*:[[:space:]]*"agent-orchestrator"' "$marketplace_json" \
    | grep -m1 '"version"' \
    | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  [ -n "$pinned" ] || return 0

  echo "agent-orchestrator: installed v${installed} | marketplace pin v${pinned}"
  if [ "$installed" != "$pinned" ]; then
    echo "*** VERSION MISMATCH: restart sessions after running plugin update ***"
  fi
  return 0
}

main 2>/dev/null
exit 0
