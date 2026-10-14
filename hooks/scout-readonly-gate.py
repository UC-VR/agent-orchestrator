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
import os

try:  # shared secret-path helpers (1.9.1); missing -> scout is denied (fail-closed)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _secret_paths import is_secret_path, indirect_file_read, jq_file_read
    import _scout_checks
    globals().update({k: v for k, v in vars(_scout_checks).items() if not k.startswith('__')})
except Exception:  # pragma: no cover
    is_secret_path = None

# --- allowlists -------------------------------------------------------------
# `env` and `printenv` are deliberately NOT allow-listed (1.8.7): they dump the process
# environment (secrets). With env gone, no wrapper command re-enters check_tokens.
# 1.9.1 (B1): scout must not read the environment or secret files by any route:
# /proc/*/environ (any spelling or glob), jq/yq env/$ENV/strenv/envsubst, awk ENVIRON/
# PROCINFO, (awk and yq were later removed entirely: awk ARGV and yq load/load_str read
# arbitrary files; jq import/include/-L/-f/--rawfile/--slurpfile are denied), `less` (LESSOPEN/+! escapes) and chezmoi verbs that render templates
# (cat/diff/status/dump/data/verify run `output`/onepassword* template functions) are
# denied, and every file operand of a content-reading command is checked against the
# shared secret-path list (.env*, keys, ~/.config/op, gh hosts.yml, docker config, .netrc,
# .git-credentials, ~/.aws ...), including glob spellings like `.en[v]`.
# Known limits (README v1.9.1): grep/rg -r can print secret lines from normally named
# files, git show/diff print committed blobs, repo-config git textconv drivers; the
# scout-write-gate content scan of briefings is the backstop.

ALLOWLIST = {
    "git", "chezmoi", "wc", "du", "stat", "ls", "find", "cat", "head", "tail",
    "grep", "rg", "jq", "sort", "uniq", "cut", "tr",
    "echo", "printf", "pwd", "whoami", "hostname", "date",
    "which", "where", "type", "file", "readlink", "realpath", "basename",
    "dirname", "tree", "diff", "cmp", "md5sum", "sha256sum", "shasum",
    "column", "nl", "fold", "paste", "test", "[", "true", "false", "sed",
}

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


def check_segment(segment):
    seg = segment.strip()
    if not seg:
        return None
    try:
        tokens = shlex.split(seg, posix=True)
    except ValueError:
        return "scout is read-only; unparseable quoting in command"
    return check_tokens(tokens)

def file_operands(first, tokens):
    """Positional operands that are read as files (approximate, errs toward checking
    more). For pattern-first commands the first positional is skipped unless the
    pattern came from -e/--regexp/-f."""
    out, skip_first, take = [], first in SCRIPT_FIRST, False
    for t in tokens[1:]:
        if take:
            take = False
            continue
        if t in ("-e", "--regexp", "-f", "--file", "--from-file") and first in ("grep", "rg", "sed", "awk"):
            skip_first = False
            if t in ("-f", "--file", "--from-file"):
                out.append("<pattern-file>")
            take = t in ("-e", "--regexp")
            continue
        if t.startswith("-") and "=" in t:
            out.append(t.split("=", 1)[1])
            continue
        if t.startswith("-"):
            continue
        if skip_first:
            skip_first = False
            continue
        out.append(t)
    return out


def check_secret_operands(first, tokens):
    if first == "git":
        rest = [t for t in tokens[1:] if not t.startswith("-")]
        cands = rest[1:]
    elif first in CONTENT_READERS:
        cands = file_operands(first, tokens)
    else:
        return None
    for c in cands:
        if c != "<pattern-file>" and is_secret_path(c):
            return "scout may not read secret-bearing files ('%s')" % c
    return None


def check_tokens(tokens):
    if not tokens:
        return None
    first_raw = tokens[0]
    first = normalize_cmd_token(first_raw)
    if first not in ALLOWLIST:
        return "scout is read-only; '%s' not in allowlist" % first_raw
    if is_secret_path is None:
        return "scout gate cannot load its secret-path helper (fail-closed)"
    reason = check_secret_operands(first, tokens) or indirect_file_read(first, tokens[1:])
    if reason:
        return "scout may not read secret-bearing files: " + reason if "reads a file" in reason else reason
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
    if first == "jq" and jq_file_read(tokens[1:]):
        return "scout may not read files via jq: " + jq_file_read(tokens[1:])
    if first in ("jq", "yq"):
        return check_jq_yq(first, tokens)
    if first == "uniq":
        return check_uniq(tokens)
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
    if is_secret_path is None:   # helper modules missing: fail CLOSED for scout
        return "scout gate cannot load its helper modules (fail-closed)"
    # Raw-string checks first: these must see the command before any unquoting.
    if _PROC_ENV_RAW_RE.search(command) or "/proc/" in command and re.search(r'/proc/[^\s]*[*?\[]', command):
        return "scout may not read the environment (/proc/*/environ)"
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
