"""The no-comment gate: the code is the comment, and the lint proves it."""

from __future__ import annotations

import ast
import importlib.util
import io
import subprocess
import sys
import tokenize
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_comments.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_comments", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


checker = load_checker()


def run(paths, *argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = checker.main([str(path) for path in paths] + list(argv))
    return code, buffer.getvalue()


def comments_in(path: Path) -> list[tokenize.TokenInfo]:
    return [
        token
        for token in tokenize.generate_tokens(
            io.StringIO(path.read_text(encoding="utf-8")).readline
        )
        if token.type == tokenize.COMMENT
    ]


def write(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_an_explanatory_comment_fails_and_names_path_and_line(tmp_path: Path) -> None:
    path = write(tmp_path, "value = 1\n# explain the value\n")

    code, output = run([tmp_path])

    assert code == 1, output
    assert f"{path}:2: # explain the value" in output
    assert "1 explanatory comment(s)" in output


def test_every_toolchain_directive_is_allowed(tmp_path: Path) -> None:
    source = (
        "#!/usr/bin/env python3\n"
        "# noqa: E501\n"
        "# type: ignore[attr-defined]\n"
        "# pragma: no cover\n"
        "# pragma: no branch\n"
        "# fmt: off\n"
        "# fmt: on\n"
        "# fmt: skip\n"
        "value = 1  # noqa: ANN202\n"
    )
    write(tmp_path, source)

    code, output = run([tmp_path])

    assert code == 0, output
    assert "0 explanatory commentary" in output


def test_a_shebang_after_line_one_is_an_explanatory_comment(tmp_path: Path) -> None:
    path = write(tmp_path, "value = 1\n#! this explains the value\n")

    code, output = run([tmp_path])

    assert code == 1, output
    assert f"{path}:2: #!" in output


def test_a_coding_cookie_is_allowed_only_on_the_first_two_lines(tmp_path: Path) -> None:
    write(
        tmp_path,
        "value = 1\n# -*- coding: utf-8 -*-\nother = 2\n# -*- coding: utf-8 -*-\n",
    )

    code, output = run([tmp_path])

    assert code == 1, output
    assert ":4:" in output
    assert ":2:" not in output


def test_a_directive_with_trailing_whitespace_is_kept(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "value = 1  # type: ignore   \n"
        "other = 2  # pragma: no cover   \n"
        "third = 3  # fmt: skip   \n",
    )

    assert run([tmp_path])[0] == 0
    assert run([tmp_path], "--fix")[0] == 0
    text = path.read_text(encoding="utf-8")
    assert "# type: ignore" in text
    assert "# pragma: no cover" in text
    assert "# fmt: skip" in text


def test_fix_keeps_every_noqa_code(tmp_path: Path) -> None:
    path = write(tmp_path, "value = 1  # noqa: E501, F401 - both codes matter\n")

    assert run([tmp_path], "--fix")[0] == 0

    assert "# noqa: E501, F401" in path.read_text(encoding="utf-8")


def test_fix_trims_parenthetical_and_second_hash_prose(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "import os  # noqa: E402  (import after the sys.path fix)\n"
        "value = 1  # type: ignore[attr-defined]  (a reason)\n"
        "other = 2  # noqa: E501  # a long line\n",
    )

    assert run([tmp_path], "--fix")[0] == 0

    text = path.read_text(encoding="utf-8")
    assert "import os  # noqa: E402" in text
    assert "value = 1  # type: ignore[attr-defined]" in text
    assert "other = 2  # noqa: E501" in text
    assert "reason" not in text
    assert "long line" not in text


def test_fix_removes_the_comments_and_keeps_the_ast(tmp_path: Path) -> None:
    source = (
        "# a banner\n"
        "def total(values):\n"
        "    result = 0  # running sum\n"
        "    # loop the values\n"
        "    for value in values:\n"
        "        result += value\n"
        "    return result\n"
        "# trailing prose\n"
    )
    path = write(tmp_path, source)
    before = ast.dump(ast.parse(source))

    code, output = run([tmp_path], "--fix")

    assert code == 0, output
    fixed = path.read_text(encoding="utf-8")
    assert "#" not in fixed
    assert ast.dump(ast.parse(fixed)) == before
    assert comments_in(path) == []


def test_fix_trims_a_directive_that_carries_prose(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "value = 1  # noqa: E501 - a long line reason\n"
        "other = 2  # type: ignore[attr-defined] - a reason\n",
    )

    code, output = run([tmp_path], "--fix")

    assert code == 0, output
    fixed = path.read_text(encoding="utf-8")
    assert "# noqa: E501" in fixed
    assert "# type: ignore[attr-defined]" in fixed
    assert "reason" not in fixed


def test_fix_refuses_a_change_that_is_not_comment_only(tmp_path: Path, monkeypatch) -> None:
    path = write(tmp_path, "value = 1\n# explain\n")
    original = checker.rewrite

    class ChangingAst:
        calls = 0

        @staticmethod
        def parse(text):
            return text

        @staticmethod
        def dump(_tree):
            ChangingAst.calls += 1
            return f"dump-{ChangingAst.calls}"

    monkeypatch.setattr(checker, "ast", ChangingAst)
    with pytest.raises(SystemExit, match="the AST would change"):
        original(path)
    assert "# explain" in path.read_text(encoding="utf-8")


def test_the_shipped_tree_has_no_explanatory_comment() -> None:
    code, output = run([REPO_ROOT / "src", REPO_ROOT / "scripts", REPO_ROOT / "tests"])

    assert code == 0, output
    assert "0 explanatory commentary" in output


def test_a_new_comment_turns_the_gate_red(tmp_path: Path) -> None:
    clean = write(tmp_path, "def value():\n    return 1\n")
    assert run([tmp_path])[0] == 0
    clean.write_text(
        clean.read_text(encoding="utf-8") + "# what the value means\n", encoding="utf-8"
    )

    code, output = run([tmp_path])

    assert code == 1, output


def test_make_lint_and_the_ci_lint_job_run_the_checker() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/check_comments.py" in makefile
    assert "MAKEFILE_LIST" in makefile, (
        "the checker must resolve from the Makefile, not the caller's cwd"
    )
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/check_comments.py" in workflow
    assert "check_comments.py" in workflow.split("lint:", 1)[1]


def test_a_tree_without_the_default_roots_is_a_clean_noop(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 file(s)" in result.stdout


def test_an_explicit_missing_path_is_an_error(tmp_path: Path) -> None:
    assert checker.main([str(tmp_path / "absent")]) == 2


def test_the_rule_is_documented_where_every_agent_reads_it() -> None:
    for name in ("AGENTS.md", "templates/AGENTS.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "**NO COMMENTS**" in text, name
        assert "scripts/check_comments.py" in text, name
    engineering = (REPO_ROOT / "references" / "Engineering.md").read_text(encoding="utf-8")
    assert "### No comments - the code is the comment" in engineering
    assert "scripts/check_comments.py" in engineering
    for charter in sorted((REPO_ROOT / "roles").glob("*.md")):
        text = charter.read_text(encoding="utf-8")
        assert "No comments:" in text, charter.name
    ci = (REPO_ROOT / "docs" / "guide" / "ci.md").read_text(encoding="utf-8")
    assert "check_comments.py" in ci
