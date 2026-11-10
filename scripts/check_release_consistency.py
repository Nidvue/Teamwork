#!/usr/bin/env python3
"""check_release_consistency.py - the release gate: published facts vs local facts.

Why this exists: an npm tarball, a git tag, a GitHub Release and a sentence in
``README.md`` are four independent claims about "what version is out". Nothing in
the repository compared them, so a tarball built from a commit that was never
tagged shipped as a release while the docs still named an older version. This
checker makes that state fail a gate instead of being found by a reader.

It implements `docs/Team/Architecture.md` section 11 (the frozen release
consistency contract). It is read-only - it never tags, publishes, pushes or
writes - it runs offline by default, and a missing or unreadable input is an
error (exit 2), never a pass.

Public surface
--------------
Entry point and contract callables (section 11.1)::

    main(argv: Optional[Sequence[str]] = None) -> int
    payload_digest(root: Path, rev: Optional[str]) -> str   # 11.3
    _http_get_json(url: str) -> object                      # 11.1.4 network seam

One function per rule, each taking explicit inputs and no hidden global state so
a unit test can point it at a fixture tree::

    rule_r1_tagged_version(repo_root) -> RuleResult
    rule_r2_head_is_newer(repo_root) -> RuleResult
    rule_r3_npm_payloads(repo_root, exceptions=(), fetch=None, fetch_bytes=None)
    rule_r4_releases_have_tags(repo_root, fetch=None)
    rule_r5_tags_have_releases(repo_root, fetch=None)
    rule_r6_markdown_versions(repo_root) -> RuleResult
    rule_r7_changelog(repo_root) -> RuleResult
    rule_r8_install_channels(repo_root, fetch=None) -> RuleResult
    rule_r9_markdown_tags(repo_root) -> RuleResult

``fetch=None`` is what makes a rule offline: R3, R4, R5 and R8 print a ``SKIP``
whose detail says why, and R3, R7, R1, R2, R6 and R9 evaluate from the tree.
Passing ``fetch`` (and for R3 ``fetch_bytes``) is ``--online``.

Supporting helpers a test may use directly::

    load_exceptions(path: Path) -> list[dict[str, str]]
    markdown_paths(repo_root: Path) -> list[str]
    RuleResult          # rule, status, detail, findings, fatal
    InputError          # an input could not be read -> exit 2
    HttpError           # an HTTP status came back -> exit 2 (or R8's 404 case)

Design notes
------------
* Python 3.9+, standard library only, no third-party import, no ``shell=True``.
* Every HTTP call funnels through one seam, ``_http_get``; ``_http_get_json`` is
  the JSON face of it and ``_http_get_bytes`` the binary face (an npm ``.tgz`` is
  not JSON, so section 11.2.3's tarball download cannot ride a JSON function).
  Tests monkeypatch ``_http_get_json``/``_http_get_bytes``; R3/R4/R5/R8 take them
  as parameters so a monkeypatch is not even required.* Status literals are exactly ``ok``, ``DRIFT`` and ``SKIP``. Exit code
  precedence is ``2 > 1 > 0``: a run that finds drift *and* cannot read an input
  exits ``2``.
* R9 matches the ``vX.Y.Z`` form only. Section 11.2.4 says "the token regex is
  R6's without the project-context condition", but its DRIFT clause is about "a
  ``vX.Y.Z`` token": a bare ``3.12.13`` in ``python: 3.12.13`` names a Python
  version, not a tag, and turning it into "missing tag v3.12.13" would be a
  defect rather than a finding. R6 owns bare version prose.

Measurement behind ``TARBALL_LAYOUT`` (11.2.3): the npm tarball does *not* keep
payload-relative paths. ``build_pi_package.copy_skill`` stages ``skills/teamwork/``
plus the pi-native layer at ``skills/teamwork-pi/`` and ``prompts/`` (= the tag
tree's ``templates/pi-package/``). Hashing the tarball where it sits produces a
digest a tag can never reproduce, so the shipped subtrees are re-laid out under
their payload paths before hashing. Measured on the published tarballs:
``1.1.2`` -> ``a01d9f0cbee641c3`` = payload of ``3f4981d``; ``1.1.0`` ->
``ebfc2538e3d3d605`` = payload of ``v1.1.0`` (identical once
``scripts/build_pi_package.py`` is excluded, which is 11.5 example 3);
``1.1.1`` -> ``726bc547afc41ead``, which matches no commit in
``git rev-list --all`` (389 commits checked) - 11.5 example 2.

Exit-code policy for an input that cannot be read (11.1.1): section 11 makes a
missing or unreadable input exit ``2``, and 11.1.4 names a non-200 response, a
URL error and a timeout as that failed API call. Section 11.2.4 carves out one
case - R8's PyPI ``404`` means "the distribution is unpublished", which is a
fact about the release, not a failed read. R3 has the same shape: an HTTP
``404`` on a version's ``dist.tarball`` is treated like a ``vX.Y.Z`` tag that
does not exist - DRIFT - because the tarball the registry advertises is absent,
which is exactly what the gate exists to report. Every other transport/status
failure (``5xx``, timeout, URL error) is *unreadable input*: ``fatal=True``,
exit ``2``, never a DRIFT finding. A network flake must be distinguishable from
a release defect, so 5xx/timeout can never share an exit code with drift.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "HttpError",
    "InputError",
    "RuleResult",
    "load_exceptions",
    "main",
    "markdown_paths",
    "payload_digest",
    "rule_r1_tagged_version",
    "rule_r2_head_is_newer",
    "rule_r3_npm_payloads",
    "rule_r4_releases_have_tags",
    "rule_r5_tags_have_releases",
    "rule_r6_markdown_versions",
    "rule_r7_changelog",
    "rule_r8_install_channels",
    "rule_r9_markdown_tags",
]

#: The single source of the version string, and the only local version fact.
VERSION_PATH = "src/teamwork/version.py"

#: Bundled payload (11.3) - the shipped set, asserted by build_pi_package.py
#: against ``teamwork.bundle.BUNDLE_FILES``/``BUNDLE_TREES``.
PAYLOAD_FILES = ("SKILL.md", "AGENTS.md")
PAYLOAD_TREES = ("references", "roles", "templates", "scripts", "src")
#: 11.2.3: the build-time generator is not shipped payload, so it is excluded
#: from every digest on every run - a repository-side edit to it is not drift.
PAYLOAD_EXCLUDES = frozenset({"scripts/build_pi_package.py"})

#: Tarball path prefix -> payload path prefix (11.2.3 + build_pi_package.copy_skill).
TARBALL_LAYOUT = (
    ("skills/teamwork", ""),
    ("skills/teamwork-pi", "templates/pi-package/skills/teamwork-pi"),
    ("prompts", "templates/pi-package/prompts"),
)

NPM_REGISTRY = "https://registry.npmjs.org/@nidvue%2Fteamwork"
GITHUB_RELEASES = "https://api.github.com/repos/Nidvue/Teamwork/releases"
PYPI_JSON = "https://pypi.org/pypi/teamwork-agents/json"
USER_AGENT = "teamwork-release-consistency/1.0 (+https://github.com/Nidvue/Teamwork)"
HTTP_TIMEOUT = 20

#: The exact literals of 11.2.4. Nothing else is a marker.
ILLUSTRATIVE = "<!-- release-consistency: illustrative -->"
CHANNEL_UNAVAILABLE = "<!-- release-consistency: channel-unavailable -->"

EXCEPTION_KEYS = ("version", "reason", "evidence", "recorded")

#: 11.2.4: historical evidence is never rewritten to satisfy a gate.
SCAN_EXCLUDED = "docs/Team/Archive.md"

#: 11.2.4 R6 scope - the narrower prose set. R8 and R9 scan every committed .md.
R6_GLOBS = ("README.md", "docs/index.md", "docs/Team/Release.md", "docs/guide/*.md")

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")
VERSION_ASSIGN = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")
DIST_NAME_ASSIGN = re.compile(r"""DIST_NAME\s*=\s*["']([^"']+)["']""")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
#: 11.2.4 version token: a ``/`` or ``.`` abuts a URL/link destination, so it
#: does not match; that is what keeps ``.../compare/v1.1.2...HEAD`` out.
VERSION_TOKEN = re.compile(r"(?<![\w./-])v?(\d+\.\d+\.\d+)(?![\w./-])")
TAGGED_TOKEN = re.compile(r"(?<![\w./-])v(\d+\.\d+\.\d+)(?![\w./-])")
PROJECT_CONTEXT = re.compile(r"(?i)teamwork")
#: 11.2.4: a foreign tool's version is not a teamwork version. Matched per
#: token, not per line: ``Install Teamwork 1.0.2 to match python: 3.12.13``
#: skips ``3.12.13`` and still flags our own stale ``1.0.2``.
FOREIGN_VERSION = re.compile(r"(?i)\b(?:python3?|cpython|node|npm|pi)\s*[:=]\s*v?(\d+\.\d+\.\d+)")
CHANGELOG_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")
FENCE_OPEN = re.compile(r"^(`{3,}|~{3,})")
PIP_PLAIN = re.compile(r"\bpip3?\s+install\s+(\S+)")
PIP_MODULE = re.compile(r"\b(?:python3?|py)\s+-m\s+pip3?\s+install\s+(\S+)")
PIPX = re.compile(r"\bpipx\s+install\s+(\S+)")
#: The two run-without-installing shapes: ``uvx --from <dist> <script>`` and
#: ``pipx run --spec <dist> <script>``. The script argument is read by
#: ``_trailing_script`` because prose continues after the distribution name and
#: a bare ``\S+`` would invent an executable out of the next English word.
UVX_FROM = re.compile(r"\buvx\s+--from\s+(\S+)")
PIPX_RUN = re.compile(r"\bpipx\s+run\s+--spec\s+(\S+)")
#: ``<script>`` must be the *next* argument after the distribution: a flag, a
#: closing quote/bracket or the end of the line must follow it (``teamwork
#: --version``, ``teamwork` ``). Prose that continues after the distribution
#: (``teamwork-agents` is the fastest way to try it``) therefore names none.
SCRIPT_ARGUMENT = re.compile(
    r"[ \t]+([A-Za-z0-9_-](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?)"
    r"(?=[ \t]+-{1,2}\S|[ \t]*[`\"')\]]|[ \t]*$)"
)
NEGATED_CHANNEL = re.compile(
    r"(?i)\b(no|not|never|without)\s+(?:a\s+|an\s+|any\s+)?"
    r"`?(?:pip3?|pipx|uvx|uv)`?\s+(?:install|run|--from)"
)


class InputError(RuntimeError):
    """An input could not be read; the run must exit 2 rather than pass."""


class HttpError(InputError):
    """An HTTP call returned a status other than 200.

    ``status`` is kept so R8 can read the 404 that 11.2.4 makes a DRIFT
    ("the distribution is unpublished") instead of the blanket exit 2 of 11.1.4.
    """

    def __init__(self, url: str, status: int | None) -> None:
        self.url = url
        self.status = status
        super().__init__(f"{url}: HTTP {status}")


@dataclass(frozen=True)
class RuleResult:
    """One rule's verdict: a table line, plus the findings behind it."""

    rule: str
    status: str
    detail: str
    findings: tuple[str, ...] = ()
    #: An input could not be read in this rule - exit 2 wins over any drift.
    fatal: bool = False


def _drift(rule: str, findings: Sequence[str], notes: Sequence[str] = ()) -> RuleResult:
    findings = tuple(_one_line(text) for text in findings)
    detail = "; ".join(list(findings) + list(notes))
    return RuleResult(rule, "DRIFT", detail, findings)


def _ok(rule: str, detail: str) -> RuleResult:
    return RuleResult(rule, "ok", _one_line(detail))


def _skip(rule: str, detail: str, fatal: bool = False) -> RuleResult:
    return RuleResult(rule, "SKIP", _one_line(detail), fatal=fatal)


def _unreadable(
    rule: str,
    findings: Sequence[str],
    notes: Sequence[str],
    reason: str,
) -> RuleResult:
    """An input could not be read (11.1.1): exit 2, and every DRIFT finding kept.

    The status stays ``DRIFT`` when there is one, so ``problems`` in ``--json``
    still names it; ``fatal=True`` makes the exit code ``2`` win over ``1``.
    With no drift it is the ``SKIP`` that carries the reason.
    """
    if findings:
        detail = "; ".join([*findings, f"unreadable input: {reason}", *notes])
        return RuleResult(rule, "DRIFT", _one_line(detail), tuple(findings), fatal=True)
    return _skip(rule, "; ".join([f"unreadable input: {reason}", *notes]), fatal=True)


def _one_line(text: str) -> str:
    """A detail is never empty and never contains a newline (11.1.2)."""
    flat = " ".join(str(text).split())
    return flat or "(no detail)"


# --------------------------------------------------------------------------- #
# Process and network seams
# --------------------------------------------------------------------------- #


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            status = getattr(response, "status", 200)
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(url, exc.code) from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise InputError(f"{url}: {exc}") from exc
    if status != 200:
        raise HttpError(url, status)
    return body


def _http_get_json(url: str) -> object:
    """The single JSON network seam of 11.1.4. Anonymous, no token, 20 s."""
    body = _http_get(url)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{url}: non-JSON body: {exc}") from exc


def _http_get_bytes(url: str) -> bytes:
    """Binary twin of the seam: an npm ``.tgz`` is not a JSON document."""
    return _http_get(url)


def _git_root(explicit: str | None) -> Path | None:
    """Resolve ``--repo-root`` and require it to be the work tree top level."""
    start = Path(explicit) if explicit else Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    top = Path(proc.stdout.decode("utf-8", "replace").strip())
    try:
        if top.resolve() != start.resolve():
            return None
        return top.resolve()
    except OSError:
        return None


def _git(repo_root: Path, *args: str, missing_ok: bool = False) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError(f"git {args[0]}: {exc}") from exc
    if proc.returncode != 0:
        if missing_ok:
            return None
        message = proc.stderr.decode("utf-8", "replace").strip()
        raise InputError(f"git {' '.join(args)} failed: {message or proc.returncode}")
    return proc.stdout.decode("utf-8", "replace")


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InputError(f"git {args[0]}: {exc}") from exc
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace").strip()
        raise InputError(f"git {' '.join(args)} failed: {message or proc.returncode}")
    return proc.stdout


# --------------------------------------------------------------------------- #
# Bundled payload digest (11.3)
# --------------------------------------------------------------------------- #


def _payload_skip(rel: Path) -> bool:
    """Mirror ``teamwork.bundle._skip``: build noise is not payload."""
    if "__pycache__" in rel.parts:
        return True
    if any(part.endswith(".egg-info") for part in rel.parts):
        return True
    return rel.suffix in (".pyc", ".pyo")


def _extract_tar(archive: tarfile.TarFile, destination: Path) -> None:
    for member in archive.getmembers():
        parts = Path(member.name).parts
        if member.name.startswith(("/", "\\")) or ".." in parts:
            raise InputError(f"archive member escapes the temporary tree: {member.name}")
        # 11.3: the payload is plain files only, so a link member is a defect by
        # itself. A name-only guard is not enough on 3.9-3.13, whose extractall
        # has no default filter and would happily write through ``linkname``.
        if member.issym() or member.islnk():
            raise InputError(
                f"archive member is a link, which the payload never contains: {member.name}"
            )
    archive.extractall(destination)


def _digest_of_tree(root: Path) -> str:
    """The 11.3 digest of the payload found at ``root``."""
    return _digest_of_files(_payload_paths(root), root)


def _payload_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in PAYLOAD_FILES:
        candidate = root / name
        if candidate.is_file():
            paths.append(candidate)
    for tree in PAYLOAD_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            try:
                is_file = path.is_file()
            except OSError as exc:
                raise InputError(f"{path}: {exc}") from exc
            if is_file:
                paths.append(path)
    return paths


def _digest_of_files(paths: Sequence[Path], root: Path) -> str:
    lines: list[str] = []
    for path in paths:
        rel = path.relative_to(root)
        if rel.as_posix() in PAYLOAD_EXCLUDES or _payload_skip(rel):
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise InputError(f"{rel.as_posix()}: unreadable payload file: {exc}") from exc
        lines.append(f"{digest}  {rel.as_posix()}")
    lines.sort()
    joined = "\n".join(lines) + "\n"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def payload_digest(root: Path, rev: str | None) -> str:
    """Digest of the bundled payload at ``rev``, or of the working tree (11.3).

    ``rev`` is materialised with ``git archive`` into a temporary directory - the
    tree is never checked out. ``rev=None`` reads ``root`` in place, which is also
    how the unpacked npm tarball is hashed.
    """
    root = Path(root)
    if rev is None:
        return _digest_of_tree(root)
    blob = _git_bytes(root, "archive", str(rev))
    with tempfile.TemporaryDirectory(prefix="release-consistency-") as tmp:
        archive_path = Path(tmp) / "payload.tar"
        archive_path.write_bytes(blob)
        destination = Path(tmp) / "tree"
        destination.mkdir()
        try:
            with tarfile.open(archive_path) as archive:
                _extract_tar(archive, destination)
        except (tarfile.TarError, OSError) as exc:
            raise InputError(f"git archive {rev}: {exc}") from exc
        return _digest_of_tree(destination)


def _tarball_payload_digest(blob: bytes) -> str:
    """Digest of an npm tarball's shipped payload, on the payload's own paths.

    11.2.3 publishes the tarball as ``package/skills/teamwork/`` plus the pi-native
    layer ``package/skills/teamwork-pi/`` and ``package/prompts/`` (see
    ``build_pi_package.copy_skill``). A tag tree keeps that layer under
    ``templates/pi-package/``. The paths are therefore *mapped back* to the
    repository's payload layout before hashing - without the map a tag tree and a
    tarball can never share a digest, and 11.5's worked examples would be
    unreachable. Everything outside the mapping (``package/package.json``,
    ``package/README.md``, the notices) is not bundled payload and is ignored.
    """
    with tempfile.TemporaryDirectory(prefix="release-npm-") as tmp:
        archive_path = Path(tmp) / "package.tgz"
        archive_path.write_bytes(blob)
        destination = Path(tmp) / "unpacked"
        destination.mkdir()
        try:
            with tarfile.open(archive_path) as archive:
                _extract_tar(archive, destination)
        except (tarfile.TarError, OSError) as exc:
            raise InputError(f"npm tarball: {exc}") from exc
        package = destination / "package"
        if not package.is_dir():
            raise InputError("npm tarball: no package/ subtree")
        # A staging root that mirrors the repository layout, so the digest is
        # computed on payload-relative paths exactly as 11.3 requires.
        staged = Path(tmp) / "payload"
        staged.mkdir()
        mapped = 0
        for source_prefix, payload_prefix in TARBALL_LAYOUT:
            base = package / source_prefix
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                target = staged / payload_prefix / path.relative_to(base)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
                mapped += 1
        if not mapped:
            raise InputError("npm tarball: none of the shipped payload paths are present")
        return _digest_of_tree(staged)


# --------------------------------------------------------------------------- #
# Local facts
# --------------------------------------------------------------------------- #


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    match = SEMVER.match(version)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _read_version(repo_root: Path, rev: str | None = None) -> str | None:
    """``__version__`` at ``rev``, or in the working tree when ``rev`` is None."""
    if rev is None:
        try:
            text = (Path(repo_root) / VERSION_PATH).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise InputError(f"{VERSION_PATH}: {exc}") from exc
    else:
        shown = _git(repo_root, "show", f"{rev}:{VERSION_PATH}", missing_ok=True)
        if shown is None:
            return None
        text = shown
    match = VERSION_ASSIGN.search(text)
    return match.group(1) if match else None


def _dist_name(repo_root: Path) -> str | None:
    text: str | None = None
    try:
        text = (Path(repo_root) / VERSION_PATH).read_text(encoding="utf-8")
    except OSError:
        text = None
    if text is not None:
        match = DIST_NAME_ASSIGN.search(text)
        if match:
            return match.group(1)
    return _pyproject_name(repo_root)


def _pyproject_section(repo_root: Path, section: str) -> list[str]:
    try:
        text = (Path(repo_root) / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return []
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            inside = stripped == section
            continue
        if inside and stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _pyproject_name(repo_root: Path) -> str | None:
    inside = False
    for line in _pyproject_section(repo_root, "[project]"):
        if inside:
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            return value or None
        if line.startswith("name") and "=" in line:
            inside = True
    return None


def _console_scripts(repo_root: Path) -> list[str]:
    scripts: list[str] = []
    for line in _pyproject_section(repo_root, "[project.scripts]"):
        if "=" not in line:
            continue
        name = line.split("=", 1)[0].strip().strip('"').strip("'")
        if name:
            scripts.append(name)
    return scripts


def _version_tags(repo_root: Path) -> list[str]:
    listed = _git(repo_root, "tag", "-l") or ""
    tags = [line.strip() for line in listed.splitlines() if VERSION_TAG.match(line.strip())]

    def sort_key(tag: str) -> tuple[int, int, int]:
        return _version_tuple(tag[1:]) or (0, 0, 0)

    return sorted(tags, key=sort_key)


def _all_tags(repo_root: Path) -> list[str]:
    """Every tag name, unfiltered - R4 compares release names against this."""
    listed = _git(repo_root, "tag", "-l") or ""
    return [line.strip() for line in listed.splitlines() if line.strip()]


def markdown_paths(repo_root: Path, globs: Sequence[str] = ("*.md",)) -> list[str]:
    """Tracked markdown, read from the working tree, minus historical evidence.

    ``docs/Team/Archive.md`` is out of scope for every scanner (11.2.4), and a
    tracked path that no longer exists on disk is skipped rather than drifted.
    """
    listed = _git(repo_root, "ls-files", "--", *globs) or ""
    found: list[str] = []
    for line in listed.splitlines():
        rel = line.strip()
        if not rel or rel == SCAN_EXCLUDED:
            continue
        if globs != ("*.md",) and not any(fnmatch.fnmatchcase(rel, glob) for glob in globs):
            continue
        if not (Path(repo_root) / rel).is_file():
            continue
        found.append(rel)
    return found


@dataclass(frozen=True)
class _MarkedLine:
    number: int
    text: str
    exempted: bool
    block: str


def _marked_lines(text: str, marker: str = ILLUSTRATIVE) -> list[_MarkedLine]:
    """Split text into lines, resolving the fence-aware marker reach of 11.2.4.

    A marker on a physical line exempts that line; a marker standing on a line of
    its own immediately above the opening fence exempts the whole fenced block.
    """
    raw = text.splitlines()
    blocks: dict[int, tuple[int, int]] = {}
    index = 0
    while index < len(raw):
        opened = FENCE_OPEN.match(raw[index].lstrip())
        if not opened:
            index += 1
            continue
        fence = opened.group(1)
        end = index
        for probe in range(index + 1, len(raw)):
            closing = FENCE_OPEN.match(raw[probe].lstrip())
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence):
                end = probe
                break
        else:
            end = len(raw) - 1
        for line_no in range(index, end + 1):
            blocks[line_no] = (index, end)
        index = end + 1

    marked: list[_MarkedLine] = []
    for line_no, line in enumerate(raw):
        block = ""
        exempted = marker in line
        if line_no in blocks:
            start, end = blocks[line_no]
            block = "\n".join(raw[start : end + 1])
            if start > 0 and raw[start - 1].strip() == marker:
                exempted = True
        marked.append(_MarkedLine(line_no + 1, line, exempted, block))
    return marked


# --------------------------------------------------------------------------- #
# The exception record (11.4)
# --------------------------------------------------------------------------- #


def load_exceptions(path: Path) -> list[dict[str, str]]:
    """Read and validate ``release-exceptions.json``; any problem is exit 2."""
    where = str(path)
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"{where}: missing (the initial state is an empty array)") from exc
    except OSError as exc:
        raise InputError(f"{where}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError(f"{where}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise InputError(f"{where}: top level must be a JSON array")
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(data):
        label = f"{where}: entry {index}"
        if not isinstance(entry, dict):
            raise InputError(f"{label}: must be a JSON object")
        keys = set(entry)
        extra = sorted(keys - set(EXCEPTION_KEYS))
        missing = [key for key in EXCEPTION_KEYS if key not in keys]
        if extra:
            raise InputError(f"{label}: unknown key(s) {', '.join(extra)}")
        if missing:
            raise InputError(f"{label}: missing key(s) {', '.join(missing)}")
        version = entry["version"]
        if not isinstance(version, str) or not SEMVER.match(version):
            raise InputError(f"{label}: version {version!r} is not X.Y.Z")
        if version in seen:
            raise InputError(f"{label}: duplicate version {version}")
        seen.add(version)
        for key in ("reason", "evidence"):
            value = entry[key]
            if not isinstance(value, str) or not value.strip():
                raise InputError(f"{label}: {key} is empty - a reviewer cannot judge it")
        recorded = entry["recorded"]
        if not isinstance(recorded, str) or not ISO_DATE.match(recorded):
            raise InputError(f"{label}: recorded {recorded!r} is not YYYY-MM-DD")
        entries.append({key: str(entry[key]) for key in EXCEPTION_KEYS})
    return entries


def _exception_notes(exceptions: Iterable[dict[str, str]]) -> list[str]:
    return [f"{entry['version']} admitted by exception ({entry['reason']})" for entry in exceptions]


def _stale_exceptions(exceptions: Iterable[dict[str, str]], tags: Sequence[str]) -> list[str]:
    """An exception for a version that *is* traceable is drift, not a pass."""
    findings: list[str] = []
    tag_set = set(tags)
    for entry in exceptions:
        version = entry["version"]
        if f"v{version}" in tag_set:
            findings.append(
                f"{version}: exception names a traceable version, tag v{version} exists; "
                f"remove the entry"
            )
    return findings


# --------------------------------------------------------------------------- #
# R1 / R2 - the tag and the local version string
# --------------------------------------------------------------------------- #


def rule_r1_tagged_version(repo_root: Path) -> RuleResult:
    """Every ``vX.Y.Z`` tag must carry that version in ``version.py`` at its commit."""
    tags = _version_tags(repo_root)
    findings: list[str] = []
    agreed = 0
    for tag in tags:
        wanted = tag[1:]
        actual = _read_version(repo_root, tag)
        if actual is None:
            findings.append(f"{tag}: {VERSION_PATH} missing at the tag or has no __version__")
        elif _version_tuple(actual) is None:
            findings.append(f"{tag}: __version__ {actual!r} is not X.Y.Z")
        elif actual != wanted:
            findings.append(f"{tag}: __version__ {actual} != tag version {wanted}")
        else:
            agreed += 1
    if findings:
        return _drift("R1", findings)
    return _ok("R1", f"{agreed} tag(s) agree with version.py")


def rule_r2_head_is_newer(repo_root: Path) -> RuleResult:
    """HEAD's version must be strictly greater than every tagged version."""
    head = _read_version(repo_root)
    if head is None:
        raise InputError(f"{VERSION_PATH}: no __version__ at HEAD")
    head_tuple = _version_tuple(head)
    if head_tuple is None:
        raise InputError(f"{VERSION_PATH}: __version__ {head!r} is not X.Y.Z")
    tags = _version_tags(repo_root)
    findings: list[str] = []
    for tag in tags:
        tagged = _version_tuple(tag[1:])
        if tagged is not None and not head_tuple > tagged:
            findings.append(f"HEAD version {head} is not greater than tag {tag}")
    if findings:
        return _drift("R2", findings)
    return _ok("R2", f"HEAD {head} is newer than {len(tags)} tag(s)")


# --------------------------------------------------------------------------- #
# R3 / R4 / R5 / R8 - the published half
# --------------------------------------------------------------------------- #


def rule_r3_npm_payloads(
    repo_root: Path,
    exceptions: Sequence[dict[str, str]] = (),
    fetch: Callable[[str], Any] | None = None,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> RuleResult:
    """Every npm version must equal a tagged payload digest, or be admitted (11.2.3)."""
    tags = _version_tags(repo_root)
    admitted = {entry["version"] for entry in exceptions}
    notes = _exception_notes(exceptions)
    findings = _stale_exceptions(exceptions, tags)

    if fetch is None:
        notes = ["offline: npm registry not queried"] + notes
        if findings:
            return _drift("R3", findings, notes)
        return _skip("R3", "; ".join(notes))

    try:
        data = fetch(NPM_REGISTRY)
    except InputError as exc:
        return _skip("R3", f"online: npm registry unreadable: {exc}", fatal=True)
    versions = data.get("versions") if isinstance(data, dict) else None
    if not isinstance(versions, dict):
        return _skip("R3", f"online: {NPM_REGISTRY} has no versions object", fatal=True)

    get_bytes = fetch_bytes if fetch_bytes is not None else _http_get_bytes
    matched = 0
    ignored: list[str] = []
    unreadable: list[str] = []
    for version in sorted(versions, key=lambda item: _version_tuple(str(item)) or (0, 0, 0)):
        if _version_tuple(str(version)) is None:
            ignored.append(str(version))
            continue
        if version in admitted:
            continue
        info = versions[version]
        dist = info.get("dist") if isinstance(info, dict) else None
        tarball = dist.get("tarball") if isinstance(dist, dict) else None
        if not isinstance(tarball, str) or not tarball:
            findings.append(f"{version}: npm record has no dist.tarball")
            continue
        try:
            digest = _tarball_payload_digest(get_bytes(tarball))
        except HttpError as exc:
            # A 404 is the registry's own answer that the tarball it advertises
            # does not exist - the release is missing, so it is drift. Anything
            # else (5xx, timeout, URL error) is unreadable input: exit 2, so a
            # network flake can never be mistaken for a release defect.
            if exc.status == 404:
                findings.append(f"{version}: tarball {tarball} is missing: {exc}")
            else:
                unreadable.append(f"{version}: tarball unreadable: {exc}")
            continue
        except InputError as exc:
            unreadable.append(f"{version}: tarball unreadable: {exc}")
            continue
        tag = f"v{version}"
        if tag not in tags:
            findings.append(f"{version}: no tag {tag} to compare; tarball payload digest {digest}")
            continue
        try:
            local = payload_digest(repo_root, tag)
        except InputError as exc:
            unreadable.append(f"{version}: {exc}")
            continue
        if local == digest:
            matched += 1
        else:
            findings.append(
                f"{version}: tarball payload digest {digest} != payload {local} at {tag}"
            )
    if ignored:
        notes.append(f"ignored non-X.Y.Z npm version(s): {', '.join(sorted(ignored))}")
    if unreadable:
        return _unreadable("R3", findings, notes, "; ".join(unreadable))
    if findings:
        return _drift("R3", findings, notes)
    return _ok(
        "R3",
        "; ".join([f"{matched} npm version(s) match a tagged payload digest"] + notes),
    )


def _github_release_names(data: object) -> list[str]:
    if not isinstance(data, list):
        raise InputError("GitHub releases: response is not a JSON array")
    names: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        for key in ("tag_name", "name"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
                break
    return names


def rule_r4_releases_have_tags(
    repo_root: Path, fetch: Callable[[str], Any] | None = None
) -> RuleResult:
    """Every GitHub Release must name a tag the repository has.

    The comparison set is the whole of ``git tag -l``, not the ``vX.Y.Z`` subset:
    11.2.4's version-tag filter is R1/R2/R5's, and a pre-release tag such as
    ``v1.1.3-rc1`` is a tag a release may legitimately carry. Filtering it out
    here would report an existing tag as missing.
    """
    tags = _all_tags(repo_root)
    if fetch is None:
        return _skip("R4", f"offline: GitHub releases API not queried; {len(tags)} tag(s) local")
    try:
        names = _github_release_names(fetch(GITHUB_RELEASES))
    except InputError as exc:
        return _skip("R4", f"online: GitHub API unreadable: {exc}", fatal=True)
    tag_set = set(tags)
    findings = [
        f"release {name} has no tag {name} in git tag -l" for name in names if name not in tag_set
    ]
    if findings:
        return _drift("R4", findings)
    return _ok("R4", f"{len(names)} release(s) name an existing tag")


def rule_r5_tags_have_releases(
    repo_root: Path, fetch: Callable[[str], Any] | None = None
) -> RuleResult:
    """Every tag must have exactly the GitHub Release that publishes it."""
    tags = _version_tags(repo_root)
    if fetch is None:
        return _skip(
            "R5",
            f"offline: GitHub releases API not queried; cannot confirm {len(tags)} tag(s) are released",
        )
    try:
        names = set(_github_release_names(fetch(GITHUB_RELEASES)))
    except InputError as exc:
        return _skip("R5", f"online: GitHub API unreadable: {exc}", fatal=True)
    findings = [f"tag {tag} has no GitHub Release" for tag in tags if tag not in names]
    if findings:
        return _drift("R5", findings)
    return _ok("R5", f"{len(tags)} tag(s) have a GitHub Release")


def _channel_claims(line: str) -> list[tuple[str, str | None]]:
    """``(distribution, executable-or-None)`` claims on one line (11.2.4)."""
    if _negated_install(line):
        return []
    claims: list[tuple[str, str | None]] = []
    for pattern in (PIP_MODULE, PIP_PLAIN, PIPX):
        for match in pattern.finditer(line):
            name = _clean_distribution(match.group(1))
            if name:
                claims.append((name, None))
    for pattern in (UVX_FROM, PIPX_RUN):
        for match in pattern.finditer(line):
            name = _clean_distribution(match.group(1))
            if name:
                claims.append((name, _trailing_script(line, match.end())))
    return claims


def _trailing_script(line: str, start: int) -> str | None:
    """The console script after ``uvx --from <dist>`` / ``pipx run --spec <dist>``.

    Only a real argument counts: ``uvx --from teamwork-agents is the fastest way
    to try it`` continues as prose, and reading ``is`` as an executable would
    report a drift the text never claimed.
    """
    match = SCRIPT_ARGUMENT.match(line, start)
    if not match:
        return None
    return match.group(1).strip() or None


def _clean_distribution(token: str) -> str | None:
    """Reduce a pip/pipx/uvx package token to a distribution name, or ``None``.

    A local path (``pip install .``, ``pip install -e ".[dev]"``) and a
    placeholder (``pip install <wheel>``) name no published distribution, so
    they are not channel claims. What survives is a PEP 503 name.
    """
    name = token.strip().strip("\"'`").strip()
    for stop in ("==", ">=", "<=", "!=", "~=", "[", ";", ","):
        name = name.split(stop, 1)[0]
    name = name.strip().strip("\"'`")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        return None
    return name


def _negated_install(line: str) -> bool:
    """A sentence that says there is *no* install channel advertises nothing.

    11.2.4 scopes R8 to markdown that *advertises* a channel; ``there is no pip
    install and no venv`` (CHANGELOG.md, SKILL.md) states the opposite, and so
    does ``no uvx --from ...`` or ``never pipx run ...``.
    """
    return bool(NEGATED_CHANNEL.search(line))


def rule_r8_install_channels(
    repo_root: Path, fetch: Callable[[str], Any] | None = None
) -> RuleResult:
    """Install-channel prose must name what this repository ships (11.2.4)."""
    dist_name = _dist_name(repo_root)
    scripts = _console_scripts(repo_root)
    findings: list[str] = []
    claimed = 0
    marked = 0
    unmarked_lines: list[str] = []
    for rel in markdown_paths(repo_root):
        try:
            text = (Path(repo_root) / rel).read_text(encoding="utf-8")
        except OSError as exc:
            raise InputError(f"{rel}: {exc}") from exc
        for line in _marked_lines(text, CHANNEL_UNAVAILABLE):
            if line.exempted and _channel_claims(line.text):
                marked += 1
            for name, executable in _channel_claims(line.text):
                claimed += 1
                where = f"{rel}:{line.number}"
                if dist_name is None:
                    findings.append(
                        f"{where}: cannot verify {name}, no DIST_NAME in {VERSION_PATH}"
                    )
                elif name != dist_name:
                    findings.append(f"{where}: channel names {name}, the project ships {dist_name}")
                elif executable and executable not in scripts:
                    findings.append(
                        f"{where}: channel runs {executable}, which is not a "
                        f"[project.scripts] entry"
                    )
                elif not line.exempted:
                    unmarked_lines.append(where)

    if fetch is None:
        notes = [
            f"offline: PyPI not queried; {claimed} channel line(s), "
            f"{marked} marked channel-unavailable"
        ]
        if findings:
            return _drift("R8", findings, notes)
        if dist_name is None:
            return _skip(
                "R8", f"cannot read DIST_NAME from {VERSION_PATH}; channel names unverifiable"
            )
        return _skip("R8", "; ".join(notes))

    try:
        fetch(PYPI_JSON)
        published = True
        reason = "HTTP 200"
    except HttpError as exc:
        if exc.status == 404:
            published = False
            reason = "HTTP 404"
        else:
            return _skip("R8", f"online: PyPI unreadable: {exc}", fatal=True)
    except InputError as exc:
        return _skip("R8", f"online: PyPI unreadable: {exc}", fatal=True)
    if published:
        if findings:
            return _drift("R8", findings, [f"PyPI {reason}"])
        return _ok(
            "R8",
            f"PyPI {reason}; {claimed} channel line(s) resolve, {marked} marked",
        )
    for where in unmarked_lines:
        findings.append(f"{where}: PyPI {reason}, the channel does not resolve and is unmarked")
    if findings:
        return _drift("R8", findings)
    return _ok("R8", f"PyPI {reason}; {marked} channel line(s) marked channel-unavailable")


# --------------------------------------------------------------------------- #
# R6 / R7 / R9 - the committed prose
# --------------------------------------------------------------------------- #


def _project_tokens(text: str) -> list[re.Match[str]]:
    """Version tokens that name this project, per 11.2.4's foreign-tool rule."""
    foreign = {match.span(1) for match in FOREIGN_VERSION.finditer(text)}
    return [match for match in VERSION_TOKEN.finditer(text) if match.span(1) not in foreign]


def rule_r6_markdown_versions(repo_root: Path) -> RuleResult:
    """Prose must not print a project version older than HEAD (11.2.4)."""
    head = _read_version(repo_root)
    if head is None:
        raise InputError(f"{VERSION_PATH}: no __version__ at HEAD")
    head_tuple = _version_tuple(head)
    if head_tuple is None:
        raise InputError(f"{VERSION_PATH}: __version__ {head!r} is not X.Y.Z")
    findings: list[str] = []
    illustrative = 0
    for rel in markdown_paths(repo_root, R6_GLOBS):
        try:
            text = (Path(repo_root) / rel).read_text(encoding="utf-8")
        except OSError as exc:
            raise InputError(f"{rel}: {exc}") from exc
        for line in _marked_lines(text):
            about_project = bool(
                PROJECT_CONTEXT.search(line.text) or PROJECT_CONTEXT.search(line.block)
            )
            tokens = list(_project_tokens(line.text)) if about_project else []
            if tokens and line.exempted:
                illustrative += 1
                continue
            for match in tokens:
                printed = _version_tuple(match.group(1))
                if printed is not None and printed < head_tuple:
                    findings.append(
                        f"{rel}:{line.number}: prints {match.group(0)}, older than HEAD {head}"
                    )
    if findings:
        return _drift("R6", findings, [f"{illustrative} illustrative"])
    return _ok("R6", f"no version older than {head}; {illustrative} illustrative")


def rule_r7_changelog(repo_root: Path) -> RuleResult:
    """Every tagged version needs exactly one ``## [X.Y.Z]`` section in CHANGELOG.md."""
    path = Path(repo_root) / "CHANGELOG.md"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise InputError("CHANGELOG.md: missing") from None
    except OSError as exc:
        raise InputError(f"CHANGELOG.md: {exc}") from exc
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = CHANGELOG_HEADING.match(line)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    findings: list[str] = []
    covered = 0
    for tag in _version_tags(repo_root):
        version = tag[1:]
        found = counts.get(version, 0)
        if found == 0:
            findings.append(f"{tag} has no '## [{version}]' section")
        elif found > 1:
            findings.append(f"{tag} has {found} '## [{version}]' sections")
        else:
            covered += 1
    if findings:
        return _drift("R7", findings)
    return _ok("R7", f"{covered} tagged version(s) have exactly one CHANGELOG.md section")


def rule_r9_markdown_tags(repo_root: Path) -> RuleResult:
    """Every ``vX.Y.Z`` token in committed markdown must name a real tag (11.2.4)."""
    tag_names = {line.strip() for line in (_git(repo_root, "tag", "-l") or "").splitlines()}
    findings: list[str] = []
    illustrative = 0
    for rel in markdown_paths(repo_root):
        try:
            text = (Path(repo_root) / rel).read_text(encoding="utf-8")
        except OSError as exc:
            raise InputError(f"{rel}: {exc}") from exc
        for line in _marked_lines(text):
            tokens = list(TAGGED_TOKEN.finditer(line.text))
            if line.exempted and tokens:
                illustrative += 1
                continue
            for match in tokens:
                tag = f"v{match.group(1)}"
                if tag not in tag_names:
                    findings.append(f"{rel}:{line.number}: names {tag}, which is not a tag")
    if findings:
        return _drift("R9", findings, [f"{illustrative} illustrative"])
    return _ok("R9", f"every vX.Y.Z token names a tag; {illustrative} illustrative")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def _all_skip(reason: str) -> list[RuleResult]:
    return [
        _skip(rule, reason, fatal=True)
        for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")
    ]


def _run_rule(rule: str, call: Callable[[], RuleResult]) -> RuleResult:
    try:
        return call()
    except InputError as exc:
        return _skip(rule, str(exc), fatal=True)
    except (OSError, ValueError) as exc:
        return _skip(rule, f"{type(exc).__name__}: {exc}", fatal=True)


def _emit(results: Sequence[RuleResult], as_json: bool) -> int:
    problems = [
        {"rule": result.rule, "detail": finding}
        for result in results
        for finding in result.findings
        if result.status == "DRIFT"
    ]
    exit_code = 2 if any(result.fatal for result in results) else (1 if problems else 0)
    if as_json:
        payload = {
            "problems": problems,
            "rules": [
                {"id": result.rule, "status": result.status, "detail": result.detail}
                for result in results
            ],
            "exit_code": exit_code,
        }
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return exit_code
    for result in results:
        print(f"{result.rule} {result.status} {result.detail}")
    print(f"# release consistency: {len(problems)} problem(s)")
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_release_consistency.py",
        description="Prove that every published version claim agrees with the local one. "
        "Read-only; runs offline unless --online is given.",
    )
    parser.add_argument(
        "--offline", action="store_true", help="open no socket (the default when no flag is given)"
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="query npm, the GitHub API and PyPI for the published half of R3/R4/R5/R8",
    )
    parser.add_argument("--json", action="store_true", help="emit the JSON object of 11.1.3")
    parser.add_argument(
        "--exceptions",
        metavar="PATH",
        default=None,
        help="exception record (default: <repo-root>/release-exceptions.json)",
    )
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        default=None,
        help="git work tree top level to check (default: current directory)",
    )
    args = parser.parse_args(argv)

    if args.offline and args.online:
        print(
            "# check_release_consistency: --offline and --online are mutually exclusive",
            file=sys.stderr,
        )
        return 2

    repo_root = _git_root(args.repo_root)
    if repo_root is None:
        reason = (
            f"not a git work tree top level: {args.repo_root or Path.cwd()} "
            f"(git rev-parse --show-toplevel does not normalise to it)"
        )
        return _emit(_all_skip(reason), args.json)

    exceptions_path = (
        Path(args.exceptions)
        if args.exceptions and Path(args.exceptions).is_absolute()
        else repo_root / (args.exceptions or "release-exceptions.json")
    )
    exceptions: list[dict[str, str]] = []
    exceptions_error: str | None = None
    try:
        exceptions = load_exceptions(exceptions_path)
    except InputError as exc:
        exceptions_error = str(exc)

    fetch = _http_get_json if args.online else None
    fetch_bytes = _http_get_bytes if args.online else None

    results: list[RuleResult] = [
        _run_rule("R1", lambda: rule_r1_tagged_version(repo_root)),
        _run_rule("R2", lambda: rule_r2_head_is_newer(repo_root)),
        _run_rule(
            "R3",
            lambda: (
                _skip(
                    "R3",
                    f"{exceptions_error}; npm versions cannot be admitted or compared",
                    fatal=True,
                )
                if exceptions_error
                else rule_r3_npm_payloads(repo_root, exceptions, fetch, fetch_bytes)
            ),
        ),
        _run_rule("R4", lambda: rule_r4_releases_have_tags(repo_root, fetch)),
        _run_rule("R5", lambda: rule_r5_tags_have_releases(repo_root, fetch)),
        _run_rule("R6", lambda: rule_r6_markdown_versions(repo_root)),
        _run_rule("R7", lambda: rule_r7_changelog(repo_root)),
        _run_rule("R8", lambda: rule_r8_install_channels(repo_root, fetch)),
        _run_rule("R9", lambda: rule_r9_markdown_tags(repo_root)),
    ]
    return _emit(results, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
