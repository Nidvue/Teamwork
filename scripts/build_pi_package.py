#!/usr/bin/env python3
"""Assemble the pi package from this repository.

Why a build step: the repository root *is* the skill (``SKILL.md`` at the root,
referenced by ``scripts/teamwork.py`` and the pip package), while pi discovers
skills as ``<root>/<name>/SKILL.md``. Copying the skill into the published tree at
build time keeps one source of truth in git and one conventional layout in the
tarball, instead of maintaining two copies of every reference file.

Usage: ``python3 scripts/build_pi_package.py [--out dist]`` - ``--help`` is safe:
argument parsing happens before anything touches the filesystem, so a probe that
asks this script what it does can never leave a build behind.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "@nidvue/teamwork"
REPO_URL = "https://github.com/Nidvue/Teamwork"
REPO_BLOB = REPO_URL + "/blob/main/"
REPO_RAW = REPO_URL.replace("github.com", "raw.githubusercontent.com") + "/main/"
PREVIEW = REPO_RAW + "assets/social-preview.png"

# The bundle manifest is engine state, not a build-tool constant: the installed
# skill, the wheel and the tarball must contain the same files.
sys.path.insert(0, str(ROOT / "src"))
from teamwork import bundle as _bundle  # noqa: E402

# Files the skill needs at runtime; tests, docs and build output stay out of the tarball.
SKILL_TREES = ("references", "roles", "templates", "scripts", "src")
SKILL_FILES = ("SKILL.md", "AGENTS.md")
assert SKILL_FILES == _bundle.BUNDLE_FILES and SKILL_TREES == _bundle.BUNDLE_TREES, (
    "the pi package manifest drifted from teamwork.bundle"
)
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
            "Nidvue Teamwork - an autonomous, self-governing agent company for pi: "
            "CEO-led decomposition, parallel lanes, two-stage review, hash-chained audit "
            "ledger and layered role-owned tests. Python 3.9+, stdlib only."
        ),
        "keywords": [
            "pi-package",
            "pi",
            "pi-coding-agent",
            "nidvue",
            "teamwork",
            "multi-agent",
            "orchestration",
            "agents",
            "skill",
        ],
        "license": "AGPL-3.0-or-later",
        "author": {"name": "Nidvue contributors"},
        "homepage": REPO_URL,
        "repository": {"type": "git", "url": "git+" + REPO_URL + ".git"},
        "bugs": {"url": REPO_URL + "/issues"},
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
            # gallery preview; a URL, so the image never enters the tarball
            "image": PREVIEW,
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


def ship_readme(dest: Path) -> None:
    """Rewrite repo-relative links and images to absolute ones.

    The tarball ships the skill and the notices, not ``assets/`` or ``docs/``, so a
    relative reference that works in the repository renders broken on npm and in
    the pi gallery - both of which show this README.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    def keep(target: str) -> bool:
        return target.startswith(("http:", "https:", "#", "mailto:", "data:"))

    def absolute(match: re.Match[str]) -> str:
        target = match.group(2)
        if keep(target):
            return match.group(0)
        return f"[{match.group(1)}]({REPO_BLOB}{target.lstrip('./')})"

    def raw(match: re.Match[str]) -> str:
        target = match.group(2)
        if keep(target):
            return match.group(0)
        return f'{match.group(1)}"{REPO_RAW}{target.lstrip("./")}"'

    rewritten = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", absolute, text)
    rewritten = re.sub(r'(src=)"([^"]+)"', raw, rewritten)
    Path(dest / "README.md").open("w", encoding="utf-8", newline="\n").write(rewritten)


def copy_docs(dest: Path) -> None:
    for name in TARBALL_FILES:
        if name == "README.md":
            continue
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, dest / name)


def parser() -> argparse.ArgumentParser:
    """``argparse``, like every other script here: ``--help`` exits 0 and a
    malformed command line exits 2 with a usage line, neither of which builds.

    The hand-rolled ``argv.index("--out") + 1`` it replaces raised ``IndexError``
    on a bare ``--out`` and, worse, built on *any* invocation that parsed - so the
    CI probe that runs every workflow script with ``--help`` assembled a real
    package into ``dist/``.
    """
    p = argparse.ArgumentParser(
        prog="build_pi_package.py",
        description=(
            f"assemble the pi package (@nidvue/teamwork) from this repository, writing <out>/{NAME}"
        ),
    )
    p.add_argument(
        "--out",
        default="",
        metavar="DIR",
        help="directory to assemble into (default: <repository>/dist)",
    )
    return p


def main(argv: list[str]) -> int:
    args = parser().parse_args(argv)
    out = Path(args.out) if args.out else ROOT / "dist"
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
    ship_readme(dest)
    manifest = json.loads((dest / "package.json").read_text(encoding="utf-8"))
    # only the list-valued resources are paths on disk; ``pi.image`` is a URL
    declared = [p for v in manifest["pi"].values() if isinstance(v, list) for p in v]
    absent = [p for p in declared if not (dest / p.lstrip("./")).exists()]
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
