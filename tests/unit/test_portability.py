"""Unit tests for the portability contract and relocated resource resolution.

Covers [Architecture](../../../docs/Team/Architecture.md) sections 3 and 6:
the OS seam in ``teamwork.portable``, the source-level portability rules, and
the fact that ``teamwork.engine`` resolves its bundle from the real repo root
rather than a hardcoded path.

Owner: architect. Task: T-0003.
"""

from __future__ import annotations

import ast
import io
import os
import re
import shlex
import subprocess
import sys
import textwrap
import tokenize
from pathlib import Path

import pytest

from teamwork import engine, portable, resources

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_TEAMWORK = REPO_ROOT / "src" / "teamwork"

FORBIDDEN_MODULES = frozenset({"fcntl", "termios", "pwd", "grp", "resource"})

SHELL_TRUE_RE = re.compile(r"shell\s*=\s*True")

SHIPPED_ROOTS = (SRC_TEAMWORK, REPO_ROOT / "scripts")


def _source_files():
    """Every shipped Python module: the runtime package and the sdist's scripts."""
    return sorted(path for root in SHIPPED_ROOTS for path in root.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _masked_source(path: Path) -> str:
    """The module's source with every comment and string literal blanked out.

    ``check_release_consistency.py`` *states* the rule in its header ("standard
    library only, no ``shell=True``"), and a regex over the raw text read that
    sentence as a violation. Masking keeps the line structure, so a real hit still
    reports the line a reader can open.
    """
    text = path.read_text(encoding="utf-8")
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def absolute(position: tuple[int, int]) -> int:
        row, column = position
        return offsets[row - 1] + column

    parts = []
    cursor = 0
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        start, end = absolute(token.start), absolute(token.end)
        parts.append(text[cursor:start])
        parts.append("".join("\n" if char == "\n" else " " for char in text[start:end]))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def test_pid_alive_current_process_is_true():
    assert portable.pid_alive(os.getpid()) is True


def test_pid_alive_rejects_non_positive_pids():
    assert portable.pid_alive(0) is False
    assert portable.pid_alive(-1) is False


def test_pid_alive_an_unlikely_pid_is_false():
    """A pid no process holds reports dead, not alive (the arbitrary-pid branch)."""
    assert portable.pid_alive(2**30) is False


def test_pid_alive_certainly_dead_process_is_false():
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

    assert portable.pid_alive(0) is False
    assert calls == [4321]


def test_pid_alive_windows_branch_can_report_dead(monkeypatch):
    monkeypatch.setattr(portable, "IS_WINDOWS", True)
    monkeypatch.setattr(portable, "_windows_pid_alive", lambda pid: False)
    assert portable.pid_alive(987654) is False


def test_newline_for_is_always_lf():
    assert portable.newline_for() == "\n"
    assert portable.newline_for(True) == "\n"
    assert portable.newline_for(False) == ""


def test_python_executable_is_non_empty_str():
    exe = portable.python_executable()
    assert isinstance(exe, str)
    assert exe.strip() != ""


def test_source_scan_sees_runtime_modules():
    """Guard against the scans passing vacuously on an empty file list."""
    names = {path.name for path in _source_files()}
    assert {"engine.py", "portable.py", "resources.py"} <= names
    assert {"build_pi_package.py", "privacy_scan.py"} <= names


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
        text = _masked_source(path)
        for match in SHELL_TRUE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path}:{line} shell=True")
    assert offenders == [], "shell=True must never be used: " + "; ".join(offenders)


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


def _checkout_with_spaces(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A fake checkout whose interpreter and shim sit under paths with spaces.

    ``tmp_path`` carries a space on this project's hosts and a backslash on
    Windows, which is exactly the shape that broke the unquoted join.
    """
    exe = tmp_path / "Py thon 3.13" / "python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    shim = tmp_path / "check out" / "scripts" / "teamwork.py"
    shim.parent.mkdir(parents=True)
    shim.write_text("", encoding="utf-8")
    monkeypatch.setattr(resources.shutil, "which", lambda _name: None)
    monkeypatch.setattr(resources.sys, "executable", str(exe))
    monkeypatch.setattr(
        resources,
        "asset",
        lambda *parts: shim if parts == ("scripts", "teamwork.py") else tmp_path / "missing",
    )
    return [str(exe), str(shim)]


def test_self_invocation_argv_is_the_structured_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = _checkout_with_spaces(tmp_path, monkeypatch)
    assert resources.self_invocation_argv() == expected


def test_self_invocation_survives_a_path_with_spaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression, T-0001: the unquoted join lost every path separator.

    Measured at 7db810a: a Windows interpreter path under a home directory was
    split at every backslash - POSIX ``shlex`` reads one as an escape - so a path
    like ``<home>/<checkout>/python.exe`` came back as three unrelated tokens
    instead of one, and the runnable-command test died with
    ``FileNotFoundError [WinError 2]``.
    """
    expected = _checkout_with_spaces(tmp_path, monkeypatch)
    assert shlex.split(resources.self_invocation(), posix=True) == expected


def test_self_invocation_quotes_an_apostrophe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``'`` in a path must not close the quote early."""
    exe = tmp_path / "O'Brien" / "python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(resources.shutil, "which", lambda _name: None)
    monkeypatch.setattr(resources.sys, "executable", str(exe))
    monkeypatch.setattr(resources, "asset", lambda *parts: tmp_path / "missing")
    assert shlex.split(resources.self_invocation(), posix=True) == [
        str(exe),
        "-m",
        "teamwork",
    ]


def test_self_invocation_prefers_the_console_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preference 1 stays a bare ``teamwork`` - nothing to quote, nothing local."""
    monkeypatch.setattr(resources.shutil, "which", lambda _name: "/usr/local/bin/teamwork")
    assert resources.self_invocation_argv() == ["teamwork"]
    assert resources.self_invocation() == "teamwork"


def test_self_invocation_falls_back_to_the_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preference 3 renders a space in the interpreter path as one argument."""
    monkeypatch.setattr(resources.shutil, "which", lambda _name: None)
    monkeypatch.setattr(resources.sys, "executable", "/opt/py thon/bin/python3")
    monkeypatch.setattr(resources, "asset", lambda *parts: Path("/nonexistent/shim.py"))
    expected = ["/opt/py thon/bin/python3", "-m", "teamwork"]
    assert resources.self_invocation_argv() == expected
    assert shlex.split(resources.self_invocation(), posix=True) == expected


def test_self_invocation_quotes_only_what_needs_it() -> None:
    """Shell-safe arguments stay bare, so a POSIX command line stays readable."""
    assert resources._shell_arg("teamwork") == "teamwork"
    assert resources._shell_arg("-m") == "-m"
    assert resources._shell_arg("/usr/bin/python3") == "/usr/bin/python3"
    assert resources._shell_arg("C:\\py\\python.exe") == "'C:\\py\\python.exe'"
    assert resources._shell_arg("/opt/py thon/python3") == "'/opt/py thon/python3'"


def _unsafe_text_writes(module_path):
    """Return the line numbers of text writes that emit CRLF on Windows.

    The 3.9-era ban on ``Path.write_text(..., newline=...)`` is retired by the
    3.11 floor: the keyword exists from 3.10 and is a normal API here. What stays
    a defect is ``open(..., "w"/"a")`` without ``newline="\\n"``, which emits
    CRLF on Windows and breaks byte-identical output. Checked statically, so the
    guard runs on every platform.
    """
    import ast

    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None)
        kwargs = {kw.arg for kw in node.keywords}
        if name == "open":
            mode = None
            if node.args and isinstance(node.args[0], ast.Constant):
                mode = node.args[0].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and any(c in mode for c in "wa") and "newline" not in kwargs:
                offenders.append((node.lineno, "open() without newline='\\n'"))
    return offenders


def test_no_crlf_text_writes():
    """Guard every shipped Python file, not just the engine package.

    ``scripts/verify_release.py`` is part of the release pipeline, so the scan is
    recursive over both directories.
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
        source = module_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return _python_310_only_writes_in(source)


def _python_310_only_writes_in(source):
    """Line numbers of 3.10-only ``write_text(newline=...)`` calls in ``source``.

    Split out from the path-based scanner because the same trap hides inside the
    Python heredocs of ``.github/workflows/*.yml``: the text is never a module on
    disk, so a file walk cannot see it (see
    ``test_no_workflow_python_uses_the_python_310_only_newline_keyword``).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "write_text"
        and any(kw.arg == "newline" or kw.arg is None for kw in node.keywords)
    ]


def test_the_retired_310_newline_guard_still_detects_its_pattern():
    """The 3.11 floor retires the ban; the detector stays proven for a re-lower.

    ``Path.write_text(newline=...)`` is legal from 3.10, so a fixture may use it
    now. This asserts the scanner still names the spelling a future floor drop
    would have to catch again, instead of keeping a tree-wide rule that no longer
    protects a supported interpreter.
    """
    sample = "from pathlib import Path\n\nPath('x').write_text('a', newline='\\n')\n"
    assert _python_310_only_writes_in(sample) == [3]
    assert _python_310_only_writes(REPO_ROOT / "tests" / "unit" / "test_portability.py") == []


_HEREDOC_RE = re.compile(r"<<-?[ \t]*['\"]?(?P<tag>[A-Za-z_][A-Za-z0-9_]*)['\"]?[ \t]*$")


def _embedded_python_blocks(workflow_path):
    """Every Python heredoc in a workflow, as ``(first line number, source)``.

    A workflow's Python is not a module on disk: it is a ``python - <<'PY'`` body
    inside YAML, extracted at run time by the integration test that executes it.
    Nothing static ever read it, so ``release.yml`` shipped a
    ``Path.write_text(..., newline="\\n")`` that raised ``TypeError`` in every
    3.9 matrix cell while this file's other guards were green. Only heredocs
    whose opener line invokes ``python`` are collected; ``python -c`` one-liners
    are not scanned - an accepted gap, stated here rather than hidden.
    """
    lines = workflow_path.read_text(encoding="utf-8").splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = _HEREDOC_RE.search(line)
        if match is None or "python" not in line:
            index += 1
            continue
        tag = match.group("tag")
        body = []
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip() != tag:
            body.append(lines[cursor])
            cursor += 1
        blocks.append((index + 2, textwrap.dedent("\n".join(body))))
        index = cursor + 1
    return blocks


def test_the_workflow_python_scanner_still_finds_the_retired_pattern(tmp_path):
    """A workflow heredoc is not a module on disk, so the reader is tested here.

    CI run 40728749217 once failed the 3.9 cells on
    ``write_text(..., newline=...)`` inside the npm publish step. The 3.11 floor
    makes that keyword legal, so the tree-wide ban is retired; the extractor and
    the detector stay proven so a future floor drop re-enables the same scan
    without re-deriving it.
    """
    workflow = tmp_path / "ci.yml"
    workflow.write_text(
        "steps:\n"
        "  - run: |\n"
        "      python - <<'PY'\n"
        "      from pathlib import Path\n"
        "      Path('x').write_text('a', newline='\\n')\n"
        "      PY\n",
        encoding="utf-8",
    )
    found = []
    for first_line, source in _embedded_python_blocks(workflow):
        found.extend(first_line + line - 1 for line in _python_310_only_writes_in(source))
    assert found == [5], found


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
            break
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
