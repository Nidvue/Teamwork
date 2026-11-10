"""Integration: the portability contract, executed as processes rather than read.

Three claims, all of them about a host other than the one that wrote the code:

1. **The CLI is invocable on every supported platform, including from a path with
   a space.** This host's checkout path contains a space (`C:\\Users\\Ping Zhao\\...`),
   which is the case that breaks an unquoted `sys.executable <shim>` string. Each
   invocation form is run as a real subprocess from a *copy* of the checkout placed
   under a deliberately space-containing directory: the checkout shim, the shim run
   from a space-containing cwd, `-m teamwork`, and the installed console script (a
   skip naming the missing entry point when it is not installed for this
   interpreter).
2. **A test that needs a privilege or an external tool states its guard.** On a
   host without Developer Mode a symlink call raises `WinError 1314`, and on a host
   without GNU make `["make", ...]` raises `FileNotFoundError`; both turn a green
   suite red for a contributor while CI stays green. A privilege/tool-dependent test
   must therefore carry a `skipif`/`skip`/`importorskip`/guarding fixture that names
   the reason.
3. **The guard policy bites.** The scanner below is a static pass over a `tests/`
   tree, and it is shown to bite on synthetic modules: an unguarded symlink test and
   an unguarded `make` invocation are each reported by path, line and capability, and
   the guarded twin of each (named `skipif`, autouse fixture, in-body `skip()`) is
   not reported. Its application to this tree is a separate change and belongs to
   whoever lands the guards: `test_every_test_that_needs_a_privilege_or_a_tool_is_guarded`
   and the end-to-end run of the guarded modules live on
   `developer-1/t-0002-guard-every-symlink-dependent-test-so-th`, not here, because
   the guards do not exist on this revision yet and asserting them here would make
   this module red for a reason that is not its own. Likewise the shell-safety of
   `resources.self_invocation()` (a spaced path splits into unusable tokens) is
   fixed and covered on `developer-1/t-0001-fix-resources-self-invocation-the-return`
   by `tests/unit/test_portability.py`, so it is deliberately not duplicated here.

Owner: tester. Task: T-0001.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

#: The bundle entries a checkout needs to run a real command (`--version`,
#: `selftest`). Copied rather than moved: the fixture never touches the checkout.
CHECKOUT_ENTRIES = ("src", "scripts", "roles", "references", "templates", "SKILL.md")


# --------------------------------------------------------------------------- #
# A checkout that lives under a path with a space
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def spaced_checkout(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the runnable checkout under a directory whose name has a space."""
    root = tmp_path_factory.mktemp("portability") / "checkout with a space"
    root.mkdir(parents=True)
    for entry in CHECKOUT_ENTRIES:
        source = REPO_ROOT / entry
        if source.is_dir():
            shutil.copytree(source, root / entry, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, root / entry)
    assert " " in str(root), f"the fixture path has no space in it: {root}"
    return root


def checkout_env(root: Path) -> dict[str, str]:
    """A clean environment: the copy's `src` on the path, the copy as the bundle."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env.pop("PYTHONPATH", None)
    env["TEAMWORK_SKILL_DIR"] = str(root)
    return env


def run(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def assert_version(stdout: str, argv: list[str], result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, (
        f"{argv} exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert stdout.strip().startswith("teamwork "), (
        f"{argv} printed {stdout.strip()!r}, not a version"
    )


def test_the_checkout_shim_runs_from_a_path_with_a_space(spaced_checkout: Path) -> None:
    """`python "<repo>/scripts/teamwork.py"` must work when the repo path has a space."""
    argv = [sys.executable, str(spaced_checkout / "scripts" / "teamwork.py"), "--version"]
    result = run(argv, cwd=spaced_checkout, env=checkout_env(spaced_checkout))
    assert_version(result.stdout, argv, result)


def test_the_shim_runs_from_a_working_directory_with_a_space(spaced_checkout: Path) -> None:
    """The cwd needs quoting too: `teamwork` writes `.pi/` and `docs/` under it."""
    cwd = spaced_checkout / "work dir with a space"
    cwd.mkdir()
    argv = [sys.executable, str(spaced_checkout / "scripts" / "teamwork.py"), "--version"]
    result = run(argv, cwd=cwd, env=checkout_env(spaced_checkout))
    assert_version(result.stdout, argv, result)


def test_the_module_invocation_runs_from_a_path_with_a_space(spaced_checkout: Path) -> None:
    """`python -m teamwork` is the third documented preference order; it must work too."""
    env = checkout_env(spaced_checkout)
    env["PYTHONPATH"] = str(spaced_checkout / "src")
    argv = [sys.executable, "-m", "teamwork", "--version"]
    result = run(argv, cwd=spaced_checkout, env=env)
    assert_version(result.stdout, argv, result)


def console_script() -> Path | None:
    """The `teamwork` console script installed next to the running interpreter."""
    bindir = Path(sys.executable).parent
    for name in ("teamwork.exe", "teamwork"):
        candidate = bindir / name
        if candidate.is_file():
            return candidate
    found = shutil.which("teamwork")
    return Path(found) if found else None


def test_the_console_script_runs_from_a_path_with_a_space(tmp_path: Path) -> None:
    """The installed entry point, run from a space-containing cwd."""
    script = console_script()
    if script is None:
        pytest.skip(
            "the `teamwork` console script is not installed for "
            f"{sys.executable} (checked {Path(sys.executable).parent} and PATH) - "
            "`pip install -e .` into this interpreter to exercise this path"
        )
    cwd = tmp_path / "console run dir with a space"
    cwd.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    argv = [str(script), "--version"]
    result = run(argv, cwd=cwd, env=env)
    assert_version(result.stdout, argv, result)


# --------------------------------------------------------------------------- #
# The skip-guard policy
# --------------------------------------------------------------------------- #

#: Calls that need a privilege this host may not have (a symlink needs Developer
#: Mode or SeCreateSymbolicLinkPrivilege on Windows).
PRIVILEGE_CALLS = frozenset({"symlink", "symlink_to", "mkfifo", "mknod", "mknod_socket"})

#: Programs the project does not depend on at runtime; CI installs them, a
#: contributor's host may not have them.
EXTERNAL_TOOLS = frozenset(
    {"make", "mkdocs", "npm", "npx", "node", "gh", "docker", "pandoc", "dot", "git-lfs", "lfs"}
)

#: `pytest` markers/attributes that carry a guard.
GUARD_NAMES = frozenset({"skipif", "skip", "importorskip", "xfail"})

SUBPROCESS_CALLS = frozenset({"run", "Popen", "check_output", "check_call", "call"})

#: Tokens that mark a module-level name as a guard when it is used as a decorator
#: (`needs_symlinks = pytest.mark.skipif(...)`).
GUARD_SOURCE_TOKENS = ("skipif", "mark.skip", "importorskip")


def _dotted(node: ast.AST) -> str:
    """`pytest.mark.skipif` / `Name` -> a dotted string, `""` for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _argv0_tool(call: ast.Call) -> str | None:
    """The external program a `subprocess.*` call runs, if it is one we know."""
    if not call.args:
        return None
    first = call.args[0]
    if not isinstance(first, (ast.List, ast.Tuple)) or not first.elts:
        return None
    head = first.elts[0]
    # `[sys.executable, "-m", "mkdocs", ...]` runs an external *module*.
    if _dotted(head) == "sys.executable" or (_const_str(head) or "").endswith(
        ("python", "python3")
    ):
        if len(first.elts) >= 3 and _const_str(first.elts[1]) == "-m":
            module = (_const_str(first.elts[2]) or "").split(".")[0]
            return module if module in EXTERNAL_TOOLS else None
        return None
    program = _const_str(head)
    if program is None:
        return None
    name = Path(program).name.lower()
    if name.endswith(".exe"):
        name = name[: -len(".exe")]
    return name if name in EXTERNAL_TOOLS else None


def capabilities(statements: list[ast.stmt]) -> set[str]:
    """What a body needs from the host: `privilege:symlink`, `tool:make`, ..."""
    needed: set[str] = set()
    for node in _walk(statements):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted(node.func)
        attribute = dotted.rsplit(".", 1)[-1]
        if attribute in PRIVILEGE_CALLS:
            needed.add(f"privilege:{attribute}")
        elif attribute in SUBPROCESS_CALLS:
            tool = _argv0_tool(node)
            if tool:
                needed.add(f"tool:{tool}")
    return needed


def _walk(statements: list[ast.stmt]):
    for statement in statements:
        yield from ast.walk(statement)


def _has_skip_call(statements: list[ast.stmt]) -> bool:
    for node in _walk(statements):
        if isinstance(node, ast.Call):
            attribute = _dotted(node.func).rsplit(".", 1)[-1]
            if attribute in {"skip", "importorskip", "skip_module"}:
                return True
    return False


class ModuleGuards:
    """What a module (or an ancestor `conftest.py`) provides as a skip guard."""

    def __init__(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        self.tree = ast.parse(text, filename=str(path))
        self.guard_names: set[str] = set()
        self.module_guard = False
        self.autouse_guard = False
        self.fixture_guards: set[str] = set()
        self.helper_guards: set[str] = set()
        for statement in self.tree.body:
            if isinstance(statement, ast.Assign):
                value = ast.unparse(statement.value)
                target = _dotted(statement.targets[0]) if statement.targets else ""
                if target == "pytestmark" and any(token in value for token in GUARD_SOURCE_TOKENS):
                    self.module_guard = True
                if any(token in value for token in GUARD_SOURCE_TOKENS):
                    for target_node in statement.targets:
                        if isinstance(target_node, ast.Name):
                            self.guard_names.add(target_node.id)
            if isinstance(statement, ast.FunctionDef):
                skip = _has_skip_call(statement.body)
                if not skip:
                    continue
                if _is_fixture(statement):
                    self.fixture_guards.add(statement.name)
                    if _is_autouse(statement):
                        self.autouse_guard = True
                else:
                    # A `require_make()`-style helper that skips is a guard too: the
                    # caller names the tool once and every test that calls it skips.
                    self.helper_guards.add(statement.name)


def _is_fixture(node: ast.FunctionDef) -> bool:
    return any(
        _dotted(dec.func if isinstance(dec, ast.Call) else dec).endswith("fixture")
        for dec in node.decorator_list
    )


def _is_autouse(node: ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "autouse" and _const_str(keyword.value) is None:
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    return True
    return False


def _decorator_guard(node: ast.FunctionDef, guard_names: set[str]) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        parts = set(_dotted(target).split("."))
        if parts & GUARD_NAMES:
            return True
        if _dotted(target) in guard_names:
            return True
    return False


def _calls_any(statements: list[ast.stmt], names: set[str]) -> bool:
    if not names:
        return False
    return any(
        isinstance(node, ast.Call) and _dotted(node.func).rsplit(".", 1)[-1] in names
        for node in _walk(statements)
    )


def _conftest_guards(directory: Path) -> bool:
    """True when `directory` or an ancestor inside `tests/` has an autouse skip fixture."""
    for parent in [directory, *directory.parents]:
        conftest = parent / "conftest.py"
        if conftest.is_file() and ModuleGuards(conftest).autouse_guard:
            return True
        if parent == TESTS_ROOT:
            break
    return False


def _label(path: Path) -> str:
    """Repository-relative when the file is in the tree, absolute for a synthetic root."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def unguarded_tests(root: Path = TESTS_ROOT) -> list[str]:
    """`path:line name needs <capability>` for every test without a guard."""
    problems: list[str] = []
    for path in sorted(root.rglob("test_*.py")):
        module = ModuleGuards(path)
        conftest_guard = _conftest_guards(path.parent)
        for node in module.tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            needed = capabilities(node.body)
            if not needed:
                continue
            guarded = (
                module.module_guard
                or module.autouse_guard
                or conftest_guard
                or _has_skip_call(node.body)
                or _decorator_guard(node, module.guard_names)
                or bool(set(argument.arg for argument in node.args.args) & module.fixture_guards)
                or _calls_any(node.body, module.helper_guards)
            )
            if not guarded:
                problems.append(
                    f"{_label(path)}:{node.lineno} {node.name} "
                    f"needs {', '.join(sorted(needed))} without a skip guard"
                )
    return problems


#: A module that needs both capabilities, in the three shapes the policy must catch.
UNGUARDED_SOURCE = """
import os
import subprocess


def test_makes_a_symlink(tmp_path):
    os.symlink("target", tmp_path / "link")


def test_runs_make():
    subprocess.run(["make", "help"], check=True)
"""

GUARDED_SOURCE = """
import os
import shutil
import subprocess

import pytest

needs_symlinks = pytest.mark.skipif(os.name == "nt", reason="symlink needs Developer Mode")


def require_make():
    if shutil.which("make") is None:
        pytest.skip("make is not installed")


@pytest.fixture(autouse=True)
def require_make_fixture():
    require_make()


@needs_symlinks
def test_makes_a_symlink(tmp_path):
    os.symlink("target", tmp_path / "link")


def test_runs_make():
    require_make()
    subprocess.run(["make", "help"], check=True)
"""


def test_the_guard_scan_bites_on_an_unguarded_test(tmp_path: Path) -> None:
    """Delete the guard and the policy must report it - by path, line and capability."""
    (tmp_path / "test_unguarded.py").write_text(UNGUARDED_SOURCE, encoding="utf-8")
    problems = unguarded_tests(tmp_path)

    assert len(problems) == 2, problems
    assert any("privilege:symlink" in problem for problem in problems), problems
    assert any("tool:make" in problem for problem in problems), problems


def test_the_guard_scan_accepts_every_guard_shape_the_tree_uses(tmp_path: Path) -> None:
    """A named `skipif` decorator, an autouse fixture and an in-body skip all count."""
    (tmp_path / "test_guarded.py").write_text(GUARDED_SOURCE, encoding="utf-8")
    assert unguarded_tests(tmp_path) == []


# --- runtime-compatibility guard -------------------------------------------
#
# `pyproject.toml` still declares `requires-python = ">=3.9"`, but both modules
# below carry `from __future__ import annotations`. That makes an annotation such
# as `def f(node: ast.AST | None)` legal on 3.9, while the *same spelling in an
# evaluated position* - `isinstance(x, ast.List | ast.Tuple)` - is a PEP 604
# union and raises `TypeError: unsupported operand type(s) for |` on 3.9. That
# is exactly how the 3.9 CI job went red on revision 20c7d23. This guard is a
# static pass, so it fails on the developer's own interpreter too.

UNION_GUARDED_MODULES = (
    Path(__file__).with_name("test_ci_release_flow.py"),
    Path(__file__),
)


def _isinstance_union_lines(tree: ast.AST) -> list[int]:
    """Line numbers of `isinstance`/`issubclass` calls taking an `X | Y` argument."""
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name not in {"isinstance", "issubclass"}:
            continue
        arguments = list(node.args) + [keyword.value for keyword in node.keywords]
        if any(
            isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitOr)
            for argument in arguments
            for inner in ast.walk(argument)
        ):
            offenders.append(node.lineno)
    return offenders


def test_no_isinstance_union_a_python_39_runtime_cannot_evaluate() -> None:
    """No `isinstance(x, X | Y)` in either module: 3.9 raises `TypeError` on it."""
    offenders = [
        f"{module.name}:{line}"
        for module in UNION_GUARDED_MODULES
        for line in _isinstance_union_lines(
            ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        )
    ]
    assert offenders == [], (
        "`isinstance`/`issubclass` takes a PEP 604 union (`X | Y`), which raises "
        "`TypeError: unsupported operand type(s) for |` on Python 3.9: "
        f"{offenders}. Spell it as a tuple: `(ast.List, ast.Tuple)`."
    )


def test_the_union_guard_bites_on_the_spelling_20c7d23_shipped() -> None:
    """The guard reports the exact expression `_argv0_tool` carried at 20c7d23."""
    source = (
        "import ast\n"
        "\n"
        "\n"
        "def _argv0_tool(call):\n"
        "    first = call.args[0]\n"
        "    return isinstance(first, ast.List | ast.Tuple)\n"
    )
    assert _isinstance_union_lines(ast.parse(source)) == [6]
    portable = source.replace("(first, ast.List | ast.Tuple)", "(first, (ast.List, ast.Tuple))")
    assert _isinstance_union_lines(ast.parse(portable)) == []
