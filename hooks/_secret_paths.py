#!/usr/bin/env python3
# Shared helpers for the scout and security-reviewer gates (1.9.1): recognise
# secret-bearing file operands (including glob spellings) and secret-looking content.
# Imported by sibling hook scripts via their own directory; a gate that cannot import
# this module must fail CLOSED for the agent it guards.
import fnmatch
import os
import re

_SAFE_ENV_SUFFIX = (".tpl", ".example", ".sample", ".template")
# basenames that always hold credentials
SECRET_BASENAMES = {
    ".netrc", "_netrc", ".git-credentials", ".npmrc", ".pypirc", ".pgpass", ".vault-token",
    ".env", "credentials", "credentials.json", "hosts.yml", "id_rsa", "id_dsa", "id_ecdsa",
    "id_ed25519", "token", "token.json", "secrets.json", "secrets.yaml", "secrets.yml",
}
# path fragments (matched on "/" + lowercased path) whose whole subtree is secret
SECRET_DIRS = ("/.git/config", "/.git/credentials", "/.config/op", "/.op", "/.config/gh", "/.docker/config.json", "/.aws",
               "/.kube/config", "/.gnupg", "/.ssh/id_", "/.password-store",
               "/.config/gcloud", "/.azure")
_GLOB_CHARS = re.compile(r'[*?\[]')
_PROC_RE = re.compile(r'(^|/)proc/[^/]*/(environ|.*\*)|(^|/)proc/[^/]*[*?\[]')


def _plain_secret(c):
    p = "/" + c.strip().rstrip("/").lower().replace("\\", "/")
    p = os.path.normpath(p.replace("/~/", "/").replace("/$home/", "/"))
    if "/proc/" in p and "environ" in p:
        return True
    for d in SECRET_DIRS:
        if d in p and (p.endswith(d) or p[p.index(d) + len(d):][:1] in ("/", "")):
            return True
        if d.endswith("/id_") and d in p:
            return not p.endswith(".pub")
    b = os.path.basename(p)
    if not b:
        return False
    if b.endswith(_SAFE_ENV_SUFFIX):
        return False
    if b in SECRET_BASENAMES or b.startswith(".env") or b.endswith(".env"):
        return True
    if "credentials" in b or b.endswith((".pem", ".key", ".p12", ".pfx", ".keystore")):
        return True
    if re.match(r'^id_(rsa|dsa|ecdsa|ed25519)', b) and not b.endswith(".pub"):
        return True
    return False


def _glob_secret(c):
    """A glob operand is secret if it could expand to a secret path."""
    p = "/" + c.strip().rstrip("/").lower().replace("\\", "/")
    p = re.sub(r'/+', "/", p.replace("/~/", "/").replace("/./", "/"))
    if "/proc/" in p or p.startswith("/proc"):
        return True
    b = os.path.basename(p)
    for name in SECRET_BASENAMES | {".env.local", ".env.production", "id_rsa", "server.pem",
                                    "private.key", "environ"}:
        if fnmatch.fnmatch(name, b):
            return True
    psegs = [x for x in p.split("/") if x]
    for d in SECRET_DIRS:
        dsegs = [x for x in d.split("/") if x]
        last = dsegs[-1]
        for start in range(len(psegs)):
            window = psegs[start:start + len(dsegs)]
            if len(window) < len(dsegs):
                break
            if all(fnmatch.fnmatch(ds if ds != last or not ds.endswith("_") else ds + "x", ps)
                   for ds, ps in zip(dsegs, window)) and any(_GLOB_CHARS.search(w) for w in window):
                return True
    return False


# Flags that make an otherwise "names-only" command read a FILE and echo its lines
# (often in error output): date -f, file -f, wc/du/sort --files0-from, tree --fromfile,
# find -files0-from, hostname -F. Both gates deny these outright (1.9.1, verifier NB2).
# (short-flag regex, dangerous GNU long-option names: any unique PREFIX is accepted by
# getopt_long, so `--f=`, `--files0=` must match too)
_INDIRECT = {
    "date": (r'^-[A-Za-z]*f', ("file",)),
    "file": (r'^-[A-Za-z]*[fm]', ("files-from", "magic-file")),
    "wc": (None, ("files0-from",)),
    "du": (r'^-[A-Za-z]*X', ("files0-from", "exclude-from")),
    "sort": (None, ("files0-from",)),
    "tree": (None, ("fromfile", "fromtabfile")),
    "find": (r'^-files0-from', ()),
    "hostname": (r'^-[A-Za-z]*F', ("file",)),
    "md5sum": (r'^-[A-Za-z]*c', ("check",)),
    "sha256sum": (r'^-[A-Za-z]*c', ("check",)),
    "sha1sum": (r'^-[A-Za-z]*c', ("check",)),
    "shasum": (r'^-[A-Za-z]*c', ("check",)),
}


def indirect_file_read(cmd, args):
    """Reason string if `cmd args` reads a file through a list/format-file flag."""
    spec = _INDIRECT.get(cmd)
    if spec is None:
        return None
    short, longs = spec
    for a in args:
        if a.startswith("--"):
            name = a[2:].split("=", 1)[0]
            if name and any(l.startswith(name) for l in longs):
                return "`%s %s` reads a file and can echo its contents" % (cmd, a)
        elif a.startswith("-") and short and re.match(short, a):
            return "`%s %s` reads a file and can echo its contents" % (cmd, a)
    return None


_JQ_PROG_FILE_RE = re.compile(r'\b(import|include)\b')
_JQ_FILE_FLAGS = ("-L", "--library-path", "-f", "--from-file", "--rawfile", "--slurpfile")


def jq_file_read(args):
    """jq can load files without a file operand: `import "x" as $c` / `include`, -L
    library paths, -f program files, --rawfile/--slurpfile. Deny all of them (1.9.1 F5)."""
    for a in args:
        if a.startswith("--"):
            if a.split("=", 1)[0] in _JQ_FILE_FLAGS:
                return "jq %s loads a file" % a
        elif a.startswith("-"):
            if re.match(r'^-[A-Za-z]*[Lf]', a):
                return "jq %s (-L/-f) loads a file" % a
        elif _JQ_PROG_FILE_RE.search(a):
            return "jq import/include loads a file"
    return None


_FD_REDIR_RE = re.compile(r'^[0-9]*<+&?')


def is_secret_path(arg):
    """True if `arg` (a file operand, possibly rev:path or key=path) names or may
    expand to a secret-bearing file."""
    if not isinstance(arg, str) or not arg:
        return False
    arg = _FD_REDIR_RE.sub("", arg)
    cands = {arg, arg.split("=", 1)[-1], arg.rsplit(":", 1)[-1]}
    for c in cands:
        if not c:
            continue
        if _GLOB_CHARS.search(c):
            if _glob_secret(c):
                return True
        elif _plain_secret(c):
            return True
    return False


_CONTENT_PATTERNS = [
    (r'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----', "private key block"),
    (r'\bgh[pousr]_[A-Za-z0-9]{30,}', "GitHub token"),
    (r'\bgithub_pat_[A-Za-z0-9_]{30,}', "GitHub fine-grained token"),
    (r'\bsk-(ant-)?[A-Za-z0-9_-]{20,}', "API secret key (sk-...)"),
    (r'\bxox[abprs]-[A-Za-z0-9-]{10,}', "Slack token"),
    (r'\b(AKIA|ASIA)[0-9A-Z]{16}\b', "AWS access key id"),
    (r'\bops_[A-Za-z0-9_-]{20,}', "1Password service-account token"),
    (r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}', "JWT"),
    (r'\bglpat-[A-Za-z0-9_-]{20,}', "GitLab token"),
    (r'\bAIza[0-9A-Za-z_-]{35}\b', "Google API key"),
    (r'(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)'
     r'["\']?\s*[:=]\s*["\']?(?![$<{%]|os\.|process\.env|op://|env\b|\*+|x{4,}|redacted|none\b|null\b|true\b|false\b)'
     r'[A-Za-z0-9+/_\-.]{16,}', "credential assignment"),
]
_CONTENT_RES = [(re.compile(p), why) for p, why in _CONTENT_PATTERNS]


def secret_content(text):
    """Return a short reason if `text` appears to contain a literal secret value."""
    if not isinstance(text, str):
        return None
    for rx, why in _CONTENT_RES:
        if rx.search(text):
            return why
    return None
