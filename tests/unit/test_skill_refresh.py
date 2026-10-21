"""The installed skill must follow the remote, not just the local checkout (T-0046).

Why: an agent host loads a **copy** of this skill from its skills directory. Two
drifts were measured on this machine: the installed copy carried an old
``SKILL.md`` and was missing engine modules a shipped behaviour imports; and after
that copy was fixed it still only moved when someone remembered to run a script.
The user's requirement is the invariant: *when the remote ``main`` moves, the
local skill updates and is reloaded*.

``teamwork refresh`` is that path: it fast-forwards the source checkout from the
remote (never clobbering uncommitted work), then mirrors the bundle into the
installed skills directory, and says when a host reload is needed. These tests pin
the mechanics against a real local git remote - fetch, fast-forward, mirror,
drift reporting - without any network.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from tests.gitenv import child_env

from teamwork import bundle, engine

# The platform variables must survive: on Windows the interpreter's RNG is
# initialised from the OS and fails without SystemRoot/TEMP.
# Hermetic, not accidentally hermetic: the caller's git configuration must not
# reach the child either, so a system ``/etc/gitconfig``, a ``~/.gitconfig`` or
# an inherited ``GIT_CONFIG_GLOBAL`` cannot hand the fixtures a
# ``commit.gpgsign``, ``core.hooksPath`` or ``init.templateDir``, and a
# credential prompt cannot block a run. ``child_env`` starts from the parent
# environment (the platform's variables survive) and re-asserts these pins on
# top of it.
GIT_ENV = child_env(
    GIT_AUTHOR_NAME="Tester",
    GIT_AUTHOR_EMAIL="tester@agents.nidvue.com",
    GIT_COMMITTER_NAME="Tester",
    GIT_COMMITTER_EMAIL="tester@agents.nidvue.com",
)


def git_path() -> str:
    """The ambient PATH plus the usual bin directories.

    Hard-coding ``/usr/bin:/bin`` hides git on NixOS and Guix, where it lives in
    ``/run/current-system/sw/bin``: the tests need *a* git, not a specific one.
    """
    ambient = os.environ.get("PATH", "")
    return os.pathsep.join(p for p in (ambient, "/usr/bin", "/bin", "/usr/local/bin") if p)


def git(path: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(path), *argv],
        capture_output=True,
        text=True,
        env={**GIT_ENV, "PATH": git_path()},
    )
    assert done.returncode == 0, (argv, done.stderr)
    return done.stdout.strip()


def make_bundle(root: Path) -> Path:
    """A miniature skill checkout with every manifest entry present."""
    root.mkdir(parents=True, exist_ok=True)
    for name in bundle.BUNDLE_FILES:
        (root / name).write_text(f"# {name} v1\n", encoding="utf-8")
    for tree in bundle.BUNDLE_TREES:
        (root / tree).mkdir(parents=True, exist_ok=True)
        (root / tree / "one.txt").write_text(f"{tree} v1\n", encoding="utf-8")
    (root / "src" / "teamwork").mkdir(parents=True, exist_ok=True)
    (root / "src" / "teamwork" / "__init__.py").write_text("", encoding="utf-8")
    return root


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    """A bare repository that acts as ``origin``."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    git(bare, "init", "--bare", "-q", "-b", "main")
    return bare


@pytest.fixture
def checkout(tmp_path: Path, remote: Path) -> Path:
    """A working clone whose ``main`` is pushed to the bare remote."""
    work = make_bundle(tmp_path / "author")
    git(work, "init", "-q", "-b", "main")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "v1")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "-u", "origin", "main")
    clone = tmp_path / "checkout"
    git(tmp_path, "clone", "-q", str(remote), str(clone))
    return clone


def refresh(cli, capsys, *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli("refresh", *argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_the_git_helper_ignores_the_callers_git_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hermetic must mean proof, not the accident of a missing ``HOME`` (T-0002).

    A future edit that forwards ``HOME``, ``GIT_CONFIG_GLOBAL`` or
    ``GIT_CONFIG_SYSTEM`` into the child would hand every fixture a foreign
    ``user.name``, a ``commit.gpgsign`` that fails each commit and an
    ``init.defaultBranch`` that renames the branch under test.
    """
    hostile = tmp_path / ".gitconfig"
    hostile.write_text(
        "[user]\n\tname = Operator\n\temail = operator@example.com\n"
        "[commit]\n\tgpgsign = true\n[init]\n\tdefaultBranch = trunk\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(hostile))

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")

    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") != "trunk", "config leaked"
    assert git(repo, "log", "-1", "--format=%an <%ae>") == "Tester <tester@agents.nidvue.com>"


def test_refresh_mirrors_the_checkout_into_the_installed_directory(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "installed"
    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest)
    assert code == 0, out
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v1\n"
    assert (dest / "references" / "one.txt").is_file()
    assert "restart the agent host" in out, "the operator must be told to reload"


def test_refresh_fast_forwards_the_source_and_carries_the_new_text(
    cli, capsys, checkout: Path, remote: Path, tmp_path: Path
) -> None:
    """The real requirement: the remote moved, so the installed copy moves."""
    dest = tmp_path / "installed"
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest)[0] == 0

    # A peer pushes to the remote; the local checkout is one commit behind.
    peer = tmp_path / "peer"
    git(tmp_path, "clone", "-q", str(remote), str(peer))
    (peer / "SKILL.md").write_text("# SKILL.md v2\n", encoding="utf-8")
    (peer / "src" / "teamwork" / "new_module.py").write_text("NEW = 1\n", encoding="utf-8")
    git(peer, "add", "-A")
    git(peer, "commit", "-q", "-m", "v2")
    git(peer, "push", "-q", "origin", "main")
    assert git(checkout, "rev-parse", "--short", "HEAD") != git(
        peer, "rev-parse", "--short", "HEAD"
    )

    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest)
    assert code == 0, out
    assert "->" in out, out
    assert git(checkout, "rev-parse", "HEAD") == git(peer, "rev-parse", "HEAD")
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v2\n"
    assert (dest / "src" / "teamwork" / "new_module.py").is_file()


def test_a_checkout_ahead_of_the_remote_is_not_reported_as_moved(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    """A lane's checkout is normally AHEAD of origin/main; do not claim a move.

    Measured failure: a branch worktree already contained origin/main, so
    ``merge --ff-only`` was a no-op, yet the command printed ``6a99e0d -> e8da9ce``
    - a revision it never checked out, and one that is an ANCESTOR of its head.
    """
    dest = tmp_path / "installed"
    (checkout / "SKILL.md").write_text("# local work in progress\n", encoding="utf-8")
    git(checkout, "commit", "-q", "-am", "ahead of the remote")
    head = git(checkout, "rev-parse", "--short", "HEAD")

    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest)
    assert code == 0, out
    source_line = next(line for line in out.splitlines() if line.startswith("# source"))
    assert "->" not in source_line, source_line
    assert "already contained in" in source_line, source_line
    assert git(checkout, "rev-parse", "--short", "HEAD") == head
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# local work in progress\n"


def test_a_dirty_checkout_is_mirrored_not_clobbered(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    """Uncommitted work is the operator's: mirror it, never reset the tree."""
    dest = tmp_path / "installed"
    (checkout / "SKILL.md").write_text("# uncommitted\n", encoding="utf-8")
    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest)
    assert code == 0, out
    assert "fast-forward skipped" in out
    assert (checkout / "SKILL.md").read_text(encoding="utf-8") == "# uncommitted\n"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# uncommitted\n"


def test_check_reports_drift_and_writes_nothing(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "installed"
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest)[0] == 0
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest, "--check")[0] == 0

    (checkout / "SKILL.md").write_text("# moved on\n", encoding="utf-8")
    before = (dest / "SKILL.md").read_bytes()
    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest, "--check")
    assert code == 1
    assert "OUT OF SYNC" in out
    assert (dest / "SKILL.md").read_bytes() == before, "--check must not write"


def test_dry_run_lists_the_plan_without_writing(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "installed"
    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest, "--dry-run")
    assert code == 0
    assert "+ SKILL.md" in out
    assert "would write" in out
    assert not dest.exists()


def test_a_removed_module_is_deleted_from_the_installed_copy(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    """A renamed engine module must not linger and shadow the new one."""
    dest = tmp_path / "installed"
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest)[0] == 0
    stale = dest / "src" / "teamwork" / "renamed_away.py"
    stale.write_text("OLD = 1\n", encoding="utf-8")
    code, out = refresh(cli, capsys, "--source", checkout, "--dest", dest)
    assert code == 0, out
    assert not stale.exists()


def test_an_operator_file_in_the_skills_directory_survives(
    cli, capsys, checkout: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "installed"
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest)[0] == 0
    note = dest / "NOTES.md"
    note.write_text("mine\n", encoding="utf-8")
    assert refresh(cli, capsys, "--source", checkout, "--dest", dest)[0] == 0
    assert note.read_text(encoding="utf-8") == "mine\n"


def test_without_a_checkout_the_mirror_is_cloned_once_then_updated(
    cli, capsys, checkout: Path, remote: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "skills" / "teamwork"
    code, out = refresh(cli, capsys, "--dest", dest, "--mirror", "--repo", str(remote))
    assert code == 0, out
    mirror = bundle.default_mirror_path(dest)
    assert (mirror / ".git").is_dir(), "the mirror checkout is tool-managed state"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v1\n"

    peer = tmp_path / "peer"
    git(tmp_path, "clone", "-q", str(remote), str(peer))
    (peer / "SKILL.md").write_text("# SKILL.md v3\n", encoding="utf-8")
    git(peer, "commit", "-qam", "v3")
    git(peer, "push", "-q", "origin", "main")

    code, out = refresh(cli, capsys, "--dest", dest, "--mirror")
    assert code == 0, out
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v3\n"


def test_a_source_that_is_not_a_checkout_is_refused(cli, capsys, tmp_path: Path) -> None:
    code, out = refresh(
        cli, capsys, "--dest", tmp_path / "installed", "--source", tmp_path / "nothing"
    )
    assert code != 0
    assert "not a git checkout" in out


def test_no_checkout_and_no_repo_fails_with_the_fix(cli, capsys, tmp_path: Path) -> None:
    code, out = refresh(cli, capsys, "--dest", tmp_path / "installed", "--mirror")
    assert code != 0
    assert "--repo" in out, "an unusable state must name the command that fixes it"


def test_the_engine_and_the_sync_script_share_one_manifest() -> None:
    """A second copy of the file list would drift silently and drop a module."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import build_pi_package
    import sync_skill

    assert sync_skill.BUNDLE_FILES == bundle.BUNDLE_FILES
    assert sync_skill.BUNDLE_TREES == bundle.BUNDLE_TREES
    assert build_pi_package.SKILL_FILES == bundle.BUNDLE_FILES
    assert build_pi_package.SKILL_TREES == bundle.BUNDLE_TREES
    engine_root = Path(engine.__file__).resolve().parents[2]
    for name in bundle.BUNDLE_FILES:
        assert (engine_root / name).is_file(), name
    for tree in bundle.BUNDLE_TREES:
        assert (engine_root / tree).is_dir(), tree
