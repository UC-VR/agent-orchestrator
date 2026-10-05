#!/usr/bin/env python3
"""Tests for hooks/model-tier-gate.py. Stdlib only (unittest + subprocess).

Pipes synthetic PreToolUse payloads into the script's stdin and asserts on its
stdout JSON, mirroring how Claude Code invokes it.
"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "model-tier-gate.py")

def run_raw(stdin_text, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("ORCHESTRATOR_ALLOW_NAMED_SPAWNS", "ORCHESTRATOR_ALLOW_FORK")}
    env.update(env_extra or {})
    proc = subprocess.run([sys.executable, HOOK], input=stdin_text,
                          capture_output=True, text=True, timeout=10, env=env)
    assert proc.returncode == 0, "hook must always exit 0, got %r stderr=%s" % (
        proc.returncode, proc.stderr)
    out = proc.stdout.strip()
    return (json.loads(out) if out else {}), proc.stderr

def spawn(tool_input, tool_name="Agent", env_extra=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool_name,
               "tool_input": tool_input}
    return run_raw(json.dumps(payload), env_extra)[0]

def is_deny(result):
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

def reason(result):
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")

class TestModelTierGate(unittest.TestCase):
    def test_haiku_denied(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "haiku"})))
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "model": "claude-haiku-4-5"})))

    def test_fable_denied(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "fable"})))
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "model": "FABLE"})))

    def test_named_spawn_denied_and_env_escape(self):
        ti = {"subagent_type": "agent-orchestrator:worker", "name": "bob"}
        self.assertTrue(is_deny(spawn(ti)))
        self.assertFalse(is_deny(spawn(ti, env_extra={"ORCHESTRATOR_ALLOW_NAMED_SPAWNS": "1"})))

    def test_unpinned_types_without_model_denied(self):
        for t in ("general-purpose", "Explore", "Plan", "claude-code-guide", "claude"):
            with self.subTest(t=t):
                self.assertTrue(is_deny(spawn({"subagent_type": t})))

    def test_unpinned_types_with_sonnet_allowed(self):
        for t in ("general-purpose", "Explore", "Plan"):
            with self.subTest(t=t):
                self.assertFalse(is_deny(spawn({"subagent_type": t, "model": "sonnet"})))

    def test_pinned_worker_without_model_allowed(self):
        for t in ("agent-orchestrator:worker", "agent-orchestrator:verifier",
                  "agent-orchestrator:judge", "agent-orchestrator:scout"):
            with self.subTest(t=t):
                self.assertFalse(is_deny(spawn({"subagent_type": t})))

    def test_explicit_sonnet_and_opus_allowed(self):
        self.assertFalse(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "sonnet"})))
        self.assertFalse(is_deny(spawn({"subagent_type": "general-purpose", "model": "opus"})))

    def test_task_alias_enforced(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose"}, tool_name="Task")))
        self.assertFalse(is_deny(spawn({"subagent_type": "general-purpose", "model": "sonnet"}, tool_name="Task")))

    def test_other_tool_ignored(self):
        self.assertEqual(spawn({"subagent_type": "general-purpose"}, tool_name="Bash"), {})

    def test_malformed_json_fails_open(self):
        result, stderr = run_raw("{not json")
        self.assertEqual(result, {})
        self.assertIn("model-tier-gate fail-open", stderr)

    # --- 1.8.2 leak closures ---
    def test_missing_subagent_type_treated_as_general_purpose(self):
        self.assertTrue(is_deny(spawn({"prompt": "x"})))
        self.assertTrue(is_deny(spawn({"subagent_type": "", "prompt": "x"})))
        self.assertFalse(is_deny(spawn({"prompt": "x", "model": "sonnet"})))

    def test_inherit_model_treated_as_no_model(self):
        for m in ("inherit", "Inherit", " INHERIT "):
            with self.subTest(m=m):
                self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "model": m})))
        # pinned type + inherit still resolves to its frontmatter pin
        self.assertFalse(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "inherit"})))

    def test_fork_denied_unless_env(self):
        res = spawn({"subagent_type": "fork", "prompt": "x"})
        self.assertTrue(is_deny(res))
        self.assertIn("fork inherits the orchestrator's model tier; spawn a typed agent instead", reason(res))
        # model override is ignored by forks, so an explicit model does not help
        self.assertTrue(is_deny(spawn({"subagent_type": "fork", "model": "sonnet"})))
        self.assertFalse(is_deny(spawn({"subagent_type": "fork"}, env_extra={"ORCHESTRATOR_ALLOW_FORK": "1"})))

if __name__ == "__main__":
    unittest.main()
