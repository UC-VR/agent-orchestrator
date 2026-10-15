#!/usr/bin/env python3
"""1.10.1 hardening tests for hooks/loop-guard.py (split from test_loop_guard.py to stay under 500 lines).
Stdlib only. Reuses the Base harness (per-test state dir and fake clock)."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_loop_guard import Base, HOOK


class TestHardening1101(Base):
    """1.10.1 P2 fixes: (a) TMPDIR fallback + O_NOFOLLOW, (b) hashed commands, (c) key cap / long commands."""

    @staticmethod
    def _mod():
        import importlib.util
        spec = importlib.util.spec_from_file_location("loop_guard_under_test", HOOK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _fallback_env(self, tmpdir):
        # LOOP_GUARD_STATE_DIR empty and the cache dir unusable -> only the $TMPDIR fallback is left
        return {"LOOP_GUARD_STATE_DIR": "", "XDG_CACHE_HOME": "/proc/nope", "TMPDIR": tmpdir}

    def _poll5(self, env):
        res = []
        for _ in range(6):
            self.now += 1
            res.append(self.decision("ListAgents", env_extra=env)[0])
        return res

    # (a) $TMPDIR fallback ownership / mode / symlink
    def test_fallback_symlinked_dir_not_used(self):
        victim = os.path.join(self.tmp.name, "victim")
        os.mkdir(victim, 0o700)
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        os.symlink(victim, os.path.join(t, "agent-orchestrator"))
        res = self._poll5(self._fallback_env(t))
        self.assertEqual(os.listdir(victim), [])        # nothing written through the symlink
        self.assertNotIn("deny", res)                    # fail open: no state, no polling denial

    def test_fallback_wrong_mode_not_used(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        d = os.path.join(t, "agent-orchestrator")
        os.mkdir(d)
        os.chmod(d, 0o755)
        res = self._poll5(self._fallback_env(t))
        self.assertEqual(os.listdir(d), [])
        self.assertNotIn("deny", res)
        self.assertEqual(os.stat(d).st_mode & 0o777, 0o755)   # left alone, not "fixed" or trusted

    def test_fallback_group_writable_or_world_mode_rejected(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        d = os.path.join(t, "agent-orchestrator")
        for mode in (0o770, 0o707, 0o777, 0o750, 0o500):
            os.mkdir(d)
            os.chmod(d, mode)
            self._poll5(self._fallback_env(t))
            self.assertEqual(os.listdir(d), [], oct(mode))
            os.chmod(d, 0o700)
            os.rmdir(d)

    def test_fallback_good_dir_used_and_created_0700(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        res = self._poll5(self._fallback_env(t))
        d = os.path.join(t, "agent-orchestrator")
        self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(d).st_uid, os.getuid())
        self.assertTrue(os.listdir(d))
        self.assertEqual(res[4], "deny")                 # state in use -> polling rule works

    def test_fallback_existing_0700_own_dir_used(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        d = os.path.join(t, "agent-orchestrator")
        os.mkdir(d, 0o700)
        os.chmod(d, 0o700)
        self.assertEqual(self._poll5(self._fallback_env(t))[4], "deny")

    def test_safe_private_dir_checks_uid_mode_symlink(self):
        mod = self._mod()
        d = os.path.join(self.tmp.name, "p")
        os.mkdir(d, 0o700)
        os.chmod(d, 0o700)
        self.assertTrue(mod.safe_private_dir(d))
        real_uid = os.getuid()
        mod.os.getuid = lambda: real_uid + 1             # pretend someone else owns it
        try:
            self.assertFalse(mod.safe_private_dir(d))
        finally:
            mod.os.getuid = lambda: real_uid
        link = os.path.join(self.tmp.name, "lnk")
        os.symlink(d, link)
        self.assertFalse(mod.safe_private_dir(link))
        self.assertFalse(mod.safe_private_dir(os.path.join(self.tmp.name, "missing")))
        f = os.path.join(self.tmp.name, "afile")
        open(f, "w").close()
        os.chmod(f, 0o700)
        self.assertFalse(mod.safe_private_dir(f))        # a regular file is not a directory

    def test_state_file_symlink_not_followed(self):
        import hashlib
        victim = os.path.join(self.tmp.name, "victim.txt")
        with open(victim, "w") as f:
            f.write("keep")
        name = "loopguard-" + hashlib.sha256(b"s1|main").hexdigest()[:24] + ".json"
        os.symlink(victim, os.path.join(self.tmp.name, name))
        res, err = self.call("ListAgents")
        self.assertEqual(res, {})
        self.assertIn("loop-guard fail-open", err)       # O_NOFOLLOW -> ELOOP -> fail open
        with open(victim) as f:
            self.assertEqual(f.read(), "keep")

    # (b) no plaintext commands in state
    def test_state_holds_no_plaintext_command(self):
        marker = "SUPERSECRETMARKER-xyz"
        cmd = "sleep 30 && tail -n 3 /tmp/claude-1000/%s/tasks/abc123.output" % marker
        for _ in range(6):
            self.now += 1
            d, _o = self.decision("Bash", {"command": cmd})
        self.assertEqual(d, "deny")                      # still watched and denied
        blob = ""
        for n in os.listdir(self.tmp.name):
            with open(os.path.join(self.tmp.name, n)) as f:
                blob += f.read()
        self.assertTrue(blob)
        self.assertNotIn(marker, blob)
        self.assertNotIn("tail", blob)
        self.assertNotIn("sleep", blob)

    def test_state_holds_no_plaintext_sleep_or_read_path(self):
        for _ in range(2):
            self.now += 1
            self.decision("Bash", {"command": "sleep 45"})
            self.decision("Read", {"file_path": "/tmp/claude-1000/PATHMARK/tasks/a1.output"})
        blob = ""
        for n in os.listdir(self.tmp.name):
            with open(os.path.join(self.tmp.name, n)) as f:
                blob += f.read()
        self.assertNotIn("PATHMARK", blob)
        self.assertNotIn("sleep", blob)
        self.assertNotIn("a1.output", blob)

    def test_signature_is_sha256_hex_and_whitespace_insensitive(self):
        mod = self._mod()
        a = mod.signature("Bash", {"command": "sleep   30"})
        b = mod.signature("Bash", {"command": "sleep 30"})
        self.assertEqual(a, b)
        self.assertRegex(a, r"^Bash:[0-9a-f]{16}$")
        self.assertNotEqual(a, mod.signature("Bash", {"command": "sleep 31"}))
        self.assertRegex(mod.signature("Read", {"file_path": "/x/claude-1/tasks/a.output"})
                         or "", r"^$|^Read:[0-9a-f]{16}$")

    # (c) cap + long commands
    def test_key_cap_prunes_oldest_first(self):
        mod = self._mod()
        st = {}
        n = mod.MAX_KEYS + 50
        for i in range(n):
            mod.check_poll(st, "TaskOutput:%04d" % i, "TaskOutput", 1000.0 + i)
        self.assertLessEqual(len(st["last_allowed"]), mod.MAX_KEYS)
        self.assertLessEqual(len(st["recent"]), mod.MAX_KEYS)
        self.assertNotIn("TaskOutput:0000", st["last_allowed"])           # oldest evicted
        self.assertIn("TaskOutput:%04d" % (n - 1), st["last_allowed"])    # newest kept
        self.assertEqual(set(st["last_allowed"]), set(st["recent"]))

    # (c)/B1: over-long or padded commands are still WATCHED (regex input bounded, hash over full string)
    def _five(self, cmd, tool="Bash", key="command", sid="pad"):
        res = []
        for _ in range(6):
            self.now += 1
            res.append(self.decision(tool, {key: cmd}, sid=sid)[0])
        return res

    def test_overlimit_padded_sleep_denied_on_fifth(self):
        for cmd in ("sleep 5" + " " * 5000, "sleep 5" + " " * 4096, "sleep" + " " * 4100 + "5",
                    "sleep 5 # " + "x" * 5000):
            res = self._five(cmd, sid="p" + str(len(cmd)))
            self.assertEqual(res[:4], [None] * 4, cmd[:12])
            self.assertEqual(res[4], "deny", cmd[:12])

    def test_whitespace_padded_sleep_denied_on_fifth(self):
        for cmd in ("  sleep   5  ", "sleep 5\t\t", "\n\nsleep 5\n", "sleep 5  # waiting"):
            res = self._five(cmd, sid="w" + str(abs(hash(cmd))))
            self.assertEqual(res[4], "deny", repr(cmd))

    def test_padding_variants_share_one_streak(self):
        # alternating paddings of the same sleep must count as identical calls
        res = []
        for i in range(6):
            self.now += 1
            res.append(self.decision("Bash", {"command": "sleep 5" + " " * (10 + i * 900)}, sid="share")[0])
        self.assertEqual(res[4], "deny")

    def test_long_tail_of_task_output_denied(self):
        cmds = ["tail -n 5 /tmp/claude-1000/" + "d" * 4500 + "/tasks/abc.output",
                "tail   -n   5   " + " " * 5000 + "/tmp/claude-1000/p/s/tasks/abc.output",
                "tail -n 5 " + "x" * 5000 + " /tmp/claude-1000/p/s/tasks/abc.output"]
        for n, cmd in enumerate(cmds):
            res = self._five(cmd, sid="t%d" % n)
            self.assertEqual(res[4], "deny", cmd[:30])

    def test_long_read_of_task_output_denied(self):
        res = self._five("/tmp/claude-1000/" + "d" * 5000 + "/tasks/a1.output", tool="Read", key="file_path", sid="rd")
        self.assertEqual(res[4], "deny")

    def test_long_non_polling_command_not_denied(self):
        for n, cmd in enumerate(("echo " + "x" * 6000, "git log " + "a " * 3000, "sleep 5 && curl " + "u" * 5000,
                                 "sleep " + "5" * 5000 + "; rm -rf x", "ls " + "y" * 5000 + " /var/log/app.log",
                                 "sleep 5 # c\nrm x")):
            for i in range(10):
                self.now += 1
                self.assertIsNone(self.decision("Bash", {"command": cmd}, sid="np%d" % n)[0], (cmd[:20], i))

    def test_long_command_state_is_hash_only(self):
        cmd = "tail -n 5 /tmp/claude-1000/LONGMARK" + "d" * 5000 + "/tasks/abc.output"
        self._five(cmd, sid="hash")
        blob = ""
        for n in os.listdir(self.tmp.name):
            with open(os.path.join(self.tmp.name, n)) as f:
                blob += f.read()
        self.assertTrue(blob)
        self.assertNotIn("LONGMARK", blob)
        self.assertLess(len(blob), 4000)

    def test_regex_input_bounded_on_pathological_command(self):
        import time
        mod = self._mod()
        t0 = time.time()
        for cmd in ("sleep " + "9" * 100000 + "!", "tail " + "/claude-1/" * 20000, "sleep 5 " + "# " * 50000):
            mod.signature("Bash", {"command": cmd})
        self.assertLess(time.time() - t0, 2.0)

    # B1 follow-up: fallback dir under a restrictive umask
    def test_fallback_dir_created_0700_under_umask_0277(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        code = ("import os,sys,runpy;os.umask(0o277);sys.argv=['x'];"
                "import importlib.util as u;s=u.spec_from_file_location('lg',%r);m=u.module_from_spec(s);"
                "s.loader.exec_module(m);print(m.state_dir())" % HOOK)
        env = {k: v for k, v in os.environ.items() if not k.startswith("LOOP_GUARD_")}
        env.update(LOOP_GUARD_STATE_DIR="", XDG_CACHE_HOME="/proc/nope", TMPDIR=t)
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=10)
        d = os.path.join(t, "agent-orchestrator")
        self.assertEqual(p.stdout.strip(), d, p.stderr)
        self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)

    def test_fallback_used_end_to_end_under_umask_0277(self):
        t = os.path.join(self.tmp.name, "t")
        os.mkdir(t, 0o700)
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "ListAgents", "tool_input": {},
                              "session_id": "um"})
        env = {k: v for k, v in os.environ.items() if not k.startswith("LOOP_GUARD_")}
        env.update(LOOP_GUARD_STATE_DIR="", XDG_CACHE_HOME="/proc/nope", TMPDIR=t)
        outs = []
        for i in range(6):
            env["LOOP_GUARD_NOW"] = str(1_000_000 + i)
            p = subprocess.run(["sh", "-c", "umask 0277; exec %s %s" % (sys.executable, HOOK)], input=payload,
                               capture_output=True, text=True, env=env, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            outs.append("deny" in p.stdout)
        d = os.path.join(t, "agent-orchestrator")
        self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)
        self.assertTrue(os.listdir(d))                   # state written (file chmod'ed to 0600 so it reopens)
        self.assertEqual(outs[:4], [False] * 4)
        self.assertTrue(outs[4])                         # state in use under the odd umask -> polling denied


if __name__ == "__main__":
    unittest.main()
