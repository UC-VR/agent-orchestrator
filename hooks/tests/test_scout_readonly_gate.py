#!/usr/bin/env python3
"""Tests for hooks/scout-readonly-gate.py. Stdlib only (unittest + subprocess).

Pipes synthetic PreToolUse payloads into the script's stdin and asserts on
its stdout JSON, mirroring how Claude Code actually invokes it.
"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scout-readonly-gate.py")

SCOUT_PAYLOAD_BASE = {
    "session_id": "test-session",
    "transcript_path": "/tmp/does-not-matter.jsonl",
    "cwd": "C:\\x",
    "agent_id": "agent-123",
    "agent_type": "agent-orchestrator:scout",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
}

WORKER_PAYLOAD_BASE = {
    "session_id": "test-session",
    "transcript_path": "/tmp/does-not-matter.jsonl",
    "cwd": "C:\\x",
    "agent_id": "agent-456",
    "agent_type": "agent-orchestrator:worker",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
}


def run_hook(payload):
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, "hook must always exit 0 (fail-open), got %r stderr=%s" % (
        proc.returncode, proc.stderr)
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def scout_command(command):
    payload = dict(SCOUT_PAYLOAD_BASE)
    payload["tool_input"] = {"command": command}
    return run_hook(payload)


def worker_command(command):
    payload = dict(WORKER_PAYLOAD_BASE)
    payload["tool_input"] = {"command": command}
    return run_hook(payload)


def is_deny(result):
    return (
        isinstance(result, dict)
        and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    )


ALLOW_COMMANDS = [
    r"git -C C:\x log --oneline -20",
    "chezmoi doctor",
    "wc -l *.md",
    "rg -n foo src | head -50",
    "jq '.a[]' big.json | sort | uniq -c",
    "cat f 2>/dev/null",
    "find . -name '*.md' | wc -l",
]

DENY_COMMANDS = [
    "git commit -m x",
    r"git -C C:\x push",
    "chezmoi apply",
    "echo hi > f.txt",
    "rg foo | tee out.txt",
    "sed -i s/a/b/ f",
    "jq -i . f",
    "find . -delete",
    'awk \'{print > "x"}\' f',
    'bash -c "rm x"',
    "op read op://v/i/f",
    "git log && rm -rf x",
    r"C:\Program Files\Git\bin\rm.exe x",
]


class TestScoutReadonlyGateAllow(unittest.TestCase):
    def test_allowed_commands_pass_for_scout(self):
        for cmd in ALLOW_COMMANDS:
            with self.subTest(cmd=cmd):
                result = scout_command(cmd)
                self.assertFalse(is_deny(result), "expected allow, got deny for: %r (%r)" % (cmd, result))


class TestScoutReadonlyGateDeny(unittest.TestCase):
    def test_denied_commands_blocked_for_scout(self):
        for cmd in DENY_COMMANDS:
            with self.subTest(cmd=cmd):
                result = scout_command(cmd)
                self.assertTrue(is_deny(result), "expected deny, got allow for: %r (%r)" % (cmd, result))


class TestScoutReadonlyGateNoOpForOthers(unittest.TestCase):
    def test_denied_commands_are_noop_for_non_scout_caller(self):
        for cmd in DENY_COMMANDS:
            with self.subTest(cmd=cmd):
                result = worker_command(cmd)
                self.assertEqual(result, {}, "expected no-op {} for non-scout caller, got: %r for %r" % (result, cmd))

    def test_noop_when_tool_name_is_not_bash(self):
        payload = dict(SCOUT_PAYLOAD_BASE)
        payload["tool_name"] = "Read"
        payload["tool_input"] = {"file_path": "f.txt"}
        result = run_hook(payload)
        self.assertEqual(result, {})

    def test_noop_for_denied_command_when_tool_name_not_bash(self):
        payload = dict(SCOUT_PAYLOAD_BASE)
        payload["tool_name"] = "Grep"
        payload["tool_input"] = {"pattern": "git commit -m x > f.txt"}
        result = run_hook(payload)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
