"""Names, roles and commit identities."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .config import IDENTITY_DOMAIN

ROLE_DISPLAY = {
    "ceo": "CEO",
    "cto": "CTO",
    "coo": "COO",
    "cfo": "CFO",
    "architect": "Architect",
    "product-manager": "Product Manager",
    "project-manager": "Project Manager",
    "designer": "Designer",
    "developer": "Developer",
    "tester": "Tester",
    "reviewer": "Reviewer",
    "security-auditor": "Security Auditor",
    "release-engineer": "Release Engineer",
    "technical-writer": "Technical Writer",
    "data-engineer": "Data Engineer",
    "team-leader": "Team Leader",
}

ACRONYMS = {
    "ceo": "CEO",
    "cto": "CTO",
    "coo": "COO",
    "cfo": "CFO",
    "pm": "PM",
    "qa": "QA",
    "ui": "UI",
    "ux": "UX",
    "api": "API",
}

ROLE_ALIASES = {
    "dev": "developer",
    "developer": "developer",
    "qa": "tester",
    "test": "tester",
    "tester": "tester",
    "design": "designer",
    "designer": "designer",
    "arch": "architect",
    "architect": "architect",
    "software-architect": "architect",
    "pm": "project-manager",
    "project-manager": "project-manager",
    "product-manager": "product-manager",
    "po": "product-manager",
    "ceo": "ceo",
    "cto": "cto",
    "rel": "release-engineer",
    "release-engineer": "release-engineer",
    "devops": "release-engineer",
    "sre": "release-engineer",
    "writer": "technical-writer",
    "tech-writer": "technical-writer",
    "technical-writer": "technical-writer",
    "docs": "technical-writer",
    "data": "data-engineer",
    "data-engineer": "data-engineer",
    "dba": "data-engineer",
    "coo": "coo",
    "cfo": "cfo",
    "reviewer": "reviewer",
    "security-auditor": "security-auditor",
    "team-leader": "team-leader",
}


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


_ALIAS_NORM = {_norm_key(k): v for k, v in ROLE_ALIASES.items()}


def pascal(name: str) -> str:
    """developer-2 -> Developer-2 ; product-manager -> ProductManager."""
    parts = [p for p in re.split(r"[-_\s]+", (name or "").strip()) if p]
    out = []
    for part in parts:
        low = part.lower()
        if low in ACRONYMS:
            out.append(ACRONYMS[low])
        elif part.isdigit():
            out.append(part)
        else:
            out.append(part[:1].upper() + part[1:])
    if len(out) > 1 and out[-1].isdigit():
        return "-".join(out[:-1]) + "-" + out[-1]
    return "".join(out) or "Team"


def safe_component(name: str) -> str:
    """A single filesystem path component derived from a user-supplied name.

    ``pascal`` is a display helper and deliberately preserves characters; a
    name such as ``../../escape`` must never turn into a path traversal when it
    becomes a directory or a slot filename. Normal names (``Developer-1``,
    ``ProductManager``) are unchanged.
    """
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "")).strip(".-")
    return text[:80] or "Team"


def slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:limit].rstrip("-") or "work"


def one_line(value, limit: int = 0) -> str:
    """Collapse every newline/run of whitespace so a value cannot inject a
    second markdown metadata line (and therefore a forged gate state)."""
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() if limit else text


def clip(text, limit: int = 600) -> str:
    """Shorten free text for a machine view: ``head... (+N chars: --full)``.

    The records keep the whole value (Reviews.md, Ledger.jsonl and Archive.md are
    the trust boundary and are never rewritten here); a *listing* only needs
    enough to triage from, and a 10 KB findings line is what makes
    ``review --queue`` or ``archive`` expensive for an agent that has to read
    it. The marker states how many characters were omitted and the flag that
    shows them, so a clipped view can never hide evidence silently. Text of
    ``limit`` characters or fewer is returned unchanged - nothing was omitted,
    so there is no marker to add.
    """
    value = str(text or "")
    if len(value) <= limit:
        return value
    omitted = len(value) - limit
    return f"{value[:limit]}... (+{omitted} chars: --full)"


def body_text(value) -> str:
    """Body text that cannot forge a new record header.

    A body line beginning with ``##`` would otherwise be parsed as the next
    task/memory/dispute entry and could hide or duplicate state. The parser
    already stops reading metadata at the first blank line; this closes the
    remaining header-injection path while keeping the body readable.
    """
    lines = str(value or "").strip().splitlines()
    return "\n".join((" " + line) if re.match(r"^##\s", line) else line for line in lines)


def team_slug(project: Path, explicit: str = "") -> str:
    raw = explicit or os.environ.get("TEAMWORK_TEAM") or project.name
    return pascal(re.sub(r"[^A-Za-z0-9_-]+", "-", raw)) or "Team"


def resolve_role(name: str) -> str:
    """Map any spelling to the canonical role slug.

    Accepts instance names, PascalCase directory names and aliases:
    Developer-2 -> developer, ProductManager -> product-manager, dev -> developer.
    """
    raw = (name or "").strip()
    n = _norm_key(raw)
    if n in _ALIAS_NORM:
        return _ALIAS_NORM[n]
    n2 = re.sub(r"\d+$", "", n)
    if n2 in _ALIAS_NORM:
        return _ALIAS_NORM[n2]
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or raw.lower()


def role_identity(role: str) -> tuple:
    """('Developer', 'developer@agents.nidvue.com') - role based, never instance based."""
    slug = resolve_role(role)
    name = ROLE_DISPLAY.get(slug) or pascal(slug).replace("-", " ")
    email = re.sub(r"[^a-z0-9]", "", slug) + "@" + IDENTITY_DOMAIN
    return name, email


def identity_string(role: str) -> str:
    name, email = role_identity(role)
    return f"{name} <{email}>"


PRESET_NAME_KEY = "teamwork.identity.name"
PRESET_EMAIL_KEY = "teamwork.identity.email"


def preset_identity(project=None) -> tuple | None:
    """The host's ambient identity: the repository's local config, else global.

    This is what ``identity --audit`` accepts as the operator's own history, not
    what a new commit is authored with - ``commit_identity`` reads only the
    declared pair, because an ambient pair made every lane commit as whoever owns
    the machine (A-0012).
    """
    import subprocess

    def read(scope: str, key: str) -> str:
        try:
            return subprocess.run(
                ["git", "config", scope, key],
                cwd=str(project) if project else None,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except OSError:
            return ""

    def resolve(key: str) -> str:
        return read("--local", key) or read("--global", key)

    name, email = resolve("user.name"), resolve("user.email")
    if not (name and email):
        return None
    if email.lower().endswith("@" + IDENTITY_DOMAIN.lower()):
        return None
    return name, email


def declared_identity(project=None) -> tuple | None:
    """The identity the team declared for its own commits, else None.

    A repository that wants its commits authored by a person or a shared mailbox
    says so once - ``teamwork.identity.name`` and ``teamwork.identity.email`` - and
    both keys must be set. The ambient ``user.name``/``user.email`` is *not* a
    declaration: it is whatever machine the lane happens to run on, so reading it
    made every lane commit as the operator (A-0012) while the constitution says a
    commit carries the acting role's mailbox.
    """
    import subprocess

    def read(scope: str, key: str) -> str:
        try:
            return subprocess.run(
                ["git", "config", scope, key],
                cwd=str(project) if project else None,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except OSError:
            return ""

    name = read("--local", PRESET_NAME_KEY) or read("--global", PRESET_NAME_KEY)
    email = read("--local", PRESET_EMAIL_KEY) or read("--global", PRESET_EMAIL_KEY)
    if not (name and email):
        return None
    if email.lower().endswith("@" + IDENTITY_DOMAIN.lower()):
        return None
    return name, email


def commit_identity(role: str, project=None) -> tuple:
    """(name, email) a commit is authored with: declared pair first, role last."""
    declared = declared_identity(project)
    return declared if declared else role_identity(role)


def git_identity_args(role: str, project=None) -> list:
    name, email = commit_identity(role, project)
    return ["-c", f"user.name={name}", "-c", f"user.email={email}"]


def git_identity_env(role: str, project=None) -> dict:
    """The git variables a commit runs with, so no ambient pair can override it.

    ``-c user.name`` loses to an exported ``GIT_AUTHOR_NAME``, which a rebase, a
    forge runner or a wrapper shell leaves behind; the environment variables win
    over every config scope, so the identity is pinned for this one commit.
    """
    name, email = commit_identity(role, project)
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }
