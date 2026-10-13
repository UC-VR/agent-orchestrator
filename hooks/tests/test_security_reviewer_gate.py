#!/usr/bin/env python3
"""Tests for hooks/security-reviewer-gate.py. Stdlib only (unittest + subprocess)."""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "security-reviewer-gate.py")


def run_raw(text):
    proc = subprocess.run([sys.executable, HOOK], input=text, capture_output=True,
                          text=True, timeout=10)
    assert proc.returncode == 0, "hook must exit 0, got %r stderr=%s" % (proc.returncode, proc.stderr)
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def bash(command, agent_id="a1", agent_type="agent-orchestrator:security-reviewer", tool="Bash"):
    p = {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": "/tmp",
         "tool_input": {"command": command}}
    if agent_id is not None:
        p["agent_id"] = agent_id
    if agent_type is not None:
        p["agent_type"] = agent_type
    return run_raw(json.dumps(p))


def is_deny(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


ALLOW = [
    "git diff",
    "git diff --stat HEAD~1",
    "git log --oneline -20",
    "git status",
    "git show HEAD:README.md",
    "git branch -a",
    "git ls-files",
    "grep -rn 'op://' .",
    "grep -rn \"op://\" src 2>/dev/null",
    "rg -n 'password' src | head -20",
    "cat .env.tpl",
    "cat .env.example",
    "head -20 config/.env.tpl",
    "cat README.md",
    "ls -la",
    "find . -name '*.env' -not -path './.git/*'",
    "env FOO=1 ls",
    "printf hello",
    "export FOO=bar",
    "wc -l *.py",
    "sort f | uniq -c",
    "git log 2>&1 | head",
    "echo hi 2>/dev/null",
    "grep -rn 'API_KEY' --include='*.py' .",
]

DENY = [
    # secret exposure
    "op read op://v/i/f",
    "op item get foo --fields password",
    "op item get foo",
    "op inject -i .env.tpl",
    "op run -- env",
    "op document get doc",
    "op --account x read op://v/i/f",
    "/usr/bin/op read op://v/i/f",
    "env",
    "env -i",
    "env FOO=1",
    "printenv",
    "printenv HOME",
    "set",
    "export -p",
    "export",
    "declare -x",
    "cat .env",
    "cat config/.env",
    "cat .env.local",
    "cat .env.production",
    "cat prod.env",
    "less .env",
    "head -5 .env",
    "tail -f .env",
    "bat .env",
    "cat creds/credentials.json",
    "cat ~/.aws/credentials",
    "cat server.pem",
    "cat tls/private.key",
    "cat ~/.ssh/id_rsa",
    "cat id_ed25519",
    "cat < .env",
    "git show HEAD:.env",
    "git diff -- .env",
    "grep -n TOKEN .env",
    "grep -e TOKEN .env",
    "cat /proc/1/environ",
    "cat /proc/self/environ",
    "tr '\\0' '\\n' < /proc/self/environ",
    "strings /proc/123/environ",
    "env | sort",
    "echo hi; printenv",
    "bash -c 'op read op://v/i/f'",
    "bash -c 'cat .env'",
    "sudo cat .env",
    "xargs cat .env",
    "echo $SECRET",
    "echo `op read op://v/i/f`",
    "cat <(op read op://v/i/f)",
    "eval 'op read x'",
    "python3 -c 'import os;print(os.environ)'",
    "bash",
    # mutation
    "rm -rf x",
    "rm f",
    "mv a b",
    "cp a b",
    "tee out.txt",
    "ls | tee out.txt",
    "echo hi > f",
    "echo hi >> f",
    "echo hi >f",
    "echo hi 1> f",
    "echo hi &> f",
    "git commit -m x",
    "git push",
    "git push origin main",
    "git reset --hard",
    "git checkout main",
    "git -C /tmp commit -m x",
    "git branch -D x",
    "git branch newbranch",
    "git config user.name x",
    "sed -i s/a/b/ f",
    "sed -ni 1p f",
    "sed --in-place s/a/b/ f",
    "find . -delete",
    "find . -exec rm {} \;",
    "touch f",
    "mkdir d",
    "chmod 777 f",
    "ls && rm f",
    "unterminated 'quote",
]


class TestAllow(unittest.TestCase):
    def test_allow(self):
        for c in ALLOW:
            with self.subTest(cmd=c):
                r = bash(c)
                self.assertFalse(is_deny(r), "expected allow: %r -> %r" % (c, r))


class TestDeny(unittest.TestCase):
    def test_deny(self):
        for c in DENY:
            with self.subTest(cmd=c):
                r = bash(c)
                self.assertTrue(is_deny(r), "expected deny: %r -> %r" % (c, r))


class TestNoOp(unittest.TestCase):
    def test_other_callers_noop_even_for_denied_commands(self):
        for at in ("agent-orchestrator:worker", "agent-orchestrator:scout", "xsecurity-reviewer",
                   "security-reviewer-lite", "security"):
            for c in ("op read op://v/i/f", "cat .env", "rm -rf x"):
                with self.subTest(at=at, cmd=c):
                    self.assertEqual(bash(c, agent_type=at), {})

    def test_no_agent_id_or_type(self):
        self.assertEqual(bash("cat .env", agent_id=None), {})
        self.assertEqual(bash("cat .env", agent_id=""), {})
        self.assertEqual(bash("cat .env", agent_type=None), {})

    def test_bare_agent_type_is_identified(self):
        self.assertTrue(is_deny(bash("cat .env", agent_type="security-reviewer")))

    def test_malformed_json_and_other_tools(self):
        self.assertEqual(run_raw("{nope"), {})
        self.assertEqual(run_raw("[]"), {})
        self.assertEqual(bash("cat .env", tool="Read"), {})

    def test_reviewer_with_missing_command_is_noop(self):
        p = {"tool_name": "Bash", "agent_id": "a", "agent_type": "security-reviewer", "tool_input": {}}
        self.assertEqual(run_raw(json.dumps(p)), {})


if __name__ == "__main__":
    unittest.main()
