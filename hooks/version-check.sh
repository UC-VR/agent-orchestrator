#!/usr/bin/env bash
# SessionStart hook: agent-orchestrator version-check
#
# For each of the 5 vr-orchestra plugins, resolves the actively installed
# version via ${HOME}/.claude/plugins/installed_plugins.json (the
# authoritative map of which version is active per plugin -- NOT by
# globbing the plugins/cache directory, since multiple version subfolders
# can coexist on disk) -> installPath -> installPath/.claude-plugin/plugin.json
# (falling back to installPath/plugin.json), and compares it against the
# version pinned for that plugin in the vr-orchestra marketplace manifest.
#
# Also warns if the vr-orchestra checkout itself -- the source of the
# marketplace pin file above, located via known_marketplaces.json rather
# than an assumed path -- is behind its cached origin/main, since a stale
# checkout would make every comparison above stale too.
#
# Fail-open: any missing file, missing field, or parse failure for a given
# plugin (or for the staleness check) is swallowed silently and that check
# is skipped; the hook never exits non-zero and never blocks a session.
#
# Registered as a SessionStart hook in hooks/hooks.json.

set -uo pipefail

MARKETPLACE_NAME="vr-orchestra"

# Enumerates plugin names straight from the vr-orchestra marketplace manifest
# (scoped to the "plugins" array so the manifest's own top-level "name" and
# "owner.name" fields aren't picked up) instead of a hardcoded list, so newly
# added/removed plugins are covered without editing this script. Fail-open:
# any missing file or parse failure just yields no names, handled by the
# caller.
list_plugin_names() {
  local marketplace_json="$1"
  [ -f "$marketplace_json" ] || return 0
  sed -n '/"plugins"[[:space:]]*:/,$p' "$marketplace_json" \
    | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | sed -E 's/.*"name"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/'
  return 0
}

# Prints a comparison line (and mismatch warning) for one plugin. Any
# failure to resolve a field for this plugin just returns 0 and moves on --
# it must never take the other plugins or the rest of the hook down with it.
check_plugin() {
  local name="$1" installed_json="$2" marketplace_json="$3"

  local block
  block=$(grep -A 20 "\"${name}@${MARKETPLACE_NAME}\"" "$installed_json") || return 0
  [ -n "$block" ] || return 0

  local install_path
  install_path=$(printf '%s\n' "$block" | grep -m1 '"installPath"' \
    | sed -E 's/.*"installPath"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  [ -n "$install_path" ] || return 0

  local plugin_json="${install_path}/.claude-plugin/plugin.json"
  [ -f "$plugin_json" ] || plugin_json="${install_path}/plugin.json"
  [ -f "$plugin_json" ] || return 0

  local installed
  installed=$(grep -m1 '"version"' "$plugin_json" | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  [ -n "$installed" ] || return 0

  local pinned
  pinned=$(grep -A 10 "\"name\"[[:space:]]*:[[:space:]]*\"${name}\"" "$marketplace_json" \
    | grep -m1 '"version"' \
    | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  [ -n "$pinned" ] || return 0

  echo "${name}: installed v${installed} | marketplace pin v${pinned}"
  if [ "$installed" != "$pinned" ]; then
    echo "*** VERSION MISMATCH (${name}): restart sessions after running plugin update ***"
  fi
  return 0
}

# Resolves the vr-orchestra checkout path from Claude Code's own
# known_marketplaces.json (installLocation for the "vr-orchestra" entry) --
# the authoritative record of where this host actually installed it --
# instead of assuming ${HOME}/agents/vr-orchestra. Falls back to that
# assumed path if the marketplaces file is missing, unparseable, or points
# at a directory that doesn't exist, so behavior on hosts using the
# conventional layout is unchanged.
resolve_vr_orchestra_dir() {
  local known="${HOME:-}/.claude/plugins/known_marketplaces.json"
  local fallback="${HOME:-}/agents/vr-orchestra"

  if [ -f "$known" ]; then
    local block
    block=$(grep -A 6 "\"${MARKETPLACE_NAME}\"[[:space:]]*:" "$known" 2>/dev/null)
    if [ -n "$block" ]; then
      local loc
      loc=$(printf '%s\n' "$block" | grep -m1 '"installLocation"' \
        | sed -E 's/.*"installLocation"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' \
        | sed 's/\\\\/\//g')
      if [ -n "$loc" ] && [ -d "$loc" ]; then
        printf '%s\n' "$loc"
        return 0
      fi
    fi
  fi

  printf '%s\n' "$fallback"
  return 0
}

# Warns if the vr-orchestra checkout (source of the marketplace pin file)
# is behind its already-fetched origin/main. Deliberately does NOT run
# `git fetch` -- this hook runs on every session start and must stay cheap
# and offline-safe, so it only compares against whatever refs are already
# cached locally.
check_vr_orchestra_staleness() {
  local dir="$1"
  [ -n "$dir" ] || return 0
  [ -d "${dir}/.git" ] || return 0
  command -v git >/dev/null 2>&1 || return 0
  command -v timeout >/dev/null 2>&1 || return 0

  local behind
  behind=$(timeout 5 git -C "$dir" rev-list HEAD..origin/main --count 2>/dev/null)
  [ -n "$behind" ] || return 0
  case "$behind" in (''|*[!0-9]*) return 0 ;; esac

  if [ "$behind" -gt 0 ]; then
    echo "*** VR-ORCHESTRA CHECKOUT STALE: ${dir} is ${behind} commit(s) behind cached origin/main -- version-check pins above may be stale, run git fetch/pull ***"
  fi
  return 0
}

main() {
  local installed_json="${HOME:-}/.claude/plugins/installed_plugins.json"
  local vr_orchestra_dir
  vr_orchestra_dir=$(resolve_vr_orchestra_dir)
  local marketplace_json="${vr_orchestra_dir}/.claude-plugin/marketplace.json"

  if [ -f "$installed_json" ] && [ -f "$marketplace_json" ]; then
    local plugins=()
    while IFS= read -r name; do
      [ -n "$name" ] && plugins+=("$name")
    done < <(list_plugin_names "$marketplace_json")

    if [ "${#plugins[@]}" -gt 0 ]; then
      local name
      for name in "${plugins[@]}"; do
        check_plugin "$name" "$installed_json" "$marketplace_json"
      done
    fi
  fi

  check_vr_orchestra_staleness "$vr_orchestra_dir"

  return 0
}

main 2>/dev/null
exit 0
