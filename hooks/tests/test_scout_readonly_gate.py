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
    "jq '.a' f.json",
    "jq -r '.items[].name' f.json",
    "cat 0<README.md",
    "git remote",
    "date +%F",
    "file README.md",
    "wc -l f",
    "du -sh .",
    "md5sum README.md",
    "cat .env.tpl",
    "cat config/.env.example",
    "grep -rn environ src",
    "rg -n '.env' src",
    "jq '.environment' f.json",
    "ls -la ~/.config",
    "cat ~/.ssh/id_ed25519.pub",
    "chezmoi managed",
    "chezmoi source-path",
    r"git -C C:\x log --oneline -20",
    "chezmoi doctor",
    "wc -l *.md",
    "rg -n foo src | head -50",
    "jq '.a[]' big.json | sort | uniq -c",
    "cat f 2>/dev/null",
    "find . -name '*.md' | wc -l",
    "sed -n 1,5p f",
    "sed -n '1,5p' f | head",
    "sed -n '/foo/p' f",
    "sed 's/a/b/g' f",
    "git branch",
    "git branch -a --list",
    "git diff --stat",
    "sort -u f",
    "ls 2>&1 | head",
    "sed -E 's/x/y/' f",
    "sed -n '/foo/p' f",
    "sort -k2 f",
    "sort -r f",
    "tree -L 2",
    "rg -n foo",
    # legit quoted/escaped READ args must survive shlex unquoting (1.8.4)
    "grep -r \"foo bar\" .",
    "find . -name '*.md'",
    "git log --grep='fix: x'",
    "uniq f",
    "uniq -c f",
    "uniq -f 1 f",
    "uniq -f1 -c f",
    "uniq -c < f",
    "rg 'a|b' .",
    "ls 2>&1",
    "ls 2>/dev/null",
    "cat < f",
    "grep -n \"foo$\" f",
    "find . -name '*.py' | wc -l",
]

DENY_COMMANDS = [
    # 1.9.1 round 3 (F1-F5): awk/yq removed, jq file loads, GNU abbreviations, fd redirects, path spellings
    "awk 'NR==1{print}' f",
    "awk '{print $1}' f",
    "awk 'BEGIN{ARGV[1]=\".en\" \"v\"; ARGC=2} 1'",
    "yq '.a' f.yaml",
    "yq -n 'load_str(\".env\")'",
    "jq -n 'import \"h/.docker/config\" as $c; $c'",
    "jq -n 'include \"x\"; 1'",
    "jq -n -L ~/.docker 'import \"config\" as $c; $c'",
    "jq -nL ~/.docker '1'",
    "jq -f prog.jq f.json",
    "jq --rawfile x f -n '$x'",
    "jq --slurpfile x f -n '$x'",
    "date --f=.env",
    "date --fi=f",
    "wc --files0=f",
    "wc --f=f",
    "du --f=f",
    "file --files=f",
    "tree --fromtabfile f",
    "cat 0<.netrc",
    "cat 0<.git/config",
    "head 0<.env.local",
    "cat .git//config",
    "cat ./.git/./config",
    "cat ~/.config//op/config",
    "cat ~/.docker//config.json",
    "cat x/../.env",
    # 1.9.1 NB2 + minor
    "awk 'BEGIN{getline l < \".env\"; print l}'",
    "awk 'BEGIN{while((getline l < \"f\")>0) print l}'",
    "awk '{getline; print}' f",
    "date -f .env",
    "date -f f",
    "date --file=f",
    "file -f list",
    "wc --files0-from=f",
    "du --files0-from=f",
    "sort --files0-from=x",
    "tree --fromfile f",
    "find -files0-from f",
    "md5sum -c .env",
    "md5sum .env",
    "git remote -v",
    "git remote get-url origin",
    "git remote show -n origin",
    "cat .git/config",
    "grep url .git/config",
    # 1.9.1 B1: environment and secret-file reads
    "cat /proc/self/environ",
    "cat /proc/1/environ",
    "tr '\\0' '\\n' < /proc/self/environ",
    "cat /proc/self/env*",
    "cat /proc/*/environ",
    "cat /pro?/self/environ",
    "head -c 500 /proc/self//environ",
    "grep -a KEY /proc/self/environ",
    "jq -n env",
    "jq -n '$ENV'",
    "jq -n '$ENV.HOME'",
    "jq -n 'env.GH_TOKEN'",
    "yq -n 'strenv(GH_TOKEN)'",
    "yq -n '\"${X}\" | envsubst'",
    "awk 'BEGIN{for(k in ENVIRON)print k,ENVIRON[k]}'",
    "awk 'BEGIN{print ENVIRON[\"HOME\"]}'",
    "awk 'BEGIN{print PROCINFO[\"pid\"]}'",
    "less README.md",
    "less +!sh f",
    "chezmoi cat ~/.bashrc",
    "chezmoi diff",
    "chezmoi status",
    "chezmoi data",
    "chezmoi dump",
    "chezmoi verify",
    "git remote show origin",
    "cat .env",
    "cat config/.env.local",
    "cat .en[v]",
    "head ~/.config/op/config",
    "cat ~/.config/o?/config",
    "cat ~/.config/gh/hosts.yml",
    "cat ~/.docker/config.json",
    "cat ~/.netrc",
    "cat ~/.git-credentials",
    "cat ~/.aws/credentials",
    "cat ~/.ssh/id_ed25519",
    "cat ~/.ssh/id_*",
    "grep -rn TOKEN ~/.config/op",
    "rg -n TOKEN .env",
    "grep -e TOKEN .env",
    "jq . secrets.json",
    "jq --rawfile x .env -n '$x'",
    "sort .env",
    "awk '{print}' .env",
    "sed -n 1p .env",
    "diff .env .env.tpl",
    "git show HEAD:.env",
    "git diff HEAD -- .env",
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
    # write bypasses closed in 1.8.2
    "find . -fprint out",
    "find . -fprintf out %p",
    "git diff --output=/tmp/x",
    "sort -o f g",
    "sort --output=f g",
    "diff <(ls) <(rm -rf x)",
    "ls & rm x",
    "awk 'BEGIN{system (\"rm x\")}'",
    "chezmoi execute-template '{{ output \"rm\" \"x\" }}'",
    "git branch -D main",
    "git branch newbranch",
    "git remote add x y",
    "sed -n -i 1p f",
    "sed -e 1p f",
    "sed 'w out' f",
    "sed 's/a/b/w out' f",
    "sed '1e rm x' f",
    # 1.8.3: option-order / cluster bypasses
    "sed s/a/Z/ -i f",
    "sed s/a/b/ f -i.bak",
    "sed s/a/b/ --in-place f",
    "sed s/a/b/ -ibak f",
    "sed -n 1,5p -i f",
    "sed s/a/b/ -ni f",
    "sort -of f",
    "sort -oout g",
    "sort -k2 -of f",
    "sort -ro f",
    "sort --out=f g",
    "sort --o=f g",
    "sort --compress-program=sh f",
    "git remote -v add x y",
    "git remote -v remove origin",
    "git remote rename a b",
    "git remote update",
    "yq --inplace '.a=1' f.yaml",
    "yq -i '.a=1' f.yaml",
    "tree -o out",
    "tree -L 2 -o out",
    "rg --pre sh foo",
    "rg --pre=sh foo",
    # 1.8.4: quoted / escaped flag-token bypass class (shlex unquoting)
    "sed s/a/Z/ '-i' f",
    "sed s/a/Z/ \"-i\" f",
    "sed s/a/Z/ \\-i f",
    "sed s/a/Z/ '--in-place' f",
    "sort '-o' out g",
    "sort \"--output=o2\" g",
    "sort '-of' g",
    "sort \\-o f g",
    "sort --out\\put=f g",
    "git log '--output=lo' -1",
    "git diff \"--output=x\"",
    "yq '-i' . f",
    "tree '-o' out",
    "rg '--pre=sh' foo",
    "find . -exe\\c rm {} \\;",
    "find . -d\\elete",
    "find . -\"exec\" rm {} \\;",
    "find . -e\"\"xec rm {} \\;",
    "sed s/a/b/ \"unterminated f",
    "sort $'-o' out g",
    "sort $FLAG out g",
    "sort {-o,x} g",
    "awk 'BEGIN{print 1 | \"sh\"}'",
    "awk -f prog.awk f",
    "env -S 'rm x'",
    # 1.8.7: env/printenv dump secrets from the environment; env is no longer allow-listed
    "env",
    "env FOO=1",
    "env -i",
    "env -u FOO ls",
    "env FOO=1 cat f",
    "env FOO=1 grep -n x f",
    "env -C /tmp git log --oneline",
    "/usr/bin/env",
    "ENV",
    "printenv",
    "printenv HOME",
    "printenv | grep KEY",
    "ls; env",
    # 1.8.7: env-wrapped mutators, uniq output operand, awk output/profile flags
    "env sed -i s/a/b/ f",
    "env FOO=1 sed -i s/a/b/ f",
    "env -i sed -i s/a/b/ f",
    "env -u FOO sed -i s/a/b/ f",
    "env -uFOO sort -o x f",
    "env --unset=FOO sort -o x f",
    "env --unset FOO sort -o x f",
    "env find . -delete",
    "env git commit -m x",
    "env env sed -i s/a/b/ f",
    "uniq f out",
    "uniq -c f out",
    "uniq -f 1 f out",
    "uniq -f1 f out",
    "uniq -cf 1 f out",
    "uniq --skip-fields 1 f out",
    "uniq - out",
    "awk -o x 1 f",
    "awk -ofile 1 f",
    "awk -p x 1 f",
    "awk -pfile 1 f",
    "awk -d 1 f",
    "awk -dfile 1 f",
    "awk --profile 1 f",
    "awk --profile=x 1 f",
    "awk --dump-variables=x 1 f",
    "awk --dump-variables 1 f",
    "awk --pretty-print=x 1 f",
    "awk --pretty-print 1 f",
    "gawk -o x 1 f",
    "gawk --profile=x 1 f",
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


class TestFailClosed(unittest.TestCase):
    """1.9.1 M1: a damaged install without the helper modules must deny scout."""

    def test_missing_helpers_denies_scout(self):
        import shutil
        import tempfile
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "scout-readonly-gate.py")
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "scout-readonly-gate.py")
            shutil.copy(src, dst)
            payload = {"tool_name": "Bash", "agent_id": "a", "agent_type": "agent-orchestrator:scout",
                       "tool_input": {"command": "ls"}}
            proc = subprocess.run([sys.executable, dst], input=json.dumps(payload),
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout or "{}")
            self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", proc.stdout + proc.stderr)
