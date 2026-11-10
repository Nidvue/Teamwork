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


def _unsafe_text_writes(module_path):
    """Return the line numbers of text writes that are unsafe for Python 3.9/Windows.

    Two traps, both found by CI on the 3x3 matrix:

    * ``Path.write_text(..., newline=...)`` does not exist before Python 3.10, so
      the package must not call it at all - it uses ``write_lf`` instead;
    * ``open(..., "w"/"a")`` without ``newline="\\n"`` emits CRLF on Windows.

    Both are checked statically, so the guard runs on every platform.
    """
    import ast

    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None)
        kwargs = {kw.arg for kw in node.keywords}
        if name == "write_text":
            offenders.append((node.lineno, "Path.write_text is Python 3.10+ only"))
        elif name == "open":
            mode = None
            if node.args and isinstance(node.args[0], ast.Constant):
                mode = node.args[0].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and any(c in mode for c in "wa") and "newline" not in kwargs:
                offenders.append((node.lineno, "open() without newline='\\n'"))
    return offenders


def test_no_python_310_only_or_crlf_text_writes():
    """Guard every shipped Python file, not just the engine package.

    ``scripts/verify_release.py`` is part of the release pipeline and had the same
    3.10-only call, so the scan is recursive over both directories.
    """
    offenders = {}
    roots = [REPO_ROOT / "src" / "teamwork", REPO_ROOT / "scripts"]
    for base in roots:
        for module_path in sorted(base.rglob("*.py")):
            found = _unsafe_text_writes(module_path)
            if found:
                offenders[str(module_path.relative_to(REPO_ROOT))] = found
    assert offenders == {}, f"unsafe text writes: {offenders}"


def _python_310_only_writes(module_path):
    """Line numbers of ``write_text`` calls that may pass the 3.10-only kwarg.

    ``kw.arg is None`` is a ``**kwargs`` splat, which can carry ``newline`` just
    as easily as a literal keyword, so it is reported too. An alias
    (``wt = Path.write_text``), a ``getattr`` lookup or the positional fourth
    argument are not detected; those are rare enough to accept as a gap that a
    reviewer catches, rather than turning this into a type checker.
    """
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
    except SyntaxError:
        # A file that does not parse under the running interpreter is another
        # matrix cell's problem; this guard only speaks about newline keywords.
        return []
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "write_text"
        and any(kw.arg == "newline" or kw.arg is None for kw in node.keywords)
    ]


def test_no_fixture_uses_the_python_310_only_newline_keyword():
    """The suite runs on the same 3x3 matrix as the package, 3.9 included.

    ``Path.write_text(newline=...)`` is 3.10+ only, so a *fixture* that pins its
    newlines that way looks correct on a modern local interpreter and raises
    ``TypeError`` in every 3.9 CI cell. Measured on the release-consistency
    fixtures: the fix for a Windows CRLF defect broke nine matrix cells instead of
    two. Only this one trap is scanned for ``tests/``; the broader
    ``open()``-without-newline rule is a Windows-correctness rule the suite has
    not adopted, and folding it in here would fail 50+ pre-existing call sites.
    """
    offenders = {}
    for module_path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        found = _python_310_only_writes(module_path)
        if found:
            offenders[str(module_path.relative_to(REPO_ROOT))] = found
    assert offenders == {}, f"3.10-only write_text(newline=...) in tests: {offenders}"


def test_engine_exposes_the_lf_write_helper():
    from teamwork import engine

    assert callable(engine.write_lf)


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
    """The committed constitution must not embed a machine path.

    It uses the ``<script>`` placeholder, which ``agents-md`` substitutes with the
    portable command; an absolute checkout path here reached AGENTS.md 13 times
    before the split (CI's privacy job caught it).
    """
    template = (REPO_ROOT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<script>" in template
    for machine_path in ("/home/", "/Users/", "C:\\Users"):
        assert machine_path not in template, machine_path


# --------------------------------------------------------------------------- #
# Architecture.md section 2 map: the module map must match the shipped tree
# --------------------------------------------------------------------------- #


def _architecture_tree_section() -> str:
    """Return the frozen repository-layout block from Architecture section 2."""
    text = (REPO_ROOT / "docs" / "Team" / "Architecture.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```[a-z]*\n(.*?)```", text, re.S)
    return next(block for block in blocks if block.lstrip().startswith("Teamwork/"))


def _tree_children(block: str, head: str) -> list[str]:
    """Nested entries of the top-level ``head`` branch, in document order."""
    lines = block.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line.startswith(("├── ", "└── ")) and line.strip()[4:].startswith(head)
    )
    nested: list[str] = []
    for line in lines[start + 1 :]:
        if not line.startswith("│"):
            break  # the next top-level branch closes this one
        if re.search(r"[├└]── ", line):
            nested.append(line)
    return nested


def test_architecture_lists_exactly_the_shipped_modules():
    block = _architecture_tree_section()
    listed = sorted(
        re.findall(r"[├└]── ([a-z_]+\.py)", " ".join(_tree_children(block, "src/teamwork/")))
    )
    shipped = sorted(path.name for path in SRC_TEAMWORK.glob("*.py"))
    assert listed == shipped


def test_architecture_lists_exactly_the_shipped_scripts():
    block = _architecture_tree_section()
    listed = sorted(
        re.findall(r"[├└]── ([a-z_]+\.py)", " ".join(_tree_children(block, "scripts/")))
    )
    shipped = sorted(path.name for path in (REPO_ROOT / "scripts").glob("*.py"))
    assert listed == shipped


def test_architecture_section_2_does_not_quote_a_version():
    """The falsifier of D-20261019-Architect, enforced as a test.

    Section 2 must never restate ``__version__``: a map that repeats a value it
    does not own drifts silently at the next bump (it said 1.0.2 while the code
    shipped 1.1.0). ``version.py`` is named as the single source instead.
    """
    text = (REPO_ROOT / "docs" / "Team" / "Architecture.md").read_text(encoding="utf-8")
    section = text.split("## 2. Frozen repository layout")[1].split("## 3.")[0]
    assert "version.py            # the single version source" in section
    assert not re.search(r'version\.py\s+#[^\n]*__version__ = "\d', section), (
        "section 2 quotes a version literal; D-20261019-Architect forbids it"
    )


def test_architecture_dependency_direction_matches_the_imports():
    """Section 3's arrows must describe the real level-1 relative imports."""
    allowed = {
        "config.py": {"resources"},
        "io.py": {"portable"},
        "names.py": {"config"},
        "layout.py": {"config", "io", "names"},
        "records.py": {"config", "io", "layout", "names"},
    }
    for name, permitted in allowed.items():
        tree = _parse(SRC_TEAMWORK / name)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    imported.add(node.module.split(".")[0])
                else:
                    imported.update(alias.name.split(".")[0] for alias in node.names)
        imported -= {"__future__"}
        assert imported <= permitted, f"{name} imports {sorted(imported - permitted)}"


def test_architecture_ownership_table_assigns_every_shipped_file():
    """No committed deliverable may be left without exactly one writer lane."""
    text = (REPO_ROOT / "docs" / "Team" / "Architecture.md").read_text(encoding="utf-8")
    table = text.split("**File ownership (one writer per file) is binding for parallel work:**")[1]
    table = table.split("## ")[0]
    owned = " ".join(
        match.group(2) for match in re.finditer(r"^\| ([a-z0-9-]+) \| (.+?) \|$", table, re.M)
    )
    for required in (
        "src/teamwork/**",
        "tests/unit/**",
        "tests/integration/**",
        "tests/acceptance/**",
        "scripts/privacy_scan.py",
        "scripts/build_pi_package.py",
        "templates/pi-package",
        "references/",
        ".agents/skills/",
        "docs/Team/Architecture.md",
        "docs/Team/Plan.md",
        "docs/Team/Board.md",
        "docs/Team/Research.md",
        "docs/Team/Risks.md",
        "docs/Team/Costs.md",
        "docs/Team/Release.md",
        "docs/Team/Design.md",
        "README.md",
    ):
        assert required in owned, f"no ownership row covers {required}"
    assert owned.count("docs/Team/Architecture.md") == 1
