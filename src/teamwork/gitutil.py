"""Git plumbing used by the branch/PR/merge flow."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .io import write_lf
from .names import slugify

DEFAULT_BASE = "main"

LFS_PATTERNS = (
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.bmp",
    "*.tif",
    "*.tiff",
    "*.psd",
    "*.ai",
    "*.sketch",
    "*.fig",
    "*.mp4",
    "*.mov",
    "*.webm",
    "*.mkv",
    "*.avi",
    "*.mp3",
    "*.wav",
    "*.flac",
    "*.ogg",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.gz",
    "*.bz2",
    "*.7z",
    "*.rar",
    "*.whl",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.a",
    "*.o",
    "*.jar",
    "*.wasm",
    "*.onnx",
    "*.pt",
    "*.pth",
    "*.safetensors",
    "*.ckpt",
    "*.bin",
    "*.gguf",
    "*.parquet",
    "*.arrow",
    "*.feather",
    "*.sqlite",
    "*.db",
    "*.ttf",
    "*.otf",
    "*.woff",
    "*.woff2",
    "*.glb",
    "*.gltf",
    "*.obj",
    "*.fbx",
    "*.blend",
    "*.exr",
    "*.hdr",
    "*.unitypackage",
)


def run_git(project: Path, *argv: str):
    return subprocess.run(["git", "-C", str(project), *argv], capture_output=True, text=True)


def is_git_repo(project: Path) -> bool:
    r = run_git(project, "rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def current_branch(project: Path) -> str:
    return run_git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def branch_exists(project: Path, branch: str) -> bool:
    r = run_git(project, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
    return r.returncode == 0


def branch_merged(project: Path, branch: str, base: str = DEFAULT_BASE) -> bool:
    if not branch or not branch_exists(project, branch):
        return False
    r = run_git(project, "branch", "--merged", base)
    return any(line.strip().lstrip("* ").strip() == branch for line in r.stdout.splitlines())


def branch_worktree(project: Path, branch: str):
    """The worktree that has ``branch`` checked out, or ``None``."""
    current = ""
    for line in run_git(project, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            current = line.split(" ", 1)[1].strip()
        elif line.strip() == f"branch refs/heads/{branch}" and current:
            return Path(current)
    return None


def ensure_lfs(project: Path, quiet: bool = False) -> dict:
    """Enable Git LFS locally and keep .gitattributes in sync."""
    result = {"available": False, "installed": False, "patterns_added": 0}
    probe = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
    if probe.returncode != 0:
        if not quiet:
            print(
                "teamwork: WARNING git-lfs is not installed; large binaries will be"
                " committed as plain blobs. Install git-lfs for archival."
            )
        return result
    result["available"] = True
    inst = subprocess.run(
        ["git", "-C", str(project), "lfs", "install", "--local"], capture_output=True, text=True
    )
    result["installed"] = inst.returncode == 0

    path = project / ".gitattributes"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    have = {line.split()[0] for line in existing if line.strip() and not line.startswith("#")}
    missing = [pat for pat in LFS_PATTERNS if pat not in have]
    if missing:
        lines = list(existing)
        if not any("teamwork: LFS" in line for line in lines):
            lines += ["", "# --- teamwork: Git LFS tracked content ---"]
        lines += [f"{pat} filter=lfs diff=lfs merge=lfs -text" for pat in missing]
        write_lf(path, "\n".join(lines).rstrip() + "\n")
        result["patterns_added"] = len(missing)
    if not quiet:
        print(
            f"teamwork: git-lfs ready (local install={result['installed']}, "
            f"{result['patterns_added']} pattern(s) added to .gitattributes)"
        )
    return result


#: Bytes git inspects when deciding whether a file is binary (see ``buffer_is_binary``).
BINARY_SNIFF_BYTES = 8000


def is_binary_file(path: Path) -> bool:
    """True when the file holds a NUL byte in its prefix, which is git's own test.

    A large *text* file - a record, a generated report, a long markdown document -
    is not LFS material: LFS stores a pointer, so the diff, the merge and
    ``git show <rev>:<path>`` all stop working, and those are exactly the
    operations a record file depends on. Only real binaries belong in LFS.
    """
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(BINARY_SNIFF_BYTES)
    except OSError:
        return False


def lfs_tracked(project: Path, rel: str) -> bool:
    path = project / ".gitattributes"
    if not path.exists():
        return False
    name = Path(rel).name
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and "filter=lfs" in line:
            pattern = parts[0]
            if pattern.startswith("*."):
                if name.endswith(pattern[1:]):
                    return True
            elif Path(rel).match(pattern):
                return True
    return False


def branch_name(instance: str, task_id: str, title: str) -> str:
    who = re.sub(r"[^a-z0-9]+", "-", (instance or "agent").lower()).strip("-")
    return f"{who}/{task_id.lower()}-{slugify(title)}"
