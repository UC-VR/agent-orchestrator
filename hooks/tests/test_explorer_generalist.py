#!/usr/bin/env python3
"""1.10.2 tests: explorer/generalist tier rules, explorer read-only gates, planner/explorer
secret-path deny, verify-reminder skipping planner, agent frontmatter. Stdlib only."""
import json
import os
import re
import subprocess
import sys
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.join(os.path.dirname(HOOKS), "agents")

def run(script, payload, raw=False):
    cmd = ["sh", os.path.join(HOOKS, script)] if script.endswith(".sh") else [sys.executable, os.path.join(HOOKS, script)]
    p = subprocess.run(cmd, input=payload if raw else json.dumps(payload),
                       capture_output=True, text=True, timeout=10)
    assert p.returncode == 0, p.stderr
    out = p.stdout.strip()
    return json.loads(out) if out else {}

def deny(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

def tool(script, name, ti, agent_type):
    return run(script, {"hook_event_name": "PreToolUse", "tool_name": name, "tool_input": ti,
                        "cwd": "/tmp", "agent_id": "a1", "agent_type": agent_type})

def spawn(ti):
    return run("model-tier-gate.py", {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": ti})

class TestTierGate(unittest.TestCase):
    def test_explorer_haiku_high_allowed(self):
        for t in ("agent-orchestrator:explorer", "explorer"):
            for m in ("pool-haiku-high", "pool-haiku", "haiku"):
                self.assertEqual(spawn({"subagent_type": t, "model": m}), {}, (t, m))
        self.assertEqual(spawn({"subagent_type": "agent-orchestrator:explorer"}), {})  # frontmatter pin

    def test_explorer_old_haiku_and_fable_denied(self):
        for m in ("claude-haiku-4-5", "pool-fable", "fable"):
            self.assertTrue(deny(spawn({"subagent_type": "agent-orchestrator:explorer", "model": m})), m)

    def test_generalist_haiku_denied(self):
        for t in ("agent-orchestrator:generalist", "generalist"):
            for m in ("haiku", "pool-haiku", "pool-haiku-high", "claude-haiku-5-5"):
                self.assertTrue(deny(spawn({"subagent_type": t, "model": m})), (t, m))

    def test_generalist_sonnet_allowed_fable_denied(self):
        t = "agent-orchestrator:generalist"
        self.assertEqual(spawn({"subagent_type": t, "model": "pool-sonnet-high"}), {})
        self.assertEqual(spawn({"subagent_type": t}), {})
        self.assertTrue(deny(spawn({"subagent_type": t, "model": "pool-fable"})))

    def test_pool_fable_still_planner_only(self):
        self.assertEqual(spawn({"subagent_type": "agent-orchestrator:planner", "model": "pool-fable"}), {})
        for t in ("agent-orchestrator:explorer", "agent-orchestrator:generalist", "planner"):
            self.assertTrue(deny(spawn({"subagent_type": t, "model": "pool-fable"})), t)

class TestExplorerGates(unittest.TestCase):
    EX = "agent-orchestrator:explorer"

    def test_bash_readonly_allowed_writes_denied(self):
        self.assertEqual(tool("scout-readonly-gate.py", "Bash", {"command": "rg foo src | head"}, self.EX), {})
        for c in ("rm -rf x", "git commit -m x", "echo hi > f", "sed -i s/a/b/ f", "curl http://x"):
            self.assertTrue(deny(tool("scout-readonly-gate.py", "Bash", {"command": c}, self.EX)), c)

    def test_bash_secret_read_denied(self):
        self.assertTrue(deny(tool("scout-readonly-gate.py", "Bash", {"command": "cat /home/v/.env"}, self.EX)))

    def test_write_edit_denied_even_for_briefings(self):
        for name, ti in (("Write", {"file_path": "/tmp/x_briefing.md", "content": "x"}),
                         ("Edit", {"file_path": "/tmp/a", "old_string": "a", "new_string": "b"}),
                         ("MultiEdit", {"file_path": "/tmp/a", "edits": []}),
                         ("NotebookEdit", {"notebook_path": "/tmp/a", "new_source": "x"})):
            self.assertTrue(deny(tool("scout-write-gate.py", name, ti, self.EX)), name)

    def test_scout_briefing_write_still_allowed(self):
        self.assertEqual(tool("scout-write-gate.py", "Write", {"file_path": "/tmp/x_briefing.md", "content": "x"},
                              "agent-orchestrator:scout"), {})

class TestSecretPathDeny(unittest.TestCase):
    def test_explorer_and_planner_read_grep(self):
        for at in ("agent-orchestrator:explorer", "agent-orchestrator:planner", "planner"):
            for name, ti in (("Read", {"file_path": "/home/v/.env"}),
                             ("Read", {"file_path": "/home/v/.ssh/id_ed25519"}),
                             ("Grep", {"pattern": "T", "path": "/home/v/.config/op"}),
                             ("Grep", {"pattern": "T", "glob": ".env*"})):
                self.assertTrue(deny(tool("scout-write-gate.py", name, ti, at)), (at, name, ti))
            for name, ti in (("Read", {"file_path": "/repo/README.md"}),
                             ("Grep", {"pattern": "x", "path": "/repo/src"})):
                self.assertEqual(tool("scout-write-gate.py", name, ti, at), {}, (at, name))

    def test_other_agents_untouched(self):
        for at in ("agent-orchestrator:worker", "agent-orchestrator:generalist"):
            self.assertEqual(tool("scout-write-gate.py", "Read", {"file_path": "/home/v/.env"}, at), {})

    def test_no_agent_id_untouched(self):
        p = {"tool_name": "Read", "tool_input": {"file_path": "/home/v/.env"}, "agent_type": "planner"}
        self.assertEqual(run("scout-write-gate.py", p), {})

class TestVerifyReminder(unittest.TestCase):
    def reminder(self, st):
        return run("verify-reminder.sh", json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": st}}), raw=True)

    def test_planner_no_reminder(self):
        for st in ("agent-orchestrator:planner", "planner"):
            self.assertEqual(self.reminder(st), {}, st)

    def test_worker_and_generalist_still_reminded(self):
        for st in ("agent-orchestrator:worker", "agent-orchestrator:generalist"):
            self.assertIn("additionalContext", self.reminder(st).get("hookSpecificOutput", {}), st)

class TestAgentFiles(unittest.TestCase):
    def fm(self, n):
        txt = open(os.path.join(AGENTS, n + ".md")).read()
        head = txt.split("---")[1]
        body = txt.split("---", 2)[2]
        return head, body

    def test_pins_and_caps(self):
        for n, model, cap in (("explorer", "pool-haiku-high", "40"), ("generalist", "pool-sonnet-high", "150")):
            head, body = self.fm(n)
            self.assertRegex(head, r"(?m)^model: %s$" % model)
            self.assertRegex(head, r"(?m)^maxTurns: %s$" % cap)
            self.assertRegex(body, r"You are running agent-orchestrator v\d+\.\d+\.\d+\.")

    def test_explorer_tools_read_only(self):
        head, _ = self.fm("explorer")
        tools = re.search(r"(?m)^tools: (.*)$", head).group(1)
        self.assertEqual(tools, "Read, Grep, Glob, Bash")

    def test_version_stamps_match_plugin_json(self):
        pj = os.path.join(os.path.dirname(HOOKS), ".claude-plugin", "plugin.json")
        if not os.path.exists(pj):
            self.skipTest("no plugin.json")
        v = json.load(open(pj))["version"]
        for n in ("explorer", "generalist", "scout"):
            self.assertIn("agent-orchestrator v%s." % v, self.fm(n)[1])

if __name__ == "__main__":
    unittest.main()
