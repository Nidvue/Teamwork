"""Integration: the CI scope classifier, driven end to end on real git change sets.

The classifier is not a module - it is the shell block of the ``scope`` job in
``.github/workflows/ci.yml``, which reads a git change set and emits
``code=true|false`` into ``$GITHUB_OUTPUT``. The matrix jobs then ask that one
question ("did this push touch anything that ships?"). Nothing else tests it as
a program, so a defect there is invisible until a documentation-only push burns
the 3x3 matrix or a code push skips it.

This module therefore extracts the *real* block from the workflow (so the test
cannot drift from the shipped classifier), runs it with a real POSIX ``bash``
against real committed repositories under ``tmp_path``, and reads the emitted
value. The shell is resolved by :func:`posix_bash`, because a bare ``bash`` on a
Windows runner is the System32 WSL launcher, not a shell. Every case is also
proved to bite: the same script is mutated in a scratch copy and the
corresponding verdict must flip.

Owner: tester. Task: T-0004.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from tests.tooling import skip_message

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCOPE_STEP = "Classify the changed paths"

#: Pinned identity and signing: the fixture must not depend on the operator's
#: git config, and a global ``tag.gpgSign`` must not break a fixture commit.
GIT_OPTIONS = (
    "-c",
    "user.email=tester@agents.nidvue.com",
    "-c",
    "user.name=Tester",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "tag.gpgSign=false",
)


# --------------------------------------------------------------------------- #
# Extracting the real classifier out of the workflow
# --------------------------------------------------------------------------- #


def extract_run_block(workflow: Path, step_name: str) -> str:
    """The body of the ``run: |`` block for the step named ``step_name``.

    ``ci.yml`` is not parsed as YAML: the point is to run the exact shell text
    that CI runs, and a YAML round-trip would only re-encode it. The block ends
    at the first non-blank line that is not indented as a body line.
    """
    lines = workflow.read_text(encoding="utf-8").splitlines()
    step = next(
        (i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}"),
        None,
    )
    assert step is not None, f"{workflow}: no step named {step_name!r}"
    run_at = next(
        (i for i in range(step, len(lines)) if lines[i].strip() == "run: |"),
        None,
    )
    assert run_at is not None, f"{workflow}: step {step_name!r} has no 'run: |' block"
    key_indent = len(lines[run_at]) - len(lines[run_at].lstrip())
    body_indent = key_indent + 2
    body: list[str] = []
    for line in lines[run_at + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) < body_indent:
            break
        body.append(line[body_indent:] if line.strip() else "")
    text = "\n".join(body).rstrip("\n") + "\n"
    assert "GITHUB_OUTPUT" in text and "code=" in text, "extracted block is not the classifier"
    return text


def write_script(tmp_path: Path, text: str, name: str = "scope.sh") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Real fixture repositories
# --------------------------------------------------------------------------- #


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout.strip()


def write(repo: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def commit(repo: Path, files: dict[str, str], message: str = "edit") -> str:
    write(repo, files)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def new_repo(tmp_path: Path, files: dict[str, str], name: str = "repo") -> tuple[Path, str]:
    repo = tmp_path / name
    repo.mkdir()
    write(repo, files)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "root")
    return repo, git(repo, "rev-parse", "HEAD")


def _posix_bash_or_skip() -> str:
    """The shell to run the classifier with: a skip when there is none.

    :func:`posix_bash` raises rather than falling back to the WSL launcher, and
    its guard is itself under test - so the raise stays. Here, where a test is
    about to execute the classifier, no usable shell means the tool is absent
    from this host: a skip that names ``bash`` and says what was tried, never a
    failure (``T-0003``).
    """
    try:
        return posix_bash()
    except AssertionError as absent:
        pytest.skip(skip_message("bash", str(absent)))
        raise  # unreachable: pytest.skip raises Skipped; keeps the return type honest


def classify(
    repo: Path,
    script: Path,
    *,
    before: str,
    head: str | None = None,
    event: str = "push",
    ref: str = "refs/heads/main",
    default_branch: str = "main",
    output_name: str = "github-output.txt",
) -> dict[str, str]:
    """Run the classifier in ``repo`` and return the ``$GITHUB_OUTPUT`` pairs."""
    output = repo / output_name
    output.write_text("", encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env.update(
        {
            "EVENT_NAME": event,
            "REF_NAME": ref,
            "BEFORE_SHA": before,
            "HEAD_SHA": head if head is not None else git(repo, "rev-parse", "HEAD"),
            "DEFAULT_BRANCH": default_branch,
            "GITHUB_OUTPUT": str(output),
        }
    )
    result = subprocess.run(
        [_posix_bash_or_skip(), str(script)],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"classifier failed in {repo}: exit {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    pairs: dict[str, str] = {}
    for line in output.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            pairs[key] = value
    assert "code" in pairs, f"classifier emitted no code: {output.read_text()!r}"
    return pairs


# --------------------------------------------------------------------------- #
# A POSIX shell, not a bare ``bash``
# --------------------------------------------------------------------------- #

#: A ``bash`` on PATH can be the WSL launcher in two places: the System32
#: shim and the Store app-execution alias. Neither is a POSIX shell - with no
#: distribution installed they exit 1 and print a UTF-16LE "no installed
#: distributions" message, which surfaces here as a mysterious "classifier
#: failed: exit 1" instead of a harness defect. Reject both by path.
WSL_LAUNCHER_DIRS = ("c:/windows/system32",)
WSL_LAUNCHER_SUFFIXES = ("/windowsapps/bash.exe",)


def _normalised(path: str) -> str:
    """Lower-case, forward-slash form so Windows paths compare reliably."""
    return path.replace("\\", "/").rstrip("/").lower()


def _is_wsl_launcher(path: str) -> bool:
    """True for a ``bash.exe`` that is the WSL launcher rather than a shell.

    Covers the System32 shim and the Store alias under ``WindowsApps``, in both
    the given form and the form ``Path.resolve()`` reports, so a shim that is a
    link into ``WindowsApps`` cannot slip through.
    """
    forms = {_normalised(path)}
    try:
        forms.add(_normalised(str(Path(path).resolve())))
    except OSError:
        pass
    for form in forms:
        if any(form.startswith(directory + "/") for directory in WSL_LAUNCHER_DIRS):
            return True
        if form.endswith(WSL_LAUNCHER_SUFFIXES):
            return True
    return False


def _git_install_bash() -> list[str]:
    """Real Git-for-Windows shells derived from ``git --exec-path``.

    On Windows ``git --exec-path`` returns e.g.
    ``C:/Program Files/Git/mingw64/libexec/git-core``. Walking up from that
    directory to the install root gives ``C:/Program Files/Git``, whose
    ``bin/bash.exe`` and ``usr/bin/bash.exe`` are genuine POSIX shells.
    """
    result = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    exec_path = Path(result.stdout.strip())
    candidates: list[str] = []
    # git-core -> libexec -> mingw64 -> install root
    for root in list(exec_path.parents)[:4]:
        candidates.append(str(root / "bin" / "bash.exe"))
        candidates.append(str(root / "usr" / "bin" / "bash.exe"))
    return candidates


def posix_bash(
    os_name: str | None = None,
    which: Callable[[str], str | None] | None = None,
    git_shells: Callable[[], list[str]] | None = None,
    exists: Callable[[str], bool] | None = None,
) -> str:
    """Return the path of a real POSIX ``bash`` to run the classifier with.

    On POSIX this is simply ``shutil.which("bash")``. On Windows a bare
    ``"bash"`` is resolved by the OS to ``C:\\Windows\\System32\\bash.exe``, the
    WSL launcher - not a shell - so it is never accepted: Git-for-Windows
    ``bash.exe`` candidates are derived from ``git --exec-path`` and the PATH
    lookup is only used when it does not land on the WSL launcher.

    Every seam (``os_name``, ``which``, ``git_shells``, ``exists``) is injectable
    so the Windows branch is testable on any host, including the rejection path:
    a test that let the real filesystem answer ``exists`` would pass merely
    because a ``C:\\...`` path is absent on POSIX, proving nothing about the
    guard. Raises ``AssertionError`` naming everything tried when no usable
    shell exists, rather than silently running the WSL launcher.
    """
    name = os.name if os_name is None else os_name
    lookup: Callable[[str], str | None] = shutil.which if which is None else which
    if name != "nt":
        bash = lookup("bash")
        if bash is None:
            raise AssertionError(f"no bash on PATH (which bash -> None, os.name={name})")
        return bash

    present: Callable[[str], bool] = (lambda p: Path(p).exists()) if exists is None else exists
    tried: list[str] = []
    on_path = lookup("bash")
    tried.append(f"which bash -> {on_path!r}")
    git_candidates = (_git_install_bash if git_shells is None else git_shells)()
    tried.extend(f"git --exec-path -> {c!r}" for c in git_candidates)

    # Git-derived shells first (the install root, never System32), then any
    # PATH candidate that is not the WSL launcher.
    for candidate in [*git_candidates, on_path]:
        if candidate and not _is_wsl_launcher(candidate) and present(candidate):
            return candidate
    raise AssertionError(
        "no usable POSIX bash found on Windows - the candidates were the WSL "
        "launcher or absent, neither of which can run the classifier. "
        "Tried: " + "; ".join(tried)
    )


def test_posix_bash_rejects_the_wsl_launcher_on_windows() -> None:
    """The Windows branch must refuse the launcher and say what it tried.

    Both shapes are exercised: the System32 shim and the Store alias under
    ``WindowsApps``, which a plain ``startswith("C:/Windows/System32")`` guard
    would accept.
    """
    for launcher in (
        "C:\\Windows\\System32\\bash.exe",
        "C:\\Users\\runner\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe",
    ):

        def on_path(_name: str, hit: str = launcher) -> str:
            """``which`` for a host whose only bash is this launcher."""
            return hit

        # ``exists`` answers True so the ONLY thing that can reject the
        # launcher is the guard: delete the guard (stub _is_wsl_launcher to
        # False) and this test fails instead of passing for the wrong reason.
        with pytest.raises(AssertionError, match="no usable POSIX bash"):
            posix_bash(
                os_name="nt",
                which=on_path,
                git_shells=lambda: [],
                exists=lambda _p: True,
            )


def test_posix_bash_prefers_a_git_install_shell_on_windows() -> None:
    """A real shell derived from ``git --exec-path`` wins over the launcher.

    ``sys.executable`` stands in for the Git-for-Windows ``bash.exe``: the point
    is which candidate is chosen, and that the launcher on PATH is never it.
    """
    real = sys.executable
    launcher = "C:\\Windows\\System32\\bash.exe"

    assert (
        posix_bash(
            os_name="nt",
            which=lambda _: launcher,
            git_shells=lambda: [real],
            exists=lambda _p: True,
        )
        == real
    ), "a Git install shell must win over the launcher on PATH"

    # The complement: with only the launcher available and it SAYING it exists,
    # the guard is the sole reason nothing is returned. This is the case the
    # ordering alone does not cover.
    with pytest.raises(AssertionError, match="no usable POSIX bash"):
        posix_bash(
            os_name="nt",
            which=lambda _: launcher,
            git_shells=lambda: [],
            exists=lambda _p: True,
        )


ZERO_SHA = "0" * 40


def offset_origin_main(repo: Path, sha: str) -> None:
    """Point ``origin/main`` at ``sha`` without configuring a real remote.

    The classifier resolves the fallback base with
    ``git rev-parse --verify -q origin/main``; a remote-tracking ref is exactly
    what CI checks out, so a local ref is the faithful stand-in.
    """
    git(repo, "update-ref", "refs/remotes/origin/main", sha)


# --------------------------------------------------------------------------- #
# The five change sets the task names
# --------------------------------------------------------------------------- #


def test_prose_only_change_is_not_code(tmp_path: Path) -> None:
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")

    assert classify(repo, script, before=root, head=head)["code"] == "false"


def test_code_change_is_code(tmp_path: Path) -> None:
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"src/teamwork/engine.py": "x = 1\n"}, message="code")

    assert classify(repo, script, before=root, head=head)["code"] == "true"


def test_rename_from_a_shipping_path_into_prose_is_code(tmp_path: Path) -> None:
    """Renames are measured with ``--no-renames``: delete + add, never one path.

    Rename detection reports only the destination, so ``src/teamwork/foo.py``
    moved to ``docs/foo.md`` would look like a prose-only change while shipping
    code was removed. With ``--no-renames`` both paths are classified.
    """
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, root = new_repo(
        tmp_path,
        {"src/teamwork/foo.py": "def f():\n    return 1\n", "docs/index.md": "# index\n"},
    )
    git(repo, "mv", "src/teamwork/foo.py", "docs/foo.md")
    git(repo, "commit", "-q", "-m", "move code into prose")
    head = git(repo, "rev-parse", "HEAD")
    offset_origin_main(repo, root)

    assert classify(repo, script, before=root, head=head)["code"] == "true"


def test_root_commit_is_measured_with_root(tmp_path: Path) -> None:
    """A root commit has no parent; ``diff-tree --root`` lists its whole change set."""
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, root = new_repo(tmp_path, {"src/teamwork/mod.py": "y = 2\n"})

    assert classify(repo, script, before=ZERO_SHA, head=root)["code"] == "true"


def test_unresolvable_before_defaults_to_code(tmp_path: Path) -> None:
    """An unknown change set must never silently skip the matrix."""
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, _ = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")
    # The remote already holds HEAD, so the fork point is HEAD itself and the
    # pre-push state is gone: undetermined, therefore code=true.
    offset_origin_main(repo, head)

    assert classify(repo, script, before=ZERO_SHA, head=head)["code"] == "true"


def test_pull_request_and_tag_push_short_circuit(tmp_path: Path) -> None:
    script = write_script(tmp_path, extract_run_block(CI_WORKFLOW, SCOPE_STEP))
    repo, root = new_repo(tmp_path, {"docs/index.md": "# index\n"})

    assert classify(repo, script, before=root, event="pull_request")["code"] == "true"
    assert (
        classify(repo, script, before=root, ref="refs/tags/v1.0.0", event="push")["code"] == "false"
    )


# --------------------------------------------------------------------------- #
# The classifier must bite: mutate it and watch the verdict flip
# --------------------------------------------------------------------------- #


def test_the_rename_case_bites_when_rename_detection_is_enabled(tmp_path: Path) -> None:
    """``--no-renames`` -> ``--renames`` must turn the rename case into prose."""
    original = extract_run_block(CI_WORKFLOW, SCOPE_STEP)
    assert "--no-renames" in original
    mutated = original.replace("--no-renames", "--renames")
    script = write_script(tmp_path, mutated, name="scope-renames.sh")

    repo, root = new_repo(
        tmp_path,
        {"src/teamwork/foo.py": "def f():\n    return 1\n", "docs/index.md": "# index\n"},
    )
    git(repo, "mv", "src/teamwork/foo.py", "docs/foo.md")
    git(repo, "commit", "-q", "-m", "move code into prose")
    head = git(repo, "rev-parse", "HEAD")

    # The defect the shipped classifier exists to prevent: the shipped-block
    # test above asserts "true" for exactly this change set.
    assert classify(repo, script, before=root, head=head)["code"] == "false"


def test_the_undetermined_fallback_bites_when_it_defaults_to_false(tmp_path: Path) -> None:
    original = extract_run_block(CI_WORKFLOW, SCOPE_STEP)
    mutated, count = re.subn(r"(?m)^(\s*)code=true$", r"\1code=false", original)
    assert count >= 1, "the undetermined fallback is no longer a bare 'code=true'"
    script = write_script(tmp_path, mutated, name="scope-undetermined.sh")

    repo, _ = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")
    offset_origin_main(repo, head)

    assert classify(repo, script, before=ZERO_SHA, head=head)["code"] == "false"
