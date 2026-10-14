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
    p = p.replace("/~/", "/")
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
    p = ("/" + c.strip().rstrip("/").lower().replace("\\", "/")).replace("/~/", "/")
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
_INDIRECT = {
    "date": re.compile(r'^(-[A-Za-z]*f|--file(=|$))'),
    "file": re.compile(r'^(-[A-Za-z]*f|--files-from(=|$)|-m|--magic-file)'),
    "wc": re.compile(r'^--files0-from'),
    "du": re.compile(r'^(--files0-from|-X|--exclude-from)'),
    "sort": re.compile(r'^--files0-from|^--f(i(l(e(s(0(-(f(r(om?)?)?)?)?)?)?)?)?)?=?$'),
    "tree": re.compile(r'^--fromfile'),
    "find": re.compile(r'^-files0-from'),
    "hostname": re.compile(r'^(-[A-Za-z]*F|--file(=|$))'),
    "md5sum": re.compile(r'^(-[A-Za-z]*c|--check)'),
    "sha256sum": re.compile(r'^(-[A-Za-z]*c|--check)'),
    "sha1sum": re.compile(r'^(-[A-Za-z]*c|--check)'),
    "shasum": re.compile(r'^(-[A-Za-z]*c|--check)'),
}


def indirect_file_read(cmd, args):
    """Reason string if `cmd args` reads a file through a list/format-file flag."""
    rx = _INDIRECT.get(cmd)
    if rx is None:
        return None
    for a in args:
        if a.startswith("-") and rx.match(a):
            return "`%s %s` reads a file and can echo its contents" % (cmd, a)
    return None


def is_secret_path(arg):
    """True if `arg` (a file operand, possibly rev:path or key=path) names or may
    expand to a secret-bearing file."""
    if not isinstance(arg, str) or not arg:
        return False
    cands = {arg, arg.split("=", 1)[-1], arg.rsplit(":", 1)[-1], arg.lstrip("<")}
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
