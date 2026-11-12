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

from teamwork import bundle, engine, lanes

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


def test_an_unrelated_mirror_history_is_recreated_and_mirrored(
    cli, capsys, checkout: Path, remote: Path, tmp_path: Path
) -> None:
    """The defect (T-0100): a rewritten remote made refresh stop for good.

    Measured on this host: the mirror sat at a pre-rewrite commit while
    ``origin/main`` had moved, so ``merge --ff-only`` answered ``refusing to merge
    unrelated histories`` and refresh exited 1 *before* mirroring - the installed
    copy kept the old engine and every lane ran the old protocol silently. A
    mirror is disposable state, so the fix recreates it instead of stopping.
    """
    dest = tmp_path / "skills" / "teamwork"
    mirror = bundle.default_mirror_path(dest)
    mirror.mkdir(parents=True)
    (mirror / "src" / "teamwork").mkdir(parents=True)
    (mirror / "SKILL.md").write_text("# rewritten history\n", encoding="utf-8")
    git(mirror, "init", "-q", "-b", "main")
    git(mirror, "add", "-A")
    git(mirror, "commit", "-q", "-m", "pre-rewrite")
    git(mirror, "remote", "add", "origin", str(remote))
    old = git(mirror, "rev-parse", "--short", "HEAD")
    wanted = git(remote, "rev-parse", "refs/heads/main")

    code, out = refresh(cli, capsys, "--dest", dest, "--mirror")

    assert code == 0, out
    assert "unrelated history" in out, out
    assert git(mirror, "rev-parse", "HEAD") == wanted, "the mirror was recreated at origin"
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v1\n"
    kept = mirror.with_name(f"{mirror.name}.stale-{old}")
    assert kept.is_dir(), "the old checkout is moved aside, never deleted"
    assert (kept / "SKILL.md").read_text(encoding="utf-8") == "# rewritten history\n"
    assert refresh(cli, capsys, "--dest", dest, "--mirror", "--check")[0] == 0


def test_a_recreated_mirror_keeps_the_remote_name_it_was_given(
    cli, capsys, checkout: Path, remote: Path, tmp_path: Path
) -> None:
    """F2 (T-0100): the repair must not rename the mirror's remote to ``origin``.

    Measured at 0de195f: the fresh clone carried only ``origin``, so the same
    ``refresh --mirror --remote upstream`` that performed the repair stopped on the
    next run with ``no branch or tag main on upstream`` - a one-time stop turned
    into a permanent one for every remote that is not named ``origin``.
    """
    dest = tmp_path / "skills" / "teamwork"
    mirror = bundle.default_mirror_path(dest)
    mirror.mkdir(parents=True)
    (mirror / "src" / "teamwork").mkdir(parents=True)
    (mirror / "SKILL.md").write_text("# rewritten history\n", encoding="utf-8")
    git(mirror, "init", "-q", "-b", "main")
    git(mirror, "add", "-A")
    git(mirror, "commit", "-q", "-m", "pre-rewrite")
    git(mirror, "remote", "add", "upstream", str(remote))

    code, out = refresh(cli, capsys, "--dest", dest, "--mirror", "--remote", "upstream")

    assert code == 0, out
    assert "unrelated history" in out, out
    assert git(mirror, "remote") == "upstream", "the repair kept the remote it was given"

    code, out = refresh(cli, capsys, "--dest", dest, "--mirror", "--remote", "upstream")

    assert code == 0, out
    assert "refresh stopped" not in out, out
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# SKILL.md v1\n"


def test_an_unrelated_explicit_source_is_never_moved_aside(
    cli, capsys, checkout: Path, remote: Path, tmp_path: Path
) -> None:
    """An operator's own checkout is not disposable: recreate only the mirror."""
    work = make_bundle(tmp_path / "operator")
    git(work, "init", "-q", "-b", "main")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "mine")
    git(work, "remote", "add", "origin", str(remote))
    head = git(work, "rev-parse", "HEAD")

    code, out = refresh(cli, capsys, "--source", work, "--dest", tmp_path / "installed")

    assert code != 0
    assert "refresh stopped" in out and "unrelated histories" in out, out
    assert git(work, "rev-parse", "HEAD") == head, "the checkout was not touched"
    assert not list(tmp_path.glob("operator.stale-*")), "nothing was moved aside"


def test_lane_start_names_a_stale_installed_bundle(tmp_path: Path) -> None:
    """A lane runs the *installed copy*, so a lagging copy must be one named line."""
    project = make_bundle(tmp_path / "project")
    git(project, "init", "-q", "-b", "main")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "v1")
    ahead = git(project, "rev-parse", "--short", "HEAD")
    root = project / ".pi" / "Teamwork" / "Teams" / "Teamwork"
    root.mkdir(parents=True)
    dest = tmp_path / "skills" / "teamwork"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("# old\n", encoding="utf-8")
    mirror = bundle.default_mirror_path(dest)
    mirror.mkdir(parents=True)
    (mirror / "src" / "teamwork").mkdir(parents=True)
    git(mirror, "init", "-q", "-b", "main")
    git(mirror, "commit", "-q", "--allow-empty", "-m", "old")
    behind = git(mirror, "rev-parse", "--short", "HEAD")

    line = lanes.stale_bundle_line(root, dest=str(dest))

    assert line.startswith("# installed skill"), line
    assert str(dest) in line and str(project) in line, line
    assert behind in line and ahead in line, "both revisions are named"
    assert "teamwork.py refresh" in line, "the line names the command that fixes it"

    bundle.sync(project, dest, dry_run=False, quiet=True)
    assert lanes.stale_bundle_line(root, dest=str(dest)) == ""


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
    import importlib.util
    import sys

    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"

    def load(name: str, filename: str):
        spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        snapshot = list(sys.path)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = snapshot
        return module

    build_pi_package = load("build_pi_package_under_test", "build_pi_package.py")
    sync_skill = load("sync_skill_under_test", "sync_skill.py")

    assert sync_skill.BUNDLE_FILES == bundle.BUNDLE_FILES
    assert sync_skill.BUNDLE_TREES == bundle.BUNDLE_TREES
    assert build_pi_package.SKILL_FILES == bundle.BUNDLE_FILES
    assert build_pi_package.SKILL_TREES == bundle.BUNDLE_TREES
    engine_root = Path(engine.__file__).resolve().parents[2]
    for name in bundle.BUNDLE_FILES:
        assert (engine_root / name).is_file(), name
    for tree in bundle.BUNDLE_TREES:
        assert (engine_root / tree).is_dir(), tree
