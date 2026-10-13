#!/usr/bin/env python3
# PreToolUse gate (matcher Write|Edit|MultiEdit|NotebookEdit): the `scout` subagent may
# Write ONLY briefing files (basename `briefing.md` or `*_briefing.md`). FAIL-OPEN for
# every other caller and for malformed input; FAIL-CLOSED for scout once identified (any
# internal error -> deny). Plugin subagents ignore frontmatter hooks, so this is registered
# centrally in hooks/hooks.json and re-derives the caller from agent_id + agent_type, the
# same way scout-readonly-gate.py does.
# The path is checked lexically (relative paths joined to the payload cwd) AND after
# os.path.realpath, so a briefing-named symlink to another target is denied. Any path
# segment named .git or .claude is denied on both forms.
import json
import os
import re
import sys

TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
BRIEFING_RE = re.compile(r'(^|.*_)briefing\.md\Z')
FORBIDDEN_SEGMENTS = {".git", ".claude"}


def out(obj):
    print(json.dumps(obj))
    sys.exit(0)


def deny(reason):
    out({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}})


def is_scout_caller(data):
    agent_id = data.get("agent_id")
    if not agent_id:
        return False
    atype = data.get("agent_type")
    if not isinstance(atype, str) or not atype.strip():
        return False
    return atype.strip().lower().split(":")[-1] == "scout"


def path_problem(p):
    """Return a reason string if this (already absolute) path is not an allowed target."""
    if any(seg.lower() in FORBIDDEN_SEGMENTS for seg in re.split(r'[\\/]+', p)):
        return "scout may not write under .git or .claude"
    if not BRIEFING_RE.match(os.path.basename(p)):
        return "scout may only write files named briefing.md or *_briefing.md"
    return None


def evaluate(data):
    tool = data.get("tool_name")
    if tool != "Write":
        return "scout may not use %s; it may only Write *_briefing.md files" % tool
    ti = data.get("tool_input")
    fp = ti.get("file_path") if isinstance(ti, dict) else None
    if not isinstance(fp, str) or not fp.strip():
        return "scout Write requires a non-empty file_path"
    cwd = data.get("cwd")
    base = cwd if isinstance(cwd, str) and os.path.isabs(cwd) else os.getcwd()
    lexical = os.path.normpath(os.path.join(base, fp))
    for candidate in (os.path.join(base, fp), lexical, os.path.realpath(lexical)):
        reason = path_problem(candidate)
        if reason:
            return "%s (path: %s)" % (reason, fp)
    return None


def main():
    try:
        data = json.loads(sys.stdin.read())
        if not isinstance(data, dict) or data.get("tool_name") not in TOOLS or not is_scout_caller(data):
            out({})
    except SystemExit:
        raise
    except Exception:
        out({})   # malformed input: cannot identify caller -> fail-open
    try:
        reason = evaluate(data)
    except Exception as e:
        reason = "scout-write-gate internal error (fail-closed): %r" % (e,)
    if reason:
        deny(reason)
    out({})


if __name__ == "__main__":
    main()
