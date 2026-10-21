"""A standard-library reader for the YAML subset a GitHub workflow uses.

Why this exists: the CI contract tests (`test_ci_contracts.py`,
`test_makefile_contracts.py`, `test_release_workflow.py`) have to read
`.github/workflows/*.yml` and come from this project's own rule that its tooling
is standard-library only. PyYAML is present in some developer virtualenvs (it
arrives with `mkdocs-material`) but it is **not** in the `dev` extra, so the
`test` job of `.github/workflows/ci.yml` - which installs `-e '.[dev]'` and
nothing else - would fail collection on `import yaml`. This module parses the
subset the two workflow files actually use: block mappings, block sequences,
block scalars (`|`, `>`, `|-`, `|+`), flow sequences (`[a, b]`), quoted scalars,
comments and blank lines. Nothing else.

It is a reader for the *contract*, not a general YAML implementation: an input it
cannot represent raises `WorkflowParseError` rather than returning a plausible
half-value, so a test can never silently assert against a mis-parsed workflow.
"""

from __future__ import annotations

import re

__all__ = ["WorkflowParseError", "parse_workflow"]

_ITEM = re.compile(r"^-(\s|$)")
_KEY = re.compile(r"^[^:\s][^:]*:(\s|$)")
_BLOCK_SCALAR = ("|", ">", "|-", ">-", "|+", ">+")


class WorkflowParseError(ValueError):
    """The text is not in the YAML subset this reader understands."""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content(lines: list[str], index: int) -> int:
    """Index of the next line that is neither blank nor a comment."""
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            return index
        index += 1
    return index


def _scalar(value: str):
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [_scalar(part) for part in inner.split(",")] if inner else []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if " #" in text:
        text = text.split(" #", 1)[0].strip()
    if text in ("", "~", "null"):
        return None
    return text


def _block(lines: list[str], index: int, indent: int):
    if index >= len(lines) or _indent(lines[index]) < indent:
        return {}, index
    if _ITEM.match(lines[index].strip()):
        return _sequence(lines, index, indent)
    return _mapping(lines, index, indent)


def _mapping(lines: list[str], index: int, indent: int):
    out: dict = {}
    while True:
        index = _next_content(lines, index)
        if index >= len(lines):
            return out, index
        line = lines[index]
        stripped = line.strip()
        if _indent(line) != indent or _ITEM.match(stripped):
            return out, index
        key, separator, value = stripped.partition(":")
        if not separator or not key.strip():
            raise WorkflowParseError(f"line {index + 1}: not a mapping entry: {stripped!r}")
        key = key.strip().strip("'\"")
        value = value.strip()
        index += 1
        if value in _BLOCK_SCALAR:
            out[key], index = _block_scalar(lines, index, indent)
            continue
        if value:
            out[key] = _scalar(value)
            continue
        following = _next_content(lines, index)
        if following < len(lines) and _indent(lines[following]) > indent:
            out[key], index = _block(lines, following, _indent(lines[following]))
        elif (
            following < len(lines)
            and _indent(lines[following]) == indent
            and _ITEM.match(lines[following].strip())
        ):
            out[key], index = _sequence(lines, following, indent)
        else:
            out[key] = None


def _block_scalar(lines: list[str], index: int, indent: int):
    body: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.strip() and _indent(line) <= indent:
            break
        body.append(line)
        index += 1
    while body and not body[-1].strip():
        body.pop()
    first = min((_indent(line) for line in body if line.strip()), default=indent + 2)
    return "\n".join(line[first:] if line.strip() else "" for line in body), index


def _sequence(lines: list[str], index: int, indent: int):
    out: list = []
    while True:
        index = _next_content(lines, index)
        if index >= len(lines):
            return out, index
        line = lines[index]
        stripped = line.strip()
        if _indent(line) != indent or not _ITEM.match(stripped):
            return out, index
        rest = stripped[1:].strip()
        if not rest:
            following = _next_content(lines, index + 1)
            if following < len(lines) and _indent(lines[following]) > indent:
                item, index = _block(lines, following, _indent(lines[following]))
                out.append(item)
            else:
                out.append(None)
                index += 1
            continue
        if _KEY.match(rest):
            # An item that opens a mapping: keep the item's own keys and everything
            # deeper-indented that belongs to it, at the item's key indentation.
            inner = [" " * (indent + 2) + rest]
            cursor = index + 1
            while cursor < len(lines):
                candidate = lines[cursor]
                if not candidate.strip() or candidate.lstrip().startswith("#"):
                    inner.append(candidate)
                    cursor += 1
                    continue
                if _indent(candidate) > indent:
                    inner.append(candidate)
                    cursor += 1
                    continue
                break
            item, _ = _block(inner, _next_content(inner, 0), indent + 2)
            out.append(item)
            index = cursor
            continue
        out.append(_scalar(rest))
        index += 1


def parse_workflow(text: str) -> dict:
    """Return the parsed document; raise `WorkflowParseError` on unreadable input."""
    lines = text.splitlines()
    start = _next_content(lines, 0)
    if start >= len(lines):
        return {}
    document, end = _block(lines, start, _indent(lines[start]))
    leftover = _next_content(lines, end)
    if leftover < len(lines):
        raise WorkflowParseError(f"line {leftover + 1}: unexpected content after the document")
    if not isinstance(document, dict):
        raise WorkflowParseError("the workflow is not a mapping")
    return document
