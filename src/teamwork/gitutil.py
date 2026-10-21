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


BINARY_SNIFF_BYTES = 8192


def is_binary_content(path: Path) -> bool:
    """True when the file's CONTENT is binary, the way git decides it.

    The LFS threshold is a binary threshold (Architecture 11.10): a text record
    that grows past it is still a document, so the gates must not refuse it. The
    test reads the bytes, never the name, because a name can be defeated - a
    real binary renamed ``.md`` is still a binary, and a genuine binary dropped
    into ``docs/Team/`` is still a binary. Git makes the same call from the
    bytes (``git diff --numstat`` prints ``-  -`` for a binary), so this is the
    model the repository already trusts.

    A NUL byte in the first 8 KiB is the discriminator, with one exception: a
    UTF-16 document also contains NUL bytes, so a head that decodes as UTF-16
    into printable text is text and stays exempt.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(BINARY_SNIFF_BYTES)
    except OSError:
        return False
    if not head:
        return False
    if b"\x00" not in head:
        return False
    for encoding in ("utf-16-le", "utf-16-be"):
        try:
            candidate = head.decode(encoding)
        except UnicodeDecodeError:
            continue
        if candidate and all(ch.isprintable() or ch in "\n\r\t" for ch in candidate):
            return False
    return True


def _attr_matches(pattern: str, rel: str, name: str) -> bool:
    """Whether a .gitattributes pattern covers this path."""
    if pattern.startswith("*."):
        return name.endswith(pattern[1:])
    return bool(Path(rel).match(pattern))


def lfs_tracked(project: Path, rel: str) -> bool:
    """Whether a .gitattributes pattern would route this file into Git LFS.

    The LAST matching line wins, as git reads it: a later ``-filter`` opt-out
    cancels an earlier ``filter=lfs`` pattern. The opt-out matters because
    `.gitattributes` opts the small social-preview PNG and the brand assets OUT
    of LFS, and a check that ignored the opt-out would report them as LFS
    files - and, for a text file, would report a misconfiguration that does not
    exist.
    """
    path = project / ".gitattributes"
    if not path.exists():
        return False
    name = Path(rel).name
    tracked = False
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if not _attr_matches(parts[0], rel, name):
            continue
        if "filter=lfs" in line:
            tracked = True
        elif "-filter" in line:
            tracked = False
    return tracked


def lfs_text_mismatch(project: Path, rel: str) -> bool:
    """True when a TEXT file is captured by an LFS pattern - a misconfiguration.

    ``.gitattributes`` routes a file into Git LFS BY NAME. A name is not
    evidence, so a text file can be routed into LFS by accident: a record
    written to ``assets/movie.bin`` is a 126-byte POINTER in the tree, and the
    document is gone for every reader without an LFS client. LFS is for
    binaries; a document in LFS is broken.

    The size threshold is not the discriminator here and must not be: a text
    file in LFS is broken at ANY size, so this check is size-independent. It
    asks two questions of the same file - is the content text (the shared
    ``is_binary_content``) and does a pattern capture the name (the shared
    ``lfs_tracked``) - and both answers are reused by the three gates, so the
    gates cannot disagree about which files are misconfigured.
    """
    if not lfs_tracked(project, rel):
        return False
    return not is_binary_content(project / rel)


def branch_name(instance: str, task_id: str, title: str) -> str:
    who = re.sub(r"[^a-z0-9]+", "-", (instance or "agent").lower()).strip("-")
    return f"{who}/{task_id.lower()}-{slugify(title)}"
