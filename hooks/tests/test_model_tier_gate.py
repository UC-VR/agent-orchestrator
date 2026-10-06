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
           if k not in ("ORCHESTRATOR_ALLOW_NAMED_SPAWNS", "ORCHESTRATOR_ALLOW_FORK",
                        "MODEL_TIER_GATE_CLI_VERSION", "CLAUDE_CODE_VERSION", "AI_AGENT")}
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

V_NEW = {"MODEL_TIER_GATE_CLI_VERSION": "2.1.291"}
V_OLD = {"MODEL_TIER_GATE_CLI_VERSION": "2.1.289"}

def out(result):
    return result.get("hookSpecificOutput", {})

class TestModelTierGate(unittest.TestCase):
    def test_haiku_denied(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "haiku"})))
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "model": "claude-haiku-4-5"})))

    def test_fable_denied(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "agent-orchestrator:worker", "model": "fable"})))
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "model": "FABLE"})))

    def test_named_spawn_denied_and_env_escape(self):
        ti = {"subagent_type": "agent-orchestrator:worker", "name": "bob"}
        self.assertTrue(is_deny(spawn(ti, env_extra=V_OLD)))
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

class TestNameStrip(unittest.TestCase):
    TI = {"subagent_type": "agent-orchestrator:verifier", "prompt": "p", "description": "d", "name": "v1"}

    def test_strip_allows_with_updated_input(self):
        res = spawn(self.TI, env_extra=V_NEW)
        o = out(res)
        self.assertEqual(o["permissionDecision"], "allow")
        self.assertEqual(o["hookEventName"], "PreToolUse")
        self.assertEqual(o["updatedInput"], {"subagent_type": "agent-orchestrator:verifier",
                                             "prompt": "p", "description": "d"})
        self.assertIn("`name` was removed", o["additionalContext"])
        self.assertIn("SendMessage", o["additionalContext"])

    def test_strip_task_alias(self):
        self.assertIn("updatedInput", out(spawn(self.TI, tool_name="Task", env_extra=V_NEW)))

    def test_strip_drops_teammate_only_fields(self):
        ti = dict(self.TI, team_name="t", teamName="t2", mode="plan")
        ui = out(spawn(ti, env_extra=V_NEW))["updatedInput"]
        for k in ("name", "team_name", "teamName", "mode"):
            self.assertNotIn(k, ui)
        self.assertEqual(ui["prompt"], "p")

    def test_haiku_beats_strip(self):
        res = spawn(dict(self.TI, model="haiku"), env_extra=V_NEW)
        self.assertTrue(is_deny(res))
        self.assertNotIn("updatedInput", out(res))

    def test_fork_beats_strip(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "fork", "name": "f"}, env_extra=V_NEW)))

    def test_unpinned_no_model_beats_strip(self):
        self.assertTrue(is_deny(spawn({"subagent_type": "general-purpose", "name": "g"}, env_extra=V_NEW)))
        self.assertTrue(is_deny(spawn({"name": "g"}, env_extra=V_NEW)))

    def test_unpinned_with_model_stripped(self):
        o = out(spawn({"subagent_type": "general-purpose", "model": "sonnet", "name": "g"}, env_extra=V_NEW))
        self.assertEqual(o["updatedInput"], {"subagent_type": "general-purpose", "model": "sonnet"})

    def test_old_version_denies_with_suffix(self):
        res = spawn(self.TI, env_extra=V_OLD)
        self.assertTrue(is_deny(res))
        self.assertIn("(strip unavailable: CLI < 2.1.290 or version unknown)", reason(res))
        self.assertTrue(is_deny(spawn(self.TI, env_extra={"MODEL_TIER_GATE_CLI_VERSION": "2.0.99"})))

    def test_boundary_version_2_1_290_strips(self):
        self.assertIn("updatedInput", out(spawn(self.TI, env_extra={"MODEL_TIER_GATE_CLI_VERSION": "2.1.290"})))
        self.assertIn("updatedInput", out(spawn(self.TI, env_extra={"MODEL_TIER_GATE_CLI_VERSION": "2.2.0"})))

    def test_unknown_version_denies(self):
        # no override, no AI_AGENT, empty PATH (no `claude`) -> unknown
        res = spawn(self.TI, env_extra={"PATH": "/nonexistent"})
        self.assertTrue(is_deny(res))
        self.assertIn("strip unavailable", reason(res))

    def test_ai_agent_env_version(self):
        self.assertIn("updatedInput", out(spawn(self.TI, env_extra={"AI_AGENT": "claude-code_2-1-291_harness", "PATH": "/nonexistent"})))
        self.assertTrue(is_deny(spawn(self.TI, env_extra={"AI_AGENT": "claude-code_2-1-289_harness", "PATH": "/nonexistent"})))

    def test_claude_version_cached(self):
        import tempfile, stat
        with tempfile.TemporaryDirectory() as d:
            exe = os.path.join(d, "claude")
            with open(exe, "w") as f:
                f.write("#!/bin/sh\necho '2.1.295 (Claude Code)'\n")
            os.chmod(exe, 0o755)
            env = {"PATH": d + ":/usr/bin:/bin", "XDG_RUNTIME_DIR": d}
            self.assertIn("updatedInput", out(spawn(self.TI, env_extra=env)))
            cache = os.path.join(d, "model-tier-gate.cliver")
            self.assertEqual(stat.S_IMODE(os.stat(cache).st_mode), 0o600)
            # cache hit: break the binary (same mtime) and the cached version is still used
            st = os.stat(exe)
            with open(exe, "w") as f:
                f.write("#!/bin/sh\nexit 1\n")
            os.utime(exe, ns=(st.st_atime_ns, st.st_mtime_ns))
            self.assertIn("updatedInput", out(spawn(self.TI, env_extra=env)))

    def test_env_escape_keeps_name_no_updated_input(self):
        res = spawn(self.TI, env_extra=dict(V_NEW, ORCHESTRATOR_ALLOW_NAMED_SPAWNS="1"))
        self.assertEqual(res, {})

    def test_no_name_output_unchanged(self):
        # golden: 1.8.5 behaviour on the 99% path (allow = empty stdout; deny = exact JSON)
        self.assertEqual(spawn({"subagent_type": "agent-orchestrator:worker"}, env_extra=V_NEW), {})
        self.assertEqual(spawn({"subagent_type": "agent-orchestrator:worker", "name": "  "}, env_extra=V_NEW), {})
        self.assertEqual(spawn({"subagent_type": "general-purpose", "model": "sonnet"}, env_extra=V_NEW), {})
        self.assertEqual(spawn({"subagent_type": "general-purpose"}), {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "Model-tier policy: unpinned agent types "
            "(general-purpose/Explore/Plan/claude) must be spawned with an explicit "
            "model: sonnet or opus — omitting it inherits the caller's model and can "
            "leak fable/haiku onto delegated work."}})

if __name__ == "__main__":
    unittest.main()
