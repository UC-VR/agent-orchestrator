#!/usr/bin/env python3
# PreToolUse gate: enforce model-tier policy on Agent/Task spawns. FAIL-OPEN on any error.
import sys, json

UNPINNED = {"general-purpose", "explore", "plan", "claude"}
FORBIDDEN = ("haiku", "fable")

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

def main():
    data = json.loads(sys.stdin.read())          # malformed -> except -> allow
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        sys.exit(0)
    model = ti.get("model")
    model_s = model.strip().lower() if isinstance(model, str) else ""
    atype = ti.get("subagent_type")
    if not isinstance(atype, str) or not atype:
        atype = ti.get("agentType")
    atype_s = atype.strip().lower() if isinstance(atype, str) else ""
    bare = atype_s.split(":")[-1] if atype_s else ""   # strip "agent-orchestrator:" prefix

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
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("model-tier-gate fail-open: %r\n" % (e,))
        sys.exit(0)   # Rule 4: never brick spawning
