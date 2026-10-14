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



class TestSecrets191(unittest.TestCase):
    """1.9.1 B1: no secret values in briefings; no Read/Grep of secret files."""

    def _w(self, content):
        with tempfile.TemporaryDirectory() as d:
            return call("Write", {"file_path": os.path.join(d, "x_briefing.md"), "content": content})

    def test_secret_content_denied(self):
        for c in ("key:\n-----BEGIN OPENSSH PRIVATE KEY-----\nabc",
                  "token ghp_" + "a" * 36,
                  "github_pat_" + "A" * 40,
                  "OPENAI=sk-" + "b" * 30,
                  "slack xoxb-1234567890-abcdef",
                  "AKIAABCDEFGHIJKLMNOP",
                  "OP_SERVICE_ACCOUNT_TOKEN=ops_" + "c" * 40,
                  "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghij",
                  "api_key: abcdefghijklmnopqrstuv",
                  'password = "hunter2hunter2hunter2"'):
            with self.subTest(c=c[:30]):
                self.assertTrue(is_deny(self._w(c)))

    def test_benign_content_allowed(self):
        for c in ("# Briefing\n- token comes from os.environ['GH_TOKEN'] (file.py:12)",
                  "password: <redacted>", "api_key = ${API_KEY}", "uses op://vault/item/field",
                  "secret: redacted", "plain notes"):
            with self.subTest(c=c[:30]):
                self.assertEqual(self._w(c), {})

    def test_read_grep_secret_paths_denied(self):
        for tool, ti in (("Read", {"file_path": "/home/v/.env"}),
                         ("Read", {"file_path": "/proc/self/environ"}),
                         ("Read", {"file_path": "/home/v/.config/op/config"}),
                         ("Read", {"file_path": "/home/v/.config/gh/hosts.yml"}),
                         ("Read", {"file_path": "/home/v/.docker/config.json"}),
                         ("Read", {"file_path": "/home/v/.netrc"}),
                         ("Read", {"file_path": "/home/v/.ssh/id_ed25519"}),
                         ("Grep", {"pattern": "TOKEN", "path": "/home/v/.config/op"}),
                         ("Grep", {"pattern": "TOKEN", "glob": ".env*"})):
            with self.subTest(tool=tool, ti=ti):
                self.assertTrue(is_deny(call(tool, ti)))

    def test_read_grep_normal_paths_allowed(self):
        for tool, ti in (("Read", {"file_path": "/repo/README.md"}),
                         ("Read", {"file_path": "/repo/.env.example"}),
                         ("Grep", {"pattern": "x", "path": "/repo/src"})):
            with self.subTest(tool=tool, ti=ti):
                self.assertEqual(call(tool, ti), {})

    def test_read_by_other_agents_untouched(self):
        self.assertEqual(call("Read", {"file_path": "/home/v/.env"},
                              agent_type="agent-orchestrator:worker"), {})


if __name__ == "__main__":
    unittest.main()
