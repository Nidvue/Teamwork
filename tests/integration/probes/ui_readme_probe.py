#!/usr/bin/env python3
"""Integration probe (area ui-readme): the rendered README loads its own images.

Builds the README into the docs site the same way `mkdocs.yml` builds every page,
serves the built site over HTTP, fetches the rendered README and then fetches
every local image it references. An image must answer 200 with the exact bytes of
the committed file it stands for; the demo block must be present and its command
readable. External badge images are counted and not fetched (no network here).

Control: deleting one served image must make the probe report it unresolved.
Exit 0 = every image resolved and the control was caught; 1 = a problem or a
blind check.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DEMO_COMMAND = "use the teamwork skill"


class ImageScan(HTMLParser):
    """Images with the tag stack that holds them, so `<p align=center>` is visible."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict] = []
        self.code: list[str] = []
        self._stack: list[tuple[str, dict]] = []
        self._in_code = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in ("img", "br", "hr", "meta", "input", "link"):
            self._stack.append((tag, attrs))
        if tag == "img":
            parents = [p for p in self._stack if p[0] in ("p", "div", "span", "a")]
            self.images.append(
                {
                    "src": attrs.get("src", ""),
                    "alt": attrs.get("alt", ""),
                    "width": attrs.get("width", ""),
                    "height": attrs.get("height", ""),
                    "centered": any(
                        (name == "p" and style.get("align") == "center")
                        or style.get("style", "").find("text-align: center") >= 0
                        for name, style in parents
                    ),
                }
            )
        elif tag in ("code", "pre"):
            self._in_code += 1

    def handle_endtag(self, tag):
        if tag in ("code", "pre") and self._in_code:
            self._in_code -= 1
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break

    def handle_data(self, data):
        if self._in_code:
            self.code.append(data)


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
    """The docs site of this revision, with the README as its home page.

    Three source roots, because the README's own references name them: the site
    pages and their theme assets (`docs/`), the page's `assets/...` images, and
    its `docs/assets/...` image which keeps that path inside the site.
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


def build(python: str, work: Path) -> int:
    run = subprocess.run(
        [python, "-m", "mkdocs", "build", "--strict", "-f", str(work / "mkdocs.yml")],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_MKDOCS_2_WARNING": "1"},
    )
    warnings = [
        line.strip()
        for line in (run.stdout + run.stderr).splitlines()
        if "WARNING" in line or "ERROR" in line
    ]
    for line in warnings:
        print(f"  {line}")
    print(f"build: exit {run.returncode}, {len(warnings)} warning/error line(s)")
    return run.returncode


def serve(site: Path):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args, **_kwargs):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(site))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def fetch(url: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "teamwork-readme-probe"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.headers.get("content-type", ""), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("content-type", ""), b""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    ap.add_argument("--python", default=None, help="interpreter with mkdocs installed")
    ap.add_argument("--work", default=None, help="build directory (default: a temp directory)")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    python = doc_python(repo, args.python)
    work = Path(args.work).resolve() if args.work else Path(tempfile.mkdtemp(prefix="ui-readme-"))
    problems: list[str] = []
    mirror(repo, work)
    site = work / "site"
    if build(python, work) != 0:
        problems.append("mkdocs build --strict exited non-zero")

    page = (site / "index.html").read_text(encoding="utf-8", errors="replace")
    scanner = ImageScan()
    scanner.feed(page)
    print(f"rendered README: {len(scanner.images)} image tag(s)")

    server, base = serve(site)
    try:
        status, _ctype, _body = fetch(base + "/")
        print(f"fetch {base}/: {status}")
        if status != 200:
            problems.append(f"the rendered README did not load over HTTP (status {status})")

        local = external = 0
        for image in scanner.images:
            src = image["src"]
            if not src:
                problems.append("an image tag carries no src")
                continue
            if src.startswith(("http://", "https://")):
                external += 1
                if not src.startswith("https://"):
                    problems.append(f"external image is not https: {src}")
                continue
            local += 1
            url = urllib.parse.urljoin(base + "/", src)
            status, ctype, body = fetch(url)
            expected_path = site / urllib.parse.unquote(src.split("?")[0])
            expected = expected_path.read_bytes() if expected_path.is_file() else b""
            digest = hashlib.sha256(body).hexdigest()[:16]
            ok = status == 200 and body and body == expected
            print(
                f"  {src}: http {status} {ctype or '-'} {len(body)} B sha {digest}"
                f" {'==' if ok else '!='} source {len(expected)} B"
                f"{'' if image['alt'] else ' ALT MISSING'}"
            )
            if not ok:
                problems.append(
                    f"image does not resolve to its committed bytes: {src} (status {status})"
                )
            if not image["alt"]:
                problems.append(f"image has no alt text: {src}")

        demo = [i for i in scanner.images if i["src"].endswith("assets/demo.svg")]
        if not demo:
            problems.append("the demo image block is absent from the rendered README")
        else:
            block = demo[0]
            if not block["centered"]:
                problems.append("the demo image is not in its centered block")
            if not block["width"]:
                problems.append("the demo image declares no width")
            print(
                f"demo block: centered={block['centered']} width={block['width'] or '-'}"
                f" height={block['height'] or '-'} alt={len(block['alt'])} char(s)"
            )
        code_text = "\n".join(scanner.code)
        if DEMO_COMMAND not in code_text:
            problems.append(f"the demo command '{DEMO_COMMAND}' is not in a rendered code block")
        else:
            print(f"demo command: '{DEMO_COMMAND}' present in a rendered code block")
        print(f"images: {local} local, {external} external badge(s) not fetched")

        control = site / "assets" / "banner.svg"
        if control.is_file():
            control.unlink()
            status, _ctype, body = fetch(base + "/assets/banner.svg")
            print(f"control: banner.svg deleted -> http {status}, {len(body)} B")
            if status == 200 and body:
                problems.append("blind check: a deleted image still fetched 200")
    finally:
        server.shutdown()

    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"RESULT FAIL ui-readme: {len(problems)} problem(s)")
        return 1
    print(
        "RESULT PASS ui-readme: rendered README served its own images, demo block and command present"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
