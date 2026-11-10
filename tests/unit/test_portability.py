"""Unit tests for the portability contract and relocated resource resolution.

Covers [Architecture](../../../docs/Team/Architecture.md) sections 3 and 6:
the OS seam in ``teamwork.portable``, the source-level portability rules, and
the fact that ``teamwork.engine`` resolves its bundle from the real repo root
rather than a hardcoded path.

Owner: architect. Task: T-0003.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from teamwork import engine, portable, resources

# ``tests/unit/test_portability.py`` -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_TEAMWORK = REPO_ROOT / "src" / "teamwork"

#: Modules banned from the runtime path by Architecture section 6.
FORBIDDEN_MODULES = frozenset({"fcntl", "termios", "pwd", "grp", "resource"})

#: Textual guard for ``shell=True`` (catches aliases the AST scan misses).
SHELL_TRUE_RE = re.compile(r"shell\s*=\s*True")


def _source_files():
    """Every Python module shipped in the runtime package."""
    return sorted(SRC_TEAMWORK.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --------------------------------------------------------------------------- #
# portable.pid_alive
# --------------------------------------------------------------------------- #


def test_pid_alive_current_process_is_true():
    assert portable.pid_alive(os.getpid()) is True


def test_pid_alive_rejects_non_positive_pids():
    assert portable.pid_alive(0) is False
    assert portable.pid_alive(-1) is False


def test_pid_alive_certainly_dead_process_is_false():
    # Spawn a short-lived process, reap it, then probe its (now dead) pid.
    # PID reuse inside the microseconds before the probe is theoretically
    # possible but practically negligible.
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    pid = proc.pid
    proc.wait(timeout=30)
    assert portable.pid_alive(pid) is False


def test_pid_alive_windows_branch_delegates(monkeypatch):
    calls = []

    def fake_windows_pid_alive(pid: int) -> bool:
        calls.append(pid)
        return True

    monkeypatch.setattr(portable, "IS_WINDOWS", True)
    monkeypatch.setattr(portable, "_windows_pid_alive", fake_windows_pid_alive)

    assert portable.pid_alive(4321) is True
    assert calls == [4321]

    # Non-positive pids short-circuit before the Windows helper is consulted.
    assert portable.pid_alive(0) is False
    assert calls == [4321]


def test_pid_alive_windows_branch_can_report_dead(monkeypatch):
    monkeypatch.setattr(portable, "IS_WINDOWS", True)
    monkeypatch.setattr(portable, "_windows_pid_alive", lambda pid: False)
    assert portable.pid_alive(987654) is False


# --------------------------------------------------------------------------- #
# portable.newline_for / python_executable
# --------------------------------------------------------------------------- #


def test_newline_for_is_always_lf():
    assert portable.newline_for() == "\n"
    assert portable.newline_for(True) == "\n"
    assert portable.newline_for(False) == ""


def test_python_executable_is_non_empty_str():
    exe = portable.python_executable()
    assert isinstance(exe, str)
    assert exe.strip() != ""


# --------------------------------------------------------------------------- #
# Source-level portability rules
# --------------------------------------------------------------------------- #


def test_source_scan_sees_runtime_modules():
    """Guard against the scans passing vacuously on an empty file list."""
    names = {path.name for path in _source_files()}
    assert {"engine.py", "portable.py", "resources.py"} <= names


def test_no_forbidden_posix_imports_in_runtime():
    offenders = []
    for path in _source_files():
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                        offenders.append(f"{path}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module_root = (node.module or "").split(".")[0]
                if module_root in FORBIDDEN_MODULES:
                    offenders.append(f"{path}:{node.lineno} from {node.module} import ...")
                for alias in node.names:
                    # e.g. ``from os import fork``
                    if module_root == "os" and alias.name == "fork":
                        offenders.append(f"{path}:{node.lineno} from os import fork")
            elif (
                isinstance(node, ast.Attribute)
                and node.attr == "fork"
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
            ):
                offenders.append(f"{path}:{node.lineno} os.fork")
    assert offenders == [], "forbidden POSIX runtime use: " + "; ".join(offenders)


def test_no_subprocess_shell_true_in_runtime():
    offenders = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for match in SHELL_TRUE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path}:{line} shell=True")
    assert offenders == [], "shell=True must never be used: " + "; ".join(offenders)


# --------------------------------------------------------------------------- #
# Engine resource resolution (relocated from the monolith)
# --------------------------------------------------------------------------- #


def test_engine_skill_dir_is_repo_root():
    assert engine.SKILL_DIR == REPO_ROOT
    assert (engine.SKILL_DIR / "SKILL.md").is_file()


def test_engine_resolves_roles_and_templates_from_bundle():
    assert engine.ROLES_DIR == REPO_ROOT / "roles"
    assert (engine.ROLES_DIR / "developer.md").is_file()

    assert engine.TEMPLATES_DIR == REPO_ROOT / "templates"
    assert (engine.TEMPLATES_DIR / "AGENTS.md").is_file()


def test_self_invocation_is_a_non_empty_command():
    command = resources.self_invocation()
    assert isinstance(command, str)
    assert command.strip() != ""
    assert shlex.split(command), "self_invocation() must be a runnable command"


def test_version_command_exits_zero_via_subprocess():
    """The documented module entrypoint must print the version and exit 0."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]).rstrip(
        os.pathsep
    )

    result = subprocess.run(
        [sys.executable, "-m", "teamwork", "--version"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"teamwork {engine.VERSION}"


def test_self_invocation_command_is_runnable():
    """The command returned by ``resources.self_invocation()`` must execute.

    ``PYTHONPATH`` is removed on purpose: the checkout shim
    (``scripts/teamwork.py``) bootstraps ``src`` itself (see its module
    docstring), and a resolved-but-shadowing ``PYTHONPATH`` entry is a separate
    defect tracked against the shim, not part of this command's contract.
    """
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        shlex.split(resources.self_invocation()) + ["--version"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"teamwork {engine.VERSION}"


# --------------------------------------------------------------------------- #
# newline hygiene: generated markdown/json must be byte-identical everywhere
# --------------------------------------------------------------------------- #


def _text_writes_missing_newline(module_path):
    """Return the line numbers of text writes that do not pin ``newline``.

    ``Path.write_text`` and ``open(..., "w"/"a")`` translate ``\\n`` to the
    platform default, which is CRLF on Windows. Every generated file must be
    written with an explicit ``newline="\\n"`` so a clone on any OS is identical
    (CI found 37 files with CR bytes on windows-latest before this was pinned).
    """
    import ast

    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None)
        kwargs = {kw.arg for kw in node.keywords}
        if name == "write_text" and "newline" not in kwargs:
            missing.append(node.lineno)
        elif name == "open":
            mode = None
            if node.args and isinstance(node.args[0], ast.Constant):
                mode = node.args[0].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and any(c in mode for c in "wa") and "newline" not in kwargs:
                missing.append(node.lineno)
    return missing


def test_every_generated_text_write_pins_lf_newlines():
    offenders = {}
    for module_path in sorted((REPO_ROOT / "src" / "teamwork").glob("*.py")):
        lines = _text_writes_missing_newline(module_path)
        if lines:
            offenders[module_path.name] = lines
    assert offenders == {}, (
        f'text writes must pass newline="\\n" so Windows does not emit CRLF: {offenders}'
    )


def test_engine_writes_a_generated_workspace_without_cr_bytes(tmp_path):
    """The real check the CI matrix runs, expressed locally on generated bytes."""
    from teamwork import engine

    project = tmp_path / "NoCr"
    project.mkdir()
    engine.main(
        [
            "init",
            "--project",
            str(project),
            "--team",
            "NoCr",
            "--no-git",
            "--agents",
            "ceo,architect,developer-1,reviewer-1",
        ]
    )
    engine.main(["task", "add", "developer", "no CR bytes", "--project", str(project)])

    offenders = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file() and b"\r" in path.read_bytes()
    ]
    assert offenders == [], f"generated files contain CR bytes: {offenders}"


def test_portable_invocation_never_contains_a_machine_path():
    """The command committed into AGENTS.md must be machine-independent.

    ``self_invocation()`` may return an absolute checkout path; that is fine for
    the gitignored ``.pi/`` state but must never reach a tracked file (CI's
    privacy job found ``/home/<user>`` in AGENTS.md 13 times before this split).
    """
    portable = resources.portable_invocation()
    assert portable == "teamwork"
    assert "/" not in portable and "\\" not in portable
    assert os.path.isabs(portable) is False


def test_agents_md_template_uses_the_portable_placeholder():
    template = (REPO_ROOT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<script>" in template
    assert "teamwork.py" not in template
