"""Exactly one release asset per name: the SHA256SUMS collision cannot come back.

Why this exists: the `v1.3.0` Release workflow wrote two files named
`SHA256SUMS` - `dist/SHA256SUMS` from `scripts/verify_release.py` and a
root-level one from a checksum step - and then asked the Release API to upload
`dist/*` *and* `SHA256SUMS`. The action uploaded the manifest once and failed
with `Not Found - releases/assets#update-a-release-asset` on the second, which
left the release a draft until a failed job was re-run (measured on the `v1.3.0`
Release run, which `gh run list --workflow Release --json attempt,headBranch,headSha -L 3`
names: the id belongs in that command's output, not in this file).

The invariant is therefore about the *resolved asset set*, not about the shape
of one step: expand every path the workflow hands to the Release, reduce each
resolved file to the asset name GitHub will use (its basename) and require the
names to be unique. The expansion is proved to bite by re-adding the deleted
`SHA256SUMS` entry in memory and watching the same function report a collision.

The manifest step itself is not trusted either: it is extracted from the shipped
workflow text and executed against fixture `dist/` trees, so the code under test
is the YAML that runs, not a copy of it.

Owner: release-engineer. Task: T-0011.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from workflow_yaml import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_PATH = ".github/workflows/release.yml"

MANIFEST_NAME = "SHA256SUMS"
MANIFEST_PATH = "dist/SHA256SUMS"

#: Steps whose `with:` mapping names files that reach the Release.
ASSET_STEPS = {
    "actions/upload-artifact": "path",
    "actions/attest-build-provenance": "subject-path",
    "softprops/action-gh-release": "files",
}


def release_text() -> str:
    return (REPO_ROOT / RELEASE_PATH).read_text(encoding="utf-8")


def release() -> dict:
    return parse_workflow(release_text())


def steps(document: dict) -> list[tuple[str, dict]]:
    return [
        (name, step)
        for name, job in (document.get("jobs") or {}).items()
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    ]


def entries(text: str) -> list[str]:
    """The path entries of a multi-line `with:` value, one per line."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def asset_entries(document: dict) -> list[tuple[str, str]]:
    """Every `(step kind, path entry)` that names a Release asset."""
    found: list[tuple[str, str]] = []
    for _, step in steps(document):
        uses = str(step.get("uses") or "")
        for action, key in ASSET_STEPS.items():
            if uses.split("@", 1)[0].strip() != action:
                continue
            value = (step.get("with") or {}).get(key)
            assert isinstance(value, str), f"{action}: no {key!r}: {value!r}"
            found.extend((action, entry) for entry in entries(value))
    return found


def resolve(entry: str, workspace: Path) -> list[Path]:
    """The files a `path:`/`files:` entry resolves to, relative to the workspace."""
    if entry.endswith("/*"):
        return sorted(p for p in (workspace / entry[:-2]).glob("*") if p.is_file())
    if entry.endswith("/"):
        return sorted(p for p in (workspace / entry).rglob("*") if p.is_file())
    candidate = workspace / entry
    return [candidate] if candidate.is_file() else []


def asset_targets(document: dict, workspace: Path) -> dict[str, list[str]]:
    """Resolved asset names per step. Each step is its own asset namespace.

    The artifact bundle, the attestation subjects and the Release are three
    different destinations: the same file may legitimately appear in each of
    them. What must never happen twice is one *name* inside one destination,
    which is what the Release API rejects.
    """
    targets: dict[str, list[str]] = {}
    for kind, entry in asset_entries(document):
        targets.setdefault(kind, []).extend(path.name for path in resolve(entry, workspace))
    return targets


def asset_names(document: dict, workspace: Path) -> list[str]:
    """Every resolved asset name, one entry per destination."""
    return [name for names in asset_targets(document, workspace).values() for name in names]


def duplicates(names: list[str]) -> list[str]:
    return sorted({name for name in names if names.count(name) > 1})


def collisions(document: dict, workspace: Path) -> list[str]:
    """Names that appear twice inside one destination."""
    found: list[str] = []
    for kind, names in asset_targets(document, workspace).items():
        found.extend(f"{kind}: {name}" for name in duplicates(names))
    return sorted(found)


def workspace_with_assets(tmp_path: Path, root_manifest: bool = False) -> Path:
    """A checkout that has been through `verify_release.py` and the SBOM steps."""
    workspace = tmp_path / "ReleaseWorkspace"
    (workspace / "dist").mkdir(parents=True, exist_ok=True)
    for name in (
        "teamwork_agents-9.9.9.tar.gz",
        "teamwork_agents-9.9.9-py3-none-any.whl",
        "SHA256SUMS",
    ):
        (workspace / "dist" / name).write_text(f"{name}\n", encoding="utf-8")
    for name in ("sbom.cyclonedx.json", "sbom.spdx.json"):
        (workspace / name).write_text(f"{name}\n", encoding="utf-8")
    if root_manifest:
        (workspace / MANIFEST_NAME).write_text("stale\n", encoding="utf-8")
    return workspace


# --------------------------------------------------------------------------- #
# the resolved asset set
# --------------------------------------------------------------------------- #


def test_the_release_publishes_exactly_one_manifest(tmp_path: Path) -> None:
    document = release()
    workspace = workspace_with_assets(tmp_path)
    targets = asset_targets(document, workspace)
    assert set(targets) == set(ASSET_STEPS), sorted(targets)
    for kind, names in targets.items():
        assert names.count(MANIFEST_NAME) == 1, (kind, names)
    assert collisions(document, workspace) == []


def test_the_manifest_is_dist_shasums_and_not_a_root_copy(tmp_path: Path) -> None:
    """The surviving entry must be the one `verify_release.py` writes."""
    entries_ = [entry for _, entry in asset_entries(release())]
    assert MANIFEST_PATH not in entries_, "dist/ is uploaded as a directory, not per file"
    assert MANIFEST_NAME not in entries_, (
        "a bare SHA256SUMS entry is the second asset with that name: the root file "
        "duplicated dist/SHA256SUMS and made the v1.3.0 upload race"
    )
    resolving = {
        entry
        for entry in entries_
        if any(
            path.name == MANIFEST_NAME for path in resolve(entry, workspace_with_assets(tmp_path))
        )
    }
    assert resolving == {"dist/", "dist/*"}, resolving


def test_the_old_asset_set_is_reported_as_a_collision(tmp_path: Path) -> None:
    """The bite check: put the deleted entry back and the invariant fails."""
    workspace = workspace_with_assets(tmp_path, root_manifest=True)
    document = release()
    for _, step in steps(document):
        if str(step.get("uses") or "").startswith("softprops/action-gh-release"):
            step["with"]["files"] = "dist/*\nSHA256SUMS\nsbom.cyclonedx.json\nsbom.spdx.json"
    # The shipped artifact and attestation steps dropped the entry too, so only
    # the step reverted to its v1.3.0 form reports the collision.
    assert collisions(document, workspace) == ["softprops/action-gh-release: SHA256SUMS"], (
        "the v1.3.0 asset set was accepted"
    )


def test_the_shipped_workflow_carries_no_second_manifest(tmp_path: Path) -> None:
    """A root-level SHA256SUMS in the tree is what made the two assets possible."""
    workspace = workspace_with_assets(tmp_path, root_manifest=False)
    document = release()
    assert collisions(document, workspace) == []
    assert MANIFEST_NAME in asset_names(document, workspace)


# --------------------------------------------------------------------------- #
# the manifest step, executed as shipped
# --------------------------------------------------------------------------- #


def manifest_step(document: dict) -> dict:
    for _, step in steps(document):
        run = str(step.get("run") or "")
        if MANIFEST_NAME in run and "manifest" in run:
            return step
    raise AssertionError("the release workflow has no step that writes the manifest")


def manifest_block(document: dict) -> str:
    """The Python body of the manifest step's `python3 - <<'PY'` heredoc."""
    run = str(manifest_step(document)["run"])
    lines = run.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "python3 - <<'PY'"), None)
    assert start is not None, "the manifest step has no python heredoc"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "PY"), None)
    assert end is not None, "the manifest heredoc is not closed"
    body = lines[start + 1 : end]
    indent = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    code = "\n".join(line[indent:] if line.strip() else "" for line in body) + "\n"
    for marker in ("sha256", "SHA256SUMS", "dist", "duplicated"):
        assert marker in code, f"extracted block is not the manifest step: no {marker!r}"
    return code


def run_manifest(workspace: Path, document: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", manifest_block(document)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_manifest_covers_the_artefacts_and_both_sboms(tmp_path: Path) -> None:
    workspace = workspace_with_assets(tmp_path)
    result = run_manifest(workspace, release())
    assert result.returncode == 0, result.stdout + result.stderr

    lines = (workspace / "dist" / MANIFEST_NAME).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4, lines
    recorded = {}
    for line in lines:
        digest, name = line.split("  ", 1)
        recorded[name] = digest
    expected = {
        "teamwork_agents-9.9.9.tar.gz": workspace / "dist" / "teamwork_agents-9.9.9.tar.gz",
        "teamwork_agents-9.9.9-py3-none-any.whl": workspace
        / "dist"
        / "teamwork_agents-9.9.9-py3-none-any.whl",
        "sbom.cyclonedx.json": workspace / "sbom.cyclonedx.json",
        "sbom.spdx.json": workspace / "sbom.spdx.json",
    }
    assert set(recorded) == set(expected), sorted(recorded)
    for name, path in expected.items():
        assert recorded[name] == hashlib.sha256(path.read_bytes()).hexdigest(), name
    # Bare names, because the Release flattens the asset set.
    assert MANIFEST_NAME not in recorded, "the manifest must not checksum itself"


def test_the_manifest_step_refuses_a_duplicate_name(tmp_path: Path) -> None:
    workspace = workspace_with_assets(tmp_path)
    (workspace / "dist" / "sbom.spdx.json").write_text("clash\n", encoding="utf-8")
    result = run_manifest(workspace, release())
    assert result.returncode == 1, result.stdout + result.stderr
    assert "not unique" in result.stderr, result.stderr


def test_the_manifest_step_refuses_a_directory_in_dist(tmp_path: Path) -> None:
    """`dist/*` would hand the release action a directory it cannot checksum."""
    workspace = workspace_with_assets(tmp_path)
    (workspace / "dist" / "@nidvue" / "teamwork").mkdir(parents=True)
    result = run_manifest(workspace, release())
    assert result.returncode == 1, result.stdout + result.stderr
    assert "must be a published file" in result.stderr, result.stderr


def test_provenance_is_attested_for_exactly_the_published_assets(tmp_path: Path) -> None:
    """A published asset with no attestation is an unverifiable download."""
    targets = asset_targets(release(), workspace_with_assets(tmp_path))
    assert sorted(targets["softprops/action-gh-release"]) == sorted(
        targets["actions/attest-build-provenance"]
    ), targets


def test_the_manifest_is_written_after_both_sboms_exist() -> None:
    """Checksumming an asset before it is generated silently leaves it uncovered."""
    document = release()
    order = [str(step.get("name") or "") for _, step in steps(document)]
    manifest_at = order.index(str(manifest_step(document)["name"]))
    sbom_at = [index for index, name in enumerate(order) if "SBOM" in name]
    assert len(sbom_at) == 2, order
    assert min(sbom_at) > 0 and max(sbom_at) < manifest_at, (sbom_at, manifest_at)


def test_the_manifest_step_is_not_skippable() -> None:
    step = manifest_step(release())
    assert "continue-on-error" not in step
    assert "if" not in step, step.get("if")
    run = str(step["run"])
    assert "|| true" not in run


def build_step(document: dict) -> dict:
    """The step that builds and verifies the release artefacts."""
    for _, step in steps(document):
        if "verify_release.py" in str(step.get("run") or ""):
            return step
    raise AssertionError("the release workflow has no step that runs verify_release.py")


def build_commands(document: dict) -> list[str]:
    """The shell commands of the build step, comments and blank lines dropped."""
    run = str(build_step(document)["run"])
    return [
        line.strip()
        for line in run.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_the_release_build_starts_from_a_clean_dist() -> None:
    """The suite leaves ``dist/@nidvue`` behind, so the build must clear ``dist/``.

    Why this exists: the workflow-invoked-script probe in
    ``tests/integration/test_ci_release_flow.py`` runs ``build_pi_package.py --help``,
    which is not implemented, so the probe performs the real build into ``dist/``.
    v1.4.0 shipped that residue into the manifest step and the release run failed
    (40771484033). Deleting the clean must break this test, not a tag.
    """
    commands = build_commands(release())
    assert commands, "the build step has no commands"
    assert commands[0] in {"rm -rf dist", "rm -rf ./dist"}, (
        f"the release build must start by cleaning dist/, found {commands[0]!r}"
    )
    assert any("verify_release.py" in command for command in commands), commands


def test_the_clean_removes_a_preseeded_bundle_directory(tmp_path: Path) -> None:
    """Run the shipped clean against a workspace that already holds the residue."""
    workspace = workspace_with_assets(tmp_path)
    residue = workspace / "dist" / "@nidvue" / "teamwork"
    residue.mkdir(parents=True)
    (residue / "package.json").write_text("{}", encoding="utf-8")

    refused = run_manifest(workspace, release())
    assert refused.returncode != 0, "the manifest guard must refuse a directory in dist/"
    assert "non-file entries" in refused.stdout + refused.stderr, refused.stdout

    clean = build_commands(release())[0]
    if shutil.which("bash") is None:
        pytest.skip("no bash on this host, so the shipped clean cannot be executed here")
    probe = subprocess.run(["bash", "-c", "true"], capture_output=True, check=False)
    if probe.returncode != 0:
        pytest.skip(
            "bash on this host is not a POSIX shell that can run the workflow's step "
            f"(it answered {probe.returncode} and said {probe.stderr.decode('utf-8', 'replace').strip()[:120]!r}); "
            "CI runs this step on ubuntu"
        )
    subprocess.run(["bash", "-c", clean], cwd=str(workspace), check=True)
    assert not (workspace / "dist" / "@nidvue").exists(), "the clean did not remove the residue"
