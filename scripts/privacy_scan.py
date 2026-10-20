#!/usr/bin/env python3
"""privacy_scan.py - zero-personal-data gate for the Teamwork repository.

Scans three sources and exits non-zero on any hit:

* ``--tree``    tracked files (``git ls-files``), read from the working tree;
* ``--staged``  index content of tracked files (``git ls-files -s`` + ``git cat-file``);
* ``--history`` every blob reachable from every ref (``git rev-list --objects --all``
  + ``git cat-file --batch``) **and** every commit's author/committer/message
  metadata (the place a personal identity usually survives a blob-level scan).

``--all`` combines the three. Flags combine freely.

It fails on: personal email addresses that are not role mailboxes at the neutral
identity domain; the retired private domain(s); absolute personal home paths
(``/home/<name>``, ``/Users/<name>``, ``C:\\Users\\<name>``); API keys and tokens
(``sk-``, ``ghp_``/``gho_``/``ghu_``/``ghs_``/``ghr_``, ``github_pat_``, ``AIza``,
``wandb_``, ``xoxb-``, ``Bearer`` tokens, provider keys such as ``gsk_``/``xai-``/
``pplx-``/``glpat-``/``npm_``/``hf_``/``sk_live_``, standalone high-entropy
secrets); private-key headers; ``.env``-style and JSON assignments of secret-named
variables; ``TODO``/``FIXME`` comments that carry credentials.

Forge-generated merge refs are not repository history. A commit whose subject is
exactly ``Merge <40-hex> into <40-hex>`` and that has two or more parents is a
pull-request merge artifact created by the forge with the PR author's identity;
its message is still scanned, but its author/committer identity is skipped so a
private mailbox on the forge account does not fail a clean repository.

It also fails on **agent-host configuration leakage**, which is the easiest way
for a local secret to reach a public tree:

* a tracked file that is private host state - ``.pi/agent/`` (auth, settings,
  sessions, memory, missions, installs), ``.env``, ``auth.json``,
  ``credentials.json``, ``settings.local.json``, ``.netrc``/``.npmrc``/``.pypirc``,
  shell history, SSH keys, ``.aws/credentials``, ``.kube/config``,
  ``.docker/config.json``, and the equivalent files of other agent hosts;
* a line that quotes a private host path (agent auth, settings or session
  state) or a JSON config object that carries a live credential
  (``"apiKey": "..."``).

Quoting the team workspace (``.pi/Teamwork/...``) in a document is not host
configuration, so the line rule stays quiet about it. A **tracked file under**
that workspace is local state and does fail, because the workspace itself is
never committed.

Design notes
------------
* Stdlib only, no network, no third-party import.
* The scanner is itself published, so it must not become the leak it detects.
  Private domains are therefore not stored as plain text (they are reconstructed
  from code points at runtime) and matched values are **masked by default** so a
  failing CI log cannot republish the secret. Unmasked values are **never**
  printed: ``--reveal`` prints a stable fingerprint (SHA-256 prefix) instead and
  ``--reveal-to PATH`` exports the raw values to a ``0600`` file for local
  remediation only.
* The allowlist file (``--allow``) holds one regular expression per line with an
  optional ``# reason`` suffix. A finding is exempt when its matched text matches
  any allowlist expression. Keep it minimal and justify each entry.

Revealing a matched value
-------------------------
Unmasked values are **never** written to stdout or stderr. A log line is a
broadcast sink - CI logs are public, terminals are recorded, and ``tee``ed
output outlives the session - so the scanner has no flag that prints a secret.

* ``--reveal`` adds ``(sha256:<12 hex>)`` to each finding line. The fingerprint
  is a stable, unsalted SHA-256 prefix: it identifies which finding is which and
  lets an operator confirm a rotated value, but it cannot be used as the
  credential.
* ``--reveal-to PATH`` writes the raw values to a file the operator names, for
  local remediation only. The file is created with ``O_EXCL`` and mode ``0600``
  (an existing path is a usage error, never overwritten), every line is
  ``location<TAB>rule<TAB>fingerprint<TAB>value``, a warning naming the file is
  printed to stderr, and a half-written file is removed on error. Delete it
  after rotating the secret; never commit it, paste it into a ticket or a chat,
  or leave it in a shared workspace.

Exit codes: ``0`` clean, ``1`` findings, ``2`` usage / git error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SCANNER_VERSION = "1.3.0"

# --------------------------------------------------------------------------- #
# Neutral identity / allowlisted email domains
# --------------------------------------------------------------------------- #

IDENTITY_DOMAIN = os.environ.get("TEAMWORK_IDENTITY_DOMAIN", "agents.nidvue.com")

# Documentation / RFC 6761-2606 placeholders and service mailboxes. These are
# not personal data: they are reserved names used in examples and by git hosts.
_ALLOWED_EMAIL_DOMAINS = {
    IDENTITY_DOMAIN,
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "invalid",
    "test",
    "localhost",
}
_ALLOWED_EMAIL_SUFFIXES = (
    ".example.com",
    ".example.org",
    ".example.net",
    ".invalid",
    ".test",
    ".localhost",
)
_ALLOWED_SERVICE_EMAILS = re.compile(
    r"^(?:noreply@github\.com|support@github\.com|[^@]+@users\.noreply\.github\.com|"
    r"git@(?:github\.com|gitlab\.com|bitbucket\.org))$"
)

# --------------------------------------------------------------------------- #
# Retired private domains
#
# Kept out of plain text on purpose: this file ships in the public tree and the
# history, and must not itself contain the string it is meant to detect. The
# list is built from code points and can be extended at runtime with the
# comma-separated TEAMWORK_PRIVATE_DOMAINS environment variable.
# --------------------------------------------------------------------------- #


def _decode(*codes: int) -> str:
    return "".join(chr(c) for c in codes)


_DEFAULT_PRIVATE_DOMAINS = (
    # The role-mailbox domain is the project's own (IDENTITY_DOMAIN, agents.nidvue.com) and
    # is allowed above; the domains below are the *personal* ones that must never
    # appear. The operator's decision is recorded in docs/Team/Decisions.md.
    _decode(122, 104, 97, 111, 46, 110, 111),  # personal identity domain
    _decode(
        98, 117, 108, 98, 105, 116, 101, 99, 104, 46, 99, 111, 109
    ),  # personal work-mail domain
)


def _private_domains() -> list:
    extra = os.environ.get("TEAMWORK_PRIVATE_DOMAINS", "")
    values = [d.strip().lower() for d in extra.split(",") if d.strip()]
    seen = []
    for domain in list(_DEFAULT_PRIVATE_DOMAINS) + values:
        if domain and domain not in seen:
            seen.append(domain)
    return seen


# Non-personal CI / placeholder usernames that may legitimately appear in a home
# path (GitHub Actions uses /home/runner). Everything else is reported.
_GENERIC_HOME_USERS = {
    "runner",
    "runneradmin",
    "user",
    "username",
    "youruser",
    "yourname",
    "you",
    "example",
    "app",
    "docker",
    "vscode",
    "ubuntu",
    "node",
    "root",
    "admin",
    "me",
    "someone",
    "teamwork",
}

# Placeholder values that are obviously not real secrets.
_PLACEHOLDERS = re.compile(
    r"^(?:\$\{?[A-Za-z0-9_]+\}?|%[A-Za-z0-9_]+%|<[^>]+>|your[-_].*|"
    r".*[-_]here|xxx+|\.\.\.|redacted|placeholder|dummy|fake|changeme|change_me|"
    r"example|sample|test|none|null|nil|todo|secret|token|password|value|"
    r"replace_me|"
    r"string|str|varname)$",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------- #
# Detection rules
# --------------------------------------------------------------------------- #

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_RE_HOME = re.compile(
    r"(?:(?<![A-Za-z0-9_])/(?:home|Users)/([A-Za-z0-9][A-Za-z0-9._\-]*))"
    r"|(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]Users[\\/]([^\\/\s\"']+))"
    # WSL and container mounts of a real home directory
    r"|(?:(?<![A-Za-z0-9])/mnt/[A-Za-z]/(?:Users|home)/([A-Za-z0-9][A-Za-z0-9._\-]*))"
)

# Built from fragments so the scanner's own source does not contain the
# contiguous header it is meant to detect.
_RE_PRIVATE_KEY = re.compile(
    r"-{5}BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-{5}"
    r"|-{5}BEGIN SSH2 ENCRYPTED PRIVATE KEY-{5}"
)

_RE_TOKEN = re.compile(
    r"\bsk-[A-Za-z0-9_\-]{16,}"
    r"|\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}"
    r"|\bAIza[0-9A-Za-z_\-]{20,}"
    r"|\bwandb_[A-Za-z0-9]{20,}"
    r"|\bxox[baprs]-[A-Za-z0-9\-]{10,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bgsk_[A-Za-z0-9]{20,}"
    r"|\bxai-[A-Za-z0-9]{20,}"
    r"|\bpplx-[A-Za-z0-9]{20,}"
    r"|\bnpm_[A-Za-z0-9]{30,}"
    r"|\bglpat-[A-Za-z0-9_\-]{20,}"
    r"|\bhf_[A-Za-z0-9]{30,}"
    r"|\bsk_live_[A-Za-z0-9]{20,}"
    r"|\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}"
    r"|\b(?i:Bearer)\s+[A-Za-z0-9._+/=\-]{16,}"
)

# Assignment values that contain code punctuation (calls, indexing, punctuation) are
# not credentials - they are source lines such as ``API_KEY = re.compile(...)``.
_RE_CODE_LIKE = re.compile(r"[(){}\[\]<>,;'\"\s]")
_CODE_KEYWORDS = {
    "function",
    "return",
    "lambda",
    "class",
    "import",
    "def",
    "const",
    "let",
    "var",
    "async",
    "await",
    "typeof",
    "none",
    "true",
    "false",
    "null",
    "undefined",
    "this",
    "new",
}


_RE_DOTTED_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def _looks_like_secret_value(value: str) -> bool:
    if value.startswith(("re.", "os.", "self.", "match.", "str(", "Path(")):
        return False
    # A dotted identifier is code (``tokenize.generate_tokens``), not a credential.
    if _RE_DOTTED_IDENT.match(value):
        return False
    if value.lower() in _CODE_KEYWORDS:
        return False
    # Paths, URLs and pure digit strings are configuration, not credentials.
    if value.startswith(("/", "\\", "http://", "https://")) or "://" in value:
        return False
    if value.isdigit():
        return False
    # A bare word such as ``candidate`` is an identifier, not a credential.
    if value.isalpha() and len(value) < 24:
        return False
    return not bool(_RE_CODE_LIKE.search(value))


# .env-style assignment of a secret-named variable to a non-placeholder value.
# The value is restricted to a credential charset so that a call expression is
# not mistaken for an assignment.
_RE_ENV_SECRET = re.compile(
    r"(?i)(?:[A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|"
    r"ACCESS[_-]?KEY|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET|AUTH[_-]?KEY|"
    r"CREDENTIAL)[A-Za-z0-9_]*)\s*[:=]\s*"
    r"(?:[\"']([^\"'\n]{8,})[\"']|([A-Za-z0-9+/=_\-.:@!#$%^&]{8,}))"
)

# Standalone high-entropy secret: 32+ base64-ish characters, not pure hex (a raw
# hash such as a git sha must not be reported). Hex secrets are still caught when
# they are assigned to a secret-named variable by the .env rule above.
_RE_HIGH_ENTROPY = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])")

_RE_TODO = re.compile(r"(?i)\b(?:TODO|FIXME|XXX|HACK)\b")

# A forge-created PR merge commit: "Merge <sha> into <sha>" with two parents.
_RE_FORGE_MERGE = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")


_RE_FORGE_MERGE_SUBJECTS = (
    re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$"),
    re.compile(r"^Merge pull request #\d+ from \S+$"),
    re.compile(r"^Merge branch '[^']+' into '[^']+'$"),
    re.compile(r"^Merge remote-tracking branch '[^']+'$"),
)


def is_forge_merge(subject: str, parents: list) -> bool:
    """True for the synthetic merge ref a forge creates for a pull request."""
    if len(parents) < 2:
        return False
    text = subject.strip()
    return any(pattern.match(text) for pattern in _RE_FORGE_MERGE_SUBJECTS)


def _host_state(*parts: str) -> str:
    """Join path fragments so this published file never quotes a private path."""
    return "".join(parts)


# Private state of an agent host. The skill directory itself
# (``<agent-dir>/skills/<name>``) is a normal install target and is not listed.
_AGENT_CONFIG_NAMES = (
    r"auth(?:[^\s\"'`]*)?|settings\.json|trust\.json|"
    r"mcp(?:-auth|-adapter|-onboarding)?\.json|models(?:-store)?\.json|"
    r"prompt-history\.json|sessions?|memory|missions|agents|install|vendor|npm|cache|git|bin"
)
_RE_AGENT_CONFIG = re.compile(
    _host_state(r"\.pi[\\/]", r"agent[\\/]")
    + r"(?:"
    + _AGENT_CONFIG_NAMES
    + r")(?=[\\/]|$)"
    + "|"
    + _host_state(r"\.claude[\\/]", "settings", r"\.local\.json")
    + "|"
    + _host_state(r"\.codex[\\/]", "auth", r"\.json")
    + "|"
    + _host_state(r"\.gemini[\\/]", "oauth_creds", r"\.json"),
    re.IGNORECASE,
)

# JSON config object carrying a live credential: ``"apiKey": "..."``. A
# placeholder (``${TOKEN}``, ``<your-key>``) is filtered like ``.env`` values.
_RE_JSON_SECRET = re.compile(
    r"(?i)[\"'][A-Za-z0-9_.\-]*(?:api[_-]?key|apikey|access[_-]?token|"
    r"refresh[_-]?token|id[_-]?token|client[_-]?secret|private[_-]?key|secret|"
    r"password|passwd|token)[\"']\s*:\s*[\"']([^\"'\n]{8,})[\"']"
)

# A tracked path that must never be published: host config, credentials, keys,
# environment files, history. ``.env.example`` and friends stay allowed.
_SENSITIVE_NAME = re.compile(
    r"(?i)^(?:\.env(?:\.(?!example$|sample$|template$|dist$)[^/]+)?"
    r"|auth(?:\.json)?(?:\.bak)?|auth\.json|credentials\.json|secrets?\.json"
    r"|mcp-auth\.json|settings\.local\.json|\.netrc|\.npmrc|\.pypirc"
    r"|\.bash_history|\.zsh_history|\.python_history"
    r"|id_(?:rsa|dsa|ecdsa|ed25519)"
    r"|\.git-credentials|\.htpasswd)$"
)
_SENSITIVE_SUFFIX = re.compile(r"(?i)\.(?:pem|p12|pfx|keystore|jks)$")
# Local working state: an agent workspace, a virtualenv, build output or a cache.
# None of it is project source, so a tracked file here leaked by accident.
_LOCAL_STATE_PARTS = (
    ".pi",  # the team workspace; a project skill under .agents/ stays tracked
    ".venv",
    "venv",
    "node_modules",
    "site",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    ".cache",
    "target",
    "Scratch",
)
_SENSITIVE_PARTS = (
    _host_state(".pi/", "agent"),
    _host_state(".claude/", "settings", ".local.json"),
    _host_state(".claude/", ".credentials.json"),
    _host_state(".claude/", "projects"),
    _host_state(".claude/", "todos"),
    _host_state(".codex/", "auth", ".json"),
    _host_state(".codex/", "sessions"),
    _host_state(".gemini/", "oauth_creds", ".json"),
    _host_state(".gemini/", "tmp"),
    _host_state(".config/", "opencode/", "auth.json"),
    _host_state(".aws/", "credentials"),
    _host_state(".kube/", "config"),
    _host_state(".docker/", "config.json"),
    _host_state(".ssh/", ""),
)
# Shell history and dotfile names above are matched on the basename only; a
# project source file called ``auth.py`` must stay allowed.
_SENSITIVE_BASENAMES = {
    "auth.json",
    "auth.json.bak",
    _host_state(".aider.", "chat.history.md"),
    _host_state(".aider.", "input.history"),
}

# Editor and build residue: local artefacts that are never project source.
_LOCAL_JUNK = re.compile(r"(?i)^(?:\.DS_Store|Thumbs\.db|.*\.(?:swp|swo|orig|rej|bak|pyc|pyo))$")


def sensitive_path(rel: str):
    """Return a reason when a tracked path is private local state, else ``None``."""
    normalised = rel.replace("\\", "/").lower()
    while normalised.startswith("./"):
        normalised = normalised[2:]
    normalised = normalised.lstrip("/")
    for part in _SENSITIVE_PARTS:
        lowered = part.lower()
        if normalised == lowered or normalised.startswith(lowered.rstrip("/") + "/"):
            return f"private host state: {part}"
    for part in _LOCAL_STATE_PARTS:
        lowered = part.lower()
        if normalised == lowered or normalised.startswith(lowered.rstrip("/") + "/"):
            return f"local state: {part}/"
    name = normalised.rsplit("/", 1)[-1]
    if name in _SENSITIVE_BASENAMES:
        return "credential file"
    if _SENSITIVE_NAME.match(name):
        return "secret-bearing file"
    if _SENSITIVE_SUFFIX.search(name):
        return "key material"
    if _LOCAL_JUNK.match(name):
        return "local state: editor or build artefact"
    return None


# An archive entry's quoted-evidence fields, mirroring the link checker's scope:
# the author of the entry is not the author of the quotation.
_QUOTED_EVIDENCE = re.compile(
    r"^- (?:self-check|author evidence|reviewer evidence|findings history): "
)
# Rules that describe a *path shape* rather than a secret. They are quiet inside a
# quotation; every credential rule below stays armed there.
_QUOTED_PATH_RULES = frozenset({"home-path", "agent-config"})

RULES = (
    {"id": "private-key", "severity": "critical", "regex": _RE_PRIVATE_KEY},
    {"id": "api-token", "severity": "critical", "regex": _RE_TOKEN},
    {"id": "env-secret", "severity": "critical", "regex": _RE_ENV_SECRET},
    {"id": "json-secret", "severity": "critical", "regex": _RE_JSON_SECRET},
    {"id": "agent-config", "severity": "high", "regex": _RE_AGENT_CONFIG},
    {"id": "private-domain", "severity": "high", "regex": None},  # compiled in scan()
    {"id": "personal-email", "severity": "high", "regex": _RE_EMAIL},
    {"id": "home-path", "severity": "high", "regex": _RE_HOME},
    {"id": "high-entropy-secret", "severity": "high", "regex": _RE_HIGH_ENTROPY},
)


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def _looks_like_secret(value: str, line: str = "", index: int = 0) -> bool:
    """Filter out hashes, identifiers, URL paths and natural words."""
    if len(value) < 32:
        return False
    if re.fullmatch(r"[0-9a-fA-F]+", value):  # pure hex -> treat as a hash
        return False
    # A long run inside a URL path is not a credential. A separate token later
    # on the same line (after whitespace) is still checked.
    scheme = line.find("://")
    if scheme != -1 and index > scheme:
        between = line[scheme + 3 : index]
        if not re.search(r"[\s\"']", between):
            return False
    has_digit = any(c.isdigit() for c in value)
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    if not (has_digit and has_upper and has_lower):
        return False
    return _shannon_entropy(value) >= 3.5


def _user_is_elided(user: str) -> bool:
    """Is this the elided form of a path, i.e. a segment with no characters left?

    Logs and commit messages routinely abbreviate a home path to its parent
    directories followed by an ellipsis and then the rest of the path. That form
    carries no account name, so it identifies nobody: flagging it makes the gate
    cry wolf on every quoted CI log, and a gate that cries wolf gets bypassed.

    Only an ellipsis standing as its own segment is accepted: three or more dots
    followed by nothing or by a separator. A name that merely starts with dots
    (``....name``) or a two-dot parent hop (``..``) still reports, and so does a
    partly masked name.
    """
    return re.fullmatch(r"\.{3,}(?:[\\/].*)?", user) is not None


def _email_allowed(value: str) -> bool:
    if _ALLOWED_SERVICE_EMAILS.match(value):
        return True
    domain = value.rsplit("@", 1)[-1].lower()
    if domain in _ALLOWED_EMAIL_DOMAINS:
        return True
    return any(domain.endswith(suffix) for suffix in _ALLOWED_EMAIL_SUFFIXES)


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    if len(value) <= 10:
        return value[0] + "*" * (len(value) - 2) + value[-1]
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def _fingerprint(value: str, length: int = 12) -> str:
    """A stable, non-usable identifier for a matched value.

    Enough to tell two findings apart and to find the secret again once its
    location is known, but not enough to reconstruct or use it. The hash is
    unsalted SHA-256 of the full value, so the same secret always yields the
    same fingerprint across runs and machines.
    """
    digest = hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()
    return "sha256:" + digest[:length]


def write_reveal_file(path, pairs):
    """Export ``(finding, raw_value)`` pairs to a new ``0600`` file.

    Unmasked values must never reach stdout/stderr (CI logs, terminals, ``tee``
    output). A file the operator names keeps the remediation use case while the
    log stays clean. The file is created with ``O_EXCL`` and mode ``0600`` so an
    existing path is never silently overwritten and no other user can read it.
    Returns the number of values written.
    """
    target = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(target), flags, 0o600)
    written = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for finding, value in pairs:
                handle.write(
                    f"{finding['location']}\t{finding['rule']}\t{_fingerprint(value)}\t{value}\n"
                )
                written += 1
        os.chmod(str(target), 0o600)
    except BaseException:
        # Do not leave a half-written plaintext secrets file behind.
        try:
            os.unlink(str(target))
        except OSError:
            pass
        raise
    return written


def _clip(line: str, value: str, width: int = 160) -> str:
    """A short, single-line context snippet around the match."""
    index = line.find(value)
    if index < 0:
        return line[:width]
    start = max(0, index - 40)
    end = min(len(line), index + len(value) + 40)
    snippet = line[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(line):
        snippet = snippet + "..."
    return snippet[:width]


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #


def make_finding(rule_id, severity, path, line_no, value, line, source, commit=None):
    masked = _mask(value)
    # Never ship the surrounding line: a second credential in the same window
    # would be republished in plaintext (the scanner is published too).
    context = ""
    return {
        "rule": rule_id,
        "severity": severity,
        "path": path,
        "line": line_no,
        "source": source,
        "commit": commit,
        "location": location(path, line_no, commit),
        "evidence": masked,
        "match": value,
        "context": context,
    }


def location(path, line_no, commit=None):
    if commit:
        return f"{path}:{line_no}" if line_no else path
    return f"{path}:{line_no}"


def scan_lines(text, path, source, rules, allow, commit=None):
    """Yield findings for one text blob (a file or a commit message body)."""
    private_domains = _private_domains()
    private_re = None
    if private_domains:
        private_re = re.compile("|".join(re.escape(d) for d in private_domains), re.IGNORECASE)

    compiled = []
    for rule in rules:
        if rule["id"] == "json-secret":
            continue  # whole-text pass below: pretty-printed values span lines
        if rule["id"] == "private-domain":
            if private_re is None:
                continue
            compiled.append((rule, private_re))
        elif rule["regex"] is not None:
            compiled.append((rule, rule["regex"]))

    ignore_file = path.endswith(".gitignore")
    archive = path.endswith("Archive.md")
    for line_no, line in enumerate(text.splitlines(), 1):
        # An archive entry quotes another agent's evidence verbatim. A path inside
        # such a quotation is that agent's measurement, not a path this repository
        # owns, and the quotation cannot be reworded after it is committed - so a
        # path-shape rule would fail every future scan on immutable history. Every
        # credential rule stays armed on the same line.
        #
        # The predicate has its own name on purpose: the env-secret arm below
        # assigns a local `quoted`, and sharing that name silently disarmed both
        # path rules in every file whenever an env-secret matched.
        quoted_evidence = archive and _QUOTED_EVIDENCE.match(line) is not None
        for rule, regex in compiled:
            # A .gitignore entry denies a private path; it is not a leak. The
            # project's own deny list must therefore not fail the deny list test.
            if rule["id"] == "agent-config" and ignore_file:
                continue
            if quoted_evidence and rule["id"] in _QUOTED_PATH_RULES:
                continue
            for match in regex.finditer(line):
                value = match.group(0)
                if rule["id"] == "personal-email" and _email_allowed(value):
                    continue
                if rule["id"] == "home-path":
                    user = match.group(1) or match.group(2) or match.group(3) or ""
                    if user.lower() in _GENERIC_HOME_USERS:
                        continue
                    if _user_is_elided(user):
                        continue
                if rule["id"] == "env-secret":
                    quoted = match.group(1) is not None
                    secret = match.group(1) or match.group(2)
                    if _PLACEHOLDERS.match(secret):
                        continue
                    if quoted:
                        # A quoted passphrase may legitimately contain spaces.
                        if not re.search(r"\s", secret) and not _looks_like_secret_value(secret):
                            continue
                    elif not _looks_like_secret_value(secret):
                        continue
                    value = secret
                if rule["id"] == "high-entropy-secret":
                    prefix = line[: match.start()].lower()
                    if "data:" in prefix and "base64" in prefix:
                        continue
                    if re.search(r"(?:sha(?:256|384|512)-|integrity=)[\"']?$", prefix):
                        continue
                    if not _looks_like_secret(value, line, match.start()):
                        continue
                if any(pattern.search(value) for pattern in allow):
                    continue
                yield make_finding(
                    rule["id"], rule["severity"], path, line_no, value, line, source, commit
                )

        # A marker that carries a credential next to it is reported too.
        if _RE_TODO.search(line):
            credential = None
            for probe in (_RE_TOKEN, _RE_PRIVATE_KEY):
                match = probe.search(line)
                if match:
                    credential = match.group(0)
                    break
            if credential is None and private_re is not None:
                match = private_re.search(line)
                if match:
                    credential = match.group(0)
            if credential is None:
                match = _RE_ENV_SECRET.search(line)
                if match:
                    candidate = match.group(1) or match.group(2)
                    if not _PLACEHOLDERS.match(candidate) and (
                        match.group(1) is not None or _looks_like_secret_value(candidate)
                    ):
                        credential = candidate
            if credential and not any(p.search(credential) for p in allow):
                yield make_finding(
                    "todo-credential", "medium", path, line_no, credential, line, source, commit
                )

    # A JSON config may put the key and the value on different lines; matching the
    # whole text keeps a pretty-printed `"apiKey":` from slipping through. This is
    # deliberately not skipped for `.gitignore`: only the agent-config line rule is
    # a deny list, and a pasted JSON credential is a leak in any file.
    for match in _RE_JSON_SECRET.finditer(text):
        value = match.group(1)
        if _PLACEHOLDERS.match(value):
            continue
        if not _looks_like_secret_value(value) and not (
            " " in value
            and any(ch.isdigit() or (not ch.isalnum() and not ch.isspace()) for ch in value)
        ):
            continue
        line_no = text.count("\n", 0, match.start()) + 1
        line = text.splitlines()[line_no - 1]
        if any(pattern.search(value) for pattern in allow):
            continue
        yield make_finding("json-secret", "critical", path, line_no, value, line, source, commit)


def scan_commit_metadata(root, allow, stats=None):
    """Scan author/committer name+email and the message of every commit."""
    fmt = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%P%x1f%B%x1e"
    proc = _run(["git", "-C", str(root), "log", "--all", "--format=" + fmt])
    if proc.returncode != 0:
        return []
    findings = []
    text = proc.stdout.decode("utf-8", "replace")
    for record in text.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) < 5:
            continue
        if stats is not None:
            stats["commits"] += 1
        sha, an, ae, cn, ce = parts[0], parts[1], parts[2], parts[3], parts[4]
        parents = parts[5].split() if len(parts) > 5 and parts[5] else []
        body = parts[6] if len(parts) > 6 else ""
        short = sha[:12]
        subject = body.splitlines()[0] if body else ""
        if not is_forge_merge(subject, parents):
            for label, value in (
                ("author name", an),
                ("author email", ae),
                ("committer name", cn),
                ("committer email", ce),
            ):
                if not value:
                    continue
                for finding in scan_lines(
                    value, f"commit:{short}", "history:commit", RULES, allow, commit=sha
                ):
                    finding["detail"] = label
                    finding["context"] = f"{label}: {finding['context']}"
                    findings.append(finding)
        for finding in scan_lines(
            body, f"commit:{short}", "history:commit", RULES, allow, commit=sha
        ):
            finding["detail"] = "message"
            findings.append(finding)
    return findings


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #


def _run(args, input_bytes=None):
    try:
        return subprocess.run(args, input=input_bytes, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out: {' '.join(args)}") from exc


def _cat_file_batch(root, shas):
    """Return {sha: bytes} for blob objects, via one ``git cat-file --batch`` run."""
    if not shas:
        return {}
    proc = _run(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input_bytes=("\n".join(shas) + "\n").encode("utf-8"),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git cat-file --batch failed: " + proc.stderr.decode("utf-8", "replace").strip()
        )
    out = proc.stdout
    result = {}
    pos = 0
    while pos < len(out):
        newline = out.find(b"\n", pos)
        if newline < 0:
            break
        header = out[pos:newline].decode("utf-8", "replace").split()
        pos = newline + 1
        if len(header) == 2 and header[1] in ("missing", "ambiguous"):
            continue
        if len(header) != 3 or header[1] not in ("blob", "tree", "commit", "tag"):
            raise RuntimeError(f"unexpected git cat-file batch header: {header!r}")
        sha, kind, raw_size = header
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise RuntimeError(f"invalid git object size in {header!r}") from exc
        payload = out[pos : pos + size]
        # Skip the payload of every object type. Previously a tree payload was
        # re-read as headers, which desynchronised the stream and could hide a
        # real blob (or crash on a crafted tree entry name).
        pos += size + 1  # git writes a trailing LF after each payload
        if kind == "blob":
            result[sha] = payload
    return result


def _tracked_paths(root):
    proc = _run(["git", "-C", str(root), "ls-files", "-z"])
    if proc.returncode != 0:
        raise RuntimeError("git ls-files failed: " + proc.stderr.decode("utf-8", "replace").strip())
    return [p.decode("utf-8", "replace") for p in proc.stdout.split(b"\x00") if p]


def _scan_bytes(data, path, source, allow, commit=None):
    head = data[:8192]
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = data.decode("utf-16", "replace")
    elif b"\x00" in head and head.count(b"\x00") / max(len(head), 1) > 0.01:
        # UTF-16 without a BOM: try both byte orders and accept only a decode
        # that is overwhelmingly printable. A real binary file stays skipped.
        text = ""
        for encoding in ("utf-16-le", "utf-16-be"):
            candidate = data.decode(encoding, "replace")
            printable = sum(1 for ch in candidate if ch.isprintable() or ch in "\n\r\t") / max(
                len(candidate), 1
            )
            if printable > 0.9 and "\x00" not in candidate:
                text = candidate
                break
        if not text:
            return []
    else:
        text = data.decode("utf-8", "replace")
    return list(scan_lines(text, path, source, RULES, allow, commit=commit))


def config_path_finding(rel, source, allow=(), commit=None):
    """A tracked path that is private host state is a finding on its own."""
    reason = sensitive_path(rel)
    if reason is None:
        return None
    if any(pattern.search(rel) for pattern in allow):
        return None
    local_state = reason.startswith("local state")
    return {
        "rule": "local-state" if local_state else "local-config",
        "severity": "high" if local_state else "critical",
        "path": rel,
        "line": 0,
        "source": source,
        "commit": commit,
        "location": rel,
        "evidence": rel,
        "match": rel,
        "context": reason,
    }


def scan_tree(root, allow, stats=None):
    findings = []
    for rel in _tracked_paths(root):
        if stats is not None:
            stats["tracked_files"] += 1
        path_finding = config_path_finding(rel, "tree", allow)
        if path_finding is not None:
            findings.append(path_finding)
        full = root / rel
        try:
            data = full.read_bytes()
        except OSError as exc:
            findings.append(
                {
                    "rule": "unreadable-tracked-file",
                    "severity": "medium",
                    "path": rel,
                    "line": 0,
                    "source": "tree",
                    "commit": None,
                    "location": rel,
                    "evidence": rel,
                    "match": rel,
                    "context": f"tracked file could not be read: {exc}",
                }
            )
            continue
        findings.extend(_scan_bytes(data, rel, "tree", allow))
    return findings


def scan_staged(root, allow, stats=None):
    """Scan the index content (what ``git commit`` would record)."""
    proc = _run(["git", "-C", str(root), "ls-files", "-s", "-z"])
    if proc.returncode != 0:
        raise RuntimeError(
            "git ls-files -s failed: " + proc.stderr.decode("utf-8", "replace").strip()
        )
    entries = {}
    for record in proc.stdout.split(b"\x00"):
        if not record:
            continue
        try:
            meta, path = record.split(b"\t", 1)
        except ValueError:
            continue
        fields = meta.split()
        if len(fields) < 2:
            continue
        entries.setdefault(fields[1].decode("ascii"), []).append(path.decode("utf-8", "replace"))
    blobs = _cat_file_batch(root, list(entries))
    findings = []
    for sha, paths in entries.items():
        data = blobs.get(sha)
        if data is None:
            continue
        for path in paths:
            if stats is not None:
                stats["staged_files"] += 1
            path_finding = config_path_finding(path, "staged", allow)
            if path_finding is not None:
                findings.append(path_finding)
            findings.extend(_scan_bytes(data, path, "staged", allow))
    return findings


def scan_history(root, allow, stats=None):
    # --reflog also reaches objects a reset or a deleted branch left behind, which
    # a plain --all scan reports as PASS even though `git fsck` still finds them.
    proc = _run(["git", "-C", str(root), "rev-list", "--objects", "--all", "--reflog"])
    if proc.returncode != 0:
        raise RuntimeError("git rev-list failed: " + proc.stderr.decode("utf-8", "replace").strip())
    sha_to_paths = {}
    order = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split(" ", 1)
        sha = parts[0]
        path = parts[1] if len(parts) > 1 else ""
        if not path:
            continue
        if sha not in sha_to_paths:
            sha_to_paths[sha] = set()
            order.append(sha)
        sha_to_paths[sha].add(path)
    blobs = _cat_file_batch(root, order)
    findings = []
    for sha in order:
        data = blobs.get(sha)
        if data is None:
            continue
        if stats is not None:
            stats["history_blobs"] += 1
        for rel in sorted(sha_to_paths[sha]):
            path_finding = config_path_finding(rel, "history:blob", allow, commit=sha)
            if path_finding is not None:
                findings.append(path_finding)
            findings.extend(_scan_bytes(data, rel, "history:blob", allow, commit=sha))
    findings.extend(scan_commit_metadata(root, allow, stats=stats))
    return findings


# --------------------------------------------------------------------------- #
# Allowlist
# --------------------------------------------------------------------------- #


def load_allow(path):
    patterns = []
    if not path:
        return patterns
    text = Path(path).read_text(encoding="utf-8")
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expression = line.split("#", 1)[0].strip()
        if not expression:
            continue
        try:
            patterns.append(re.compile(expression))
        except re.error as exc:
            print(f"privacy_scan: {path}:{line_no}: bad allow regex: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
    return patterns


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def summarize(findings):
    by_severity = Counter(f["severity"] for f in findings)
    by_rule = Counter(f["rule"] for f in findings)
    return {"by_severity": dict(by_severity), "by_rule": dict(by_rule)}


def dedupe(findings):
    seen = set()
    unique = []
    for finding in findings:
        key = (finding["rule"], finding["location"], finding["match"], finding.get("commit") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="privacy_scan.py",
        description="Fail on personal data, credentials and secrets in the tree, "
        "the index and the full git history.",
    )
    parser.add_argument(
        "--tree", action="store_true", help="scan tracked files from the working tree"
    )
    parser.add_argument("--staged", action="store_true", help="scan the staged index content")
    parser.add_argument(
        "--history", action="store_true", help="scan every blob of every commit and commit metadata"
    )
    parser.add_argument("--all", action="store_true", help="combine --tree, --staged and --history")
    parser.add_argument(
        "--allow",
        metavar="FILE",
        default=None,
        help="allowlist: one regex per line with an optional '# reason'",
    )
    parser.add_argument(
        "--root", metavar="DIR", default=None, help="repository root (default: current directory)"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--reveal",
        action="store_true",
        help="print a stable fingerprint (sha256 prefix) per finding; never the value itself",
    )
    parser.add_argument(
        "--reveal-to",
        metavar="PATH",
        default=None,
        help="write unmasked matched values to PATH (created 0600, never overwritten)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print the one-line summary")
    args = parser.parse_args(argv)

    if args.all:
        args.tree = args.staged = args.history = True
    if not (args.tree or args.staged or args.history):
        args.tree = True  # safe default

    root = _git_root(args.root)
    if root is None:
        print("privacy_scan: not inside a git repository", file=sys.stderr)
        return 2

    try:
        allow = load_allow(args.allow)
    except OSError as exc:
        print(f"privacy_scan: cannot read allowlist: {exc}", file=sys.stderr)
        return 2
    modes = [
        name
        for name, flag in (("tree", args.tree), ("staged", args.staged), ("history", args.history))
        if flag
    ]

    findings = []
    stats = {"tracked_files": 0, "staged_files": 0, "history_blobs": 0, "commits": 0}
    try:
        if args.tree:
            findings.extend(scan_tree(root, allow, stats))
        if args.staged:
            findings.extend(scan_staged(root, allow, stats))
        if args.history:
            findings.extend(scan_history(root, allow, stats))
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"privacy_scan: {exc}", file=sys.stderr)
        return 2

    findings = dedupe(findings)
    # Unmasked values are never printed. A log line - CI output, a terminal, a
    # `tee`d file - is a broadcast sink: --reveal only adds a stable fingerprint
    # and --reveal-to exports the raw values to a file the operator names.
    reveal_path = args.reveal_to
    reveal_values = []
    for finding in findings:
        match = finding.pop("match", None)
        if match is None:
            continue
        if args.reveal:
            finding["fingerprint"] = _fingerprint(match)
        if reveal_path:
            reveal_values.append((finding, match))

    reveal_written = 0
    if reveal_path:
        try:
            reveal_written = write_reveal_file(reveal_path, reveal_values)
        except FileExistsError:
            print(
                f"privacy_scan: refusing to overwrite existing file {reveal_path}",
                file=sys.stderr,
            )
            return 2
        except OSError as exc:
            print(f"privacy_scan: cannot write reveal file: {exc}", file=sys.stderr)
            return 2
        print(
            f"privacy_scan: WARNING - {reveal_written} unmasked value(s) written to "
            f"{reveal_path} (mode 0600). Delete it after remediation; never commit, "
            f"copy into a ticket, or paste it into a chat.",
            file=sys.stderr,
        )

    report = {
        "scanner_version": SCANNER_VERSION,
        # The absolute root is deliberately not emitted: a privacy scanner must
        # not republish the operator's home path into public CI logs.
        "root": root.name,
        "modes": modes,
        # Never publish an absolute (possibly home) path in the report.
        "allow_file": Path(args.allow).name if args.allow else None,
        "identity_domain": IDENTITY_DOMAIN,
        "scanned": stats,
        "finding_count": len(findings),
        "findings": findings,
    }
    report.update(summarize(findings))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        if not args.quiet:
            for finding in findings:
                # The unmasked value is never printed: stdout is a broadcast
                # sink. --reveal only adds a non-usable fingerprint.
                shown = finding["evidence"]
                fingerprint = finding.get("fingerprint")
                if fingerprint:
                    shown = f"{shown} ({fingerprint})"
                print(
                    f"{finding['location']}: [{finding['severity']}/"
                    f"{finding['rule']}] {shown}  {finding.get('detail', '')}"
                )
        state = "FAIL" if findings else "PASS"
        print(f"privacy_scan: {state} - {len(findings)} finding(s) in {', '.join(modes)}")
    return 1 if findings else 0


def _git_root(explicit):
    start = Path(explicit) if explicit else Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.decode("utf-8", "replace").strip())


if __name__ == "__main__":
    sys.exit(main())
