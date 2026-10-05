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
import shlex
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
GIT_REMOTE_ALLOW = {"-v", "--verbose", "-n"}
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

# All per-command checks below run on the shlex-UNQUOTED argv, never the raw
# string: `'-i'`, `"--output=x"`, `\-o`, `-exe\c` all arrive here as the real flag.
_FIND_DENY = {"-delete", "-exec", "-execdir", "-ok", "-okdir",
              "-fprint", "-fprint0", "-fprintf", "-fls"}
_AWK_SYSTEM_RE = re.compile(r'\bsystem\s*\(|@(?:load|include)\b')
_GIT_OUTPUT_RE = re.compile(r'^--output(=|$)')
_SORT_SHORT_O_RE = re.compile(r'^-[^-]*o')
# sed is only allowed with a simple address+print/delete/quit or s///[gpiIm0-9]
# script: no -i/-e/-f, and no w/W/e/r commands or s///w|e flags can be expressed.
_SED_ADDR = r'(?:\d+|\$|/(?:[^/\\]|\\.)*/)'
_SED_SCRIPT_RE = re.compile(
    r'^(?:' + _SED_ADDR + r'?(?:,' + _SED_ADDR + r')?!?[pdq=l]'
    r'|s/(?:[^/\\]|\\.)*/(?:[^/\\]|\\.)*/[gpiIm0-9]*)\Z')
_SED_FLAGS_RE = re.compile(r'^-[nErs]+$|^--(quiet|silent|regexp-extended)$')
_JQ_YQ_SHORT_I_RE = re.compile(r'^-[A-Za-z]*i')
_ENV_SPLIT_RE = re.compile(r'^-[^-]*S|^--s')   # env -S / --split-string[=...] execs its value
# Known residual (not closed here; need config/interactive features): `less +!cmd`,
# `git diff --ext-diff/--textconv` (need repo/user config), and unquoted glob
# flags like `sed s/a/b/ -[i] f` (only bite if a file literally named `-i` exists).
_EVAL_WORD_RE = re.compile(r'(^|[\s;&|])eval(\s|$)')
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
    style) and a trailing .exe, lowercase. Input is already shlex-unquoted
    (posix), so Windows-style backslash paths get their backslashes eaten and
    resolve to a non-allowlisted token -- that fails closed. NOTE: this
    leniency applies to the COMMAND NAME only; flag tokens must always be
    validated on the unquoted argv (see check_segment), because a quoted or
    escaped flag does not start with '-' in the raw string."""
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
    """Only `git remote [-v]`, `git remote show ...`, `git remote get-url ...`.
    Flags may appear anywhere, so the FIRST non-flag arg is the verb; a flag
    before it must not smuggle a mutating verb past an args[0]-only check."""
    verb = next((a for a in args if not a.startswith("-")), None)
    if verb is not None and verb not in ("show", "get-url"):
        return "scout is read-only; git remote %s is not permitted" % verb
    for a in args:
        if a.startswith("-") and a not in GIT_REMOTE_ALLOW:
            return "scout is read-only; git remote %s is not permitted" % a
    return None

def check_sed(tokens):
    """GNU getopt permutes options, so `sed s/a/b/ -i f` is in-place. After
    shlex unquoting, every dash-prefixed token ANYWHERE in argv must be a
    known-safe flag; the first non-dash token is the script, the rest are
    input files."""
    script = None
    for t in tokens[1:]:
        if t.startswith("-"):
            if not _SED_FLAGS_RE.match(t):
                return "scout is read-only; sed %s is not permitted (only -n/-E/-r/-s)" % t
            continue
        if script is None:
            script = t
            if not _SED_SCRIPT_RE.match(script):
                return "scout is read-only; sed script not a simple print/s/// expression"
    if script is None:
        return "scout is read-only; sed with no script"
    return None

def check_sort(tokens):
    """Deny any short cluster containing `o` (-o, -of, -k2 -of, -ro) and any
    GNU-abbreviated --output / --compress-program."""
    for t in tokens[1:]:
        if _SORT_SHORT_O_RE.match(t):
            return "scout is read-only; sort -o is not permitted"
        if t.startswith("--"):
            name = t[2:].split("=", 1)[0]
            if name and ("output".startswith(name) or
                         (len(name) >= 2 and "compress-program".startswith(name))):
                return "scout is read-only; sort --output/--compress-program is not permitted"
    return None

def check_tree(tokens):
    for t in tokens[1:]:
        if _SORT_SHORT_O_RE.match(t) or t.startswith("--output"):
            return "scout is read-only; tree -o/--output is not permitted"
    return None

def check_rg(tokens):
    for t in tokens[1:]:
        if re.match(r'^--(pre|hostname-bin)(=|$)', t):
            return "scout is read-only; rg --pre/--hostname-bin run external programs"
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
        if _ENV_SPLIT_RE.match(t):
            return "scout is read-only; env -S/--split-string executes its argument"
        if t.startswith("-"):
            continue
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            continue
        wrapped = normalize_cmd_token(t)
        if wrapped not in ALLOWLIST:
            return "scout is read-only; env-wrapped '%s' not in allowlist" % t
        break
    return None


def check_awk(tokens):
    args = tokens[1:]
    if _AWK_SYSTEM_RE.search(" ".join(args)):
        return "scout is read-only; awk system()/@load/@include is not permitted"
    for t in args:
        if t.startswith("--"):
            name = t[2:].split("=", 1)[0]
            if name and any(l.startswith(name) for l in ("include", "load", "file", "exec")):
                return "scout is read-only; awk %s is not permitted" % t
        elif t.startswith("-"):
            if t[1:2] in ("i", "l", "f", "E"):
                return "scout is read-only; awk %s (include/load/-f/exec) is not permitted" % t
        elif "|" in t and ("getline" in t or "print" in t):
            # quote-aware splitting keeps `print | "cmd"` / `"cmd" | getline`
            # inside one token; they spawn processes. (`-F '|'` stays allowed.)
            return "scout is read-only; awk pipes (print | cmd, cmd | getline) are not permitted"
    return None

def check_jq_yq(first, tokens):
    for t in tokens[1:]:
        if t.startswith("--"):
            name = t[2:].split("=", 1)[0]
            if len(name) >= 2 and ("in-place".startswith(name) or "inplace".startswith(name)):
                return "scout is read-only; jq/yq -i/--in-place is not permitted"
            if first == "yq" and name and "split-exp".startswith(name):
                return "scout is read-only; yq --split-exp writes files"
        elif _JQ_YQ_SHORT_I_RE.match(t):
            return "scout is read-only; jq/yq -i/--in-place is not permitted"
        elif first == "yq" and re.match(r'^-[A-Za-z]*s', t):
            return "scout is read-only; yq -s/--split-exp writes files"
    return None

def check_segment(segment):
    seg = segment.strip()
    if not seg:
        return None
    try:
        tokens = shlex.split(seg, posix=True)
    except ValueError:
        return "scout is read-only; unparseable quoting in command"
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
    if first == "find" and any(t in _FIND_DENY for t in tokens[1:]):
        return "scout is read-only; find -delete/-exec/-execdir/-ok/-fprint*/-fls is not permitted"
    if first == "sed":
        return check_sed(tokens)
    if first == "sort":
        return check_sort(tokens)
    if first == "tree":
        return check_tree(tokens)
    if first == "rg":
        return check_rg(tokens)
    if first == "awk":
        return check_awk(tokens)
    if first in ("jq", "yq"):
        return check_jq_yq(first, tokens)
    if first == "env":
        return check_env(tokens)
    return None

class _Reject(Exception):
    pass

def split_segments(command):
    """Quote-aware split on unquoted ; & | newline (so `rg 'a|b'` and
    `find ... \\;` stay in one segment). Also rejects constructs the shell
    expands into flag tokens that no argv check could see: `$` outside single
    quotes ($'-i', $VAR, "${x}") and unquoted `{` (brace expansion {-o,x}).
    Backslash-newline is a bash line continuation and is deleted, matching
    bash (shlex would keep it inside the token)."""
    segs, cur = [], []
    sq = dq = False
    i, n = 0, len(command)
    while i < n:
        c = command[i]
        if sq:
            cur.append(c)
            if c == "'":
                sq = False
        elif c == "\\":
            if i + 1 >= n:
                raise _Reject("scout is read-only; trailing backslash")
            if command[i + 1] == "\n":
                i += 2
                continue
            cur.append(c)
            cur.append(command[i + 1])
            i += 2
            continue
        elif c == "`" or (c == "$" and not (dq and not re.match(r'[A-Za-z_{(0-9@*#?!$-]', command[i + 1:i + 2]))):
            # inside "..." a lone `$` (e.g. "foo$") is literal; anything that
            # starts an expansion, or any `$` outside quotes, is rejected.
            raise _Reject("scout is read-only; shell expansion ($ / backtick) is not permitted outside single quotes")
        elif dq:
            cur.append(c)
            if c == '"':
                dq = False
        elif c == "'":
            sq = True
            cur.append(c)
        elif c == '"':
            dq = True
            cur.append(c)
        elif c in ";&|\n":
            segs.append("".join(cur))
            cur = []
        elif c == "{":
            raise _Reject("scout is read-only; brace expansion is not permitted")
        else:
            cur.append(c)
        i += 1
    if sq or dq:
        raise _Reject("scout is read-only; unparseable quoting in command (unbalanced quote)")
    segs.append("".join(cur))
    return segs

def evaluate(command):
    # Raw-string checks first: these must see the command before any unquoting.
    if _PROC_SUBST_RE.search(command):
        return "scout is read-only; process substitution (<()/>()) is not permitted"
    if has_bad_redirection(command):
        return "scout is read-only; output redirection ('>'/'>>') is not permitted"
    if has_subshell(command):
        return "scout is read-only; command substitution ($()/backticks) is not permitted"
    if _EVAL_WORD_RE.search(command):
        return "scout is read-only; eval is not permitted"
    # strip harmless stderr redirections so their `&` is not read as a separator
    scrubbed = command.replace("2>&1", " ").replace("2>/dev/null", " ")
    try:
        segments = split_segments(scrubbed)
    except _Reject as e:
        return str(e)
    for seg in segments:
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
