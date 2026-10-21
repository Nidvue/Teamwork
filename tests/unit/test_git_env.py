"""The child environment the harnesses build: platform variables in, caller git config out.

Layer ``unit``, area ``git-env``, owner Developer (T-0011). Two requirements
pull in opposite directions and a child environment that satisfies only one of
them is a defect:

* the platform's own variables must reach the child (on Windows the
  interpreter's hash seed comes from the OS RNG, which needs ``SystemRoot``,
  ``TEMP`` and ``TMP``; without them the child dies before it runs a command);
* the caller's git configuration must not (it decides where hooks are written,
  what a fresh branch is called and whether a commit is signed).

``tests/gitenv.py`` is the one place that rule lives, so it is the one place
these tests pin it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.gitenv import GIT_CONFIG_VARS, GIT_REPO_VARS, HERMETIC_GIT, child_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_platform_variables_reach_the_child(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Windows RNG needs SystemRoot/TEMP/TMP; a hand-built env drops them.

    This is the defect the fix exists for: the child died with "Fatal Python
    error: _Py_HashRandomization_Init" before it could run a command.
    """
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setenv("TEMP", r"C:\Users\runneradmin\AppData\Local\Temp")
    monkeypatch.setenv("TMP", r"C:\Users\runneradmin\AppData\Local\Temp")
    monkeypatch.setenv("ComSpec", r"C:\Windows\system32\cmd.exe")

    env = child_env()

    for name in ("SystemRoot", "TEMP", "TMP", "ComSpec"):
        assert env.get(name) == os.environ[name], f"{name} did not reach the child"


def test_the_callers_git_configuration_does_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inherited GIT_CONFIG_GLOBAL would decide what the harness measures.

    ``core.hooksPath`` moves the hook, ``init.defaultBranch`` renames the
    branch and ``commit.gpgsign`` fails every commit; git also reads the
    system config and ``$XDG_CONFIG_HOME/git/config`` besides the global one.
    """
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text(
        "[user]\n\tname = Operator\n\temail = operator@example.com\n"
        "[commit]\n\tgpgsign = true\n[init]\n\tdefaultBranch = trunk\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(hostile))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    env = child_env()

    for name in GIT_CONFIG_VARS:
        if name == "GIT_CONFIG_GLOBAL":
            # this one is pinned, not removed
            assert env[name] == os.devnull, f"{name} was not pinned"
        else:
            assert name not in env, f"{name} reached the child: {env.get(name)!r}"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_a_child_git_run_ignores_a_hostile_caller_config(tmp_path: Path) -> None:
    """The proof, not the accident: git in the child does not see the caller's config.

    A future edit that drops the pins would hand every fixture a foreign
    ``user.name``, a ``commit.gpgsign`` that fails each commit and an
    ``init.defaultBranch`` that renames the branch under test.
    """
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text(
        "[user]\n\tname = Operator\n\temail = operator@example.com\n"
        "[commit]\n\tgpgsign = true\n[init]\n\tdefaultBranch = trunk\n",
        encoding="utf-8",
    )
    env = child_env(
        HOME=str(tmp_path),
        GIT_AUTHOR_NAME="Tester",
        GIT_AUTHOR_EMAIL="tester@agents.nidvue.com",
        GIT_COMMITTER_NAME="Tester",
        GIT_COMMITTER_EMAIL="tester@agents.nidvue.com",
    )
    # the caller's configuration is what the child must not see: a caller
    # carries it in the environment, so the child's environment is built from
    # an environment that carries it, and the helper must take it back out.
    caller = dict(os.environ)
    caller["GIT_CONFIG_GLOBAL"] = str(hostile)
    caller["GIT_CONFIG_SYSTEM"] = str(hostile)
    caller["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    env = child_env(
        caller,
        HOME=str(tmp_path),
        GIT_AUTHOR_NAME="Tester",
        GIT_AUTHOR_EMAIL="tester@agents.nidvue.com",
        GIT_COMMITTER_NAME="Tester",
        GIT_COMMITTER_EMAIL="tester@agents.nidvue.com",
    )

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo), *argv],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "x")

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert branch != "trunk", "the caller's init.defaultBranch reached the child"
    author = git("log", "-1", "--format=%an <%ae>").stdout.strip()
    assert author == "Tester <tester@agents.nidvue.com>", author


def test_the_callers_repository_pointers_do_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inherited GIT_DIR would make the child act on the caller's repository.

    This is not a hermetic failure but a wrong-repository failure: the child
    would write into the repository the developer's shell points at, instead of
    the throwaway tree the test made.
    """
    for name in GIT_REPO_VARS:
        monkeypatch.setenv(name, str(tmp_path / "elsewhere"))

    env = child_env()

    for name in GIT_REPO_VARS:
        assert name not in env, f"{name} reached the child: {env.get(name)!r}"


def test_the_overrides_win_over_the_pins() -> None:
    """A site that wants its own HOME or identity still gets it."""
    env = child_env(HOME="/tmp/throwaway", GIT_AUTHOR_NAME="Tester")
    assert env["HOME"] == "/tmp/throwaway"
    assert env["GIT_AUTHOR_NAME"] == "Tester"
    # and the pins are still there
    for name, value in HERMETIC_GIT.items():
        assert env[name] == value


def test_the_helper_is_importable_from_every_test_layer() -> None:
    """The rule lives in one place, so all three layers must be able to import it.

    A helper that only one layer can import is a helper the other two will
    re-implement, and the rule will drift.
    """
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from tests.gitenv import child_env;"
        "print(child_env(HOME='x')['GIT_CONFIG_GLOBAL'])"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe, str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == os.devnull
