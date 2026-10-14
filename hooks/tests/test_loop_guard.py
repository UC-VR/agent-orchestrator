#!/usr/bin/env python3
"""Tests for hooks/loop-guard.py. Stdlib only. Each test gets its own state dir and fake clock."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "loop-guard.py")

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 1_000_000.0

    def call(self, tool, ti=None, sid="s1", agent_id=None, raw=None, env_extra=None):
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti or {},
                   "session_id": sid}
        if agent_id:
            payload["agent_id"] = agent_id
        env = {k: v for k, v in os.environ.items() if not k.startswith("LOOP_GUARD_")}
        env.update(LOOP_GUARD_STATE_DIR=self.tmp.name, LOOP_GUARD_NOW=str(self.now))
        env.update(env_extra or {})
        p = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(payload),
                           capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return (json.loads(p.stdout) if p.stdout.strip() else {}), p.stderr

    def decision(self, *a, **k):
        o = self.call(*a, **k)[0].get("hookSpecificOutput", {})
        return (o.get("permissionDecision") or ("warn" if o.get("additionalContext") else None)), o

class TestPolling(Base):
    def test_four_identical_allowed_fifth_denied(self):
        for i in range(4):
            self.now += 1
            self.assertIsNone(self.decision("ListAgents")[0], i)
        self.now += 1
        d, o = self.decision("ListAgents")
        self.assertEqual(d, "deny")
        self.assertIn("WAIT for the notification", o["permissionDecisionReason"])

    def test_backoff_then_allowed_again(self):
        for _ in range(4):
            self.now += 1
            self.decision("ListAgents")
        self.now += 1
        self.assertEqual(self.decision("ListAgents")[0], "deny")
        self.now += 10
        self.assertEqual(self.decision("ListAgents")[0], "deny")   # still inside 30s+ backoff
        self.now += 400
        self.assertIsNone(self.decision("ListAgents")[0])

    def test_different_args_not_identical(self):
        for i in range(10):
            self.now += 1
            self.assertIsNone(self.decision("TaskOutput", {"task_id": "t%d" % i})[0])

    def test_interleaved_work_resets_streak(self):
        for _ in range(4):
            self.now += 1
            self.decision("ListAgents")
        self.now += 1
        self.assertIsNone(self.decision("Edit", {"file_path": "/x"})[0])
        self.now += 1
        self.assertIsNone(self.decision("ListAgents")[0])

    def test_window_rule_catches_alternation(self):
        denied = False
        for i in range(12):
            self.now += 5
            self.decision("ListAgents")
            self.now += 1
            self.decision("Edit", {"file_path": "/x"})
            self.now += 1
            d, _ = self.decision("ListAgents")
            denied = denied or d == "deny"
        self.assertTrue(denied)

    def test_normal_tools_never_watched(self):
        for i in range(30):
            self.now += 1
            self.assertIsNone(self.decision("Bash", {"command": "git status"})[0])
            self.assertIsNone(self.decision("Read", {"file_path": "/home/vr/a.py"})[0])

    def test_bash_sleep_and_output_tail_watched(self):
        for cmd in ("sleep 30", "tail -n 5 /tmp/claude/tasks/abc.output"):
            sid = "s-" + cmd[:4]
            res = []
            for _ in range(6):
                self.now += 1
                res.append(self.decision("Bash", {"command": cmd}, sid=sid)[0])
            self.assertEqual(res[:4], [None] * 4, cmd)
            self.assertEqual(res[4], "deny", cmd)

    def test_ansible_tasks_file_never_denied(self):
        for tool, ti in (("Read", {"file_path": "/home/vr/infra/roles/web/tasks/main.yml"}),
                         ("Read", {"file_path": "/home/vr/infra/roles/web/tasks/main.output.yml"}),
                         ("Bash", {"command": "cat roles/web/tasks/main.yml"}),
                         ("Bash", {"command": "ls /home/vr/infra/roles/web/tasks/"}),
                         ("Bash", {"command": "tail -n 5 /var/log/subagents/x.log"})):
            for i in range(12):
                self.now += 1
                self.assertIsNone(self.decision(tool, ti, sid="a-" + tool + ti.get("command", ti.get("file_path", "")))[0],
                                  (ti, i))
            # with an edit in between, as in the incident report
        for i in range(10):
            self.now += 1
            self.assertIsNone(self.decision("Read", {"file_path": "roles/web/tasks/main.yml"}, sid="e")[0])
            self.assertIsNone(self.decision("Edit", {"file_path": "roles/web/tasks/main.yml"}, sid="e")[0])

    def test_sleep_with_real_work_not_denied(self):
        for cmd in ("sleep 5 && curl -fsS http://localhost:8080/health",
                    "sleep 2; systemctl is-active foo", "sleep 1 | cat"):
            for i in range(10):
                self.now += 1
                self.assertIsNone(self.decision("Bash", {"command": cmd}, sid="c" + cmd[:12])[0], (cmd, i))

    def test_sleep_plus_output_file_check_watched(self):
        cmd = "sleep 30 && tail -n 3 /tmp/claude-1000/proj/sess/tasks/abc123.output"
        res = []
        for _ in range(6):
            self.now += 1
            res.append(self.decision("Bash", {"command": cmd})[0])
        self.assertEqual(res[4], "deny")

    def test_retry_hint_is_accurate(self):
        import re
        for _ in range(4):
            self.now += 1
            self.decision("ListAgents")
        self.now += 1
        d, o = self.decision("ListAgents")
        self.assertEqual(d, "deny")
        m = re.search(r"allowed again in ~(\d+)s \(the wait after that doubles, to ~(\d+)s\)",
                      o["permissionDecisionReason"])
        self.assertTrue(m, o["permissionDecisionReason"])
        wait, nxt = int(m.group(1)), int(m.group(2))
        # hammering while denied must not lengthen the wait
        self.now += 3
        d, o2 = self.decision("ListAgents")
        self.assertEqual(d, "deny")
        wait2 = int(re.search(r"allowed again in ~(\d+)s", o2["permissionDecisionReason"]).group(1))
        self.assertLessEqual(wait2, wait - 2)
        # one second early: still denied; at the stated time: allowed
        self.now += wait2 - 2
        self.assertEqual(self.decision("ListAgents")[0], "deny")
        self.now += 2
        self.assertIsNone(self.decision("ListAgents")[0])
        # and the very next retry now needs the announced longer wait
        self.now += 1
        d, o3 = self.decision("ListAgents")
        self.assertEqual(d, "deny")
        wait3 = int(re.search(r"allowed again in ~(\d+)s", o3["permissionDecisionReason"]).group(1))
        self.assertGreaterEqual(nxt, wait3)
        self.assertGreater(nxt, wait)
        self.now += wait3
        self.assertIsNone(self.decision("ListAgents")[0])

    def test_denial_tells_to_wait_for_notification(self):
        for _ in range(5):
            self.now += 1
            d, o = self.decision("ListAgents")
        self.assertIn("WAIT for the notification", o["permissionDecisionReason"])

    def test_read_of_output_file_watched(self):
        res = []
        for _ in range(6):
            self.now += 1
            res.append(self.decision("Read", {"file_path": "/tmp/claude-1000/p/s/tasks/a1.output"})[0])
        self.assertEqual(res[4], "deny")

    def test_threshold_env_override(self):
        env = {"LOOP_GUARD_MAX_IDENTICAL": "2"}
        self.now += 1
        self.assertIsNone(self.decision("ListAgents", env_extra=env)[0])
        self.now += 1
        self.assertEqual(self.decision("ListAgents", env_extra=env)[0], "deny")

    def test_sessions_and_agents_isolated(self):
        for _ in range(4):
            self.now += 1
            self.decision("ListAgents", sid="a")
        self.now += 1
        self.assertIsNone(self.decision("ListAgents", sid="b")[0])
        self.assertIsNone(self.decision("ListAgents", sid="a", agent_id="ag1")[0])

class TestStopChurn(Base):
    def test_taskstop_churn_denied(self):
        res = []
        for i in range(8):
            self.now += 60
            res.append(self.decision("TaskStop", {"task_id": "t%d" % i})[0])
        self.assertEqual(res[:6], [None] * 6)
        self.assertEqual(res[6], "deny")
        self.now += 3700
        self.assertIsNone(self.decision("TaskStop", {"task_id": "tz"})[0])

class TestLifetime(Base):
    def test_under_limit_silent(self):
        for _ in range(20):
            self.now += 1
            self.assertIsNone(self.decision("Bash", {"command": "ls"}, agent_id="a1")[0])

    def test_turn_limit_warns_then_denies(self):
        env = {"LOOP_GUARD_MAX_TURNS": "10"}
        res = []
        for i in range(16):
            self.now += 1
            d, o = self.decision("Bash", {"command": "ls %d" % i}, agent_id="a1", env_extra=env)
            res.append((d, o.get("additionalContext", "")))
        self.assertEqual([d for d, _ in res[:9]], [None] * 9)
        self.assertEqual(res[9][0], "warn")
        self.assertNotIn("permissionDecision", self.call("Bash", {"command": "ls x"}, agent_id="a2", env_extra={"LOOP_GUARD_MAX_TURNS": "1"})[0].get("hookSpecificOutput", {}))
        self.assertIn("handoff summary", res[9][1])
        self.assertIsNone(res[10][0])                # warn is rate-limited
        self.assertEqual(res[14][0], "deny")         # 15 = 1.5x

    def test_hour_limit(self):
        env = {"LOOP_GUARD_MAX_HOURS": "1"}
        self.assertIsNone(self.decision("Bash", {"command": "ls"}, agent_id="a1", env_extra=env)[0])
        self.now += 3700
        self.assertEqual(self.decision("Bash", {"command": "ls"}, agent_id="a1", env_extra=env)[0], "warn")
        self.now += 2000
        self.assertEqual(self.decision("Bash", {"command": "ls"}, agent_id="a1", env_extra=env)[0], "deny")

    def test_main_thread_not_limited(self):
        env = {"LOOP_GUARD_MAX_TURNS": "3"}
        for i in range(10):
            self.now += 1
            self.assertIsNone(self.decision("Bash", {"command": "ls %d" % i}, env_extra=env)[0])

class TestFailOpen(Base):
    def test_malformed_json(self):
        res, err = self.call("x", raw="{nope")
        self.assertEqual(res, {})
        self.assertIn("loop-guard fail-open", err)

    def test_missing_session_id_or_tool(self):
        self.assertEqual(self.call("x", raw=json.dumps({"tool_name": "ListAgents"}))[0], {})
        self.assertEqual(self.call("x", raw=json.dumps({"session_id": "s"}))[0], {})

    def test_corrupt_state_file_recovers(self):
        self.decision("ListAgents")
        for n in os.listdir(self.tmp.name):
            with open(os.path.join(self.tmp.name, n), "w") as f:
                f.write("garbage{")
        self.assertIsNone(self.decision("ListAgents")[0])

    def test_unwritable_state_dir(self):
        res, _ = self.call("ListAgents", env_extra={"LOOP_GUARD_STATE_DIR": "/proc/nope/x",
                                                    "XDG_CACHE_HOME": "/proc/nope", "TMPDIR": "/proc/nope"})
        self.assertIsInstance(res, dict)

    def test_disable_env(self):
        for _ in range(8):
            self.now += 1
            self.assertIsNone(self.decision("ListAgents", env_extra={"LOOP_GUARD_DISABLE": "1"})[0])

if __name__ == "__main__":
    unittest.main()
