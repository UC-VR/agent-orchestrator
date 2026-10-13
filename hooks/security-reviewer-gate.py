#!/usr/bin/env python3
# PreToolUse gate (matcher Bash): keep the `security-reviewer` subagent from (a) printing
# secret VALUES and (b) mutating anything -- it is a read-only agent. FAIL-OPEN for every
# other caller and for malformed input; FAIL-CLOSED for security-reviewer once identified
# (any internal error -> deny). Caller identification matches scout-readonly-gate.py:
# truthy agent_id AND bare agent_type (after any "plugin:" prefix) == "security-reviewer".
#
# This is a DENYLIST guardrail, not a sandbox: it blocks the obvious exposure/mutation
# commands and fails closed on constructs it cannot inspect ($-expansion, backticks,
# process substitution, eval, shells without -c, inline interpreters). Known residuals:
# glob spellings of secret files (`cat .en[v]`), and exotic readers not listed below.
import json
import os
import re
import shlex
import sys

OP_NAMES = {"op", "opix"}
READER_ENV_CMDS = {"printenv"}                   # always prints values -> always denied
MUTATORS = {
    "rm", "mv", "cp", "tee", "dd", "chmod", "chown", "chgrp", "ln", "touch", "mkdir",
    "rmdir", "truncate", "install", "shred", "unlink", "rsync", "patch",
}
GIT_DENY = {
    "commit", "push", "reset", "checkout", "add", "rm", "mv", "merge", "rebase", "stash",
    "clean", "switch", "restore", "tag", "pull", "fetch", "apply", "am", "cherry-pick",
    "revert", "config", "worktree", "gc", "prune",
}
GIT_BRANCH_MUTATING = re.compile(r'^-[a-zA-Z]*[dDmMcC]|^--(delete|move|copy|set-upstream)')
WRAPPERS = {"env", "sudo", "doas", "command", "builtin", "nohup", "time", "nice", "ionice",
            "exec", "xargs", "stdbuf", "timeout", "setsid", "watch"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
INTERPRETERS = re.compile(r'^(python[0-9.]*|perl|ruby|node|nodejs|php|lua)$')
GREP_FAMILY = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}
SAFE_META = {"ls", "stat", "file", "wc", "du", "test", "[", "realpath", "readlink",
             "basename", "dirname", "find", "which", "type", "echo", "printf"}
_FIND_DENY = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
_PROC_ENVIRON_RE = re.compile(r'/proc/[^\s\'"]*/environ')
_ENV_ASSIGN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
_SAFE_ENV_SUFFIX = (".tpl", ".example", ".sample", ".template")


def out(obj):
    print(json.dumps(obj))
    sys.exit(0)


def deny(reason):
    out({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "security-reviewer is read-only and must not expose secrets: " + reason}})


def is_reviewer_caller(data):
    if not data.get("agent_id"):
        return False
    atype = data.get("agent_type")
    if not isinstance(atype, str) or not atype.strip():
        return False
    return atype.strip().lower().split(":")[-1] == "security-reviewer"


class Reject(Exception):
    pass


def norm_cmd(tok):
    base = re.split(r'[\\/]', tok.strip())[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def secret_name(arg):
    """True if `arg` (a file operand) names a secret-bearing file."""
    cands = {arg, arg.split("=", 1)[-1], arg.rsplit(":", 1)[-1]}
    for c in cands:
        b = os.path.basename(c.rstrip("/")).lower()
        if not b:
            continue
        if b == ".env" or (b.startswith(".env") and not b.endswith(_SAFE_ENV_SUFFIX)):
            return True
        if b.endswith(".env") or "credentials" in b or b.endswith(".pem") or b.endswith(".key"):
            return True
        if re.match(r'^id_(rsa|dsa|ecdsa|ed25519)', b) and not b.endswith(".pub"):
            return True
    return False


def split_command(command):
    """Quote-aware split on unquoted ; & | newline. Raises Reject for expansions we cannot
    inspect and for any unquoted output redirect (other than to /dev/null or an fd dup)."""
    segs, cur = [], []
    sq = dq = False
    i, n = 0, len(command)
    while i < n:
        c = command[i]
        if sq:
            cur.append(c)
            sq = c != "'"
        elif c == "\\":
            if i + 1 >= n:
                raise Reject("trailing backslash")
            if command[i + 1] != "\n":
                cur.append(c + command[i + 1])
            i += 2
            continue
        elif c == "`" or (c == "$" and not (dq and not re.match(r'[A-Za-z_{(0-9@*#?!$-]', command[i + 1:i + 2]))):
            raise Reject("shell expansion ($ / backtick) is not permitted outside single quotes")
        elif dq:
            cur.append(c)
            dq = c != '"'
        elif c == "'":
            sq = True
            cur.append(c)
        elif c == '"':
            dq = True
            cur.append(c)
        elif c in "<>" and command[i + 1:i + 2] == "(":
            raise Reject("process substitution is not permitted")
        elif c == ">" or (c == "&" and command[i + 1:i + 2] == ">"):
            m = re.compile(r'&?>{1,2}\|?\s*(\S*)').match(command, i)
            target = m.group(1)
            if target == "/dev/null" or re.match(r'^&[0-9-]$', target):
                i = m.end()   # harmless: discard to /dev/null or fd duplication (2>&1)
                continue
            raise Reject("output redirection ('>'/'>>') is not permitted")
        elif c in ";&|\n":
            segs.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if sq or dq:
        raise Reject("unbalanced quote")
    segs.append("".join(cur))
    return segs


def check_args_for_secrets(cmd, args):
    if cmd in SAFE_META:
        return None
    args = [a.lstrip("<") for a in args]
    if cmd in GREP_FAMILY:
        skipped, rest, take = False, [], False
        for a in args:
            if take:
                take = False
                continue
            if a in ("-e", "--regexp"):
                take, skipped = True, True
                continue
            if a.startswith("--regexp="):
                skipped = True
                continue
            if not a.startswith("-") and not skipped:
                skipped = True   # first positional is the search pattern
                continue
            rest.append(a)
        args = rest
    for a in args:
        if secret_name(a):
            return "'%s' looks like a secret-bearing file" % a
    return None


def check_tokens(tokens, depth=0):
    if depth > 4:
        return "command nesting too deep to inspect"
    while tokens and _ENV_ASSIGN_RE.match(tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return None
    cmd = norm_cmd(tokens[0])
    args = tokens[1:]
    dashless = [a for a in args if not a.startswith("-")]

    if cmd in OP_NAMES:
        # global flags (`op --account x read ...`) can precede the verb, so match anywhere
        words = set(dashless)
        if words & {"read", "inject", "run"} or {"item", "get"} <= words or {"document", "get"} <= words:
            return "`%s` read/inject/run/get verbs print or inject secret values" % cmd
        return None
    if cmd in READER_ENV_CMDS:
        return "printenv prints environment values"
    if cmd == "set" and not args:
        return "bare `set` prints shell variables"
    if cmd in ("export", "declare", "typeset", "readonly"):
        if not dashless or any(a in ("-p", "-x", "-xp", "-px") for a in args):
            return "`%s` listing prints environment values" % cmd
        return None
    if cmd == "env" and all(a.startswith("-") or _ENV_ASSIGN_RE.match(a) for a in args):
        return "bare `env` prints environment values"
    if cmd in ("eval", "source", "."):
        return "%s executes uninspectable code" % cmd
    if cmd in SHELLS:
        for idx, a in enumerate(args):
            if re.match(r'^-[A-Za-z]*c', a) and idx + 1 < len(args):
                return check_command(args[idx + 1], depth + 1)
        return "shell invocation without -c cannot be inspected"
    if INTERPRETERS.match(cmd) and any(re.match(r'^-[A-Za-z]*[ceE]', a) or a == "-" for a in args):
        return "inline interpreter code cannot be inspected"
    if cmd in MUTATORS:
        return "`%s` mutates files" % cmd
    verb = ""
    if cmd == "git":
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in ("-C", "-c") else 1
        verb = args[i].lower() if i < len(args) else ""
        if verb in GIT_DENY:
            return "`git %s` mutates the repository" % verb
        if verb == "branch" and any(GIT_BRANCH_MUTATING.match(a) for a in args[i + 1:] if a.startswith("-")):
            return "`git branch` mutating form"
        if verb == "branch" and any(not a.startswith("-") for a in args[i + 1:]) and not any(
                a in ("-l", "--list", "--contains", "--merged", "--no-merged") for a in args[i + 1:]):
            return "`git branch <name>` creates a branch"
    if cmd == "find" and any(a in _FIND_DENY for a in args):
        return "find -delete/-exec/-ok/-fprint* mutates or executes"
    if cmd == "sed" and any(re.match(r'^-[^-]*i|^--i', a) for a in args):
        return "`sed -i` edits files in place"
    if cmd in ("awk", "gawk") and "inplace" in args:
        return "awk inplace edits files"
    if cmd in WRAPPERS:
        for i in range(1, len(tokens)):
            reason = check_tokens(tokens[i:], depth + 1)
            if reason:
                return reason
    if cmd == "git" and verb not in ("show", "diff", "blame", "log", "grep", "cat-file"):
        return None   # ls-files/status/etc. list names only
    return check_args_for_secrets(cmd, args)


def check_command(command, depth=0):
    if _PROC_ENVIRON_RE.search(command):
        return "reading /proc/*/environ exposes environment secrets"
    try:
        segments = split_command(command)
    except Reject as e:
        return str(e)
    for seg in segments:
        if not seg.strip():
            continue
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            return "unparseable quoting in command"
        reason = check_tokens(tokens, depth)
        if reason:
            return reason
    return None


def main():
    try:
        data = json.loads(sys.stdin.read())
        if (not isinstance(data, dict) or data.get("tool_name") != "Bash"
                or not is_reviewer_caller(data)):
            out({})
    except SystemExit:
        raise
    except Exception:
        out({})   # cannot identify caller -> fail-open
    try:
        ti = data.get("tool_input")
        command = ti.get("command") if isinstance(ti, dict) else None
        reason = check_command(command) if isinstance(command, str) and command.strip() else None
    except Exception as e:
        reason = "internal error (fail-closed): %r" % (e,)
    if reason:
        deny(reason)
    out({})


if __name__ == "__main__":
    main()
