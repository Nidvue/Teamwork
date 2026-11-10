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
these tests pin it. The environment is a configuration source of its own, so
the tests cover the file pointers (``GIT_CONFIG_GLOBAL``, ``GIT_CONFIG_SYSTEM``,
``XDG_CONFIG_HOME``), the environment-injected pairs (``GIT_CONFIG_COUNT`` and
its numbered ``GIT_CONFIG_KEY_<n>`` / ``GIT_CONFIG_VALUE_<n>``), the ``--file``
pointer ``GIT_CONFIG`` and the template directory ``GIT_TEMPLATE_DIR``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.gitenv import (
    GIT_CONFIG_PAIR_PREFIXES,
    GIT_CONFIG_VARS,
    GIT_REPO_VARS,
    GIT_TEMPLATE_VAR,
    HERMETIC_GIT,
    child_env,
)

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

    # Windows upper-cases the environment KEYS, so look the value up the way
    # the platform stores it: case-insensitively, or the variable is present and
    # the guard cannot see it.
    for name in ("SystemRoot", "TEMP", "TMP", "ComSpec"):
        stored = next((v for k, v in os.environ.items() if k.upper() == name.upper()), None)
        assert stored is not None, f"{name} was not set in the parent environment"
        reached = next((v for k, v in env.items() if k.upper() == name.upper()), None)
        assert reached == stored, f"{name} did not reach the child"


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


def test_the_callers_quarantine_path_does_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inherited GIT_QUARANTINE_PATH makes the child refuse every ref update.

    The name is written out literally here on purpose. The test above loops
    over ``GIT_REPO_VARS``, so dropping a member from that tuple would shrink
    the loop with it and the test would stay green - which is how the
    quarantine hole survived. A literal cannot shrink: drop
    ``GIT_QUARANTINE_PATH`` from the tuple and this goes red.

    ``GIT_QUARANTINE_PATH`` is git's quarantine object directory (the one a
    clone writes into before the objects are accepted). A child that inherits
    it fails EVERY ref update with "error: ref updates forbidden inside
    quarantine environment" (git exit 1), so the harness measures the
    quarantine instead of the contract.
    """
    monkeypatch.setenv("GIT_QUARANTINE_PATH", str(tmp_path / "quarantine"))

    env = child_env()

    assert "GIT_QUARANTINE_PATH" not in env, (
        f"GIT_QUARANTINE_PATH reached the child: {env.get('GIT_QUARANTINE_PATH')!r}"
    )


def test_a_child_git_run_ignores_a_hostile_quarantine_path(tmp_path: Path) -> None:
    """The proof, not the accident: the child's git still updates refs.

    A future edit that stops removing ``GIT_QUARANTINE_PATH`` hands every
    fixture a git that refuses to commit.
    """
    caller = dict(os.environ)
    caller["GIT_QUARANTINE_PATH"] = str(tmp_path / "quarantine")
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

    assert git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != ""


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


def test_the_environment_injected_config_pairs_do_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GIT_CONFIG_COUNT injects configuration straight into the child.

    Git reads the injected pairs *above* the global file, so the pins do not
    neutralise them: with ``GIT_CONFIG_GLOBAL=os.devnull`` and
    ``GIT_CONFIG_NOSYSTEM=1`` still set, an injected ``commit.gpgsign=true``
    makes every commit in the child fail.
    """
    monkeypatch.setenv("GIT_CONFIG_COUNT", "2")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "commit.gpgsign")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    monkeypatch.setenv("GIT_CONFIG_KEY_1", "init.defaultBranch")
    monkeypatch.setenv("GIT_CONFIG_VALUE_1", "trunk")

    env = child_env()

    assert "GIT_CONFIG_COUNT" not in env, "GIT_CONFIG_COUNT reached the child"
    for name in env:
        for prefix in GIT_CONFIG_PAIR_PREFIXES:
            assert not name.startswith(prefix), f"{name} reached the child"


def test_the_environment_injected_config_does_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GIT_CONFIG is git's --file pointer: a whole config file, by another name.

    The pins point the global config at /dev/null, but this pointer is a
    separate source, so a caller's file would decide what the harness
    measures.
    """
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text(
        "[user]\n\tname = Operator\n\temail = operator@example.com\n"
        "[commit]\n\tgpgsign = true\n[init]\n\tdefaultBranch = trunk\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG", str(hostile))

    env = child_env()

    assert "GIT_CONFIG" not in env, "GIT_CONFIG reached the child"


def test_the_callers_template_directory_does_not_reach_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GIT_TEMPLATE_DIR installs the caller's hooks into every fresh repository.

    It is the environment twin of ``init.templateDir``: git copies the
    template's ``hooks/`` into each repository it creates, so a caller's
    pre-commit hook would run inside the harness.
    """
    monkeypatch.setenv(GIT_TEMPLATE_VAR, str(tmp_path / "template"))

    env = child_env()

    assert GIT_TEMPLATE_VAR not in env, "GIT_TEMPLATE_DIR reached the child"


def test_a_child_git_run_ignores_the_environment_injected_config(tmp_path: Path) -> None:
    """The proof for the injected pairs: the child's git does not see them.

    The pins cannot cover this source, so the helper has to remove it. A
    future edit that stops doing so hands every fixture a
    ``commit.gpgsign`` that fails each commit.
    """
    caller = dict(os.environ)
    caller["GIT_CONFIG_COUNT"] = "1"
    caller["GIT_CONFIG_KEY_0"] = "commit.gpgsign"
    caller["GIT_CONFIG_VALUE_0"] = "true"
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

    author = git("log", "-1", "--format=%an <%ae>").stdout.strip()
    assert author == "Tester <tester@agents.nidvue.com>", author
