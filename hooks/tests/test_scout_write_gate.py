#!/usr/bin/env python3
"""Tests for hooks/scout-write-gate.py. Stdlib only (unittest + subprocess)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "scout-write-gate.py")


def run_raw(text):
    proc = subprocess.run([sys.executable, HOOK], input=text, capture_output=True,
                          text=True, timeout=10)
    assert proc.returncode == 0, "hook must exit 0, got %r stderr=%s" % (proc.returncode, proc.stderr)
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def call(tool, tool_input, cwd="/tmp", agent_id="a1", agent_type="agent-orchestrator:scout"):
    p = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": cwd}
    if agent_id is not None:
        p["agent_id"] = agent_id
    if agent_type is not None:
        p["agent_type"] = agent_type
    return run_raw(json.dumps(p))


def write(path, **kw):
    return call("Write", {"file_path": path, "content": "x"}, **kw)


def is_deny(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class TestAllowed(unittest.TestCase):
    def test_absolute_briefing_names(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("_briefing.md", "slice1_briefing.md", "briefing.md"):
                with self.subTest(n=n):
                    self.assertEqual(write(os.path.join(d, n)), {})

    def test_relative_path_resolved_against_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(write("out/slice2_briefing.md", cwd=d), {})

    def test_bare_plugin_agent_type(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(write(os.path.join(d, "a_briefing.md"), agent_type="scout"), {})


class TestDenied(unittest.TestCase):
    def test_non_briefing_names(self):
        for n in ("x.md", "a.txt", "notes_briefing.md.sh", "briefing.md.bak", "xbriefing.md", "my-briefing.md"):
            with self.subTest(n=n):
                self.assertTrue(is_deny(write("/tmp/" + n)))

    def test_dotdot_escape_to_non_briefing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(is_deny(write("../evil.md", cwd=d)))
            self.assertTrue(is_deny(write(os.path.join(d, "sub", "..", "evil.sh"))))

    def test_git_and_claude_dirs(self):
        for p in ("/tmp/repo/.git/x_briefing.md", "/tmp/repo/.claude/x_briefing.md",
                  "/tmp/repo/.git/hooks/pre-commit"):
            with self.subTest(p=p):
                self.assertTrue(is_deny(write(p)))
        self.assertTrue(is_deny(write(".claude/settings_briefing.md", cwd="/tmp/repo")))

    def test_symlink_to_non_briefing_target(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "victim.sh")
            open(target, "w").close()
            link = os.path.join(d, "evil_briefing.md")
            os.symlink(target, link)
            self.assertTrue(is_deny(write(link)))

    def test_symlinked_dir_into_dotclaude(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".claude"))
            os.symlink(os.path.join(d, ".claude"), os.path.join(d, "lnk"))
            self.assertTrue(is_deny(write(os.path.join(d, "lnk", "x_briefing.md"))))

    def test_edit_family_denied_outright(self):
        self.assertTrue(is_deny(call("Edit", {"file_path": "/tmp/x_briefing.md", "old_string": "a", "new_string": "b"})))
        self.assertTrue(is_deny(call("MultiEdit", {"file_path": "/tmp/x_briefing.md", "edits": []})))
        self.assertTrue(is_deny(call("NotebookEdit", {"notebook_path": "/tmp/x_briefing.md", "new_source": "x"})))

    def test_missing_or_empty_file_path(self):
        self.assertTrue(is_deny(call("Write", {"content": "x"})))
        self.assertTrue(is_deny(call("Write", {"file_path": "", "content": "x"})))
        self.assertTrue(is_deny(call("Write", {"file_path": "  "})))
        self.assertTrue(is_deny(call("Write", {"file_path": 5})))
        self.assertTrue(is_deny(call("Write", None)))


class TestNoOp(unittest.TestCase):
    def test_other_callers(self):
        for at in ("agent-orchestrator:worker", "agent-orchestrator:verifier", "xscout", "scout-like", "myscout"):
            with self.subTest(at=at):
                self.assertEqual(write("/tmp/x.md", agent_type=at), {})

    def test_no_agent_id_or_type(self):
        self.assertEqual(write("/tmp/x.md", agent_id=None), {})
        self.assertEqual(write("/tmp/x.md", agent_id=""), {})
        self.assertEqual(write("/tmp/x.md", agent_type=None), {})

    def test_malformed_json_noop(self):
        self.assertEqual(run_raw("{nope"), {})
        self.assertEqual(run_raw("[]"), {})

    def test_other_tool_noop(self):
        self.assertEqual(call("Read", {"file_path": "/tmp/x.md"}), {})


if __name__ == "__main__":
    unittest.main()
