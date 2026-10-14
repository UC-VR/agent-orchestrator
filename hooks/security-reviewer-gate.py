#!/usr/bin/env python3
# PreToolUse gate (matcher Bash): keep the `security-reviewer` subagent from (a) printing
# secret VALUES and (b) mutating anything -- it is a read-only agent. FAIL-OPEN for every
# other caller and for malformed input; FAIL-CLOSED for security-reviewer once identified
# (any internal error -> deny). Caller identification matches scout-readonly-gate.py:
# truthy agent_id AND bare agent_type (after any "plugin:" prefix) == "security-reviewer".
#
# Since 1.9.1 this is a DEFAULT-DENY ALLOWLIST (see ALLOWED), not a denylist: anything not
# listed is refused, and it fails closed on constructs it cannot inspect ($-expansion,
# backticks, process substitution, redirects). Known residuals: repo-config driven
# git textconv/diff drivers, and secrets that sit inside ordinary-named files (`grep -r`
# over a tree prints matching lines -- the agent prompt requires grep -l/-c for those).
import json
import os
import re
import shlex
import sys

# 1.9.1 (B2): DEFAULT-DENY. Only the commands below may run; everything else (gh, curl,
# wget, op, python/node/perl..., shells, sed/awk, sudo, docker ...) is denied. Secret-file
# operands are checked against the shared hooks/_secret_paths.py list (.env*, keys,
# ~/.config/op, gh hosts.yml, docker config.json, .netrc, .git-credentials, ~/.aws ...,
# glob spellings included). Read/Grep tool calls by this agent get the same path check.
ALLOWED = {
    "git", "grep", "egrep", "fgrep", "rg", "ls", "stat", "file", "wc", "du", "find", "cat",
    "head", "tail", "sort", "uniq", "cut", "tr", "jq", "echo", "printf", "test", "[", "true",
    "false", "pwd", "realpath", "readlink", "basename", "dirname", "which", "type", "diff",
    "cmp", "comm", "column", "nl", "fold", "paste", "tree", "md5sum", "sha256sum", "sha1sum",
    "shasum", "date", "whoami", "hostname", "id", "uname", "strings", "systemctl", "ss",
    "export", "declare", "typeset", "readonly",
}
# wrappers: (flags that take a value, number of leading positional args before the command)
WRAPPERS = {
    "env": ({"-u", "--unset", "-C", "--chdir"}, 0),
    "timeout": ({"-s", "--signal", "-k", "--kill-after"}, 1),
    "nice": ({"-n", "--adjustment"}, 0),
    "stdbuf": ({"-i", "-o", "-e"}, 0),
    "time": (set(), 0),
    "command": (set(), 0),
}
CONTENT_READERS = {"md5sum", "sha256sum", "sha1sum", "shasum", "cat", "head", "tail", "grep", "egrep", "fgrep", "rg", "sort", "uniq",
                   "cut", "tr", "jq", "diff", "cmp", "comm", "column", "nl", "fold", "paste",
                   "strings"}
PATTERN_FIRST = {"grep", "egrep", "fgrep", "rg", "jq"}
GIT_GLOBAL_OK = {"--no-pager", "--no-optional-locks", "--literal-pathspecs", "--bare"}
GIT_GLOBAL_VALUE = {"-C", "--git-dir", "--work-tree"}
GIT_READ = {"diff", "log", "show", "status", "blame", "grep", "ls-files", "ls-tree",
            "cat-file", "rev-parse", "describe", "shortlog", "rev-list", "merge-base",
            "branch", "remote", "tag", "name-rev", "check-ignore", "for-each-ref",
            "count-objects", "whatchanged", "show-ref"}
GIT_CONTENT = {"show", "diff", "blame", "log", "grep", "cat-file", "whatchanged"}
_GIT_BAD_ARG = re.compile(r'^(--output(=|$)|--ext-diff$|-O|--open-files-in-pager|--exec|-c$|--config)')
GIT_BRANCH_MUTATING = re.compile(r'^-[a-zA-Z]*[dDmMcCuf]|^--(delete|move|copy|set-upstream|unset-upstream|edit-description|force|track)')
SYSTEMCTL_READ = {"status", "cat", "show", "list-units", "list-unit-files", "list-timers",
                  "list-sockets", "is-enabled", "is-active", "is-failed", "list-dependencies"}
_FIND_DENY = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
_PROC_ENVIRON_RE = re.compile(r'/proc/[^\s\'"]*(environ|[*?\[])')
_JQ_ENV_RE = re.compile(r'\$ENV\b|\$__loc__|(^|[^A-Za-z0-9_.$])(env|getenv)\b')
_ENV_ASSIGN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

try:  # shared helper; if missing, every reviewer call is denied (fail-closed)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _secret_paths import is_secret_path, indirect_file_read, jq_file_read, _FD_REDIR_RE
except Exception:  # pragma: no cover
    is_secret_path = None


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


def reader_operands(cmd, args):
    out, skip_first, take = [], cmd in PATTERN_FIRST, False
    for a in args:
        a = _FD_REDIR_RE.sub("", a)
        if not a:
            continue
        if take:
            take = False
            continue
        if a in ("-e", "--regexp", "-f", "--file"):
            skip_first = False
            take = a in ("-e", "--regexp")
            continue
        if a.startswith("-"):
            if "=" in a:
                out.append(a.split("=", 1)[1])
            continue
        if skip_first:
            skip_first = False
            continue
        out.append(a)
    return out


def secret_operand(cands):
    for c in cands:
        if is_secret_path(c):
            return "'%s' looks like a secret-bearing file" % c
    return None


def check_git(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a in GIT_GLOBAL_VALUE:
            i += 2
            continue
        if a.split("=", 1)[0] in GIT_GLOBAL_VALUE or a in GIT_GLOBAL_OK:
            i += 1
            continue
        return "git global option %s is not permitted (-c/--config-env/--exec-path/-p run code)" % a
    verb = args[i].lower() if i < len(args) else ""
    rest = args[i + 1:]
    if verb not in GIT_READ:
        return "`git %s` is not a read-only verb on the allowlist" % (verb or "<none>")
    for a in rest:
        if _GIT_BAD_ARG.match(a):
            return "git %s writes a file or runs an external program" % a
    if verb == "branch":
        if any(GIT_BRANCH_MUTATING.match(a) for a in rest if a.startswith("-")):
            return "`git branch` mutating form"
        if any(not a.startswith("-") for a in rest) and not any(
                a in ("-l", "--list", "--contains", "--merged", "--no-merged", "--points-at") for a in rest):
            return "`git branch <name>` creates a branch"
    if verb == "remote":
        sub = next((a for a in rest if not a.startswith("-")), None)
        if sub is not None or any(a.startswith("-") for a in rest):
            return "only bare `git remote` is allowed (-v/get-url/show print token-bearing URLs; other verbs mutate or hit the network)"
    if verb == "tag" and any(not a.startswith("-") for a in rest) and not any(
            a in ("-l", "--list") for a in rest):
        return "`git tag <name>` creates a tag"
    if verb == "tag" and any(re.match(r'^-[a-zA-Z]*[dafsum]', a) or a.startswith(("--delete", "--force", "--sign", "--annotate")) for a in rest):
        return "`git tag` mutating form"
    if verb in GIT_CONTENT:
        return secret_operand([a for a in rest if not a.startswith("-")] +
                              [a.split("=", 1)[1] for a in rest if a.startswith("-") and "=" in a])
    return None


def strip_wrapper(cmd, args):
    """Return the wrapped argv, [] if the wrapper runs nothing, or None if unparseable."""
    value_flags, npos = WRAPPERS[cmd]
    i = 0
    while i < len(args):
        a = args[i]
        if cmd == "env" and _ENV_ASSIGN_RE.match(a):
            i += 1
            continue
        if a == "--":
            i += 1
            break
        if a.startswith("-"):
            if cmd == "env" and (a in ("-S", "--split-string") or a.startswith(("-S", "--split-string"))):
                return None
            i += 2 if a in value_flags else 1
            continue
        break
    i += npos
    return args[i:]


def check_tokens(tokens, depth=0):
    if depth > 4:
        return "command nesting too deep to inspect"
    while tokens and _ENV_ASSIGN_RE.match(tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return None
    cmd = norm_cmd(tokens[0])
    args = tokens[1:]
    if cmd in WRAPPERS:
        inner = strip_wrapper(cmd, args)
        if inner is None:
            return "`%s` form cannot be inspected" % cmd
        if not inner:
            if cmd == "env":
                return "bare `env` prints environment values"
            return None
        return check_tokens(inner, depth + 1)
    if cmd not in ALLOWED:
        return "`%s` is not on the security-reviewer allowlist (default-deny)" % cmd
    dashless = [a for a in args if not a.startswith(("-", "+"))]
    if cmd in ("export", "declare", "typeset", "readonly"):
        if not dashless or any(a.startswith(("-", "+")) and "p" in a for a in args):
            return "`%s` listing prints environment values" % cmd
        return None
    reason = indirect_file_read(cmd, args)
    if reason:
        return reason
    if cmd == "git":
        return check_git(args)
    if cmd == "find":
        if any(a in _FIND_DENY for a in args):
            return "find -delete/-exec/-ok/-fprint* mutates or executes"
        return None
    if cmd == "systemctl":
        verb = next((a for a in args if not a.startswith("-")), None)
        if verb not in SYSTEMCTL_READ:
            return "`systemctl %s` is not a read-only verb" % verb
        return None
    if cmd == "ss" and any(a in ("-K", "--kill") or re.match(r'^-[a-zA-Z]*K', a) for a in args):
        return "`ss -K` kills sockets"
    if cmd == "sort" and any(re.match(r'^-[^-]*o', a) or a.startswith(("--output", "--compress")) for a in args):
        return "sort -o/--output writes a file"
    if cmd == "tree" and any(re.match(r'^-[^-]*o', a) or a.startswith("--output") for a in args):
        return "tree -o writes a file"
    if cmd == "uniq" and len([a for a in dashless]) > 1:
        return "uniq with an output operand writes a file"
    if cmd == "rg" and any(re.match(r'^--(pre|hostname-bin|search-zip)(=|$)|^-z', a) for a in args):
        return "rg --pre/--search-zip run external programs"
    if cmd == "jq":
        if jq_file_read(args):
            return jq_file_read(args)
        if any(not a.startswith("-") and _JQ_ENV_RE.search(a) for a in args):
            return "jq env/$ENV prints environment values"
    if cmd in CONTENT_READERS:
        return secret_operand(reader_operands(cmd, args))
    return None


def check_command(command, depth=0):
    if is_secret_path is None:
        return "security-reviewer gate cannot load its secret-path helper (fail-closed)"
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
        if (not isinstance(data, dict) or data.get("tool_name") not in ("Bash", "Read", "Grep")
                or not is_reviewer_caller(data)):
            out({})
    except SystemExit:
        raise
    except Exception:
        out({})   # cannot identify caller -> fail-open
    try:
        ti = data.get("tool_input")
        if data.get("tool_name") != "Bash":
            reason = None
            for key in ("file_path", "path", "glob"):
                v = ti.get(key) if isinstance(ti, dict) else None
                if isinstance(v, str) and v and (is_secret_path is None or is_secret_path(v)):
                    reason = "%s %s names a secret-bearing path" % (key, v)
                    break
        else:
            command = ti.get("command") if isinstance(ti, dict) else None
            reason = check_command(command) if isinstance(command, str) and command.strip() else None
    except Exception as e:
        reason = "internal error (fail-closed): %r" % (e,)
    if reason:
        deny(reason)
    out({})


if __name__ == "__main__":
    main()
