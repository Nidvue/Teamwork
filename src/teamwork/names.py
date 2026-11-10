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


def git_identity_args(role: str) -> list:
    name, email = role_identity(role)
    return ["-c", f"user.name={name}", "-c", f"user.email={email}"]
