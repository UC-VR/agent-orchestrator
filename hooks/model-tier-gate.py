#!/usr/bin/env python3
# PreToolUse gate: enforce model-tier policy on Agent/Task spawns. FAIL-OPEN on any error.
import os, sys, json, re, subprocess, shutil

MIN_STRIP_VERSION = (2, 1, 290)   # first CLI where rules/safety checks re-run after a hook rewrites input
TEAMMATE_ONLY_KEYS = ("name", "team_name", "teamName", "mode")
STRIP_NOTE = ("Agent spawn: `name` was removed (agent teams are disabled by fleet policy; "
              "named spawns would run as in-process teammates with clamped tools). Track this "
              "agent by the ID in the tool result and use SendMessage with that ID for follow-ups.")

UNPINNED = {"general-purpose", "explore", "plan", "claude", "claude-code-guide"}
FORBIDDEN = ("haiku", "fable")

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
    bare = atype_s.split(":")[-1] if atype_s else ""   # strip "agent-orchestrator:" prefix
    if not bare:
        bare = "general-purpose"   # Claude Code defaults a missing subagent_type to general-purpose

    # Rule 0: named spawns silently degrade tools via the CLI's in-process teammate
    # path (anthropics/claude-code#81746, #78234, #31977) — the requested agent
    # definition is dropped and the spawn collapses to a fixed reduced tool profile.
    name = ti.get("name")
    stripped = False
    if name and isinstance(name, str) and name.strip() and os.environ.get("ORCHESTRATOR_ALLOW_NAMED_SPAWNS") != "1":
        ver = cli_version()
        if ver is not None and ver >= MIN_STRIP_VERSION:
            # Strip teammate-only fields via updatedInput; remaining rules run on the stripped input.
            ti = {k: v for k, v in ti.items() if k not in TEAMMATE_ONLY_KEYS}
            stripped = True
        else:
            deny("Named spawns are blocked: Claude Code's in-process teammate path "
                 "(anthropics/claude-code#81746/#78234) silently drops the agent "
                 "definition and degrades tools. Omit `name`; use the returned agent ID "
                 "with SendMessage for follow-ups. Override: "
                 "ORCHESTRATOR_ALLOW_NAMED_SPAWNS=1. "
                 "(strip unavailable: CLI < 2.1.290 or version unknown)")

    # Rule 0b: forks inherit the main model and ignore any `model` override.
    if bare == "fork" and os.environ.get("ORCHESTRATOR_ALLOW_FORK") != "1":
        deny("Model-tier policy: fork inherits the orchestrator's model tier; spawn a "
             "typed agent instead. Override: ORCHESTRATOR_ALLOW_FORK=1.")

    # Rule 1: explicit forbidden model tier
    if model_s and any(f in model_s for f in FORBIDDEN):
        deny("Blocked by model-tier policy: subagents run sonnet or opus only "
             "(never haiku, never fable — fable is reserved for the orchestrator "
             "main thread). Re-spawn with model: sonnet or opus.")
    # Rule 2: unpinned agent type with no explicit model (would inherit caller's model)
    if not model_s and bare in UNPINNED:
        deny("Model-tier policy: unpinned agent types "
             "(general-purpose/Explore/Plan/claude) must be spawned with an explicit "
             "model: sonnet or opus — omitting it inherits the caller's model and can "
             "leak fable/haiku onto delegated work.")
    # Rule 3/default: allow (pinned types with no model resolve to their frontmatter pin)
    if stripped:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": ti,
            "additionalContext": STRIP_NOTE}}))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("model-tier-gate fail-open: %r\n" % (e,))
        sys.exit(0)   # Rule 4: never brick spawning
