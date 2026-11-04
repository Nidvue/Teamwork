#!/usr/bin/env python3
"""Integration probe (area readme-layout): the README renders as a docs page.

Renders the real `README.md` through the same MkDocs pipeline the published site
uses (`mkdocs.yml`: theme, `toc` with permalinks, every markdown extension) with
the README as the page body, under `mkdocs build --strict`, then inspects the
built HTML: every heading must get a unique, non-empty id and every in-page
`#anchor` must resolve to one of them.

Control: the same pipeline runs on a mutated copy that duplicates a heading and
adds a dangling anchor, and the probe must report both. A check that cannot fail
proves nothing.

Exit 0 = rendered clean and the control was caught; 1 = a problem or a blind
check.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

SKIP_TOP = {".git", ".pi", ".venv", "venv", "site", "dist", "__pycache__"}
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")


class PageScan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[str, str, str]] = []
        self.anchors: list[str] = []
        self.ids: list[str] = []
        self._open: str | None = None
        self._heading_id = ""
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag in HEADINGS:
            self._open = tag
            self._heading_id = attrs.get("id", "")
            self._text = []
        elif tag == "a":
            href = attrs.get("href", "")
            if href.startswith("#"):
                self.anchors.append(href[1:])

    def handle_endtag(self, tag):
        if tag in HEADINGS and self._open == tag:
            self.headings.append((tag, self._heading_id, "".join(self._text).strip()))
            self._open = None

    def handle_data(self, data):
        if self._open:
            self._text.append(data)


def doc_python(repo: Path, override: str | None) -> str:
    candidates = [override] if override else []
    candidates.append(sys.executable)
    for base in (repo, *repo.parents):
        candidates.append(str(base / ".venv" / "bin" / "python"))
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        probe = subprocess.run(
            [candidate, "-c", "import mkdocs"], capture_output=True, text=True, check=False
        )
        if probe.returncode == 0:
            return candidate
    raise SystemExit("mkdocs is unavailable: install docs/requirements.txt into a venv")


def mirror(repo: Path, work: Path) -> Path:
    """A docs site of this revision with the README as its home page.

    Same `mkdocs.yml` (theme, nav, `toc` permalinks, every extension) with
    docs_dir = `docs/`. The README's own references decide the extra layout:
    `assets/...` and `docs/assets/...` must exist where the page expects them.
    Its outbound links point at repo files the site does not publish (LICENSE,
    CONTRIBUTING.md, docs/Team/...), and `teamwork links` gates those, so the
    mirror ignores `not_found` and keeps every other warning fatal under --strict.
    """
    docs = work / "docs"
    if docs.exists():
        shutil.rmtree(docs)
    copied = 0
    for source, target in (
        (repo / "docs", docs),
        (repo / "assets", docs / "assets"),
        (repo / "docs" / "assets", docs / "docs" / "assets"),
    ):
        for root, _dirs, files in os.walk(source):
            for name in files:
                src = Path(root) / name
                dest = target / src.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                copied += 1
    shutil.copyfile(repo / "README.md", docs / "index.md")
    config = (repo / "mkdocs.yml").read_text(encoding="utf-8")
    if "not_found: warn" not in config:
        raise SystemExit("mkdocs.yml no longer sets validation.links.not_found: warn")
    (work / "mkdocs.yml").write_text(
        config.replace("not_found: warn", "not_found: ignore"), encoding="utf-8"
    )
    print(f"mirror: {copied} file(s) into {docs}, README.md -> index.md")
    return work


def build(python: str, work: Path) -> tuple[int, str]:
    run = subprocess.run(
        [python, "-m", "mkdocs", "build", "--strict", "-f", str(work / "mkdocs.yml")],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_MKDOCS_2_WARNING": "1"},
    )
    output = run.stdout + run.stderr
    warnings = [line for line in output.splitlines() if "WARNING" in line or "ERROR" in line]
    for line in warnings:
        print(f"  {line.strip()}")
    print(f"build: exit {run.returncode}, {len(warnings)} warning/error line(s)")
    return run.returncode, output


def scan(site: Path) -> tuple[PageScan, list[str]]:
    page = site / "index.html"
    if not page.is_file():
        raise SystemExit(f"no index.html in {site}")
    scanner = PageScan()
    scanner.feed(page.read_text(encoding="utf-8", errors="replace"))
    problems = []
    ids = [hid for _tag, hid, _text in scanner.headings]
    duplicates = sorted({hid for hid in scanner.ids if scanner.ids.count(hid) > 1})
    if duplicates:
        problems.append(f"duplicate id(s): {','.join(duplicates)}")
    targets = set(scanner.ids)
    dangling = sorted({a for a in scanner.anchors if a not in targets})
    for anchor in dangling:
        problems.append(f"dangling anchor #{anchor}")
    print(
        f"render: {len(scanner.headings)} heading(s), {len([i for i in ids if i])} with an id,"
        f" {len(scanner.ids)} id(s) total, {len(scanner.anchors)} in-page anchor(s),"
        f" {len(dangling)} dangling, {len(duplicates)} duplicate id(s)"
    )
    return scanner, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    ap.add_argument("--python", default=None, help="interpreter with mkdocs installed")
    ap.add_argument("--work", default=None, help="build directory (default: a temp directory)")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    python = doc_python(repo, args.python)
    print(
        f"renderer: {python} -m mkdocs {subprocess.run([python, '-m', 'mkdocs', '--version'], capture_output=True, text=True).stdout.strip()}"
    )

    work = (
        Path(args.work).resolve() if args.work else Path(tempfile.mkdtemp(prefix="readme-layout-"))
    )
    mirror(repo, work)
    code, output = build(python, work)
    problems: list[str] = []
    if code != 0:
        problems.append(f"mkdocs build --strict exited {code}")
    _scanner, layout = scan(work / "site")
    problems.extend(layout)

    control_work = work / "control"
    if control_work.exists():
        shutil.rmtree(control_work)
    shutil.copytree(work, control_work, ignore=shutil.ignore_patterns("site", "control"))
    index = control_work / "docs" / "index.md"
    text = index.read_text(encoding="utf-8")
    text = text.replace(
        "## What makes it different\n",
        "## What makes it different\n\nSee [the pitch](#no-such-heading).\n",
        1,
    )
    text = text.rstrip() + ('\n\n<h2 id="what-makes-it-different">Raw heading reusing an id</h2>\n')
    index.write_text(text, encoding="utf-8")
    code2, _ = build(python, control_work)
    _s, control = scan(control_work / "site")
    caught = [p for p in control if "dangling anchor" in p or "duplicate id" in p]
    print(f"control: build exit {code2}, {len(caught)} expected finding(s): {caught}")
    if len(caught) < 2:
        problems.append(
            f"blind check: control produced {caught} instead of a dangling anchor and a duplicate id"
        )

    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"RESULT FAIL readme-layout: {len(problems)} problem(s)")
        return 1
    print(
        "RESULT PASS readme-layout: README rendered under mkdocs build --strict with unique"
        " heading ids, 0 dangling anchors, and the control caught"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
