#!/usr/bin/env python3
# Per-command argv checks for hooks/scout-readonly-gate.py (split out in 1.9.1 to keep
# each file under 500 lines). Imported by the gate from its own directory; if this
# module cannot be imported the gate denies every scout Bash call (fail-closed; tested
# in test_scout_readonly_gate.TestFailClosed).
# All checks run on the shlex-UNQUOTED argv.
import re

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
GIT_REMOTE_ALLOW = set()   # 1.9.1: only bare `git remote` (names); -v/get-url/show can print token-bearing URLs
GIT_DENY = {
    "commit", "add", "push", "pull", "fetch", "checkout", "switch", "reset",
    "rebase", "merge", "stash", "clean", "rm", "mv", "tag", "apply",
    "cherry-pick", "restore", "worktree", "config",
}
# Commands whose file operands are READ and whose content could reach scout's output.
CONTENT_READERS = {
    "cat", "head", "tail", "grep", "rg", "jq", "yq", "sort", "uniq", "cut", "awk", "tr",
    "diff", "cmp", "column", "nl", "fold", "paste", "sed", "md5sum", "sha256sum", "shasum",
}
# readers whose first positional is a pattern/program, not a file
SCRIPT_FIRST = {"grep", "rg", "jq", "yq", "awk", "sed"}
_PROC_ENV_RAW_RE = re.compile(r'/proc/\S*(environ|[*?\[])')
_JQ_ENV_RE = re.compile(r'\$ENV\b|\$__loc__|(^|[^A-Za-z0-9_.$])(env|strenv|envsubst|getenv)\b')
_AWK_ENV_RE = re.compile(r'\b(ENVIRON|PROCINFO)\b')

CHEZMOI_ALLOW = {
    "doctor", "managed", "unmanaged", "source-path", "target-path",
}  # every verb that renders templates (cat/diff/status/dump/data/verify/execute-template)
#    is absent: template funcs (`output`, onepassword*) run commands and read secrets
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
# Known residual (not closed here; need config/interactive features): `less +!cmd`,
# `git diff --ext-diff/--textconv` (need repo/user config), and unquoted glob
# flags like `sed s/a/b/ -[i] f` (only bite if a file literally named `-i` exists).
_EVAL_WORD_RE = re.compile(r'(^|[\s;&|])eval(\s|$)')
_PROC_SUBST_RE = re.compile(r'[<>]\(')


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
    if verb is not None:
        return "scout may only run bare `git remote`; `git remote %s` can contact the network or print token-bearing URLs" % verb
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


def check_uniq(tokens):
    """`uniq [OPTION] [INPUT [OUTPUT]]`: a second positional is an output file."""
    positionals = 0
    skip = False
    for t in tokens[1:]:
        if skip:
            skip = False
            continue
        if t.startswith("<"):
            skip = t == "<"   # stdin redirection: `< f` is not an operand
        elif t.startswith("--"):
            name = t[2:].split("=", 1)[0]
            if "=" not in t and name and any(
                    l.startswith(name) for l in ("skip-fields", "skip-chars", "check-chars")):
                skip = True
        elif t.startswith("-") and len(t) > 1:
            for pos, ch in enumerate(t[1:], 1):
                if ch in "fsw":
                    skip = pos == len(t) - 1
                    break
        else:
            positionals += 1
    if positionals > 1:
        return "scout is read-only; uniq with an output file operand is not permitted"
    return None

def check_awk(tokens):
    args = tokens[1:]
    if re.search(r'\bgetline\b', " ".join(args)):
        return "scout may not use awk getline (reads arbitrary files/commands)"
    if _AWK_ENV_RE.search(" ".join(args)):
        return "scout may not read the environment; awk ENVIRON/PROCINFO is not permitted"
    if _AWK_SYSTEM_RE.search(" ".join(args)):
        return "scout is read-only; awk system()/@load/@include is not permitted"
    for t in args:
        if t.startswith("--"):
            name = t[2:].split("=", 1)[0]
            if name and any(l.startswith(name) for l in (
                    "include", "load", "file", "exec", "profile", "dump-variables", "pretty-print")):
                return "scout is read-only; awk %s is not permitted" % t
        elif t.startswith("-"):
            if t[1:2] in ("i", "l", "f", "E", "o", "p", "d"):
                return "scout is read-only; awk %s (include/load/-f/exec/-o/-p/-d) is not permitted" % t
        elif "|" in t and ("getline" in t or "print" in t):
            # quote-aware splitting keeps `print | "cmd"` / `"cmd" | getline`
            # inside one token; they spawn processes. (`-F '|'` stays allowed.)
            return "scout is read-only; awk pipes (print | cmd, cmd | getline) are not permitted"
    return None

def check_jq_yq(first, tokens):
    for t in tokens[1:]:
        if not t.startswith("-") and _JQ_ENV_RE.search(t):
            return "scout may not read the environment; jq/yq env/$ENV/strenv/envsubst is not permitted"
        if t in ("--rawfile", "--slurpfile", "--args", "--jsonargs") or t.startswith(("--rawfile=", "--slurpfile=")):
            pass  # file operands are covered by the secret-path check
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
