#!/usr/bin/env python3
"""Fail the gate on any comment the code can speak for itself.

The team's rule is that the code is the comment: a name, a type, a small function
or a docstring says what and why, and an explanatory ``#`` is a maintenance
liability that is neither compiled nor tested. Only the comments a toolchain
itself reads are allowed:

* a shebang on line 1;
* ``# noqa`` (optionally with rule codes - no prose);
* ``# type: ignore[...]``;
* ``# pragma: no cover`` and ``# pragma: no branch``;
* ``# fmt: off``, ``# fmt: on`` and ``# fmt: skip``;
* ``# -*- coding: ... -*-`` on lines 1-2.

Every other comment is a finding, printed as ``path:line: text``. ``--fix``
removes a whole-line comment, trims a trailing one, and normalises an allowed
directive that carries prose; it refuses any file whose parsed AST would change,
so the only thing a fix can alter is the comments.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

DEFAULT_PATHS = ("src", "scripts", "tests")
SKIP_DIRS = {".git", ".pi", ".venv", "venv", "site", "dist", "build", "__pycache__", "node_modules"}

SHEBANG = re.compile(r"^#!.*$")
CODING = re.compile(r"^#\s*-\*-\s*coding[:=].*-\*-$")
NOQA = re.compile(r"^#\s*noqa(?::\s*[A-Z0-9]+(?:\s*,\s*[A-Z0-9]+)*)?$")
TYPE_IGNORE = re.compile(r"^#\s*type:\s*ignore(?:\[[^\]]*\])?$")
PRAGMA = re.compile(r"^#\s*pragma:\s*no\s+(?:cover|branch)$")
FMT = re.compile(r"^#\s*fmt:\s*(?:off|on|skip)$")
DIRECTIVES = (NOQA, TYPE_IGNORE, PRAGMA, FMT)


def is_directive(comment: str, row: int) -> bool:
    """A toolchain directive, and only where the toolchain reads it.

    A shebang is a directive on line 1 and a comment anywhere else; a coding
    cookie is read from the first two lines only. Trailing whitespace is not
    part of the directive.
    """
    text = comment.rstrip()
    if row == 1 and SHEBANG.match(text):
        return True
    if row <= 2 and CODING.match(text):
        return True
    return any(pattern.match(text) for pattern in DIRECTIVES)


def normalised(comment: str) -> str:
    """The directive without the prose someone appended after a dash."""
    text = comment.rstrip()
    noqa = re.match(r"^#\s*noqa(?::\s*([A-Z0-9]+(?:\s*,\s*[A-Z0-9]+)*))?", text)
    if noqa:
        codes = (noqa.group(1) or "").strip()
        return f"# noqa: {codes}" if codes else "# noqa"
    type_ignore = re.match(r"^#\s*(type:\s*ignore(?:\[[^\]]*\])?)", text)
    if type_ignore:
        return f"# {type_ignore.group(1)}"
    pragma = re.match(r"^#\s*(pragma:\s*no\s+(?:cover|branch))", text)
    if pragma:
        return f"# {pragma.group(1)}"
    fmt = re.match(r"^#\s*(fmt:\s*(?:off|on|skip))", text)
    if fmt:
        return f"# {fmt.group(1)}"
    return text


def python_files(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            found.append(root)
            continue
        for path in sorted(root.rglob("*.py")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            found.append(path)
    return sorted(set(found))


def comment_tokens(path: Path) -> list[tokenize.TokenInfo]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    readline = io.StringIO(text).readline
    return [token for token in tokenize.generate_tokens(readline) if token.type == tokenize.COMMENT]


def explanatory(path: Path) -> list[tokenize.TokenInfo]:
    return [
        token for token in comment_tokens(path) if not is_directive(token.string, token.start[0])
    ]


def prose_head(comment: str, row: int) -> str:
    """The longest directive prefix, when the rest of the comment is prose.

    A reason can follow a directive with a dash, a parenthetical, a second ``#``
    or a colon; every one of them normalises to the directive alone. The longest
    valid prefix wins, so ``# noqa: E501, F401 - x`` keeps both codes.
    """
    text = comment.rstrip()
    if is_directive(text, row):
        return ""
    for end in range(len(text), 0, -1):
        head = text[:end].rstrip()
        if head == text:
            continue
        if is_directive(head, row):
            return normalised(head)
    return ""


def rewrite(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    removed = 0
    trimmed = 0
    edits: list[tuple[int, int, int, str | None]] = []
    for token in comment_tokens(path):
        row, column = token.start
        end_row, end_column = token.end
        if row != end_row:
            continue
        comment = token.string
        if is_directive(comment, row):
            continue
        head = prose_head(comment, row)
        if head:
            edits.append((row, column, end_column, head))
            trimmed += 1
            continue
        line = lines[row - 1]
        if line[:column].strip() == "":
            edits.append((row, column, end_column, None))
        else:
            edits.append((row, column, end_column, ""))
        removed += 1

    for row, column, end_column, replacement in sorted(edits, reverse=True):
        line = lines[row - 1]
        if replacement is None:
            lines[row - 1] = ""
            continue
        lines[row - 1] = line[:column] + replacement + line[end_column:]
        if replacement == "":
            lines[row - 1] = lines[row - 1].rstrip() + "\n"
    updated = "".join(line for line in lines if line.strip() != "" or line.endswith("\n"))
    if not updated.endswith("\n"):
        updated += "\n"
    before = ast.dump(ast.parse(text))
    after = ast.dump(ast.parse(updated))
    if before != after:
        raise SystemExit(f"{path}: refusing to write: the AST would change")
    if updated != text:
        path.write_bytes(updated.encode("utf-8"))
    return removed, trimmed


def check(roots: list[Path]) -> int:
    files = python_files(roots)
    findings: list[str] = []
    for path in files:
        try:
            tokens = explanatory(path)
        except (tokenize.TokenError, IndentationError, SyntaxError) as error:
            findings.append(f"{path}: unreadable Python ({error})")
            continue
        for token in tokens:
            findings.append(f"{path}:{token.start[0]}: {token.string.strip()}")
    print(f"# no-comment check: {len(files)} file(s)")
    for finding in findings:
        print(f"- {finding}")
    if findings:
        print(
            f"# {len(findings)} explanatory comment(s); allowed directives: shebang, noqa, "
            "type: ignore, pragma, fmt, coding"
        )
        return 1
    print("# 0 explanatory commentary; only the toolchain directives are present")
    return 0


def fix(roots: list[Path]) -> int:
    files = python_files(roots)
    removed = 0
    trimmed = 0
    changed = 0
    for path in files:
        try:
            before = path.read_text(encoding="utf-8-sig")
            is_changed = bool(explanatory(path))
        except (tokenize.TokenError, IndentationError, SyntaxError) as error:
            raise SystemExit(f"{path}: cannot read Python ({error})") from error
        if not is_changed:
            continue
        was_removed, was_trimmed = rewrite(path)
        removed += was_removed
        trimmed += was_trimmed
        changed += 1
        if not path.read_text(encoding="utf-8-sig").strip():
            path.write_bytes(before.encode("utf-8"))
            raise SystemExit(f"{path}: refusing to empty a file")
    print(
        f"# no-comment fix: {changed} file(s) changed, {removed} removed, "
        f"{trimmed} normalised; every written file has an unchanged AST"
    )
    return check(roots)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        default=list(DEFAULT_PATHS),
        help="files or directories to scan (default: src scripts tests)",
    )
    parser.add_argument("--fix", action="store_true", help="remove or normalise the findings")
    args = parser.parse_args(argv)
    roots = [Path(path) for path in args.paths]
    missing = [str(root) for root in roots if not root.exists()]
    if missing:
        print(f"no such path: {', '.join(missing)}", file=sys.stderr)
        return 2
    return fix(roots) if args.fix else check(roots)


if __name__ == "__main__":
    sys.exit(main())
