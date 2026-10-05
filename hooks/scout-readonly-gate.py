#!/usr/bin/env python3
# PreToolUse gate: restrict the `scout` subagent's Bash access to read-only
# inspection commands. FAIL-CLOSED for scout (deny anything not affirmatively
# allow-listed), FAIL-OPEN for everyone else and on any internal error here —
# this must never brick Bash for worker/verifier/judge/orchestrator, and must
# never brick Bash entirely on a bug in this script.
#
# Scoping mechanism (verified against https://code.claude.com/docs/en/hooks.md
# and https://code.claude.com/docs/en/sub-agents.md, 2026-09-05):
#   - Plugin subagents IGNORE `hooks:` in their own frontmatter (official
#     docs), so a plugin-level hooks/hooks.json keyed on the payload's
#     agent_type is the ONLY mechanism that works for plugin agents. This
#     script is therefore registered centrally in hooks/hooks.json
#     (PreToolUse, matcher "Bash") and re-derives the caller identity from the
#     stdin payload:
#       - `agent_id`   present ONLY when the hook fires inside a subagent call
#                      (absent for the orchestrator/main thread).
#       - `agent_type` names the running subagent persona, e.g. "scout" or
#                      "agent-orchestrator:scout" (plugin-qualified).
#     If either field is missing, or agent_type's bare name (after stripping
#     any "plugin:" prefix) isn't exactly "scout", this hook is a strict
#     no-op — it never gates the orchestrator or any other subagent.
import re
import sys
import json

# --- allowlists -------------------------------------------------------------

ALLOWLIST = {
    "git", "chezmoi", "wc", "du", "stat", "ls", "find", "cat", "head", "tail",
    "less", "grep", "rg", "jq", "yq", "sort", "uniq", "cut", "awk", "tr",
    "echo", "printf", "pwd", "whoami", "hostname", "date", "env", "printenv",
    "which", "where", "type", "file", "readlink", "realpath", "basename",
    "dirname", "tree", "diff", "cmp", "md5sum", "sha256sum", "shasum",
    "column", "nl", "fold", "paste", "test", "[", "true", "false", "sed",
}

GIT_ALLOW = {
    "log", "status", "diff", "show", "branch", "rev-parse", "ls-files",
    "ls-tree", "blame", "describe", "remote",
}
# `git branch` / `git remote` are allow-listed verbs but have mutating forms
# (-D, create, add, set-url ...), so their arguments are checked strictly.
GIT_BRANCH_FLAGS = {
    "-a", "-r", "-v", "-vv", "-l", "-i", "--all", "--remotes", "--verbose",
    "--list", "--ignore-case", "--show-current", "--color", "--no-color",
    "--column", "--no-column",
}
GIT_BRANCH_VALUE_FLAGS = {
    "--contains", "--no-contains", "--merged", "--no-merged", "--points-at",
    "--format", "--sort", "--abbrev",
}
GIT_REMOTE_ALLOW = {"-v", "--verbose", "show", "get-url", "-n"}
GIT_DENY = {
    "commit", "add", "push", "pull", "fetch", "checkout", "switch", "reset",
    "rebase", "merge", "stash", "clean", "rm", "mv", "tag", "apply",
    "cherry-pick", "restore", "worktree", "config",
}

CHEZMOI_ALLOW = {
    "doctor", "diff", "status", "managed", "unmanaged", "data", "source-path",
    "target-path", "verify", "cat", "dump",
}  # execute-template deliberately absent: template funcs (`output`) run commands
CHEZMOI_DENY = {
    "apply", "add", "init", "update", "edit", "forget", "remove", "purge",
    "re-add", "merge",
}

_FIND_DENY_RE = re.compile(r'-delete\b|-execdir\b|-exec\b|-okdir\b|-ok\b|-f(?:print0?|printf|ls)\b')
_AWK_SYSTEM_RE = re.compile(r'\bsystem\s*\(')
_GIT_OUTPUT_RE = re.compile(r'^--output(=|$)')
_SORT_DENY_RE = re.compile(r'^(-[A-Za-z]*o|--output(=.*)?|--compress-program(=.*)?)$')
# sed is only allowed with a simple address+print/delete/quit or s///[gpiIm0-9]
# script: no -i/-e/-f, and no w/W/e/r commands or s///w|e flags can be expressed.
_SED_ADDR = r'(?:\d+|\$|/(?:[^/\\]|\\.)*/)'
_SED_SCRIPT_RE = re.compile(
    r'^(?:' + _SED_ADDR + r'?(?:,' + _SED_ADDR + r')?!?[pdq=l]'
    r'|s/(?:[^/\\]|\\.)*/(?:[^/\\]|\\.)*/[gpiIm0-9]*)$')
_SED_FLAGS_RE = re.compile(r'^-[nErs]+$|^--(quiet|silent|regexp-extended)$')
_JQ_YQ_DENY_RE = re.compile(r'(^|\s)-i(\s|$)|--in-place\b')
_EVAL_WORD_RE = re.compile(r'(^|[\s;&|])eval(\s|$)')
_SEGMENT_SPLIT_RE = re.compile(r'\|\||&&|;|\r\n|\n|\||&')
_PROC_SUBST_RE = re.compile(r'[<>]\(')


def allow():
    print("{}")
    sys.exit(0)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def is_scout_caller(data):
    """Positive-identification only: True iff we can affirmatively say this
    tool call was made by the scout subagent. Anything ambiguous -> False,
    which makes the whole hook a no-op (fail-open for everyone but scout)."""
    agent_id = data.get("agent_id")
    if not agent_id:
        return False  # no subagent context at all (e.g. orchestrator/main thread)
    atype = data.get("agent_type")
    if not isinstance(atype, str) or not atype.strip():
        return False
    bare = atype.strip().lower().split(":")[-1]  # strip "plugin:" prefix if present
    return bare == "scout"


def normalize_cmd_token(tok):
    """First-token normalization: strip a leading directory path (either slash
    style) and a trailing .exe, lowercase. Intentionally naive (whitespace-
    based tokenizing upstream, no full shell-quote parsing) -- unusual/unquoted
    paths with spaces resolve to a non-allowlisted first token, which the
    fail-closed allowlist denies anyway, so imprecision here only ever makes
    the gate stricter, never looser."""
    t = tok.strip().strip('"\'')
    base = re.split(r'[\\/]', t)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base.lower()


def has_bad_redirection(command):
    scrubbed = command.replace("2>&1", "").replace("2>/dev/null", "")
    return ">" in scrubbed


def has_subshell(command):
    return "$(" in command or "`" in command


def check_git(tokens):
    rest = tokens[1:]
    i = 0
    while i < len(rest) and rest[i] == "-C":
        i += 2  # skip -C and its path argument
    if i >= len(rest):
        return "scout is read-only; git command has no recognized sub-verb"
    verb = rest[i].lower()
    if verb in GIT_DENY or verb not in GIT_ALLOW:
        return "scout is read-only; git %s not in allowlist" % verb
    args = rest[i + 1:]
    if any(_GIT_OUTPUT_RE.match(a) for a in args):
        return "scout is read-only; git --output (writes a file) is not permitted"
    if verb == "branch":
        return check_git_branch(args)
    if verb == "remote":
        return check_git_remote(args)
    return None

def check_git_branch(args):
    listing = any(a in ("-l", "--list") for a in args)
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        name = a.split("=", 1)[0]
        if name in GIT_BRANCH_VALUE_FLAGS:
            skip = "=" not in a
            continue
        if a.startswith("-"):
            if a not in GIT_BRANCH_FLAGS:
                return "scout is read-only; git branch %s is not permitted" % a
        elif not listing:
            return "scout is read-only; git branch <name> would create a branch"
    return None

def check_git_remote(args):
    for a in args:
        if a not in GIT_REMOTE_ALLOW and a.startswith("-"):
            return "scout is read-only; git remote %s is not permitted" % a
    if args and not args[0].startswith("-") and args[0] not in GIT_REMOTE_ALLOW:
        return "scout is read-only; git remote %s is not permitted" % args[0]
    return None

def check_sed(tokens):
    script = None
    for t in tokens[1:]:
        if script is None and t.startswith("-"):
            if not _SED_FLAGS_RE.match(t):
                return "scout is read-only; sed %s is not permitted (only -n/-E/-r/-s)" % t
            continue
        if script is None:
            script = t
            if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"":
                script = t[1:-1]
            if not _SED_SCRIPT_RE.match(script):
                return "scout is read-only; sed script not a simple print/s/// expression"
    if script is None:
        return "scout is read-only; sed with no script"
    return None

def check_sort(tokens):
    for t in tokens[1:]:
        if _SORT_DENY_RE.match(t):
            return "scout is read-only; sort -o/--output/--compress-program is not permitted"
    return None


def check_chezmoi(tokens):
    rest = tokens[1:]
    if not rest:
        return "scout is read-only; chezmoi command has no recognized sub-verb"
    verb = rest[0].lower()
    if verb in CHEZMOI_DENY or verb not in CHEZMOI_ALLOW:
        return "scout is read-only; chezmoi %s not in allowlist" % verb
    return None


def check_env(tokens):
    """env with no wrapped command (bare, flags, VAR=val only) is fine; env
    used to launch another program must itself resolve to an allow-listed
    verb, closing the `env <mutating cmd>` bypass."""
    for t in tokens[1:]:
        if t.startswith("-"):
            continue
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            continue
        wrapped = normalize_cmd_token(t)
        if wrapped not in ALLOWLIST:
            return "scout is read-only; env-wrapped '%s' not in allowlist" % t
        break
    return None


def check_segment(segment):
    seg = segment.strip()
    if not seg:
        return None
    tokens = seg.split()
    if not tokens:
        return None
    first_raw = tokens[0]
    first = normalize_cmd_token(first_raw)
    if first not in ALLOWLIST:
        return "scout is read-only; '%s' not in allowlist" % first_raw
    if first == "git":
        return check_git(tokens)
    if first == "chezmoi":
        return check_chezmoi(tokens)
    if first == "find" and _FIND_DENY_RE.search(seg):
        return "scout is read-only; find -delete/-exec/-execdir/-ok/-fprint*/-fls is not permitted"
    if first == "sed":
        return check_sed(tokens)
    if first == "sort":
        return check_sort(tokens)
    if first == "awk" and _AWK_SYSTEM_RE.search(seg):
        return "scout is read-only; awk system() is not permitted"
    if first in ("jq", "yq") and _JQ_YQ_DENY_RE.search(seg):
        return "scout is read-only; jq/yq -i/--in-place is not permitted"
    if first == "env":
        return check_env(tokens)
    return None


def evaluate(command):
    if _PROC_SUBST_RE.search(command):
        return "scout is read-only; process substitution (<()/>()) is not permitted"
    if has_bad_redirection(command):
        return "scout is read-only; output redirection ('>'/'>>') is not permitted"
    if has_subshell(command):
        return "scout is read-only; command substitution ($()/backticks) is not permitted"
    if _EVAL_WORD_RE.search(command):
        return "scout is read-only; eval is not permitted"
    # strip harmless stderr redirections so their `&` is not read as a separator
    scrubbed = command.replace("2>&1", "").replace("2>/dev/null", "")
    for seg in _SEGMENT_SPLIT_RE.split(scrubbed):
        reason = check_segment(seg)
        if reason:
            return reason
    return None


def main():
    data = json.loads(sys.stdin.read())
    if data.get("tool_name") != "Bash":
        sys.exit(0)  # out of scope for this gate; allow
    if not is_scout_caller(data):
        sys.exit(0)  # can't positively identify scout -> no-op, never gate others

    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        sys.exit(0)
    command = ti.get("command")
    if not isinstance(command, str) or not command.strip():
        sys.exit(0)

    reason = evaluate(command)
    if reason:
        deny(reason)
    allow()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("scout-readonly-gate fail-open: %r\n" % (e,))
        sys.exit(0)
