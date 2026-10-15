#!/usr/bin/env python3
# PreToolUse gate (matcher "*"): (1) stop tight status-polling loops and stop/respawn churn,
# (2) enforce a best-effort subagent lifetime limit. FAIL-OPEN on any internal error (never
# bricks a tool call); best-effort guardrail, not a sandbox.
#
# Why: an orchestrator once called ListAgents 142x (37 identical calls in a row), TaskStop 28x
# and respawned 26 agents instead of waiting for completion notifications. Subagents also ran
# 10-26 h, dominating cache-read cost.
#
# (1) Polling. Only "status-check" calls are watched: ListAgents, TaskOutput, TaskGet, TaskList,
#     BashOutput, TaskStop, SendMessage (identical args), Bash where the WHOLE command is `sleep N`
#     (a `sleep 5 && curl ...` health check is not watched) or a sleep/tail/cat/head/wc/ls/stat on
#     one of Claude Code's task output files, and Read of such a file. Task output files are
#     .../tasks/<id>.output or any .output file under a /claude-<uid>/ tmp tree; ordinary files in
#     a directory merely named tasks/ (Ansible roles/*/tasks/main.yml) are never watched. A call is identical when tool + arguments match. The Nth
#     identical call is denied when N >= LOOP_GUARD_MAX_IDENTICAL (default 5) consecutive (any
#     other tool call in between resets the streak), or when >= LOOP_GUARD_WINDOW_MAX (default 8)
#     identical calls fall within LOOP_GUARD_WINDOW_SECS (default 300). Past the limit it is an
#     exponential backoff, not a lockout: the next identical call is allowed only after
#     30s, 60s, 120s ... (cap 600s) since the last allowed one. Denied attempts change nothing, so the stated wait is exact; only an allowed call doubles the next wait.
#     TaskStop churn: more than LOOP_GUARD_MAX_STOPS (default 6) TaskStop calls per hour are denied.
# (2) Lifetime (subagents only, i.e. input has agent_id; the main thread auto-compacts). Tool calls
#     per agent are counted. At LOOP_GUARD_MAX_TURNS (default 150) or LOOP_GUARD_MAX_HOURS
#     (default 4) since first seen, the call is ALLOWED with an additionalContext warning (repeated
#     every 10 calls) telling the agent to compact or finish with a handoff summary. At
#     LOOP_GUARD_HARD_FACTOR (default 1.5) times either limit the call is DENIED so the agent
#     must end with its handoff summary as its final message.
# State: JSON per (session_id, agent_id) under $LOOP_GUARD_STATE_DIR, else
# ${XDG_CACHE_HOME:-~/.cache}/agent-orchestrator/ (fallback $TMPDIR); files older than 3 days
# are pruned. 1.10.1 hardening: (a) the $TMPDIR fallback dir is used only if it is a real
# directory (not a symlink) owned by us with mode 0700, else it is skipped (fail open); the state
# file is opened with O_NOFOLLOW. (b) Watched Bash commands are stored only as a sha256 hex digest,
# never as plaintext. (c) Per-file state keys are capped (oldest first); a watched command or path
# is normalised (strip + collapse whitespace) and hashed in full, but the regexes only ever see
# at most MAX_CMD_LEN chars of it (head + tail), so over-long input is still watched (padding does
# not evade the polling rule) while regex cost stays bounded. LOOP_GUARD_DISABLE=1 turns the hook off. LOOP_GUARD_NOW overrides the clock (tests).
# Limits: a model that alternates two different watched calls evades the streak rule (the window
# rule still catches identical repeats); wall-clock starts at the first tool call the hook sees.
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time

try:
    import fcntl
except ImportError:  # non-POSIX: no locking, still works single-threaded
    fcntl = None

WATCHED_TOOLS = {"ListAgents", "TaskOutput", "TaskGet", "TaskList", "BashOutput", "TaskStop", "SendMessage"}
# Claude Code's own background-task output files only: .../tasks/<id>.output, or any .output file
# under a /claude-<uid>/ tmp tree. A bare "/tasks/" (e.g. Ansible roles/web/tasks/main.yml) is NOT one.
OUT_PATH = r"(?:/tasks/[^/\s'\"]+\.output|/claude-\d+/[^\s'\"]*\.output)"
OUT_PATH_RE = re.compile(OUT_PATH + r"(?![\w.])")
READ_POLL = re.compile(OUT_PATH + r"$")
BASH_SLEEP_ONLY = re.compile(r"^\s*sleep\s+[\d.smhd]+\s*(?:\s#.*)?$")   # whole command is `sleep N` (+ optional # comment)
BASH_READER = re.compile(r"\b(sleep|tail|cat|head|wc|ls|stat)\b")
BACKOFF_BASE, BACKOFF_CAP = 30, 600
MAX_CMD_LEN = 4096     # regexes see at most this many chars (bounds CPU); signatures hash the full string
MAX_KEYS = 200         # cap on distinct signatures kept in `recent` / `last_allowed`

def env_num(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)

def emit(decision, text):
    out = {"hookEventName": "PreToolUse"}
    if decision == "deny":
        out.update(permissionDecision="deny", permissionDecisionReason=text)
    else:
        out.update(additionalContext=text)   # no permissionDecision: a warning must not bypass permission prompts
    print(json.dumps({"hookSpecificOutput": out}))

def norm(text):
    """Strip and collapse whitespace, so padding cannot make identical calls look different."""
    return " ".join(text.split())

def scan_view(text):
    """The part of an already-normalised string the regexes may see: all of it, or for over-long input
    the first and last MAX_CMD_LEN//2 chars (head for the command, tail for end-anchored `.output`)."""
    if len(text) <= MAX_CMD_LEN:
        return text
    h = MAX_CMD_LEN // 2
    return text[:h] + text[-h:]

def signature(tool, ti):
    """Return a string identifying a watched status-check call, or None if not watched."""
    if not isinstance(ti, dict):
        ti = {}
    if tool in WATCHED_TOOLS:
        return tool + ":" + hashlib.sha256(json.dumps(ti, sort_keys=True, default=str).encode()).hexdigest()[:16]
    if tool == "Bash":
        cmd = ti.get("command")
        if isinstance(cmd, str):
            full = norm(cmd)
            view = scan_view(full)
            # whole-command `sleep N`: single line only (norm() folds newlines, which would let a
            # `# comment` swallow a following command), and over-long input only when the length
            # comes from a trailing comment (so a long command that merely starts like a sleep is not)
            head = full[:MAX_CMD_LEN]
            sleep_only = ("\n" not in cmd.strip() and BASH_SLEEP_ONLY.match(head) is not None
                          and (len(full) <= MAX_CMD_LEN or " #" in head))
            if sleep_only or (OUT_PATH_RE.search(view) and BASH_READER.search(view)):
                # hashed (full normalised string): the state file never holds a plaintext command
                return "Bash:" + hashlib.sha256(full.encode()).hexdigest()[:16]
    if tool == "Read":
        p = ti.get("file_path")
        if isinstance(p, str):
            full = norm(p)
            if READ_POLL.search(scan_view(full)):
                return "Read:" + hashlib.sha256(
                    ("%s:%s:%s" % (full, ti.get("offset"), ti.get("limit"))).encode()).hexdigest()[:16]
    return None

def safe_private_dir(d):
    """True iff d is a real directory (not a symlink) owned by us with mode exactly 0700."""
    try:
        st = os.lstat(d)
    except OSError:
        return False
    return (stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid()
            and stat.S_IMODE(st.st_mode) == 0o700)

def state_dir():
    # (path, must_be_private): the shared-tmp fallback is attacker-reachable, so it is only used
    # when lstat shows our own 0700 directory; explicit/cache locations keep the old behaviour.
    cands = [(os.environ.get("LOOP_GUARD_STATE_DIR"), False),
             (os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "agent-orchestrator"), False),
             (os.path.join(tempfile.gettempdir(), "agent-orchestrator"), True)]
    for d, strict in cands:
        if d:
            try:
                if strict and not os.path.lexists(d):
                    os.mkdir(d, 0o700)
                    # mkdir mode is subject to umask: force 0700, but only on the dir we just made,
                    # via an O_NOFOLLOW fd so a swapped-in symlink is never chmod'ed
                    dfd = os.open(d, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
                    try:
                        os.fchmod(dfd, 0o700)
                    finally:
                        os.close(dfd)
                if strict and not safe_private_dir(d):
                    continue
                os.makedirs(d, mode=0o700, exist_ok=True)
                if os.access(d, os.W_OK):
                    return d
            except OSError:
                continue
    return None

def cap_keys(st):
    """Bound the per-signature maps: keep the MAX_KEYS most recently allowed signatures."""
    last = st.get("last_allowed")
    if not isinstance(last, dict) or len(last) <= MAX_KEYS:
        return
    keep = set(sorted(last, key=lambda k: last[k])[-MAX_KEYS:])
    st["last_allowed"] = {k: v for k, v in last.items() if k in keep}
    if isinstance(st.get("recent"), dict):
        st["recent"] = {k: v for k, v in st["recent"].items() if k in keep}

def prune(d, now):
    try:
        for n in os.listdir(d):
            if n.startswith("loopguard-"):
                p = os.path.join(d, n)
                if now - os.stat(p).st_mtime > 3 * 86400:
                    os.unlink(p)
    except OSError:
        pass

def backoff(excess):
    return min(BACKOFF_CAP, BACKOFF_BASE * (2 ** max(0, excess - 1)))

def check_poll(st, sig, tool, now):
    """Return a deny message, or None (and record the call) if allowed."""
    t_max = int(env_num("LOOP_GUARD_MAX_IDENTICAL", 5))
    w_max = int(env_num("LOOP_GUARD_WINDOW_MAX", 8))
    w_secs = env_num("LOOP_GUARD_WINDOW_SECS", 300)
    streak = st.get("streak") or {}
    n_pos = streak.get("n", 0) + 1 if streak.get("sig") == sig else 1
    recent = [t for t in (st.get("recent") or {}).get(sig, []) if now - t <= w_secs]
    excess = max(n_pos - t_max + 1, len(recent) + 1 - w_max + 1, 0)
    last = (st.get("last_allowed") or {}).get(sig)
    if excess > 0 and last is not None and now - last < backoff(excess):
        # Denied attempts do not touch the streak/window, so the stated wait is exact: a retry after
        # `wait` seconds is allowed, and only then does the next wait double.
        wait = int(backoff(excess) - (now - last)) + 1
        return ("Polling loop blocked: this identical %s call has now been made %d times in a row "
                "(%d within %ds). Do not poll subagent status - background subagents notify you "
                "on completion, so end your turn and WAIT for the notification. If a check is "
                "truly unavoidable, back off exponentially (30s, 60s, 120s ... cap 10m): this "
                "exact call is allowed again in ~%ds (the wait after that doubles, to ~%ds). Never stop and respawn a subagent that is "
                "still progressing; TaskStop is only for a genuinely hung or dead agent."
                % (tool, n_pos, len(recent) + 1, int(w_secs), wait, backoff(excess + 1)))
    st["streak"] = {"sig": sig, "n": n_pos}
    recent.append(now)
    st.setdefault("recent", {})[sig] = recent[-50:]
    st.setdefault("last_allowed", {})[sig] = now
    cap_keys(st)
    return None

def check_stops(st, now):
    stops = [t for t in st.get("stops", []) if now - t <= 3600]
    limit = int(env_num("LOOP_GUARD_MAX_STOPS", 6))
    if len(stops) >= limit:
        st["stops"] = stops
        return ("TaskStop churn blocked: %d TaskStop calls in the last hour. Stopping and respawning "
                "burns tokens and loses progress. Only stop a subagent that is genuinely hung or "
                "dead; otherwise wait for its completion notification." % len(stops))
    stops.append(now)
    st["stops"] = stops
    return None

def check_lifetime(st, now):
    """Return (decision, text) for a subagent past its lifetime limit, or None."""
    t_lim = env_num("LOOP_GUARD_MAX_TURNS", 150)
    h_lim = env_num("LOOP_GUARD_MAX_HOURS", 4)
    hard = env_num("LOOP_GUARD_HARD_FACTOR", 1.5)
    turns, hours = st["turns"], (now - st["first"]) / 3600.0
    if turns < t_lim and hours < h_lim:
        return None
    detail = "%d tool calls, %.1fh since first seen (limits: %d calls / %gh)" % (turns, hours, t_lim, h_lim)
    if turns >= t_lim * hard or hours >= h_lim * hard:
        return ("deny", "Subagent lifetime limit exceeded: " + detail + ". Stop calling tools now and end "
                "with your handoff summary (done / in-flight / next steps) as your final message so "
                "the orchestrator can restart a fresh agent with it.")
    if turns - st.get("last_warn", -10**9) >= 10:
        st["last_warn"] = turns
        return ("allow", "Subagent lifetime limit reached: " + detail + ". Compact your context now, or "
                "finish up and return a handoff summary (done / in-flight / next steps) so the "
                "orchestrator can restart a fresh agent with it. Tool calls are denied at "
                "%gx these limits." % hard)
    return None

def evaluate(st, data, now):
    tool = data.get("tool_name")
    ti = data.get("tool_input")
    st["turns"] = st.get("turns", 0) + 1
    st.setdefault("first", now)
    msg = None
    sig = signature(tool, ti)
    if sig is None:
        st["streak"] = {}
    else:
        msg = check_poll(st, sig, tool, now)
        if msg is None and tool == "TaskStop":
            msg = check_stops(st, now)
    if msg:
        return "deny", msg
    if data.get("agent_id"):
        return check_lifetime(st, now)
    return None

def main():
    if os.environ.get("LOOP_GUARD_DISABLE") == "1":
        return
    data = json.loads(sys.stdin.read())          # malformed -> except -> allow
    sid = data.get("session_id")
    if not isinstance(data, dict) or not isinstance(sid, str) or not sid or not data.get("tool_name"):
        return
    now = float(os.environ.get("LOOP_GUARD_NOW") or time.time())
    d = state_dir()
    if not d:
        return
    key = "%s|%s" % (sid, data.get("agent_id") or "main")
    path = os.path.join(d, "loopguard-" + hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")
    new = not os.path.exists(path)
    if new:
        prune(d, now)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+") as f:
        try:
            os.fchmod(fd, 0o600)   # creation mode is subject to umask; a 0400 file could not be reopened
        except OSError:
            pass
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            st = json.loads(f.read() or "{}")
            if not isinstance(st, dict):
                st = {}
        except ValueError:
            st = {}
        result = evaluate(st, data, now)
        f.seek(0)
        f.truncate()
        f.write(json.dumps(st))
    if result:
        emit(*result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("loop-guard fail-open: %r\n" % (e,))
    sys.exit(0)   # never brick a tool call
