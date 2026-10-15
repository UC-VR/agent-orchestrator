#!/usr/bin/env python3
# PreToolUse gate: enforce model-tier policy on Agent/Task spawns. FAIL-OPEN on any error.
# Policy: subagents run sonnet or opus. fable is banned everywhere (orchestrator main thread only)
# EXCEPT the exact pool id "pool-fable" for the plugin's `planner` agent (1.10.1).
# Model values are matched by SUBSTRING on the lowercased string, so 9router pool ids work the same
# as aliases: "pool-fable"/"pool-fable-high" contain "fable" (denied unless the planner exception
# applies), "pool-haiku" contains "haiku" (allowlisted types only), "pool-opus*"/"pool-sonnet*" pass.
# The Agent tool's `model` param is an enum (sonnet|opus|haiku|fable), so pool ids normally arrive
# via agent frontmatter, not here.
# Haiku 5.5 ("haiku", "pool-haiku", "claude-haiku-5-5") is allowed ONLY for the bare agent types in
# HAIKU_OK (cheap enumeration/lookup work); never for verifier, judge, security-reviewer, planner,
# workers or any code-editing type. "pool-haiku-high" is narrower still: scout and explorer only (HAIKU_HIGH_OK). Haiku 4.x / 3.x ids are denied for every type. Precedence: fork deny,
# forbidden (fable) deny, haiku deny, unpinned-no-model deny all take effect over any input strip.
import os, sys, json, re, subprocess, shutil

MIN_STRIP_VERSION = (2, 1, 290)   # first CLI where rules/safety checks re-run after a hook rewrites input
TEAMMATE_ONLY_KEYS = ("name", "team_name", "teamName", "mode")
STRIP_NOTE = ("Agent spawn: `name` was removed (agent teams are disabled by fleet policy; "
              "named spawns would run as in-process teammates with clamped tools). Track this "
              "agent by the ID in the tool result and use SendMessage with that ID for follow-ups.")

ISOLATION_NOTE = ("Agent spawn: `isolation` was removed (cwd is not a git repo, so a worktree "
                  "cannot be created). The agent runs in the shared cwd.")

# Built-in types with no frontmatter pin: with no explicit model they would inherit the caller's model.
UNPINNED = {"general-purpose", "explore", "plan", "claude", "claude-code-guide", "statusline-setup"}
FORBIDDEN = ("fable",)
# Bare lowercase subagent_type values (after prefix strip) that may run Haiku 5.5.
HAIKU_OK = {"scout", "explorer", "explore", "claude-code-guide", "statusline-setup"}
# Never Haiku, even if someone later adds them to HAIKU_OK (enforced below).
HAIKU_NEVER = {"verifier", "final-verifier", "judge", "security-reviewer", "planner", "generalist"}
HAIKU_OK -= HAIKU_NEVER
# Types that may use the "-high" haiku pool (pool-haiku-high); other haiku-ok types get plain haiku only.
HAIKU_HIGH_OK = {"scout", "explorer"}
# The only fable exception: exact model id + the plugin-qualified type, taken from `subagent_type`
# ONLY (never `agentType`, never a bare "planner": bare names do not resolve to this plugin's agents
# and could be an untrusted ~/.claude/agents/planner.md). If `agentType` is also set and disagrees,
# no exception. The planner agent is pinned to pool-fable in its own frontmatter.
# HAIKU_NEVER stays broad: "planner" matches bare and prefixed forms (bare = text after the last ":").
FABLE_OK_MODEL = "pool-fable"
FABLE_OK_TYPE = "agent-orchestrator:planner"
# Pinned fleet types (orchestrator, worker, planner, generalist, verifier, final-verifier,
# judge, scout, explorer, security-reviewer) carry a pool id in their frontmatter, so they are simply absent
# from UNPINNED: with no explicit model they resolve to that pin (Rule 3/default allow). There is no separate pinned list to maintain.
# Haiku 4.x / 3.x model-id substrings: always denied.
HAIKU_OLD = ("haiku-4", "3-5-haiku", "3-haiku", "claude-haiku-4")

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

def _parse_ver(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else None

def cli_version():
    """Return (major, minor, patch) of the running Claude Code CLI, or None if unknown. Never raises.
    Order: test override, CLAUDE_CODE_VERSION, AI_AGENT (Claude Code sets claude-code_<maj>-<min>-<pat>_...
    in hook processes), then `claude --version` cached by binary path+mtime."""
    try:
        for var in ("MODEL_TIER_GATE_CLI_VERSION", "CLAUDE_CODE_VERSION"):
            v = _parse_ver(os.environ.get(var))
            if v:
                return v
        m = re.search(r"claude-code_(\d+)-(\d+)-(\d+)", os.environ.get("AI_AGENT", ""))
        if m:
            return tuple(int(x) for x in m.groups())
        exe = shutil.which("claude")
        if not exe:
            return None
        key = "%s|%s" % (os.path.realpath(exe), os.stat(exe).st_mtime_ns)
        cache = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "model-tier-gate.cliver")
        try:
            with open(cache) as f:
                k, _, val = f.read().strip().partition("\t")
            if k == key:
                return _parse_ver(val)
        except Exception:
            pass
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=2).stdout
        v = _parse_ver(out)
        if v:
            try:
                fd = os.open(cache, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write("%s\t%d.%d.%d\n" % ((key,) + v))
            except Exception:
                pass
        return v
    except Exception:
        return None

def in_git_work_tree(cwd):
    """True iff cwd is inside a git work tree. Returns None (unknown) on any error
    (git missing, timeout) so the caller leaves `isolation` untouched."""
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=3)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return None

def main():
    data = json.loads(sys.stdin.read())          # malformed -> except -> allow
    if data.get("tool_name") not in ("Agent", "Task"):
        sys.exit(0)   # out of scope for this gate; allow
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        sys.exit(0)
    model = ti.get("model")
    model_s = model.strip().lower() if isinstance(model, str) else ""
    if model_s == "inherit":
        model_s = ""   # "inherit" == no model: resolves to the caller's (fable) tier
    atype = ti.get("subagent_type")
    if not isinstance(atype, str) or not atype:
        atype = ti.get("agentType")
    atype_s = atype.strip().lower() if isinstance(atype, str) else ""
    # Trusted planner identity for the fable exception: subagent_type only, exact match, no conflict.
    st = ti.get("subagent_type")
    st_s = st.strip().lower() if isinstance(st, str) else ""
    at = ti.get("agentType")
    conflict = at not in (None, "") and not (isinstance(at, str) and at.strip().lower() == st_s)
    planner_ok = st_s == FABLE_OK_TYPE and not conflict
    bare = atype_s.split(":")[-1] if atype_s else ""   # strip "agent-orchestrator:" prefix
    if not bare:
        bare = "general-purpose"   # Claude Code defaults a missing subagent_type to general-purpose

    # Rule 0: named spawns silently degrade tools via the CLI's in-process teammate
    # path (anthropics/claude-code#81746, #78234, #31977) — the requested agent
    # definition is dropped and the spawn collapses to a fixed reduced tool profile.
    name = ti.get("name")
    stripped = False
    notes = []
    if name and isinstance(name, str) and name.strip() and os.environ.get("ORCHESTRATOR_ALLOW_NAMED_SPAWNS") != "1":
        ver = cli_version()
        if ver is not None and ver >= MIN_STRIP_VERSION:
            # Strip teammate-only fields via updatedInput; remaining rules run on the stripped input.
            ti = {k: v for k, v in ti.items() if k not in TEAMMATE_ONLY_KEYS}
            stripped = True
            notes.append(STRIP_NOTE)
        else:
            deny("Named spawns are blocked: Claude Code's in-process teammate path "
                 "(anthropics/claude-code#81746/#78234) silently drops the agent "
                 "definition and degrades tools. Omit `name`; use the returned agent ID "
                 "with SendMessage for follow-ups. Override: "
                 "ORCHESTRATOR_ALLOW_NAMED_SPAWNS=1. "
                 "(strip unavailable: CLI < 2.1.290 or version unknown)")

    # Rule 0a: some main-thread models pass isolation:"worktree" on every spawn; outside a
    # git repo that makes the spawn fail. Strip it there (inside a repo it is untouched).
    if ti.get("isolation") == "worktree":
        cwd = data.get("cwd")
        if in_git_work_tree(cwd if isinstance(cwd, str) and cwd else os.getcwd()) is False:
            ti = {k: v for k, v in ti.items() if k != "isolation"}
            stripped = True
            notes.append(ISOLATION_NOTE)

    # Rule 0b: forks inherit the main model and ignore any `model` override.
    if bare == "fork" and os.environ.get("ORCHESTRATOR_ALLOW_FORK") != "1":
        deny("Model-tier policy: fork inherits the orchestrator's model tier; spawn a "
             "typed agent instead. Override: ORCHESTRATOR_ALLOW_FORK=1.")

    # Rule 1: explicit forbidden model tier (fable); sole exception: pool-fable for agent-orchestrator:planner
    if model_s and any(f in model_s for f in FORBIDDEN):
        if not (model_s == FABLE_OK_MODEL and planner_ok):
            deny("Blocked by model-tier policy: fable is reserved for the orchestrator "
                 "main thread and is never used for subagents (sole exception: model pool-fable "
                 "for subagent_type agent-orchestrator:planner). Re-spawn with model: sonnet or opus (or a pool-sonnet*/pool-opus* pool id).")
    # Rule 1b: Haiku is allowlisted by agent type, and only the 5.x line
    if "haiku" in model_s:
        if any(o in model_s for o in HAIKU_OLD):
            deny("Blocked by model-tier policy: Haiku 4.x / 3.x model ids are never allowed. "
                 "Haiku 5.5 (model: haiku or claude-haiku-5-5) is allowed only for scout, "
                 "explorer, Explore, claude-code-guide and statusline-setup; everything else runs "
                 "sonnet or opus.")
        if bare not in HAIKU_OK:
            deny("Blocked by model-tier policy: Haiku 5.5 is allowed only for scout, explorer, Explore, "
                 "claude-code-guide and statusline-setup (cheap enumeration/lookup work) - "
                 "never for verification, judgement, code edits or security review. "
                 "Re-spawn %s with model: sonnet or opus." % (bare or "this agent"))
        if "high" in model_s and bare not in HAIKU_HIGH_OK:
            deny("Blocked by model-tier policy: pool-haiku-high is allowed only for "
                 "scout and explorer. Re-spawn %s with plain haiku, sonnet or opus." % bare)
    # Rule 2: unpinned agent type with no explicit model (would inherit caller's model)
    if not model_s and bare in UNPINNED:
        deny("Model-tier policy: unpinned agent types "
             "(general-purpose/Explore/Plan/claude/claude-code-guide/statusline-setup) must be "
             "spawned with an explicit model: sonnet or opus (haiku only for Explore/"
             "claude-code-guide/statusline-setup) - omitting it inherits the caller's model "
             "and can leak fable onto delegated work.")
    # Rule 3/default: allow (pinned types with no model resolve to their frontmatter pin)
    if stripped:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": ti,
            "additionalContext": " ".join(notes)}}))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("model-tier-gate fail-open: %r\n" % (e,))
        sys.exit(0)   # Rule 4: never brick spawning
