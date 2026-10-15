#!/usr/bin/env python3
# PreToolUse gate (matcher Write|Edit|MultiEdit|NotebookEdit|Read|Grep): the `scout` subagent may
# Write ONLY briefing files (basename `briefing.md` or `*_briefing.md`). FAIL-OPEN for
# every other caller and for malformed input; FAIL-CLOSED for scout once identified (any
# internal error -> deny). Plugin subagents ignore frontmatter hooks, so this is registered
# centrally in hooks/hooks.json and re-derives the caller from agent_id + agent_type, the
# same way scout-readonly-gate.py does.
# The path is checked lexically (relative paths joined to the payload cwd) AND after
# os.path.realpath, so a briefing-named symlink to another target is denied. Any path
# segment named .git or .claude is denied on both forms.
# 1.9.1 (B1): the Write content is scanned and denied if it looks like it carries a
# literal secret (private keys, GitHub/Slack/AWS/1Password/sk- tokens, JWTs, credential
# assignments), and scout's Read/Grep calls are denied on secret-bearing paths (.env*,
# keys, ~/.config/op, gh hosts.yml, docker config, .netrc, /proc/*/environ ...), using the
# shared hooks/_secret_paths.py. Missing helper -> deny (fail-closed for scout).
import json
import os
import re
import sys

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _secret_paths import is_secret_path, secret_content
except Exception:  # pragma: no cover
    is_secret_path = secret_content = None

TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read", "Grep")
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


# 1.10.2: scout keeps its briefing-only Write rule. explorer and planner (read-only agents with
# no Write tool) get the Read/Grep secret-path deny, and any write-class call by them is denied.
READ_GATED = ("scout", "explorer", "planner")

def caller_type(data):
    """Bare agent type if this call is from a gated subagent, else None (fail-open for everyone else)."""
    agent_id = data.get("agent_id")
    if not agent_id:
        return None
    atype = data.get("agent_type")
    if not isinstance(atype, str) or not atype.strip():
        return None
    bare = atype.strip().lower().split(":")[-1]
    return bare if bare in READ_GATED else None

def is_scout_caller(data):
    return caller_type(data) is not None


def path_problem(p):
    """Return a reason string if this (already absolute) path is not an allowed target."""
    if any(seg.lower() in FORBIDDEN_SEGMENTS for seg in re.split(r'[\\/]+', p)):
        return "scout may not write under .git or .claude"
    if not BRIEFING_RE.match(os.path.basename(p)):
        return "scout may only write files named briefing.md or *_briefing.md"
    return None


def evaluate(data):
    tool = data.get("tool_name")
    who = caller_type(data) or "scout"
    if is_secret_path is None or secret_content is None:
        return "scout-write-gate cannot load its secret helper (fail-closed)"
    ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    if tool in ("Read", "Grep"):
        for key in ("file_path", "path", "glob"):
            v = ti.get(key)
            if isinstance(v, str) and v and is_secret_path(v):
                return "%s may not read secret-bearing files (%s: %s)" % (who, key, v)
        return None
    if who != "scout":
        return "%s is read-only; it may not use %s" % (who, tool)
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
    why = secret_content(ti.get("content"))
    if why:
        return ("scout briefings must not contain secret values (looks like: %s); "
                "cite file:line and redact instead" % why)
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
