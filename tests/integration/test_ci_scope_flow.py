"""Integration: the CI scope classifier, driven end to end on real git change sets.

`scripts/ci_scope.py` is the shipped classifier the `scope` job runs. Every case
here executes the module as a subprocess against a real repository, so the test
measures what CI does rather than what a helper of ours does: prose-only, code,
mixed, a rename from code into prose, a root commit, an undetermined change set,
a tag push and a non-push event. Two mutant copies prove the cases bite - rename
detection turned on, and the undetermined fallback turned into a skip.

Owner: team-leader. Task: T-0001.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci_scope.py"

ZERO_SHA = "0" * 40

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


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"ci_scope_{path.stem}", path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def classify(
    repo: Path,
    *,
    script: Path = SCRIPT,
    before: str,
    head: str | None = None,
    event: str = "push",
    ref: str = "refs/heads/main",
    default_branch: str = "main",
    files: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Run the shipped classifier in `repo` and return its `$GITHUB_OUTPUT` pairs."""
    sink = repo.parent / f"github-output-{len(list(repo.parent.glob('github-output-*')))}.txt"
    sink.write_text("", encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env.update(
        {
            "EVENT_NAME": event,
            "REF_NAME": ref,
            "BEFORE_SHA": before,
            "HEAD_SHA": head if head is not None else git(repo, "rev-parse", "HEAD"),
            "DEFAULT_BRANCH": default_branch,
            "GITHUB_OUTPUT": str(sink),
        }
    )
    command = [sys.executable, str(script)]
    for path in files or ():
        command += ["--file", path]
    result = subprocess.run(
        command,
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
    for line in sink.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            pairs[key] = value
    assert "code" in pairs and "prose" in pairs, f"classifier emitted {pairs!r}"
    return pairs


def offset_origin_main(repo: Path, sha: str) -> None:
    git(repo, "update-ref", "refs/remotes/origin/main", sha)


def test_prose_only_change_is_not_code(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")

    pairs = classify(repo, before=root, head=head)

    assert (pairs["code"], pairs["prose"]) == ("false", "true")


def test_code_change_is_code(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"src/teamwork/engine.py": "x = 1\n"}, message="code")

    pairs = classify(repo, before=root, head=head)

    assert (pairs["code"], pairs["prose"]) == ("true", "false")


def test_mixed_change_is_code(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(
        repo,
        {"docs/guide/page.md": "# page\n", "src/teamwork/engine.py": "x = 1\n"},
        message="mixed",
    )

    pairs = classify(repo, before=root, head=head)

    assert (pairs["code"], pairs["prose"]) == ("true", "false")


def test_rename_from_code_into_prose_is_code(tmp_path: Path) -> None:
    """Rename detection reports only the destination; --no-renames reports both."""
    repo, root = new_repo(
        tmp_path,
        {"src/teamwork/foo.py": "def f():\n    return 1\n", "docs/index.md": "# index\n"},
    )
    git(repo, "mv", "src/teamwork/foo.py", "docs/foo.md")
    git(repo, "commit", "-q", "-m", "move code into prose")
    head = git(repo, "rev-parse", "HEAD")

    pairs = classify(repo, before=root, head=head)

    assert (pairs["code"], pairs["prose"]) == ("true", "false")


def test_root_commit_of_code_is_code(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"src/teamwork/mod.py": "y = 2\n"})

    pairs = classify(repo, before=ZERO_SHA, head=root)

    assert (pairs["code"], pairs["prose"]) == ("true", "false")


def test_root_commit_of_prose_is_prose_only(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"docs/index.md": "# index\n"})

    pairs = classify(repo, before=ZERO_SHA, head=root)

    assert (pairs["code"], pairs["prose"]) == ("false", "true")


def test_unresolvable_before_defaults_to_code(tmp_path: Path) -> None:
    """The remote already holds HEAD, so the pre-push state is gone: never skip."""
    repo, _ = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")
    offset_origin_main(repo, head)

    pairs = classify(repo, before=ZERO_SHA, head=head)

    assert (pairs["code"], pairs["prose"]) == ("true", "false")


def test_an_empty_change_set_is_neither_code_nor_prose(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"README.md": "# Prose\n"})

    pairs = classify(repo, before=root, head=root)

    assert (pairs["code"], pairs["prose"]) == ("false", "false")


def test_pull_request_and_tag_push_short_circuit(tmp_path: Path) -> None:
    repo, root = new_repo(tmp_path, {"docs/index.md": "# index\n"})

    pull_request = classify(repo, before=root, event="pull_request")
    tag_push = classify(repo, before=root, ref="refs/tags/v1.0.0")

    assert (pull_request["code"], pull_request["prose"]) == ("true", "false")
    assert (tag_push["code"], tag_push["prose"]) == ("false", "false")


def test_every_docs_trigger_path_is_prose_to_the_classifier(tmp_path: Path) -> None:
    prose = load_module(SCRIPT).prose_paths()
    repo, previous = new_repo(tmp_path, {"README.md": "# root\n"}, name="prose-paths")

    for marker in prose:
        rel = marker[: -len("/**")] + "/probe/page.md" if marker.endswith("/**") else marker
        head = commit(repo, {rel: "probe\n"}, message=f"touch {rel}")
        pairs = classify(repo, before=previous, head=head)
        assert (pairs["code"], pairs["prose"]) == ("false", "true"), rel
        previous = head


def test_near_misses_are_code_even_though_they_look_like_prose(tmp_path: Path) -> None:
    near_misses = ("NOTICE", "SKILL.md", "LICENSE.md", "README.md.bak", "docs-notes/page.md")
    repo, previous = new_repo(tmp_path, {"README.md": "# root\n"}, name="near-misses")

    for rel in near_misses:
        head = commit(repo, {rel: "probe\n"}, message=f"touch {rel}")
        pairs = classify(repo, before=previous, head=head)
        assert (pairs["code"], pairs["prose"]) == ("true", "false"), rel
        previous = head


def mutant(tmp_path: Path, old: str, new: str, name: str) -> Path:
    source = SCRIPT.read_text(encoding="utf-8")
    mutated = source.replace(old, new)
    assert mutated != source, f"mutant anchor {old!r} is gone from scripts/ci_scope.py"
    path = tmp_path / name
    path.write_text(mutated, encoding="utf-8")
    return path


def test_the_rename_case_bites_when_rename_detection_is_enabled(tmp_path: Path) -> None:
    script = mutant(tmp_path, "--no-renames", "-M", "ci_scope_renames.py")
    repo, root = new_repo(
        tmp_path,
        {"src/teamwork/foo.py": "def f():\n    return 1\n", "docs/index.md": "# index\n"},
    )
    git(repo, "mv", "src/teamwork/foo.py", "docs/foo.md")
    git(repo, "commit", "-q", "-m", "move code into prose")
    head = git(repo, "rev-parse", "HEAD")

    pairs = classify(repo, script=script, before=root, head=head)

    assert (pairs["code"], pairs["prose"]) == ("false", "true")


def test_the_undetermined_fallback_bites_when_it_defaults_to_false(tmp_path: Path) -> None:
    script = mutant(
        tmp_path,
        "return Scope(code=True, prose=False, reason=reason, undetermined=True)",
        "return Scope(code=False, prose=False, reason=reason, undetermined=True)",
        "ci_scope_undetermined.py",
    )
    repo, _ = new_repo(tmp_path, {"README.md": "# Prose\n"})
    head = commit(repo, {"docs/guide/page.md": "# page\n"}, message="prose only")
    offset_origin_main(repo, head)

    pairs = classify(repo, script=script, before=ZERO_SHA, head=head)

    assert (pairs["code"], pairs["prose"]) == ("false", "false")
