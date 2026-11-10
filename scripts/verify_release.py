#!/usr/bin/env python3
"""Build, inspect and smoke-test the Teamwork release artefacts.

The single command that proves acceptance criterion AC-1 end to end:

1. ``python -m build`` produces the sdist and the wheel in ``dist/``.
2. The wheel is inspected with :mod:`zipfile`; the bundled skill assets
   ``teamwork/data/SKILL.md`` and ``teamwork/data/templates/AGENTS.md`` must be
   present, and the metadata must declare no runtime dependency.
3. ``SHA256SUMS`` is written next to the artefacts.
4. A throwaway virtual environment is created and the wheel installed into it
   with ``--no-deps`` (the package has no dependencies by contract).
5. The installed ``teamwork`` console script is executed:
   ``teamwork --version``, ``teamwork selftest`` and a ``teamwork init`` inside a
   temporary project directory.

Only the standard library is used at runtime; ``build`` is the one external
requirement (it is part of the ``dev`` extra).

Exit code 0 means the release was verified; any failure exits 1.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"

#: Members that must exist inside the built wheel.
REQUIRED_WHEEL_MEMBERS = (
    "teamwork/data/SKILL.md",
    "teamwork/data/templates/AGENTS.md",
)


def log(message: str) -> None:
    print(f"verify_release: {message}", flush=True)


def run(
    command: Sequence[object],
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    capture: bool = False,
    timeout: int = 900,
) -> subprocess.CompletedProcess:
    """Run a command, echoing it, and return the completed process."""
    rendered = " ".join(str(part) for part in command)
    log(f"run: {rendered}")
    try:
        result = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            env=env,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise VerificationError(f"command timed out after {timeout}s: {rendered}") from exc
    except OSError as exc:
        raise VerificationError(f"could not run {rendered}: {exc}") from exc
    if capture:
        for stream in (result.stdout, result.stderr):
            if stream:
                print(stream, end="" if stream.endswith("\n") else "\n")
    return result


def run_ok(
    command: Sequence[object],
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a command and abort the whole verification when it fails."""
    result = run(command, cwd=cwd, env=env, capture=True)
    if result.returncode != 0:
        raise VerificationError(
            f"command failed with exit {result.returncode}: "
            + " ".join(str(part) for part in command)
        )
    return result


class VerificationError(Exception):
    """A release check failed; the message is user-facing."""


def build_artefacts() -> None:
    """Run ``python -m build`` from the repository root."""
    try:
        import build  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise VerificationError(
            "'build' is not installed; run `make dev` or `python -m pip install build`"
        ) from exc
    run_ok([sys.executable, "-m", "build"])


def project_version() -> str:
    text = (REPO_ROOT / "src" / "teamwork" / "version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise VerificationError("cannot read __version__ from src/teamwork/version.py")
    return match.group(1)


def find_artefacts() -> dict[str, Path]:
    """Return the newest sdist and wheel *for this source tree's version*."""
    version = project_version()
    wheels = list(DIST_DIR.glob(f"teamwork_agents-{version}-*.whl"))
    sdists = list(DIST_DIR.glob(f"teamwork_agents-{version}.tar.gz"))
    if not wheels:
        raise VerificationError(f"no {version} wheel found in dist/ after build")
    if not sdists:
        raise VerificationError(f"no {version} sdist found in dist/ after build")
    newest = lambda path: path.stat().st_mtime  # noqa: E731 - local key helper
    return {"wheel": max(wheels, key=newest), "sdist": max(sdists, key=newest)}


def expected_bundle_members() -> list[str]:
    """Every skill-bundle file the wheel must carry, derived from the checkout.

    Comparing against the source directories (rather than a hand-written count)
    means adding a role charter or a template can never silently stop being
    shipped, and a rename cannot pass unnoticed.
    """
    members: list[str] = ["teamwork/data/SKILL.md"]
    for folder in ("roles", "references", "templates"):
        for path in sorted((REPO_ROOT / folder).rglob("*.md")):
            members.append("teamwork/data/" + path.relative_to(REPO_ROOT).as_posix())
    return members


def inspect_wheel(wheel: Path) -> None:
    """Assert the payload and metadata contract of the wheel."""
    expected = expected_bundle_members()
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        for member in REQUIRED_WHEEL_MEMBERS:
            if member not in names:
                raise VerificationError(f"wheel is missing required member: {member}")
        missing = [member for member in expected if member not in names]
        if missing:
            raise VerificationError(
                f"wheel is missing {len(missing)} bundled skill file(s): "
                + ", ".join(missing[:5])
                + (" ..." if len(missing) > 5 else "")
            )
        if len(expected) < 20:
            raise VerificationError(
                f"only {len(expected)} bundle files found in the checkout; the "
                "comparison would be vacuous (expected SKILL.md + roles + "
                "references + templates)"
            )
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        if not metadata_names:
            raise VerificationError("wheel has no METADATA file")
        metadata = archive.read(metadata_names[0]).decode("utf-8", "replace")
        expected_version = project_version()
        if "Name: teamwork-agents" not in metadata:
            raise VerificationError("wheel metadata does not name teamwork-agents")
        if f"Version: {expected_version}" not in metadata:
            raise VerificationError(
                f"wheel version does not match src/teamwork/version.py ({expected_version})"
            )
    # ``Requires-Dist`` is also emitted for optional extras; only an
    # ungated requirement violates the zero-runtime-dependency contract.
    runtime = [
        line
        for line in metadata.splitlines()
        if line.startswith("Requires-Dist:") and "extra ==" not in line
    ]
    if runtime:
        raise VerificationError(
            "wheel declares runtime dependencies but the contract is zero: " + "; ".join(runtime)
        )
    log(f"wheel payload ok ({len(names)} entries, {len(expected)}/{len(expected)} bundle files)")
    log("wheel metadata ok (no ungated Requires-Dist)")


def inspect_sdist(sdist: Path) -> None:
    """Assert the sdist carries the same bundle and metadata contract."""
    import tarfile

    expected = set(expected_bundle_members())
    expected_dirs = {name[len("teamwork/data/") :] for name in expected}
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
    roots = {name.split("/", 1)[0] for name in names if "/" in name}
    if len(roots) != 1:
        raise VerificationError(f"sdist has an unexpected root layout: {sorted(roots)[:3]}")
    root = roots.pop()
    present = {name[len(root) + 1 :] for name in names}
    missing = sorted(expected_dirs - present)
    if missing:
        raise VerificationError(
            f"sdist is missing {len(missing)} skill bundle file(s): " + ", ".join(missing[:5])
        )
    if not any(name.endswith("PKG-INFO") for name in names):
        raise VerificationError("sdist has no PKG-INFO")
    log(f"sdist payload ok ({len(names)} entries)")


def write_checksums(artefacts: dict[str, Path]) -> Path:
    """Write ``SHA256SUMS`` next to the artefacts."""
    manifest = DIST_DIR / "SHA256SUMS"
    lines: list[str] = []
    for path in sorted(artefacts.values()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    # ``Path.write_text(..., newline=...)`` is Python 3.10+ only; the project
    # supports 3.9, so the file is opened directly (see ``engine.write_lf``).
    with manifest.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    log(f"wrote {manifest.relative_to(REPO_ROOT)}")
    return manifest


def venv_paths(venv_dir: Path) -> tuple:
    """Return ``(python, bin_dir)`` for a virtual environment."""
    if os.name == "nt":  # pragma: no cover - exercised on Windows CI
        return venv_dir / "Scripts" / "python.exe", venv_dir / "Scripts"
    return venv_dir / "bin" / "python", venv_dir / "bin"


def fresh_env() -> dict[str, str]:
    """Environment without ambient Teamwork overrides.

    ``TEAMWORK_ROOT`` redirects workspace commands unconditionally, so leaving
    it set would make the smoke test mutate the operator's live team tree.
    Every ``TEAMWORK_*`` variable is dropped; the smoke test sets only the ones
    it needs. ``PYTHONPATH`` is dropped so the checkout cannot shadow the wheel.
    """
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("TEAMWORK_"):
            env.pop(key, None)
    env.pop("PYTHONPATH", None)
    return env


def smoke_test(wheel: Path, workdir: Path) -> None:
    """Install the wheel in a clean venv and exercise the console script."""
    venv_dir = workdir / "venv"
    log(f"creating throwaway virtualenv at {venv_dir}")
    venv.EnvBuilder(with_pip=True, clear=True).create(str(venv_dir))
    python, bin_dir = venv_paths(venv_dir)
    if not python.is_file():
        raise VerificationError(f"virtualenv python not found: {python}")

    env = fresh_env()
    run_ok(
        [python, "-m", "pip", "install", "--quiet", "--no-deps", wheel],
        env=env,
    )

    console = bin_dir / ("teamwork.exe" if os.name == "nt" else "teamwork")
    if not console.is_file():
        raise VerificationError(f"console script not installed: {console}")

    result = run_ok([console, "--version"], env=env)
    expected = f"teamwork {project_version()}"
    if result.stdout.strip() != expected:
        raise VerificationError(
            f"unexpected --version output: {result.stdout!r} (expected {expected!r})"
        )

    run_ok([console, "selftest"], env=env)

    full_loop_smoke(console, workdir, env)

    project = workdir / "init-project"
    project.mkdir()
    run_ok(
        [console, "init", "--no-git", "--agents", "ceo,architect,developer-1,reviewer-1"],
        cwd=project,
        env=env,
    )
    teams = project / ".pi" / "Teamwork" / "Teams"
    if not teams.is_dir() or not any(teams.iterdir()):
        raise VerificationError(f"`teamwork init` created no workspace under {teams}")
    log("installed-wheel smoke test ok (--version, selftest, init)")


def cli(console: Path, args: Sequence[str], cwd: Path, env: dict[str, str]) -> str:
    """Run the *installed* console script and return its combined output."""
    result = run([console, *args], cwd=cwd, env=env, capture=True)
    if result.returncode != 0:
        raise VerificationError(
            f"installed `teamwork {' '.join(args)}` failed with exit "
            f"{result.returncode}: {(result.stderr or result.stdout).strip()[:400]}"
        )
    return (result.stdout or "") + (result.stderr or "")


def full_loop_smoke(console: Path, workdir: Path, env: dict[str, str]) -> None:
    """Drive the complete gate loop through the *installed wheel* (AC-10).

    The acceptance suite proves the loop from the repository checkout. This
    proves the same behaviour from a wheel installed into a clean virtualenv,
    which is what a user actually runs.

    The roster is deliberately tiny (CEO, one Developer, one Reviewer) so that
    every staffed role owns a test layer and the stop condition is reachable.
    """
    project = workdir / "loop-project"
    project.mkdir()
    cli(console, ["init", "--no-git", "--agents", "ceo,developer-1,reviewer-1"], project, env)

    cli(
        console,
        [
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the release loop works",
            "--owner",
            "developer",
            "--by",
            "ceo",
        ],
        project,
        env,
    )
    cli(
        console,
        [
            "tests",
            "require",
            "--area",
            "engine",
            "--layers",
            "unit,acceptance",
            "--by",
            "ceo",
            "--reason",
            "release smoke test",
        ],
        project,
        env,
    )

    def add_and_run(layer: str, command: str, by: str) -> None:
        out = cli(
            console,
            ["tests", "add", "--layer", layer, "--area", "engine", "--command", command],
            project,
            env,
        )
        match = re.search(r"(TS-\d+)", out)
        if not match:
            raise VerificationError(f"`tests add {layer}` printed no id: {out.strip()[:200]}")
        cli(
            console,
            [
                "tests",
                "run",
                match.group(1),
                "--by",
                by,
                "--result",
                "pass",
                "--evidence",
                f"{command} @wheel -> ok",
            ],
            project,
            env,
        )

    add_and_run("goal", "teamwork criteria list", "CEO")
    add_and_run("unit", "python -m pytest tests/unit", "Developer-1")
    add_and_run("acceptance", "python -m pytest tests/acceptance", "Reviewer-1")

    added = cli(
        console,
        ["task", "add", "developer", "ship the widget", "--priority", "P0"],
        project,
        env,
    )
    match = re.search(r"(T-\d+)", added)
    if not match:
        raise VerificationError(f"`task add` printed no id: {added.strip()[:200]}")
    task_id = match.group(1)
    cli(console, ["task", "set", "Developer-1", task_id, "--status", "selfcheck"], project, env)
    cli(
        console,
        [
            "selfcheck",
            "developer",
            task_id,
            "--by",
            "Developer-1",
            "--note",
            "re-read the diff and ran the unit layer",
            "--test",
            "python -m pytest tests/unit @wheel -> ok",
        ],
        project,
        env,
    )
    cli(console, ["task", "set", "Developer-1", task_id, "--status", "review"], project, env)
    cli(
        console,
        [
            "review",
            "developer",
            task_id,
            "--by",
            "Reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "python -m pytest tests/acceptance @wheel -> ok",
        ],
        project,
        env,
    )
    cli(
        console,
        [
            "criteria",
            "verify",
            "AC-1",
            "--by",
            "Reviewer-1",
            "--evidence",
            "python -m pytest tests/acceptance @wheel -> ok",
        ],
        project,
        env,
    )

    stopped = run([console, "loop"], cwd=project, env=env, capture=True)
    combined = (stopped.stdout or "") + (stopped.stderr or "")
    if stopped.returncode != 0 or "> STOP" not in combined:
        raise VerificationError(
            "the installed wheel could not reach the stop condition: "
            f"exit {stopped.returncode}; {combined.strip()[-400:]}"
        )
    log("installed-wheel full-loop smoke test ok (gate cleared, loop -> STOP)")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verify_release.py",
        description="Build, inspect and smoke-test the Teamwork release artefacts.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the throwaway virtualenv and project for inspection",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build_artefacts()
        artefacts = find_artefacts()
        inspect_wheel(artefacts["wheel"])
        inspect_sdist(artefacts["sdist"])

        if args.keep:
            workdir = Path(tempfile.mkdtemp(prefix="teamwork-verify-"))
            try:
                smoke_test(artefacts["wheel"], workdir)
            finally:
                log(f"kept scratch directory: {workdir}")
        else:
            with tempfile.TemporaryDirectory(prefix="teamwork-verify-") as tmp:
                smoke_test(artefacts["wheel"], Path(tmp))
        # Publish checksums only after every check passed: a failed run must not
        # leave a manifest next to unverified artefacts.
        write_checksums(artefacts)
    except VerificationError as exc:
        log(f"FAILED: {exc}")
        return 1
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        log(f"FAILED: {type(exc).__name__}: {exc}")
        return 1
    log("OK - release verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
