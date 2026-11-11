#!/usr/bin/env python3
"""privacy_scan.py - zero-personal-data gate for the Teamwork repository.

Scans three sources and exits non-zero on any hit:

* ``--tree``    tracked files (``git ls-files``), read from the working tree;
* ``--staged``  index content of tracked files (``git ls-files -s`` + ``git cat-file``);
* ``--history`` every blob reachable from every ref or reflog (``git rev-list
  --objects --all --reflog``) **and** every commit's author/committer/message
  metadata over the same set (``git log --all --reflog``) - the place a personal
  identity usually survives a blob-level scan. The reflog is part of the set: an
  amended or reset commit is unreachable from any ref and still recoverable, so
  both walkers read ``_HISTORY_REVISIONS``.

``--all`` combines the three git sources. Flags combine freely.

``--stores`` scans the team memory stores under the local workspace
(``.pi/Teamwork/Teams/*/Knowledge.md``, ``Global/GlobalMemory.md``,
``Roles/*/{Short,Long}TermMemory.md``, ``ArchivedMemory.md``, ``Lessons.md``).
Every lane injects those files and the workspace is gitignored, so the three git
sources above never see them; only the content rules apply, because a store is
local state by design and its location proves nothing.

It fails on: personal email addresses that are not role mailboxes at the neutral
identity domain and not at a name RFC 2606 / RFC 6761 reserves for documentation
(``example.com``/``example.net``/``example.org``, the ``.example`` TLD, ``.test``,
``.invalid``, ``.localhost``); the retired private domain(s); absolute personal
home paths
(``/home/<name>``, ``/Users/<name>``, ``C:\\Users\\<name>``); API keys and tokens
(``sk-``, ``ghp_``/``gho_``/``ghu_``/``ghs_``/``ghr_``, ``github_pat_``, ``AIza``,
``wandb_``, ``xoxb-``, ``Bearer``/``Basic``/``Token`` credentials, provider keys such
as ``gsk_``/``xai-``/``pplx-``/``glpat-``/``npm_``/``hf_``/``sk_live_``, Slack
incoming-webhook URLs, database URLs with an inline password, standalone
high-entropy secrets - including a value written straight after ``=``, as in
``NAME=<base64>``); private-key headers; ``.env``-style and JSON assignments of
secret-named variables; ``TODO``/``FIXME`` comments that carry credentials.

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
  from code points at runtime) and a matched value never reaches a log in any
  form: the report names the rule (``<redacted-rule>``) and no more, so a failing
  CI log cannot republish the secret, not even a prefix of it. The raw value is
  held outside the report record (see ``Finding``), so no reporting sink can
  serialise it by accident. ``--reveal`` prints a stable fingerprint (SHA-256
  prefix) instead and ``--reveal-to PATH`` exports the raw values to a ``0600``
  file for local remediation only.
* The allowlist file (``--allow``) holds one regular expression per line with a
  ``# reason`` suffix that must be separated by whitespace. A finding is exempt
  when its matched text matches any allowlist expression. Keep it minimal and
  justify each entry. A ``#`` that is not whitespace-separated is part of the
  pattern (a literal ``#``, as in ``^ab#cd$``); write ``\\#`` for a literal ``#``
  that must sit after a space. A pattern left mid-escape by the comment strip is
  refused with exit 2 rather than compiled into something nobody wrote.

Revealing a matched value
-------------------------
Unmasked values are **never** written to stdout or stderr. A log line is a
broadcast sink - CI logs are public, terminals are recorded, and ``tee``ed
output outlives the session - so the scanner has no flag that prints a secret.

* The report line for a finding is
  ``<location>: [<severity>/<rule>] <redacted-<rule>>``: it says which rule fired
  where, and deliberately no character of the value - a partly masked preview
  still publishes the first and last characters of a credential to every reader
  of the log, which is the disclosure this scanner exists to prevent.
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

SCANNER_VERSION = "1.5.0"

_HISTORY_REVISIONS = ("--all", "--reflog")


IDENTITY_DOMAIN = os.environ.get("TEAMWORK_IDENTITY_DOMAIN", "agents.nidvue.com")

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
    ".example",
    ".invalid",
    ".test",
    ".localhost",
)
_ALLOWED_SERVICE_EMAILS = re.compile(
    r"^(?:noreply@(?:github|gitlab)\.com|support@github\.com|"
    r"[^@]+@users\.noreply\.github\.com|"
    r"git@(?:github\.com|gitlab\.com|bitbucket\.org))$"
)


def _decode(*codes: int) -> str:
    return "".join(chr(c) for c in codes)


_DEFAULT_PRIVATE_DOMAINS = (
    _decode(122, 104, 97, 111, 46, 110, 111),
    _decode(98, 117, 108, 98, 105, 116, 101, 99, 104, 46, 99, 111, 109),
)


def _private_domains() -> list:
    extra = os.environ.get("TEAMWORK_PRIVATE_DOMAINS", "")
    values = [d.strip().lower() for d in extra.split(",") if d.strip()]
    seen = []
    for domain in list(_DEFAULT_PRIVATE_DOMAINS) + values:
        if domain and domain not in seen:
            seen.append(domain)
    return seen


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

_PLACEHOLDERS = re.compile(
    r"^(?:\$\{?[A-Za-z0-9_]+\}?|%[A-Za-z0-9_]+%|<[^>]+>|your[-_].*|"
    r".*[-_]here|xxx+|\.\.\.|redacted|placeholder|dummy|fake|changeme|change_me|"
    r"example|sample|test|none|null|nil|todo|secret|token|password|value|"
    r"replace_me|"
    r"string|str|varname)$",
    re.IGNORECASE,
)


def _email_pattern() -> re.Pattern:
    """The personal-email rule, with bounded quantifiers.

    An unbounded local part made the scan quadratic on a long run of word
    characters - a 1 MB text file took minutes - which hung the pre-commit gate
    on a large staged document (T-0022). RFC 5321 caps a local part at 64 and a
    domain label at 63, so the bounds cost no real match.
    """
    return re.compile(
        r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]{1,64}@"
        r"[A-Za-z0-9\-]{1,63}(?:\.[A-Za-z0-9\-]{1,63}){0,8}\.[A-Za-z]{2,24}"
    )


_RE_HOME = re.compile(
    r"(?:(?<![A-Za-z0-9_])/(?:home|Users)/([A-Za-z0-9][A-Za-z0-9._\-]*))"
    r"|(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]Users[\\/]([A-Za-z0-9][A-Za-z0-9._\-]*))"
    r"|(?:(?<![A-Za-z0-9])/mnt/[A-Za-z]/(?:Users|home)/([A-Za-z0-9][A-Za-z0-9._\-]*))"
)

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
    r"|\bhooks\.slack\.com/services/[A-Za-z0-9]{8,}/[A-Za-z0-9]{8,}/[A-Za-z0-9]{16,}"
    r"|\b(?i:Bearer|Basic|Token)\s+[A-Za-z0-9._+/=\-]{16,}"
    r"|(?<![A-Za-z0-9+.\-])"
    r"(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|rediss?|amqps?|mssql|sqlserver)"
    r"://[^:/@\s]{1,64}:[^@/\s]{6,}@[^\s\"'<>]+"
)

_RE_AUTH_PREFIX = re.compile(r"(?i)^(?:Bearer|Basic|Token)\s+(\S+)$")
_RE_URL_CREDENTIAL = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.\-]*)://([^:/@\s]+):([^@/\s]+)@")

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

_RE_PY_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_SECRET_WORDS = ("secret", "password", "passwd", "passphrase", "credential")


def _is_code_name(value: str) -> bool:
    """True for a bare identifier used as a value: code, not a credential.

    ``token = _current_github_token()`` assigns the *result of a call*, and the
    scanner only sees the name because the call's parentheses are outside the
    credential charset. A name-shaped value is code when it is written the way
    code is written: underscored, digit-free and not itself naming a secret.
    A value that carries digits (a cloud access key, a hex blob) or that names a
    secret stays a credential, so the rule is not weakened.
    """
    if not _RE_PY_IDENT.match(value):
        return False
    if "_" not in value or any(c.isdigit() for c in value):
        return False
    lowered = value.lower()
    return not any(word in lowered for word in _SECRET_WORDS)


def _looks_like_secret_value(value: str) -> bool:
    if value.startswith(("re.", "os.", "self.", "match.", "str(", "Path(")):
        return False
    if _RE_DOTTED_IDENT.match(value):
        return False
    if value.lower() in _CODE_KEYWORDS:
        return False
    if value.startswith(("/", "\\", "http://", "https://")) or "://" in value:
        return False
    if value.isdigit():
        return False
    if value.isalpha() and len(value) < 24:
        return False
    return not bool(_RE_CODE_LIKE.search(value))


def _plausible_credential(value: str) -> bool:
    """Reject the prose a credential rule would otherwise claim as a value.

    ``Basic`` and ``Token`` are English words as well as HTTP schemes, and the
    prose ``Basic interoperability`` reads to the pattern exactly like a scheme
    followed by a base64 payload. A scheme-prefixed value is therefore only a
    credential when its payload carries a credential signal: a digit, base64
    padding, base64 punctuation, or 24+ characters that read as a secret rather
    than as a word.

    A URL with an inline password is a credential unless the password is a
    placeholder (``user:password@host``, ``app:<pw>@db``, ``${DB_PASSWORD}``),
    which is how every document writes an example.
    """
    auth = _RE_AUTH_PREFIX.match(value)
    if auth is not None:
        payload = auth.group(1)
        if any(ch.isdigit() for ch in payload) or "=" in payload:
            return True
        return _looks_like_secret_value(payload)
    url = _RE_URL_CREDENTIAL.match(value)
    if url is not None:
        password = url.group(2)
        return len(password) >= 6 and not _PLACEHOLDERS.match(password)
    return True


def _env_secret_pattern() -> re.Pattern:
    """The env-secret rule, with a bounded keyword prefix.

    An unbounded ``[A-Za-z0-9_]*`` before the keyword alternation is quadratic on
    a long run of word characters (100 kB took minutes), which hung the
    pre-commit gate (T-0022). A keyword sits at most 64 characters from its
    assignment, so the bound costs no real match.
    """
    return re.compile(
        r"(?i)(?<![A-Za-z0-9_])(?:[A-Za-z0-9_]{0,64}(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|"
        r"ACCESS[_-]?KEY|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET|AUTH[_-]?KEY|CREDENTIAL)"
        r"[A-Za-z0-9_]{0,64})\s*[:=]\s*"
        r"(?:[\"']([^\"'\n]{8,})[\"']|([A-Za-z0-9+/=_\-.:@!#$%^&]{8,}))"
    )


_RE_HIGH_ENTROPY = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])")

_RE_TODO = re.compile(r"(?i)\b(?:TODO|FIXME|XXX|HACK)\b")

_RE_FORGE_MERGE = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")


_RE_FORGE_MERGE_SUBJECTS = (
    re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$"),
    re.compile(r"^Merge pull request #\d+ from \S+$"),
    re.compile(r"^Merge branch '[^']+' into '[^']+'$"),
    re.compile(r"^Merge remote-tracking branch '[^']+'$"),
)

_RE_FORGE_COMMITTER_STAMP = re.compile(r"^(?:noreply@github\.com|noreply@gitlab\.com)$")


def is_forge_merge(subject: str, parents: list, committer: str) -> bool:
    """True for the synthetic merge ref a forge creates for a pull request.

    The subject alone is not evidence. Any commit can be written with
    ``-m "Merge <sha> into <sha>"`` and two parents, and its author/committer
    identity is then exempt from this scan while its tree is still scanned - so a
    fabricated merge message used to be enough to hide a personal mailbox from
    the history gate. The exemption therefore requires the documented forge
    committer stamp as well: the subject says what the commit claims to be, the
    committer says what actually created it.

    Residual risks, stated rather than hidden:

    * A committer address is settable locally (``GIT_COMMITTER_EMAIL=...``), so an
      author who deliberately stamps a host service address *and* a forged merge
      subject can still keep an identity out of this scan. That is a second,
      deliberate act of forgery rather than a typo in a subject line; the forged
      stamp is itself the finding to look for when a history is suspected.
    * A real host merge whose committer is not one of the two documented stamps -
      for example a forge that commits a merge as the account that clicked the
      button instead of as itself - is now scanned and may be reported. That is
      the intended trade (identity over convenience): the remedy is a dated
      ``--allow`` entry for a value that is genuinely not personal, never an
      exemption keyed on a message the committer can type.

    The commit *message* is scanned unconditionally by the caller; this predicate
    only decides whether the author/committer fields are skipped.
    """
    if len(parents) < 2:
        return False
    text = subject.strip()
    if not any(pattern.match(text) for pattern in _RE_FORGE_MERGE_SUBJECTS):
        return False
    return _RE_FORGE_COMMITTER_STAMP.match(committer.strip().lower()) is not None


def _host_state(*parts: str) -> str:
    """Join path fragments so this published file never quotes a private path."""
    return "".join(parts)


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

_RE_JSON_SECRET = re.compile(
    r"(?i)[\"'][A-Za-z0-9_.\-]*(?:api[_-]?key|apikey|access[_-]?token|"
    r"refresh[_-]?token|id[_-]?token|client[_-]?secret|private[_-]?key|secret|"
    r"password|passwd|token)[\"']\s*:\s*[\"']([^\"'\n]{8,})[\"']"
)

_SENSITIVE_NAME = re.compile(
    r"(?i)^(?:\.env(?:\.(?!example$|sample$|template$|dist$)[^/]+)?"
    r"|auth(?:\.json)?(?:\.bak)?|auth\.json|credentials\.json|secrets?\.json"
    r"|mcp-auth\.json|settings\.local\.json|\.netrc|\.npmrc|\.pypirc"
    r"|\.bash_history|\.zsh_history|\.python_history"
    r"|id_(?:rsa|dsa|ecdsa|ed25519)"
    r"|\.git-credentials|\.htpasswd)$"
)
_SENSITIVE_SUFFIX = re.compile(r"(?i)\.(?:pem|p12|pfx|keystore|jks)$")
_LOCAL_STATE_PARTS = (
    ".pi",
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
_SENSITIVE_BASENAMES = {
    "auth.json",
    "auth.json.bak",
    _host_state(".aider.", "chat.history.md"),
    _host_state(".aider.", "input.history"),
}

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


_QUOTED_EVIDENCE = re.compile(
    r"^- (?:self-check|author evidence|reviewer evidence|findings history): "
)
_QUOTED_STORE_FIELD = re.compile(r"^- (?:statement|evidence): ")
_QUOTED_PATH_RULES = frozenset({"home-path", "agent-config"})

RULES = (
    {"id": "private-key", "severity": "critical", "regex": _RE_PRIVATE_KEY},
    {"id": "api-token", "severity": "critical", "regex": _RE_TOKEN},
    {"id": "env-secret", "severity": "critical", "regex": _env_secret_pattern()},
    {"id": "json-secret", "severity": "critical", "regex": _RE_JSON_SECRET},
    {"id": "agent-config", "severity": "high", "regex": _RE_AGENT_CONFIG},
    {"id": "private-domain", "severity": "high", "regex": None},
    {"id": "personal-email", "severity": "high", "regex": _email_pattern()},
    {"id": "home-path", "severity": "high", "regex": _RE_HOME},
    {"id": "high-entropy-secret", "severity": "high", "regex": _RE_HIGH_ENTROPY},
)


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


_TOKEN_CHARS = re.compile(r"[A-Za-z0-9._/+=-]+")
_PATH_SEGMENT = re.compile(r"\.?[A-Za-z0-9][A-Za-z0-9._-]*")
_NAME_WORDS = re.compile(r"[A-Z][0-9]+|[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|[0-9]+")
_CAMEL_CASE = re.compile(r"[a-z][A-Z]")
_MAX_NAME_WORDS = 3
_MIN_NAME_WORD = 2


def _token_around(line: str, index: int, length: int) -> str:
    """The whole token the match at ``index`` sits in, or ``""``."""
    for match in _TOKEN_CHARS.finditer(line):
        if match.start() <= index and index + length <= match.end():
            return match.group(0)
    return ""


def _is_path_name(token: str) -> bool:
    """Does this token read as a repository path rather than as a random string?

    Every segment must be a name: a word (or a few words in CamelCase) with an
    optional extension, and a leading dot is allowed so this repository's own
    ``.pi/Teamwork/...`` layout reads as a path rather than as a secret. A lane or milestone id counts as one word, not as a
    one-letter fragment followed by digits (see ``_NAME_WORDS``), so a document
    path such as ``Agents/SecurityAuditor/Reports/M13-security-audit.md`` reads
    as a name. A random base64 run splits into many short fragments, which is
    what tells the two apart.
    """
    if "/" not in token:
        return False
    segments = [segment for segment in token.split("/") if segment and segment != "."]
    if not segments:
        return False
    for segment in segments:
        if not _PATH_SEGMENT.fullmatch(segment):
            return False
        words = _NAME_WORDS.findall(segment.lstrip(".").split(".")[0])
        if not words or len(words) > _MAX_NAME_WORDS:
            return False
        if any(len(word) < _MIN_NAME_WORD and word.isalpha() for word in words):
            return False
    return True


def _is_path_fragment(line: str, index: int, length: int) -> bool:
    """Is the match a piece of a path, rather than a value in its own right?

    The high-entropy rule matches 32+ base64-ish characters, so it also matches
    the first 33 characters of a longer path: ``ProductManager/Artifacts/Harness2``
    is the head of ``ProductManager/Artifacts/Harness2-Brief.md``. A credential
    is a whole token, so two signals together are decisive - the token must read
    as a path, and it must be a NAME (CamelCase, or cut out of a longer path).
    A random base64 run reads as neither: it has too many fragments to be a
    name, and it is a whole token.

    ``=`` is part of the token (it is a base64 and an assignment character), so
    the token around ``root=ProductManager/...`` carries the assignment too. The
    value after the last ``=`` is the token under judgement, because that is the
    token the rule actually matched into: ``conn=<base64>`` and
    ``root=ProductManager/...`` are the same shape at this point, and only the
    path exemption tells them apart.
    """
    whole = _token_around(line, index, length)
    _, _, assigned = whole.rpartition("=")
    if assigned:
        whole = assigned
    if not _is_path_name(whole):
        return False
    if len(whole) > length:
        following = whole[length]
        if following.isalnum() or following in "-_":
            return True
    return any(_CAMEL_CASE.search(part) for part in whole.split("/") if part)


def _looks_like_secret(value: str, line: str = "", index: int = 0) -> bool:
    """Filter out hashes, identifiers, URL paths and natural words."""
    if len(value) < 32:
        return False
    if re.fullmatch(r"[0-9a-fA-F]+", value):
        return False
    scheme = line.find("://")
    if scheme != -1 and index > scheme:
        between = line[scheme + 3 : index]
        if not re.search(r"[\s\"']", between):
            return False
    if _is_path_fragment(line, index, len(value)):
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
    """Is this address one the ``personal-email`` rule must not report?

    Role mailboxes and forge service addresses are transport, not personal data.
    The rest are the names RFC 2606 and RFC 6761 reserve for documentation:
    ``example.com``/``.net``/``.org``, the ``.example`` TLD, ``.test``,
    ``.invalid`` and ``.localhost``. An address at a reserved name identifies
    nobody, so a document may quote one. This exempts the ``personal-email`` rule
    ONLY: every other rule reads the same line, so a configured private domain is
    still reported by ``private-domain`` and a credential beside it is still
    reported by its own rule.
    """
    if _ALLOWED_SERVICE_EMAILS.match(value):
        return True
    domain = value.rsplit("@", 1)[-1].lower()
    if domain in _ALLOWED_EMAIL_DOMAINS:
        return True
    return any(domain.endswith(suffix) for suffix in _ALLOWED_EMAIL_SUFFIXES)


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
        try:
            os.unlink(str(target))
        except OSError:
            pass
        raise
    return written


class Finding(dict):
    """One report row, with the raw matched value held outside the mapping.

    Every reporting sink serialises *items*: ``json.dumps(report)`` walks the
    dict, the text report reads ``evidence``, and both end up in a CI log. A
    value kept as an attribute therefore cannot be published by any of them, so
    "the log never carries a secret" is a property of the shape rather than a
    promise held by one ``pop`` before one ``print``. Everything that needs the
    value itself - ``--reveal``, ``--reveal-to`` and the archive mask - reads
    ``.raw`` explicitly, which is greppable and reviewable in one place each.
    """

    __slots__ = ("raw",)

    def __init__(self, items, raw=""):
        super().__init__(items)
        self.raw = raw


def make_finding(rule_id, severity, path, line_no, value, line, source, commit=None):
    return Finding(
        {
            "rule": rule_id,
            "severity": severity,
            "path": path,
            "line": line_no,
            "source": source,
            "commit": commit,
            "location": location(path, line_no, commit),
            "evidence": f"<redacted-{rule_id}>",
            "context": "",
        },
        value,
    )


def location(path, line_no, commit=None):
    if commit:
        return f"{path}:{line_no}" if line_no else path
    return f"{path}:{line_no}"


_LINE_CACHE: dict[tuple, tuple[tuple[str, str, str], ...]] = {}
_LINE_CACHE_LIMIT = 200_000


def reset_line_cache():
    """Forget every memoised line verdict (tests, and any rule-set change)."""
    _LINE_CACHE.clear()


def _line_verdicts(line, flags, compiled, allow, private_re):
    """Rule verdicts for one line: ``(rule id, severity, value)`` triples.

    Split out of ``scan_lines`` so the verdict can be memoised: it depends on the
    line and the three path-derived flags, never on the file or commit it came
    from. The allowlist is applied here, so a hit the allowlist exempts is not
    re-derived per occurrence either.
    """
    ignore_file, archive, store = flags
    verdicts = []
    quoted_evidence = archive and _QUOTED_EVIDENCE.match(line) is not None
    quoted_store_field = store and _QUOTED_STORE_FIELD.match(line) is not None
    for rule, regex in compiled:
        if rule["id"] == "agent-config" and ignore_file:
            continue
        if quoted_evidence and rule["id"] in _QUOTED_PATH_RULES:
            continue
        if quoted_store_field and rule["id"] == "agent-config":
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
                    if not re.search(r"\s", secret) and not _looks_like_secret_value(secret):
                        continue
                elif _is_code_name(secret) or not _looks_like_secret_value(secret):
                    continue
                value = secret
            if rule["id"] == "api-token" and not _plausible_credential(value):
                continue
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
            verdicts.append((rule["id"], rule["severity"], value))

    if _RE_TODO.search(line):
        credential = None
        for probe in (_RE_TOKEN, _RE_PRIVATE_KEY):
            for match in probe.finditer(line):
                if probe is _RE_TOKEN and not _plausible_credential(match.group(0)):
                    continue
                credential = match.group(0)
                break
            if credential:
                break
        if credential is None and private_re is not None:
            match = private_re.search(line)
            if match:
                credential = match.group(0)
        if credential is None:
            match = _env_secret_pattern().search(line)
            if match:
                candidate = match.group(1) or match.group(2)
                if not _PLACEHOLDERS.match(candidate) and (
                    match.group(1) is not None
                    or not _is_code_name(candidate)
                    and _looks_like_secret_value(candidate)
                ):
                    credential = candidate
        if credential and not any(p.search(credential) for p in allow):
            verdicts.append(("todo-credential", "medium", credential))
    return tuple(verdicts)


def scan_lines(text, path, source, rules, allow, commit=None):
    """Yield findings for one text blob (a file or a commit message body).

    Verdicts are memoised per (allowlist, flags, line) because history holds
    hundreds of near-identical renders of the same append-only document: the
    archive alone is re-rendered on every merge, so the same line is scanned
    hundreds of times for a verdict that cannot differ. The memo is only used
    for the shipped rule set, so a caller passing its own rules always re-derives.
    """
    private_domains = _private_domains()
    private_re = None
    if private_domains:
        private_re = re.compile("|".join(re.escape(d) for d in private_domains), re.IGNORECASE)

    compiled = []
    for rule in rules:
        if rule["id"] == "json-secret":
            continue
        if rule["id"] == "private-domain":
            if private_re is None:
                continue
            compiled.append((rule, private_re))
        elif rule["regex"] is not None:
            compiled.append((rule, rule["regex"]))

    flags = (path.endswith(".gitignore"), path.endswith("Archive.md"), source == "stores")
    allow_key = tuple(pattern.pattern for pattern in allow)
    domain_key = private_re.pattern if private_re is not None else ""
    cache = _LINE_CACHE if rules is RULES else None
    for line_no, line in enumerate(text.splitlines(), 1):
        key = (allow_key, flags, domain_key, line)
        verdicts = cache.get(key) if cache is not None else None
        if verdicts is None:
            verdicts = _line_verdicts(line, flags, compiled, allow, private_re)
            if cache is not None and len(cache) < _LINE_CACHE_LIMIT:
                cache[key] = verdicts
        for rule_id, severity, value in verdicts:
            yield make_finding(rule_id, severity, path, line_no, value, line, source, commit)

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
    """Scan author/committer name+email and the message of every commit.

    "Every commit" is ``_HISTORY_REVISIONS`` - all refs plus the reflog, the same
    set ``scan_history`` walks for blobs. ``--reflog`` is load-bearing: a commit
    an amend rewrote away is unreachable from any ref, so without it its blobs get
    scanned while its author/committer mailbox is skipped.
    """
    fmt = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%P%x1f%B%x1e"
    proc = _run(["git", "-C", str(root), "log", *_HISTORY_REVISIONS, "--format=" + fmt])
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
        if not is_forge_merge(subject, parents, ce):
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
        pos += size + 1
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
    return Finding(
        {
            "rule": "local-state" if local_state else "local-config",
            "severity": "high" if local_state else "critical",
            "path": rel,
            "line": 0,
            "source": source,
            "commit": commit,
            "location": rel,
            "evidence": rel,
            "context": reason,
        },
        rel,
    )


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
                Finding(
                    {
                        "rule": "unreadable-tracked-file",
                        "severity": "medium",
                        "path": rel,
                        "line": 0,
                        "source": "tree",
                        "commit": None,
                        "location": rel,
                        "evidence": rel,
                        "context": f"tracked file could not be read: {exc}",
                    },
                    rel,
                )
            )
            continue
        findings.extend(_scan_bytes(data, rel, "tree", allow))
    return findings


_TEAM_WORKSPACE = _host_state(".pi/", "Teamwork/", "Teams")
_STORE_NAMES = (
    "ShortTermMemory.md",
    "LongTermMemory.md",
    "ArchivedMemory.md",
    "Lessons.md",
)


def store_paths(root):
    """The team memory stores under the local workspace, relative to ``root``.

    Every lane's context is built from these files, and the workspace itself is
    gitignored local state, so ``--tree``/``--staged``/``--history`` never see
    them: a secret or a personal address written into a store is republished to
    every lane with no gate in the way. Discovery is by layout, not by a fixed
    list, so a new team or role is covered the moment its directory exists.
    """
    workspace = Path(root) / _TEAM_WORKSPACE
    if not workspace.is_dir():
        return []
    found = []
    for team in sorted(p for p in workspace.iterdir() if p.is_dir()):
        candidates = [team / "Knowledge.md", team / "Global" / "GlobalMemory.md"]
        for role in sorted(p for p in (team / "Roles").glob("*") if p.is_dir()):
            candidates.extend(role / name for name in _STORE_NAMES)
        found.extend(p for p in candidates if p.is_file())
    return [p.relative_to(root).as_posix() for p in found]


def scan_stores(root, allow, stats=None):
    """Scan the memory store content.

    The path rule stays quiet: a store under the workspace is local state by
    design, so failing it for its location would fail every clean store. Only
    the content rules decide, because the content is what a lane injects.
    """
    findings = []
    for rel in store_paths(root):
        try:
            data = (Path(root) / rel).read_bytes()
        except OSError as exc:
            findings.append(
                Finding(
                    {
                        "rule": "unreadable-store",
                        "severity": "medium",
                        "path": rel,
                        "line": 0,
                        "source": "stores",
                        "commit": None,
                        "location": rel,
                        "evidence": rel,
                        "context": f"memory store could not be read: {exc}",
                    },
                    rel,
                )
            )
            continue
        if stats is not None:
            stats["store_files"] += 1
        findings.extend(_scan_bytes(data, rel, "stores", allow))
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
    proc = _run(["git", "-C", str(root), "rev-list", "--objects", *_HISTORY_REVISIONS])
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


def allow_expression(line):
    """One allowlist line with its comment suffix removed, pattern intact.

    Only a WHITESPACE-SEPARATED trailing ``#`` starts a comment. Splitting on the
    first ``#`` instead turns ``^ab#cd$`` into ``^ab`` - a shorter, more
    permissive expression that still compiles, so a pattern for one literal would
    quietly exempt everything sharing its prefix. A ``#`` that is not
    whitespace-separated is a literal in the pattern; a literal that has to follow
    a space is written ``\\#``, which the comment rule cannot match.
    """
    return re.sub(r"\s+#.*$", "", line).strip()


def _ends_mid_escape(expression):
    """Whether the expression ends with an escaped or dangling backslash run."""
    trailing = len(expression) - len(expression.rstrip("\\"))
    return bool(trailing % 2)


def load_allow(path):
    patterns = []
    if not path:
        return patterns
    text = Path(path).read_text(encoding="utf-8")
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expression = allow_expression(line)
        if not expression:
            continue
        if _ends_mid_escape(expression):
            print(
                f"privacy_scan: {path}:{line_no}: allow pattern ends mid-escape "
                "(a comment strip would have to break it); write '\\#' for a literal "
                "'#' that follows whitespace",
                file=sys.stderr,
            )
            raise SystemExit(2)
        try:
            patterns.append(re.compile(expression))
        except re.error as exc:
            print(f"privacy_scan: {path}:{line_no}: bad allow regex: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
    return patterns


def summarize(findings):
    by_severity = Counter(f["severity"] for f in findings)
    by_rule = Counter(f["rule"] for f in findings)
    return {"by_severity": dict(by_severity), "by_rule": dict(by_rule)}


def dedupe(findings):
    seen = set()
    unique = []
    for finding in findings:
        key = (finding["rule"], finding["location"], finding.raw, finding.get("commit") or "")
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
    parser.add_argument(
        "--stores",
        action="store_true",
        help="scan the team memory stores under the local workspace (never committed)",
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
    if not (args.tree or args.staged or args.history or args.stores):
        args.tree = True

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
        for name, flag in (
            ("tree", args.tree),
            ("staged", args.staged),
            ("history", args.history),
            ("stores", args.stores),
        )
        if flag
    ]

    findings = []
    stats = {
        "tracked_files": 0,
        "staged_files": 0,
        "history_blobs": 0,
        "commits": 0,
        "store_files": 0,
    }
    try:
        if args.tree:
            findings.extend(scan_tree(root, allow, stats))
        if args.staged:
            findings.extend(scan_staged(root, allow, stats))
        if args.history:
            findings.extend(scan_history(root, allow, stats))
        if args.stores:
            findings.extend(scan_stores(root, allow, stats))
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"privacy_scan: {exc}", file=sys.stderr)
        return 2

    findings = dedupe(findings)
    reveal_path = args.reveal_to
    reveal_values = []
    for finding in findings:
        if not finding.raw:
            continue
        if args.reveal:
            finding["fingerprint"] = _fingerprint(finding.raw)
        if reveal_path:
            reveal_values.append((finding, finding.raw))

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
        "root": root.name,
        "modes": modes,
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
                shown = finding["evidence"]
                fingerprint = finding.get("fingerprint")
                if fingerprint:
                    shown = f"{shown} ({fingerprint})"
                line = f"{finding['location']}: [{finding['severity']}/{finding['rule']}] {shown}"
                detail = finding.get("detail", "")
                if detail:
                    line = f"{line}  {detail}"
                print(line)
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
