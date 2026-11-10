#!/usr/bin/env python3
"""Assemble the pi package from this repository.

Why a build step: the repository root *is* the skill (``SKILL.md`` at the root,
referenced by ``scripts/teamwork.py`` and the pip package), while pi discovers
skills as ``<root>/<name>/SKILL.md``. Copying the skill into the published tree at
build time keeps one source of truth in git and one conventional layout in the
tarball, instead of maintaining two copies of every reference file.

Usage: ``python3 scripts/build_pi_package.py [--out dist]``
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "pi-teamwork"
# Files the skill needs at runtime; tests, docs and build output stay out of the tarball.
SKILL_TREES = ("references", "roles", "templates", "scripts", "src")
SKILL_FILES = ("SKILL.md", "AGENTS.md")
TARBALL_FILES = ("README.md", "LICENSE", "NOTICE", "CHANGELOG.md", "SECURITY.md")


def version() -> str:
    """The single source is ``src/teamwork/version.py``; pyproject reads it too."""
    text = (ROOT / "src" / "teamwork" / "version.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("no __version__ in src/teamwork/version.py")


def package_json(ver: str) -> dict:
    return {
        "name": NAME,
        "version": ver,
        "description": (
            "Run a user prompt to completion with an autonomous multi-agent team on pi: "
            "CEO-led decomposition, parallel lanes, two-stage review, hash-chained audit "
            "ledger, layered role-owned tests."
        ),
        "keywords": [
            "pi-package",
            "pi",
            "pi-coding-agent",
            "teamwork",
            "multi-agent",
            "orchestration",
            "agents",
            "skill",
        ],
        "license": "AGPL-3.0-or-later",
        "homepage": "https://pi.dev/packages",
        "repository": {"type": "git", "url": "https://github.com/Nidvue/Teamwork"},
        # everything the runtime needs lives under skills/ and prompts/; the
        # licence and the notices must ship too, or npm drops them silently
        "files": [
            "skills",
            "prompts",
            "README.md",
            "LICENSE",
            "NOTICE",
            "CHANGELOG.md",
            "SECURITY.md",
        ],
        "pi": {
            "skills": ["./skills"],
            "prompts": ["./prompts"],
        },
        # Host-provided packages are peers, never dependencies: a physical copy
        # bypasses pi's module mapping and duplicates registries (docs/packages.md).
        "peerDependencies": {
            "@earendil-works/pi-ai": "*",
            "@earendil-works/pi-agent-core": "*",
            "@earendil-works/pi-coding-agent": "*",
            "@earendil-works/pi-tui": "*",
            "typebox": "*",
        },
        "peerDependenciesMeta": {
            "@earendil-works/pi-ai": {"optional": True},
            "@earendil-works/pi-agent-core": {"optional": True},
            "@earendil-works/pi-coding-agent": {"optional": True},
            "@earendil-works/pi-tui": {"optional": True},
            "typebox": {"optional": True},
        },
        "engines": {"node": ">=20"},
    }


def copy_skill(dest: Path) -> None:
    skill = dest / "skills" / "teamwork"
    skill.mkdir(parents=True)
    for name in SKILL_FILES:
        shutil.copy2(ROOT / name, skill / name)
    for name in SKILL_TREES:
        shutil.copytree(
            ROOT / name,
            skill / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info", "pi-package"),
        )
    # the pi-native layer, shipped beside the portable skill
    shutil.copytree(
        ROOT / "templates" / "pi-package" / "skills" / "teamwork-pi",
        skill.parent / "teamwork-pi",
    )
    shutil.copytree(ROOT / "templates" / "pi-package" / "prompts", dest / "prompts")


def copy_docs(dest: Path) -> None:
    for name in TARBALL_FILES:
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, dest / name)


def main(argv: list[str]) -> int:
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "dist"
    dest = out / NAME
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ver = version()
    Path(dest / "package.json").open("w", encoding="utf-8", newline="\n").write(
        json.dumps(package_json(ver), indent=2, ensure_ascii=False) + "\n"
    )
    copy_skill(dest)
    copy_docs(dest)
    manifest = json.loads((dest / "package.json").read_text(encoding="utf-8"))
    missing = [p for p in json.loads(json.dumps(manifest["pi"])).values() for p in p]
    absent = [p for p in missing if not (dest / p.lstrip("./")).exists()]
    if absent:
        print(f"missing declared resources: {absent}", file=sys.stderr)
        return 1
    sized = subprocess.run(
        ["du", "-sh", str(dest)], capture_output=True, text=True, check=False
    ).stdout.split()[0]
    print(f"built {dest} ({NAME} {ver}, {sized})")
    print("next: npm pack --dry-run --json  (inside the built directory) and pi -e ./dist/" + NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
