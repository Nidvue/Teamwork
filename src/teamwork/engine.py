#!/usr/bin/env python3
"""teamwork.py - workspace + memory manager for the /teamwork skill.

Everything is plain markdown under <project>/.pi/Teamwork/Teams/<Team>/.
Names are PascalCase; the tree is hidden and independent of project output.  Standard library
only, so every teammate can run it with the system python3.

Memory model
------------
* ShortTermMemory.md  loaded into the agent context at startup, continuously
                 updated, auto-consolidated (stale entries move to long-term
                 or are dropped).
* LongTermMemory.md   never loaded automatically, queried with `recall`,
                 capped; the least important overflow is parked in
                 ArchivedMemory.md so the live file never exceeds its cap.
* Global/GlobalMemory.md  CEO-owned shared memory every agent may read, so
                 facts are not duplicated in every private memory.

Usage
-----
    teamwork.py init --project DIR [--agents a,b,c] [--force]
    teamwork.py load AGENT [--limit N]
    teamwork.py remember AGENT TEXT [--layer short|long] [--key K]
                                  [--importance 0-5] [--tags a,b] [--pin]
    teamwork.py global TEXT [--key K] [--importance N] [--tags a,b] [--pin]
    teamwork.py recall QUERY [--agent A] [--all] [--global] [--layer both|short|long]
    teamwork.py touch AGENT ID|KEY [--layer short|long]
    teamwork.py forget AGENT ID|KEY [--layer short|long]
    teamwork.py consolidate [--agent A] [--all] [--dry-run]
    teamwork.py stats [--agent A] [--all]
    teamwork.py agents
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from typing import NoReturn

try:  # normal package import
    from . import resources as _resources
    from .portable import newline_for, pid_alive
    from .version import __version__ as VERSION
except ImportError:  # pragma: no cover - executed as a plain script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import resources as _resources  # type: ignore
    from portable import (
        newline_for,  # type: ignore
        pid_alive,  # type: ignore
    )
    from version import __version__ as VERSION  # type: ignore

# --------------------------------------------------------------------------- #
# Paths and tunables
#
# The bundled skill (SKILL.md, roles/, references/, templates/) is located by
# `resources`, so the same engine works from a git checkout, from an installed
# wheel (`teamwork/data/`) and from an explicit $TEAMWORK_SKILL_DIR override.
# --------------------------------------------------------------------------- #

SKILL_DIR = _resources.skill_root()
ROLES_DIR = _resources.asset("roles")
TEMPLATES_DIR = _resources.asset("templates")
DIR_TEAM_MAP_TPL = "TeamMap.md"

# --------------------------------------------------------------------------- #
# Layout: the team's own tree is hidden and independent of project output.
#
#   <project>/.pi/Teamwork/Teams/<Team>/
#   ├── TeamMap.md              workspace map
#   ├── Settings.json           provider caps and limits
#   ├── Global/                 shared memory + disputes (CEO owns)
#   ├── Roles/<Role>/           SHARED memory + task queue per role
#   ├── Agents/<Instance>/      private charter, worklog, inbox, artifacts, scratch
#   └── Runtime/                locks and provider slots (ephemeral)
#
# Project output (code, tests, docs/Team/*.md) lives in the repository and is
# never mixed with this tree. Team-created names are PascalCase.
# --------------------------------------------------------------------------- #

TEAM_ROOT_DIR = ".pi/Teamwork"
TEAMS_SUBDIR = "Teams"
DIR_GLOBAL = "Global"
DIR_ROLES = "Roles"
DIR_AGENTS = "Agents"
DIR_RUNTIME = "Runtime"
DIR_LOCKS = "Locks"
DIR_SLOTS = "Slots"
DIR_ARTIFACTS = "Artifacts"
DIR_REPORTS = "Reports"
DIR_SCRATCH = "Scratch"
DIR_DOCS = ("docs", "Team")

F_SHORT = "ShortTermMemory.md"
F_LONG = "LongTermMemory.md"
F_MEM_ARCHIVE = "ArchivedMemory.md"
F_TASKS = "TaskQueue.md"
F_ROLE = "Role.md"
F_START = "StartHere.md"
F_WORKLOG = "WorkLog.md"
F_INBOX = "Inbox.md"
F_GLOBAL = "GlobalMemory.md"
F_GLOBAL_ARCHIVE = "GlobalMemoryArchive.md"
F_DISPUTES = "Disputes.md"
F_REDLINES = "RedLines.md"
F_MAP = "TeamMap.md"
F_REVIEWS = "Reviews.md"
F_CRITERIA = "Criteria.md"
DIR_WORKTREES = "Worktrees"
F_SETTINGS = "Settings.json"

# --------------------------------------------------------------------------- #
# Git identity, commit style and Git LFS
#
# Team commits are authored by the ROLE, never by an instance: the mailbox is
# "Developer <developer@agents.nidvue.com>", never "Developer-1 <developer-1@...>".
# --------------------------------------------------------------------------- #

IDENTITY_DOMAIN = os.environ.get("TEAMWORK_IDENTITY_DOMAIN", "agents.nidvue.com")

COMMIT_TYPES = (
    "feat",
    "fix",
    "test",
    "docs",
    "design",
    "research",
    "refactor",
    "perf",
    "build",
    "ci",
    "chore",
    "revert",
)

# Paths tracked with Git LFS: binaries, media, models, datasets, archives.
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

ROLE_DISPLAY = {
    "ceo": "CEO",
    "cto": "CTO",
    "coo": "COO",
    "cfo": "CFO",
    "architect": "Architect",
    "product-manager": "Product Manager",
    "project-manager": "Project Manager",
    "designer": "Designer",
    "developer": "Developer",
    "tester": "Tester",
    "reviewer": "Reviewer",
    "security-auditor": "Security Auditor",
    "release-engineer": "Release Engineer",
    "technical-writer": "Technical Writer",
    "data-engineer": "Data Engineer",
}


def role_identity(role: str) -> tuple:
    """('Developer', 'developer@agents.nidvue.com') - role based, never instance based."""
    slug = resolve_role(role)
    name = ROLE_DISPLAY.get(slug) or pascal(slug).replace("-", " ")
    email = re.sub(r"[^a-z0-9]", "", slug) + "@" + IDENTITY_DOMAIN
    return name, email


def identity_string(role: str) -> str:
    name, email = role_identity(role)
    return f"{name} <{email}>"


def git_identity_args(role: str) -> list:
    name, email = role_identity(role)
    return ["-c", f"user.name={name}", "-c", f"user.email={email}"]


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


# --------------------------------------------------------------------------- #
# Branch -> PR -> Reviewer merge
#
# main only ever receives merges performed by the Reviewer. Every instance works
# on its own branch and hands a PR to the Reviewer.
# --------------------------------------------------------------------------- #

DEFAULT_BASE = "main"
REVIEW_STATUSES = ("open", "approved", "changes-requested", "merged", "closed")

REVIEWS_HEADER = (
    "# Reviews - PRs awaiting the Reviewer\n\n"
    "> One entry per pull request. A branch may only be merged into `main` by the\n"
    "> Reviewer, after its review passed. Manage with `teamwork.py pr ...`.\n\n"
    "Related: [team map](TeamMap.md) | [disputes](Disputes.md)\n"
)


def reviews_path(root: Path) -> Path:
    return root / F_REVIEWS


def new_pr(title: str, **kw) -> dict:
    pr = {
        "id": "",
        "title": one_line(title),
        "status": "open",
        "task": "",
        "role": "",
        "author": "",
        "branch": "",
        "base": DEFAULT_BASE,
        "opened": today_iso(),
        "updated": today_iso(),
        "reviewer": "",
        "merge_commit": "",
        "summary": "",
        "notes": [],
    }
    pr.update({k: one_line(v) if k != "notes" else v for k, v in kw.items() if v})
    return pr


def parse_reviews(path: Path) -> list:
    if not path.exists():
        return []
    out, cur, section = [], None, "meta"
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(P-\d+)\s*(?:·|:)?\s*(.*)$", raw)
        if m:
            if cur:
                out.append(cur)
            cur = new_pr(m.group(2))
            cur["id"] = m.group(1)
            section = "meta"
            continue
        if cur is None:
            continue
        if raw.startswith("### "):
            section = raw[4:].strip().lower()
            continue
        if section == "notes":
            if raw.startswith("- "):
                cur["notes"].append(raw[2:].strip())
            continue
        mm = META_RE.match(raw)
        if mm:
            field, value = mm.group(1), mm.group(2).strip()
            if field in cur and field != "notes":
                cur[field] = value
    if cur:
        out.append(cur)
    return out


def render_reviews(prs: list) -> str:
    assign_ids(prs, "P-")
    out = [REVIEWS_HEADER, ""]
    for pr in sorted(prs, key=lambda x: x["id"]):
        out.append(f"## {pr['id']} · {one_line(pr['title']) or 'PR'}")
        for field in (
            "status",
            "task",
            "role",
            "author",
            "branch",
            "base",
            "opened",
            "updated",
            "reviewer",
            "merge_commit",
        ):
            out.append(f"- {field}: {one_line(pr.get(field, ''))}")
        out.append("")
        if pr["summary"]:
            out.append(f"- summary: {one_line(pr['summary'])}")
            out.append("")
        out.append("### notes")
        for note in pr["notes"]:
            out.append(f"- {one_line(note)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_reviews(path: Path, prs: list) -> None:
    atomic_write(path, render_reviews(prs))


def find_pr(prs: list, handle: str):
    want = (handle or "").strip().upper()
    for i, pr in enumerate(prs):
        if pr["id"].upper() == want or pr["task"].upper() == want:
            return i
    for i, pr in enumerate(prs):
        if want and want.lower() in pr["title"].lower():
            return i
    return None


def find_pr_exact(prs: list, handle: str):
    """Exact id/task match only: a merge must never hit a fuzzy title match."""
    want = (handle or "").strip().upper()
    for i, pr in enumerate(prs):
        if pr["id"].upper() == want or pr["task"].upper() == want:
            return i
    return None


def slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:limit].rstrip("-") or "work"


def one_line(value, limit: int = 0) -> str:
    """Collapse every newline/run of whitespace so a value cannot inject a
    second markdown metadata line (and therefore a forged gate state)."""
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() if limit else text


def body_text(value) -> str:
    """Body text that cannot forge a new record header.

    A body line beginning with ``##`` would otherwise be parsed as the next
    task/memory/dispute entry and could hide or duplicate state. The parser
    already stops reading metadata at the first blank line; this closes the
    remaining header-injection path while keeping the body readable.
    """
    lines = str(value or "").strip().splitlines()
    return "\n".join((" " + line) if re.match(r"^##\s", line) else line for line in lines)


def branch_name(instance: str, task_id: str, title: str) -> str:
    who = re.sub(r"[^a-z0-9]+", "-", (instance or "agent").lower()).strip("-")
    return f"{who}/{task_id.lower()}-{slugify(title)}"


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


def require_reason(force: str, what: str) -> str:
    """A gate override must carry a writeable reason; a blank one is refused."""
    reason = (force or "").strip()
    if not reason:
        die(
            f"--force needs a reason: --force '<why {what} must be overridden>'. "
            "The reason is recorded on the record, in the ledger, and surfaced by "
            "`audit`.",
            2,
        )
    return reason


def validate_actor(
    root: Path, value: str, kind: str = "actor", allow_role: bool = True, must_exist: bool = True
) -> tuple:
    """Resolve an actor to a real instance (or its role).

    Identity here is accountability, not cryptography: it must at least name an
    agent that exists. `--by Reviewer-1` names one instance; a bare role name is
    accepted only when exactly one instance of that role exists, and is refused as
    ambiguous otherwise.
    """
    raw = (value or "").strip()
    if not raw:
        die(f"{kind} must name an agent (an existing instance, or its role)")
    role = resolve_role(raw)
    insts = instances_of(root, role)
    want = pascal(raw)
    for inst in insts:
        if pascal(inst) == want:
            return inst, role
    if allow_role and insts and want == pascal(role):
        return pascal(role), role
    if not allow_role and insts and want == pascal(role) and len(insts) == 1:
        # `--by reviewer` is what the tool prints and the docs teach: accept it
        # when there is exactly one candidate, and resolve it to that instance.
        return insts[0], role
    if not allow_role and insts and want == pascal(role):
        die(
            f"'{raw}' is ambiguous: the {role} role has several instances "
            f"({', '.join(insts)}). Name the one acting."
        )
    if must_exist:
        known = sorted(i for r in list_roles(root) for i in instances_of(root, r))
        hint = ""
        if insts:
            hint = f" The {role} role has instances: {', '.join(insts)} - name one of them."
        die(
            f"unknown {kind} '{raw}'. Known agents: "
            + (", ".join(known) if known else "(none initialised)")
            + hint
        )
    return pascal(raw), role


def check_claimant(root: Path, value: str, kind: str = "claim", role: str = "") -> str:
    """A holder must be a real instance (and, where relevant, of this role).

    A phantom leaks work and capacity; a holder from another role means the task
    silently left its own shared queue. The role check is only applied when the
    caller names the queue it belongs to (task/branch operations).
    """
    name = (value or "").strip()
    if not name or name == "-":
        return ""
    resolved = resolve_role(name)
    if role and resolved != resolve_role(role) and pascal(name) != pascal(role):
        die(
            f"{kind} '{name}' belongs to the {resolved} role, but this work is on "
            f"the {resolve_role(role)} queue. Claimants must come from the owning role."
        )
    known = known_instances(root)
    if not known:
        return name
    if pascal(name) in {pascal(i) for i in known}:
        return name
    if pascal(name) == pascal(resolved) and instances_of(root, resolved):
        return name  # the role itself = shared pool
    print(
        f"# WARNING {kind} '{name}' is not an instance in this team "
        f"({', '.join(known)}); it is recorded but `audit` will flag it"
    )
    return name


def known_instances(root: Path) -> list:
    return sorted(i for r in list_roles(root) for i in instances_of(root, r))


def _find_task_anywhere(root: Path, handle: str, role_hint: str = ""):
    """(task, path, role, index) for a task id on any role queue."""
    roles = [resolve_role(role_hint)] if role_hint else list_roles(root)
    for role in roles:
        path = task_file(root, role)
        tasks = parse_tasks(path)
        idx = find_task(tasks, handle)
        if idx is not None:
            return tasks[idx], path, role, idx
    return None, None, None, None


def retire_branch(root: Path, here: Path, branch: str, force: bool = False) -> bool:
    """Delete a merged branch, retiring the worktree that holds it if needed."""
    flag = "-D" if force else "-d"
    r = run_git(here, "branch", flag, branch)
    if r.returncode != 0 and "used by worktree" in (r.stderr + r.stdout):
        wt_root = str(root / DIR_RUNTIME / DIR_WORKTREES)
        listing = run_git(here, "worktree", "list", "--porcelain").stdout
        target = ""
        for block in listing.split("\n\n"):
            if f"branch refs/heads/{branch}" in block:
                for line in block.splitlines():
                    if line.startswith("worktree "):
                        target = line.split(" ", 1)[1].strip()
        if target and target.startswith(wt_root):
            run_git(here, "worktree", "remove", "--force", target)
            r = run_git(here, "branch", flag, branch)
    if r.returncode == 0:
        print(f"# deleted branch {branch}" + (" (squashed, so forced)" if force else ""))
        return True
    print(f"# could not delete branch {branch}: {r.stderr.strip() or r.stdout.strip()}")
    print(
        f"#   remove its worktree first: git worktree remove --force <path>, then "
        f"git branch -D {branch}"
    )
    return False


def cmd_branch(args) -> int:
    root = project_root(args)
    project = project_of(root)
    here = work_repo(root)
    if not is_git_repo(project):
        die("not a git repository: run `teamwork.py repo`")

    if args.branch_cmd == "list":
        print(f"# Branches ({project})")
        r = run_git(project, "branch", "--format=%(refname:short)")
        print(r.stdout.rstrip() or "  (none)")
        print()
        print("# task -> branch -> PR -> state")
        rows = 0
        for role in list_roles(root):
            for t in parse_tasks(task_file(root, role)):
                if not t.get("branch"):
                    continue
                state = "merged" if branch_merged(project, t["branch"]) else "open"
                print(
                    f"- {role} {t['id']} {t['branch']} pr={t.get('pr') or '-'} "
                    f"{t.get('status')} ({state}) by {t.get('claimed_by') or '-'}"
                )
                rows += 1
        if not rows:
            print("- none")
        return 0

    # start
    task, task_path, task_role, _idx = _find_task_anywhere(root, args.task, args.agent)
    if task is None:
        die(f"no task '{args.task}' on the {resolve_role(args.agent)} queue")
    actor, arole = validate_actor(root, args.agent, "branch owner")
    if arole != task_role:
        die(f"{actor} is {arole}, but {task['id']} belongs to the {task_role} queue")
    if task.get("claimed_by") and pascal(task["claimed_by"]) != pascal(actor):
        if pascal(actor) != pascal(task_role):
            die(
                f"{task['id']} is already claimed by {task['claimed_by']}; "
                f"{actor} cannot start a branch for it. Reclaim it deliberately "
                f"(`task reclaim {task_role} {task['id']} --as {actor} --reason ...`)."
            )
    args.agent = actor
    base = args.base or DEFAULT_BASE
    if not branch_exists(project, base):
        base = current_branch(project) or "HEAD"
    branch = task.get("branch") or branch_name(args.agent, task["id"], task["title"])
    if not branch_exists(project, branch):
        r = run_git(project, "branch", branch, base)
        if r.returncode != 0:
            die(f"could not create {branch} from {base}: {r.stderr.strip()}")

    worktree_note = ""
    if args.worktree:
        # a worktree checks the branch out itself; checking it out here first
        # would make `git worktree add` fail with "already used by worktree"
        wt = root / DIR_RUNTIME / DIR_WORKTREES / safe_component(pascal(args.agent))
        wt.parent.mkdir(parents=True, exist_ok=True)
        listing = run_git(project, "worktree", "list", "--porcelain").stdout
        if str(wt) not in listing:
            r = run_git(project, "worktree", "add", str(wt), branch)
            if r.returncode != 0:
                die(f"worktree add failed for {branch}: {r.stderr.strip()}")
        worktree_note = str(wt)
    else:
        r = run_git(here, "checkout", branch)
        if r.returncode != 0:
            die(f"could not switch to {branch} in {here}: {r.stderr.strip()}")

    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{task_role}.lock"):
        tasks = parse_tasks(task_path)
        idx = find_task(tasks, task["id"])
        tasks[idx]["branch"] = branch
        tasks[idx]["base"] = base
        if worktree_note:
            tasks[idx]["worktree"] = worktree_note
        tasks[idx]["claimed_by"] = tasks[idx].get("claimed_by") or check_claimant(
            root, args.agent, "claim", task_role
        )
        if tasks[idx]["status"] == "todo":
            tasks[idx]["status"] = "doing"
        tasks[idx]["updated"] = today_iso()
        write_tasks(task_path, tasks, task_role)

    ledger_append(
        root,
        "branch.start",
        args.agent,
        task["id"],
        f"{branch} from {base}" + (f" (worktree {worktree_note})" if worktree_note else ""),
        "",
        task_role,
    )
    print(f"# branch {branch} for {args.agent} on {task['id']} ({task_role})")
    print(f"#   commit: teamwork.py commit --role {task_role} --task {task['id']} ...")
    if worktree_note:
        print(f"#   worktree: {worktree_note}")
    print(f"#   submit: teamwork.py pr open --agent {args.agent} --task {task['id']}")
    return 0


def cmd_pr(args) -> int:
    root = project_root(args)
    project = project_of(root)
    here = work_repo(root)
    path = reviews_path(root)

    if args.pr_cmd == "list":
        prs = parse_reviews(path)
        if args.open:
            prs = [p for p in prs if p["status"] in ("open", "approved", "changes-requested")]
        if not prs:
            print("# no PRs" + (" open" if args.open else ""))
            return 0
        print(f"# Reviews ({path})")
        for pr in sorted(prs, key=lambda x: x["id"]):
            print(
                f"- {pr['id']} [{pr['status']}] {pr['task']} {pr['branch']} "
                f"author={pr['author']} reviewer={pr['reviewer'] or '-'} "
                f"merge={pr['merge_commit'] or '-'}"
            )
            if pr["summary"]:
                print(f"    {pr['summary']}")
        return 0

    if args.pr_cmd == "merge":
        return _pr_merge(args, root, project, here, path)

    # open
    actor, role = validate_actor(root, args.agent, "PR author", allow_role=False)
    args.agent = actor
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "merge.lock"):
        return _pr_open(args, root, project, here, path, role)


def _pr_merge(args, root: Path, project: Path, here: Path, path: Path) -> int:
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "merge.lock"):
        with lock(root / DIR_RUNTIME / DIR_LOCKS / "reviews.lock"):
            prs = parse_reviews(path)
            idx = find_pr_exact(prs, args.pr)
            if idx is None:
                die(f"no PR '{args.pr}'")
            pr = prs[idx]
        merger, mrole = validate_actor(root, args.by or "reviewer", "merger", allow_role=False)
        if mrole != "reviewer":
            die(
                f"only the Reviewer may merge into {pr['base']} (you passed "
                f"{merger}). A branch is merged after its review passed; the author "
                "never merges their own work."
            )
        if pascal(pr.get("author") or "") == pascal(merger):
            die(
                f"{merger} authored {pr['id']} and cannot merge it; a different "
                "instance must review and merge."
            )
        if pr["status"] == "merged":
            print(f"# {pr['id']} already merged at {pr['merge_commit']}")
            if args.delete_branch and branch_exists(project, pr["branch"]):
                retire_branch(root, here, pr["branch"], force=True)
            return 0
        if pr["status"] != "approved" and not args.force:
            die(
                f"refusing to merge {pr['id']}: PR status is {pr['status']}, not "
                "'approved'. The Reviewer must pass the review first.",
                2,
            )
        same_as_verdict = pascal(pr.get("reviewer") or "") == pascal(merger)
        other_reviewers = [i for i in instances_of(root, "reviewer") if pascal(i) != pascal(merger)]
        if same_as_verdict and other_reviewers:
            die(
                f"{merger} passed the review of {pr['id']} and cannot also merge it; "
                f"another Reviewer must merge: {', '.join(other_reviewers)}"
            )
        if args.force:
            args.force = require_reason(args.force, "merging without a passing review")
        if same_as_verdict and not other_reviewers:
            print(
                f"# NOTE {merger} both verified and merged {pr['id']}: it is the only "
                "Reviewer instance. Add reviewer-2 to separate the two duties."
            )
            ledger_append(
                root,
                "review.merge_self",
                merger,
                pr["task"],
                f"{pr['id']}: the sole Reviewer instance verified and merged "
                "(no second reviewer to separate the duties)",
            )
        role = resolve_role(pr["role"] or pr["author"])
        if not role:
            die(f"{pr['id']} has no role or author: the PR record is incomplete")
        tpath = task_file(root, role)
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
            tasks = parse_tasks(tpath)
            tidx = find_task(tasks, pr["task"]) if pr["task"] else None
            t = tasks[tidx] if tidx is not None else None
        if t is None:
            die(f"task {pr['task']} not found on the {role} queue")
        if args.force:
            ledger_append(
                root,
                "pr.merge.forced",
                merger,
                pr["task"],
                f"{pr['id']} merged with review_status={t.get('review_status')}: {args.force}",
            )
        if t.get("review_status") != "passed" and not args.force:
            die(
                f"refusing to merge {pr['id']}: review_status={t.get('review_status')}.\n"
                "  The Reviewer must pass it first:\n"
                f"  teamwork.py review {role} {pr['task']} --by <Reviewer instance> "
                "--result pass --evidence '<verify cmd @rev -> result>'",
                2,
            )
        base = pr["base"] or DEFAULT_BASE
        branch = pr["branch"]
        if not branch_exists(project, branch):
            die(f"branch {branch} no longer exists")
        # identify pending generated records (they belong to the merge, not to
        # whichever branch happens to be checked out)
        docs_prefix = "/".join(DIR_DOCS)
        dirty = [
            ln[3:].strip()
            for ln in run_git(here, "status", "--porcelain").stdout.splitlines()
            if ln.strip()
        ]
        records = [d for d in dirty if d == docs_prefix or d.startswith(docs_prefix + "/")]
        if len(records) != len(dirty):
            die(
                "working tree has uncommitted work outside the reviewed records:\n  "
                + "\n  ".join(d for d in dirty if d not in records)
                + "\n  commit it on its task branch first (branch start + commit)"
            )
        base_sha = run_git(here, "rev-parse", base).stdout.strip()
        r = run_git(here, "checkout", base)
        if r.returncode != 0:
            die(f"could not switch to {base} in {here}: {r.stderr.strip()}")
        if records:
            run_git(here, "add", "--", *records)
            rec_msg = build_commit_message(
                "reviewer",
                {
                    "type": "chore",
                    "area": "records",
                    "task": pr["task"],
                    "producers": pr["author"],
                    "goal": f"record the accepted result of {pr['id']}",
                    "deliverable": ", ".join(records),
                    "why": "the evidence ledger and plan must match the merged revision",
                    "status": "recorded",
                    "result": f"review {t.get('review_status')} by {t.get('reviewer') or merger}",
                },
            )
            rr = subprocess.run(
                ["git", "-C", str(here)]
                + git_identity_args("reviewer")
                + ["commit", "-q", "-F", "-"],
                input=rec_msg,
                capture_output=True,
                text=True,
            )
            if rr.returncode != 0:
                run_git(here, "reset", "-q", "--", *records)
                die(
                    "could not commit the generated records (a hook or config "
                    "blocked it); nothing was merged and the records stay staged "
                    "for a retry:\n  "
                    + (rr.stderr.strip() or rr.stdout.strip() or "(no output)").replace(
                        "\n", "\n  "
                    )
                )
            print(f"# recorded {len(records)} team record(s) on {base} before merging")
            base_sha = run_git(here, "rev-parse", base).stdout.strip()
        message = build_commit_message(
            role,
            {
                "type": "chore",
                "area": "merge",
                "task": pr["task"],
                "producers": pr["author"],
                "goal": f"integrate {pr['id']} into {base}",
                "deliverable": f"merge of {branch}",
                "why": f"review passed: {t.get('evidence') or 'see task evidence'}",
                "status": f"merged into {base}",
                "result": f"review by {t.get('reviewer') or args.by} ({t.get('review_status')})",
            },
        )
        if args.squash:
            r = run_git(here, "merge", "--squash", branch)
            if r.returncode == 0:
                r = subprocess.run(
                    ["git", "-C", str(here)]
                    + git_identity_args("reviewer")
                    + ["commit", "-q", "-F", "-"],
                    input=message,
                    capture_output=True,
                    text=True,
                )
            merged = r
        else:
            merged = subprocess.run(
                ["git", "-C", str(here)]
                + git_identity_args("reviewer")
                + ["merge", "--no-ff", "-m", message, branch],
                capture_output=True,
                text=True,
            )
        if merged.returncode != 0:
            run_git(here, "merge", "--abort")
            if args.squash:
                # a squashed-but-uncommitted merge leaves staged changes; restore base
                run_git(here, "reset", "--hard", base_sha or "HEAD")
            die(
                "merge conflict or failure on "
                f"{branch}; nothing was merged and {base} is back at "
                f"{base_sha[:7] if base_sha else 'HEAD'}. The owner must rebase:\n"
                f"{merged.stderr.strip() or merged.stdout.strip()}"
            )
        if (
            args.squash
            and base_sha
            and run_git(here, "diff", "--quiet", f"{base_sha}..HEAD").returncode == 0
        ):
            run_git(here, "reset", "--hard", base_sha)
            die("squash merge produced no change; nothing merged")
        sha = run_git(here, "rev-parse", "--short", "HEAD").stdout.strip()
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
            tasks = parse_tasks(tpath)
            tidx = find_task(tasks, pr["task"])
            if tidx is not None and tasks[tidx].get("review_status") != "passed" and not args.force:
                run_git(here, "reset", "--hard", base_sha)
                die(
                    f"review of {pr['task']} changed during the merge; the merge was "
                    "rolled back and nothing was integrated.",
                    2,
                )
            if tidx is not None:
                tasks[tidx]["merge_commit"] = sha
                tasks[tidx]["status"] = "done"
                tasks[tidx]["updated"] = today_iso()
                write_tasks(tpath, tasks, role)
            # Reviews.md is written under the same lock order as `cmd_review`:
            # role -> reviews. Re-read before writing so a verdict issued during
            # the git merge is not lost.
            with lock(root / DIR_RUNTIME / DIR_LOCKS / "reviews.lock"):
                fresh_prs = parse_reviews(path)
                pidx = find_pr_exact(fresh_prs, pr["id"])
                if pidx is not None:
                    fresh_prs[pidx]["status"] = "merged"
                    fresh_prs[pidx]["reviewer"] = merger
                    fresh_prs[pidx]["merge_commit"] = sha
                    fresh_prs[pidx]["updated"] = today_iso()
                    fresh_prs[pidx]["notes"].append(f"merged into {base} at {sha} by {merger}")
                    if args.force:
                        fresh_prs[pidx]["notes"].append(f"FORCED merge by {merger}: {args.force}")
                    write_reviews(path, fresh_prs)
        ledger_append(
            root, "pr.merge", merger, pr["task"], f"{pr['id']} {branch} -> {base} at {sha}", sha
        )
        print(f"# merged {pr['id']} {branch} -> {base} at {sha} by {merger}")
        if not args.keep_branch:
            if retire_branch(root, here, branch, force=args.squash):
                ledger_append(
                    root,
                    "branch.retire",
                    merger,
                    pr["task"],
                    f"deleted {branch} after {pr['id']} merged",
                    sha,
                )
        return 0


def _pr_open(args, root: Path, project: Path, here: Path, path: Path, role: str) -> int:
    tpath = task_file(root, role)
    lock_path = root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"
    with lock(lock_path):
        tasks = parse_tasks(tpath)
        tidx = find_task(tasks, args.task)
        if tidx is None:
            die(f"no task '{args.task}' on the {role} queue")
        t = tasks[tidx]
    if t.get("review", "required") != "na" and t.get("self_check") != "passed":
        die(
            f"run your own self-check before opening a PR on {t['id']}:\n"
            f"  1) task set {role} {t['id']} --status selfcheck\n"
            f"  2) selfcheck {role} {t['id']} --by {args.agent} --note '...' "
            "--test '<cmd @rev -> result>'",
            2,
        )
    if not t.get("branch"):
        die(
            f"{t['id']} has no branch; start one: "
            f"teamwork.py branch start --agent {args.agent} --task {t['id']}"
        )
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "reviews.lock"):
        prs = parse_reviews(path)
        existing = find_pr(prs, t["id"])
        if existing is not None:
            pr = prs[existing]
            pr["status"] = "open"
            pr["updated"] = today_iso()
            if args.summary:
                pr["summary"] = one_line(args.summary)
            pr["notes"].append(f"re-submitted by {args.agent} after rework")
        else:
            pr = new_pr(
                args.title or t["title"],
                task=t["id"],
                role=role,
                author=args.agent,
                branch=t["branch"],
                base=args.base or t.get("base") or DEFAULT_BASE,
                summary=args.summary or t.get("self_note", ""),
            )
            pr["notes"].append(f"opened by {args.agent}")
            prs.append(pr)
        write_reviews(path, prs)
    with lock(lock_path):
        fresh = parse_tasks(tpath)
        idx = find_task(fresh, t["id"])
        if idx is None:
            die(f"task {t['id']} disappeared while the PR was being opened")
        fresh[idx]["pr"] = pr["id"]
        fresh[idx]["status"] = "review"
        fresh[idx]["updated"] = today_iso()
        t = fresh[idx]
        write_tasks(tpath, fresh, role)

    pushed = ""
    if args.push:
        remote = run_git(here, "remote").stdout.split()
        if not remote:
            pushed = "no remote configured; PR record stays local"
        else:
            r = run_git(here, "push", "-u", remote[0], t["branch"])
            pushed = (
                f"pushed {t['branch']} to {remote[0]}"
                if r.returncode == 0
                else f"push failed: {r.stderr.strip()}"
            )
    ledger_append(
        root, "pr.open", args.agent, t["id"], f"{pr['id']} {pr['branch']} -> {pr['base']}", "", role
    )
    print(f"# {pr['id']} open: {pr['title']}")
    print(f"#   branch {pr['branch']} -> {pr['base']}   author {pr['author']}")
    if pushed:
        print(f"#   {pushed}")
    print(
        f"#   Reviewer: teamwork.py review {role} {t['id']} --by <Reviewer instance> "
        "--result pass|fail ..."
    )
    print(f"#   merge: teamwork.py pr merge --pr {pr['id']} --by <another Reviewer>")
    return 0


# --------------------------------------------------------------------------- #
# Acceptance criteria as records: `loop` cannot report STOP without them
# --------------------------------------------------------------------------- #

F_CRITERIA = "Criteria.md"


def criteria_header(path: Path) -> str:
    f = link_fields(path, "ceo")
    return (
        "# Criteria - acceptance criteria with verification evidence\n\n"
        "> Machine-checkable definition of done. `loop` refuses to STOP while a\n"
        "> criterion is unverified. The CEO writes them from the user's prompt; the\n"
        "> verifier must not come from the owning role.\n\n"
        f"Related: [project]({f['project']}) | [plan]({f['plan']}) | "
        f"[archive ledger]({f['archive']}) | [team map]({f['map']}) | "
        f"[reviews]({_rel(path, reviews_path(team_root_from(path)))}) | "
        f"[disputes]({f['disputes']})\n"
    )


def criteria_path(root: Path) -> Path:
    return root / F_CRITERIA


def new_criterion(cid: str, text: str, owner: str = "", evidence: str = "") -> dict:
    return {
        "id": cid.strip().upper(),
        "text": one_line(text),
        "owner": one_line(owner),
        "status": "open",
        "evidence": one_line(evidence),
        "verified_by": "",
        "verified": "",
        "rev": "",
    }


def parse_criteria(path: Path) -> list:
    if not path.exists():
        return []
    out, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(AC-[A-Za-z0-9._-]+)\s*(?:·|:)?\s*(.*)$", raw)
        if m:
            if cur:
                out.append(cur)
            cur = new_criterion(m.group(1), m.group(2))
            continue
        if cur is None:
            continue
        mm = META_RE.match(raw)
        if mm:
            field, value = mm.group(1), mm.group(2).strip()
            if field in cur:
                cur[field] = value
    if cur:
        out.append(cur)
    return out


def render_criteria(items: list, path: Path = None) -> str:
    header = (
        criteria_header(path)
        if path is not None
        else "# Criteria - acceptance criteria with verification evidence\n"
    )
    out = [header, ""]
    for c in items:
        out.append(f"## {c['id']} · {one_line(c['text']) or 'criterion'}")
        for field in ("status", "owner", "verified_by", "verified", "evidence", "rev"):
            out.append(f"- {field}: {one_line(c.get(field, ''))}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_criteria(path: Path, items: list) -> None:
    atomic_write(path, render_criteria(items, path))


def find_criterion(items: list, handle: str):
    want = (handle or "").strip().upper()
    for i, c in enumerate(items):
        if c["id"].upper() == want:
            return i
    for i, c in enumerate(items):
        if want and want in c["text"].upper():
            return i
    return None


def _criteria_mutate(args, root: Path, path: Path, items: list) -> int:
    """add/verify/reopen/rm under criteria.lock, with a ledger record each."""
    if args.criteria_cmd == "add":
        import re as _re

        if not _re.fullmatch(r"AC-[A-Za-z0-9._-]+", (args.id or "").strip().upper()):
            die(
                f"criterion id '{args.id}' is not readable; use AC-<word> "
                "(letters, digits, dot, dash, underscore)"
            )
        if find_criterion(items, args.id) is not None:
            die(f"criterion {args.id} already exists")
        owner = args.owner or args.by or "ceo"
        owner, _r = validate_actor(root, owner, "criterion owner", must_exist=False)
        actor, _ar = validate_actor(root, args.by, "criterion author")
        items.append(new_criterion(args.id, args.text, owner))
        write_criteria(path, items)
        ledger_append(root, "criteria.add", actor, args.id.upper(), f"{args.text} (owner {owner})")
        print(f"# added {args.id.upper()}: {args.text}")
        return 0
    if args.criteria_cmd == "verify":
        idx = find_criterion(items, args.id)
        if idx is None:
            die(f"no criterion '{args.id}'")
        c = items[idx]
        who, wrole = validate_actor(root, args.by, "verifier")
        if args.test:
            idx_t = find_test(parse_tests(tests_path(root)), args.test)
            trecs = parse_tests(tests_path(root))
            if idx_t is None:
                die(f"no test record '{args.test}'")
            tr = trecs[idx_t]
            if tr["status"] != "passing":
                die(
                    f"{tr['id']} is {tr['status']}, not passing: a criterion cannot "
                    "cite a test that has not passed"
                )
            if resolve_role(tr["owner"]) == wrole:
                die(
                    f"{tr['id']} was run by the owning role ({tr['owner']}): "
                    "verification must be independent"
                )
            args.evidence = f"{tr['id']} ({tr['layer']}/{tr['area']}): {tr['evidence']}"
        if not (args.evidence or "").strip():
            die(
                "verification needs --evidence '<command> @<rev> -> <result>' or "
                "--test <TS-id> of a passing record"
            )
        if not c.get("owner"):
            die(
                f"{c['id']} has no owner role, so independence cannot be checked; "
                "re-add it with --owner <role>"
            )
        if resolve_role(c["owner"]) == wrole:
            die(
                f"{who} is from the owning role ({wrole}) and cannot verify "
                f"{c['id']}; an independent role must verify it"
            )
        c.update(
            {
                "status": "verified",
                "verified_by": who,
                "verified": today_iso(),
                "evidence": args.evidence.strip(),
                "rev": args.rev or "",
            }
        )
        write_criteria(path, items)
        ledger_append(
            root,
            "criteria.verify",
            who,
            c["id"],
            f"{c['evidence'][:140]} (owner {c['owner']})",
            args.rev or "",
        )
        print(f"# {c['id']} verified by {who}: {c['evidence']}")
        return 0
    if args.criteria_cmd == "reopen":
        idx = find_criterion(items, args.id)
        if idx is None:
            die(f"no criterion '{args.id}'")
        actor, _r = validate_actor(root, args.by, "actor")
        items[idx].update(
            {"status": "open", "verified_by": "", "verified": "", "evidence": "", "rev": ""}
        )
        write_criteria(path, items)
        ledger_append(
            root,
            "criteria.reopen",
            actor,
            items[idx]["id"],
            f"verification cleared: {args.reason or '-'}",
        )
        print(f"# {items[idx]['id']} reopened")
        return 0
    # rm
    idx = find_criterion(items, args.id)
    if idx is None:
        die(f"no criterion '{args.id}'")
    actor, arole = validate_actor(root, args.by, "actor")
    if arole != "ceo":
        args.force = require_reason(args.force, "removing a criterion that is not yours to remove")
    removed = items.pop(idx)
    write_criteria(path, items)
    ledger_append(
        root,
        "criteria.rm",
        actor,
        removed["id"],
        f"removed: {removed['text'][:100]}" + (f" FORCED: {args.force}" if args.force else ""),
    )
    print(f"# removed {removed['id']}")
    return 0


def cmd_criteria(args) -> int:
    root = project_root(args)
    path = criteria_path(root)
    items = parse_criteria(path)

    plan_lock = root / DIR_RUNTIME / DIR_LOCKS / "criteria.lock"
    if args.criteria_cmd in ("add", "verify", "reopen", "rm"):
        with lock(plan_lock):
            items = parse_criteria(path)
            return _criteria_mutate(args, root, path, items)

    if args.criteria_cmd == "add":
        if find_criterion(items, args.id) is not None:
            die(f"criterion {args.id} already exists")
        owner = ""
        if args.owner:
            owner, _ = validate_actor(
                root, args.owner, "criterion owner", allow_role=True, must_exist=False
            )
        items.append(new_criterion(args.id, args.text, owner))
        write_criteria(path, items)
        ledger_append(
            root, "criteria.add", "ceo", args.id.upper(), f"{args.text} (owner {owner or '-'})"
        )
        print(f"# added {args.id.upper()}: {args.text}")
        return 0

    if args.criteria_cmd == "verify":
        idx = find_criterion(items, args.id)
        if idx is None:
            die(f"no criterion '{args.id}'")
        c = items[idx]
        who, wrole = validate_actor(root, args.by, "verifier")
        if not (args.evidence or "").strip():
            die("verification needs --evidence '<command> @<rev> -> <result>'")
        if c.get("owner") and resolve_role(c["owner"]) == wrole:
            die(
                f"{who} is from the owning role ({wrole}) and cannot verify "
                f"{c['id']}; an independent role must verify it"
            )
        c["status"] = "verified"
        c["verified_by"] = who
        c["verified"] = today_iso()
        c["evidence"] = args.evidence.strip()
        c["rev"] = args.rev or ""
        write_criteria(path, items)
        ledger_append(
            root,
            "criteria.verify",
            who,
            c["id"],
            f"{c['evidence'][:140]} (owner {c['owner'] or '-'})",
            args.rev or "",
        )
        print(f"# {c['id']} verified by {who}: {c['evidence']}")
        return 0

    if args.criteria_cmd == "reopen":
        idx = find_criterion(items, args.id)
        if idx is None:
            die(f"no criterion '{args.id}'")
        items[idx].update(
            {"status": "open", "verified_by": "", "verified": "", "evidence": "", "rev": ""}
        )
        write_criteria(path, items)
        print(f"# {items[idx]['id']} reopened")
        return 0

    if args.criteria_cmd == "rm":
        idx = find_criterion(items, args.id)
        if idx is None:
            die(f"no criterion '{args.id}'")
        removed = items.pop(idx)
        write_criteria(path, items)
        print(f"# removed {removed['id']}")
        return 0

    # list
    if not items:
        print(f"# no criteria yet ({path})")
        print("# the CEO must write them from the user prompt: criteria add --id AC-1 --text '...'")
        return 3
    done = sum(1 for c in items if c["status"] == "verified")
    print(f"# Criteria ({done}/{len(items)} verified)")
    for c in items:
        print(
            f"- {c['id']} [{c['status']}] {c['text']}"
            + (f"  owner={c['owner']}" if c["owner"] else "")
            + (f"  by={c['verified_by']} {c['verified']}" if c["verified_by"] else "")
        )
        if c["evidence"]:
            print(f"    {c['evidence']}")
    return 0 if done == len(items) else 1


# --------------------------------------------------------------------------- #
# Layered tests: each layer is designed, developed and run by its owning role
#
#   unit        -> Developer      (its own unit tests)
#   integration -> Tester         (its own integration/system/E2E suites)
#   system      -> Architect      (architecture-conformance tests: boundaries, deps, contracts)
#   ui          -> Designer       (UI use-case / flow / a11y tests)
#   acceptance  -> Reviewer       (acceptance tests over every role's output)
#   security    -> Security Auditor
#
# Layers are independent and run in parallel. A (layer, area) pair is unique, so
# the same thing is never tested twice by accident.
# --------------------------------------------------------------------------- #

F_TESTS = "Tests.md"
F_TESTPLAN = "TestPlan.md"
# Every role owns a test layer. Nobody delegates their own layer, and every
# layer is designed, developed, executed and evidenced by its owner.
TEST_LAYERS = (
    "goal",
    "requirements",
    "plan",
    "tech",
    "release",
    "data",
    "process",
    "cost",
    "system",
    "ui",
    "docs",
    "unit",
    "integration",
    "acceptance",
    "security",
)
LAYER_OWNER = {
    "goal": "ceo",
    "requirements": "product-manager",
    "plan": "project-manager",
    "tech": "cto",
    "release": "release-engineer",
    "data": "data-engineer",
    "process": "coo",
    "cost": "cfo",
    "system": "architect",
    "ui": "designer",
    "docs": "technical-writer",
    "unit": "developer",
    "integration": "tester",
    "acceptance": "reviewer",
    "security": "security-auditor",
}
LAYER_WHAT = {
    "goal": "black-box verification that the delivered result meets the user's objective",
    "requirements": "requirement coverage and traceability: every requirement maps to a passing check",
    "plan": "plan integrity: dependency graph, duplicate work, milestone exit criteria",
    "tech": "technology validation: toolchain and dependency upgrades, feasibility spikes, version drills",
    "release": "release tests: reproducible build, CI gates, packaging, upgrade and rollback",
    "data": "data tests: schema and migration correctness, backfill, backup and restore drills",
    "process": "process and automation tests: the documented workflow and tooling actually run",
    "cost": "cost and budget tests: metering, cap enforcement, unit-economics assertions",
    "system": "architecture-conformance tests (boundaries, dependency direction, contract, ADR)",
    "ui": "UI use-case tests (flows, component states, accessibility)",
    "docs": "documentation tests: every documented command and claim is executed as written",
    "unit": "unit tests for the code the Developer wrote",
    "integration": "integration / system / end-to-end tests",
    "acceptance": "acceptance tests over every role's output",
    "security": "security tests (auth, input handling, secrets, red lines)",
}
DEFAULT_REQUIRED_LAYERS = ("unit", "integration", "acceptance")
ALL_LAYERS_SENTINEL = "__all__"
LAYER_CELL = {
    "goal": "goal",
    "requirements": "req",
    "plan": "plan",
    "tech": "tech",
    "release": "rel",
    "data": "data",
    "process": "proc",
    "cost": "cost",
    "system": "sys",
    "ui": "ui",
    "docs": "docs",
    "unit": "unit",
    "integration": "int",
    "acceptance": "acc",
    "security": "sec",
}


def staffed_layers(root: Path) -> list:
    """Layers whose owning role actually has an instance."""
    return [ly for ly in TEST_LAYERS if instances_of(root, LAYER_OWNER[ly])]


TEST_STATUSES = ("pending", "passing", "failing", "na")


def tests_path(root: Path) -> Path:
    return root / F_TESTS


def testplan_path(root: Path) -> Path:
    return root / F_TESTPLAN


def new_test_record(
    layer: str, area: str, owner: str = "", command: str = "", task: str = ""
) -> dict:
    return {
        "id": "",
        "layer": one_line(layer).lower(),
        "area": one_line(area).lower(),
        "owner": one_line(owner),
        "command": one_line(command),
        "task": one_line(task),
        "status": "pending",
        "evidence": "",
        "rev": "",
        "forced": "",
        "updated": today_iso(),
        "by": "",
    }


def parse_tests(path: Path) -> list:
    if not path.exists():
        return []
    out, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(TS-\d+)\s*(?:·|:)?\s*(.*)$", raw)
        if m:
            if cur:
                out.append(cur)
            title = m.group(2)
            parts = [p.strip() for p in title.split("·")]
            cur = new_test_record(parts[0] if parts else "", parts[1] if len(parts) > 1 else "")
            cur["id"] = m.group(1)
            continue
        if cur is None:
            continue
        mm = META_RE.match(raw)
        if mm:
            field, value = mm.group(1), mm.group(2).strip()
            if field in cur:
                cur[field] = value
    if cur:
        out.append(cur)
    return out


def render_tests(records: list, path: Path = None) -> str:
    assign_ids(records, "TS-")
    if path is not None:
        f = link_fields(path, "ceo")
        header = (
            "# Tests - one record per test layer and area\n\n"
            "> A (layer, area) pair appears once: that is what prevents duplicate\n"
            "> testing. Each layer is designed, implemented and run by its owning role.\n\n"
            f"Related: [test plan]({_rel(path, testplan_path(team_root_from(path)))}) | "
            f"[criteria]({_rel(path, criteria_path(team_root_from(path)))}) | "
            f"[reviews]({_rel(path, reviews_path(team_root_from(path)))}) | "
            f"[archive ledger]({f['archive']}) | [team map]({f['map']})\n"
        )
    out = [header, ""]
    order = {ly: i for i, ly in enumerate(TEST_LAYERS)}
    for r in sorted(records, key=lambda x: (order.get(x["layer"], 9), x["area"], x["id"])):
        out.append(f"## {r['id']} · {one_line(r['layer'])} · {one_line(r['area'])}")
        for field in (
            "layer",
            "area",
            "owner",
            "status",
            "task",
            "command",
            "evidence",
            "rev",
            "by",
            "forced",
            "updated",
        ):
            out.append(f"- {field}: {one_line(r.get(field, ''))}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_tests(path: Path, records: list) -> None:
    atomic_write(path, render_tests(records, path))


def parse_testplan(path: Path) -> dict:
    """{area: [layers]} - which layers an area must cover."""
    plan = {}
    if not path.exists():
        return plan
    area = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", raw)
        if m:
            area = m.group(1).strip().lower()
            plan.setdefault(area, [])
            continue
        mm = META_RE.match(raw)
        if mm and area and mm.group(1) == "layers":
            value = mm.group(2).strip()
            if value in ("", "(all staffed role layers)", ALL_LAYERS_SENTINEL):
                plan[area] = [ALL_LAYERS_SENTINEL] if value else []
            else:
                plan[area] = [x.strip() for x in value.split(",") if x.strip()]
    return plan


def render_testplan(plan: dict, path: Path = None) -> str:
    lines = [
        "# Test plan - required layers per area",
        "",
        "> Declared by the Architect with the CEO. `loop` refuses to STOP while a",
        "> required layer is missing, pending or failing.",
        "> Default when an area is not listed: the proportionate core set",
        f"> ({', '.join(DEFAULT_REQUIRED_LAYERS)}) restricted to staffed roles; use",
        "> `__all__` to demand every staffed role's layer for that area.",
        "",
    ]
    if path is not None:
        f = link_fields(path, "ceo")
        lines.append(
            f"Related: [tests]({_rel(path, tests_path(team_root_from(path)))}) | "
            f"[criteria]({_rel(path, criteria_path(team_root_from(path)))}) | "
            f"[architecture]({f['architecture']}) | [plan]({f['plan']})"
        )
        lines.append("")
    for area in sorted(plan):
        lines.append(f"## {area}")
        value = ALL_LAYERS_SENTINEL if plan[area] == [ALL_LAYERS_SENTINEL] else ",".join(plan[area])
        lines.append(f"- layers: {value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_testplan(path: Path, plan: dict) -> None:
    atomic_write(path, render_testplan(plan, path))


def find_test(records: list, handle: str):
    want = (handle or "").strip().upper()
    for i, r in enumerate(records):
        if r["id"].upper() == want:
            return i
    for i, r in enumerate(records):
        if want and (want == r["area"].upper() or want in r["area"].upper()):
            return i
    return None


def areas_in_use(root: Path) -> list:
    """Areas needing coverage: declared in the plan, in tests, or by finished task areas."""
    areas = set(parse_testplan(testplan_path(root)))
    areas |= {r["area"] for r in parse_tests(tests_path(root)) if r["area"]}
    for role in list_roles(root):
        for t in parse_tasks(task_file(root, role)):
            if t.get("area") and t["status"] in ("done", "review"):
                areas.add(t["area"])
    return sorted(a for a in areas if a)


def required_layers_for(root: Path, area: str) -> list:
    """Required layers for an area.

    Default is the proportionate core set (unit + integration + acceptance),
    plus any layer whose role owns a deliverable in that area (declared with
    `tests require`). "Every staffed role must have at least one test record"
    is enforced once, globally, rather than per area.
    """
    plan = parse_testplan(testplan_path(root))
    if area in plan:
        declared = plan[area]
        if declared == [ALL_LAYERS_SENTINEL]:
            return list(staffed_layers(root)) or list(DEFAULT_REQUIRED_LAYERS)
        if declared:
            # an explicitly declared requirement is enforced even if unstaffed: the
            # team must either add the role or narrow it, on the record
            return declared
    staffed = staffed_layers(root)
    core = [ly for ly in DEFAULT_REQUIRED_LAYERS if ly in staffed]
    return core or staffed or list(DEFAULT_REQUIRED_LAYERS)


def test_gaps(root: Path) -> list:
    """[(area, layer, reason)] for required layers that are not passing."""
    records = parse_tests(tests_path(root))
    by_key = {(r["layer"], r["area"]): r for r in records}
    gaps = []
    for area in areas_in_use(root):
        for layer in required_layers_for(root, area):
            owner = LAYER_OWNER.get(layer, "")
            staffed = bool(instances_of(root, owner))
            r = by_key.get((layer, area))
            if r is None:
                why = "missing"
                if not staffed:
                    why = (
                        f"missing: no {owner} instance exists (add one, or narrow "
                        f"it: tests require --area {area} --layers <...> --by ceo "
                        "--reason ...)"
                    )
                gaps.append((area, layer, why))
            elif r["status"] != "passing":
                gaps.append((area, layer, r["status"]))
    return gaps


def owner_for_layer(root: Path, layer: str) -> str:
    return LAYER_OWNER.get(layer, "")


def cmd_tests(args) -> int:
    root = project_root(args)
    path = tests_path(root)
    plan_path = testplan_path(root)
    if args.tests_cmd in ("add", "run", "rm", "require", "plan"):
        with lock(root / DIR_RUNTIME / DIR_LOCKS / "tests.lock"):
            return _tests_mutate(args, root, path, plan_path)
    records = parse_tests(path)

    return _tests_list(args, root, records)


def _tests_mutate(args, root: Path, path: Path, plan_path: Path) -> int:
    records = parse_tests(path)
    plan = parse_testplan(plan_path)
    force = getattr(args, "force", "") or ""
    if force and not force.strip():
        force = require_reason(force, "overriding a test-layer rule")
    if args.tests_cmd == "add":
        layer = args.layer.lower()
        if layer not in TEST_LAYERS:
            die(f"unknown layer '{layer}'. Layers: {', '.join(TEST_LAYERS)}")
        area = (args.area or args.task or "general").lower()
        for r in records:
            if r["layer"] == layer and r["area"] == area:
                die(
                    f"{r['id']} already covers {layer}/{area}: one record per layer "
                    "and area. Update it with `tests run` instead of adding a twin."
                )
        if force:
            force = require_reason(force, "declaring another role's layer")
        owner = args.owner or ""
        if owner:
            owner, orole = validate_actor(root, owner, "test owner")
            want = owner_for_layer(root, layer)
            if orole != want and not force:
                die(
                    f"{layer} tests belong to the {want} role (you passed {owner}). "
                    f"{LAYER_WHAT.get(layer, '')}"
                )
            if orole != want and force:
                print(
                    f"# FORCED: {getattr(args, 'by', '') or owner} declares the "
                    f"{layer} layer for another role's owner: {force}"
                )
        elif not args.no_owner_check:
            inst = instances_of(root, owner_for_layer(root, layer))
            if not inst:
                die(
                    f"no {owner_for_layer(root, layer)} instance exists to own {layer} tests. "
                    f"Add one: init --agents ...,{owner_for_layer(root, layer)}"
                )
            owner = inst[0]
        dup = [r for r in records if args.command and r["command"].strip() == args.command.strip()]
        rec = new_test_record(layer, area, owner, args.command, args.task)
        records.append(rec)
        write_tests(path, records)
        ledger_append(
            root,
            "tests.add",
            owner,
            rec["id"],
            f"{layer}/{area}: {args.command or '-'}" + (f" FORCED: {force}" if force else ""),
        )
        print(f"# added {rec['id']} {layer}/{area} owner={owner}")
        if LAYER_WHAT.get(layer):
            print(f"#   {layer}: {LAYER_WHAT[layer]}")
        if dup:
            print(
                f"#   NOTE the same command is already run by {dup[0]['id']} "
                f"({dup[0]['layer']}/{dup[0]['area']}): avoid testing the same "
                "thing twice."
            )
        return 0

    if args.tests_cmd == "run":
        idx = find_test(records, args.id)
        if idx is None:
            die(f"no test record '{args.id}'")
        rec = records[idx]
        actor, arole = validate_actor(root, args.by, "test runner")
        want = owner_for_layer(root, rec["layer"])
        if arole != want and not force:
            die(
                f"{rec['id']} is a {rec['layer']} record owned by the {want} role; "
                f"{actor} is {arole}. A layer is designed and run by its own role."
            )
        if force:
            force = require_reason(force, "running another role's layer")
        if not (args.evidence or "").strip():
            die("a run needs --evidence '<command> @<rev> -> <result>'")
        rec["status"] = "passing" if args.result == "pass" else "failing"
        rec["evidence"] = args.evidence.strip()
        rec["rev"] = args.rev or ""
        rec["by"] = actor
        rec["updated"] = today_iso()
        if args.command:
            rec["command"] = args.command.strip()
        if force:
            rec["forced"] = f"run by {actor} ({arole}) for {want}: {force}"
        write_tests(path, records)
        ledger_append(
            root,
            "tests.run",
            actor,
            rec["id"],
            f"{rec['layer']}/{rec['area']} {rec['status']}: "
            f"{rec['evidence'][:120]}" + (f" FORCED: {force}" if force else ""),
            rec["rev"],
        )
        print(f"# {rec['id']} {rec['layer']}/{rec['area']} -> {rec['status']} by {actor}")
        if rec["status"] == "failing":
            print("#   the owning role must fix it; a failing layer blocks STOP")
        return 0

    if args.tests_cmd == "require":
        area = args.area.lower()
        layers = [x.strip().lower() for x in args.layers.split(",") if x.strip()]
        if not layers:
            die(
                "name at least one layer: --layers "
                + ",".join(staffed_layers(root) or list(TEST_LAYERS))
            )
        for ly in layers:
            if ly not in TEST_LAYERS:
                die(f"unknown layer '{ly}'. Layers: {', '.join(TEST_LAYERS)}")
        actor, arole = validate_actor(root, args.by, "actor")
        if arole not in ("architect", "ceo") and not force:
            die(
                f"only the Architect (with the CEO) declares required test layers "
                f"(you are {actor}). Use --force <reason> to override."
            )
        if force:
            force = require_reason(force, "declaring coverage from another role")
        if not (args.reason or "").strip() and not force:
            die(
                "declare coverage with --reason '<why these layers>': the decision is "
                "recorded and audited"
            )
        previous = ",".join(parse_testplan(plan_path).get(area, [])) or "(default)"
        plan[area] = layers
        write_testplan(plan_path, plan)
        ledger_append(
            root,
            "tests.require",
            actor,
            area,
            f"required layers {previous} -> {','.join(layers)}: "
            f"{args.reason or force}" + (f" FORCED: {force}" if force else ""),
        )
        print(f"# {area} must cover: {', '.join(layers)}")
        return 0

    if args.tests_cmd == "rm":
        idx = find_test(records, args.id)
        if idx is None:
            die(f"no test record '{args.id}'")
        actor, arole = validate_actor(root, args.by, "actor")
        if arole != owner_for_layer(root, records[idx]["layer"]) and not force:
            die(
                f"only the {owner_for_layer(root, records[idx]['layer'])} role may "
                f"remove its own test record (you are {actor})"
            )
        removed = records.pop(idx)
        write_tests(path, records)
        ledger_append(
            root,
            "tests.rm",
            actor,
            removed["id"],
            f"removed {removed['layer']}/{removed['area']}"
            + (f" FORCED: {force}" if force else ""),
        )
        print(f"# removed {removed['id']} ({removed['layer']}/{removed['area']})")
        return 0

    if args.tests_cmd == "plan":
        print(f"# Test coverage plan ({root})")
        areas = areas_in_use(root)
        if not areas:
            print(
                "- no areas yet: declare requirements with "
                "'tests require --area <a> --layers unit,integration'"
            )
            return 3
        idx = {(r["layer"], r["area"]): r for r in records}
        cells = LAYER_CELL
        print(
            "# required per area: the core set ("
            + ",".join(DEFAULT_REQUIRED_LAYERS)
            + ") unless declared; every staffed role must also run its own layer "
            "at least once"
        )
        print("# " + "  ".join(f"{cells[ly]}={ly}" for ly in TEST_LAYERS))
        for area in areas:
            req = required_layers_for(root, area)
            row = []
            for layer in TEST_LAYERS:
                r = idx.get((layer, area))
                if r is None:
                    row.append(f"{cells[layer]}·" if layer not in req else f"{cells[layer]}?")
                else:
                    mark = {
                        "passing": "+",
                        "failing": "!",
                        "pending": ".",
                        "na": "-",
                    }.get(r["status"], "?")
                    row.append(f"{cells[layer]}{mark}")
            print(f"- {area:16s} " + " ".join(row))
        print("# marks: + passing   ! failing   . pending   ? missing   · not required")
        print()
        print("# role coverage (has the role designed, built and run any test?)")
        missing_roles = []
        for layer in TEST_LAYERS:
            owner = LAYER_OWNER[layer]
            if not instances_of(root, owner):
                continue
            mine = [r for r in records if r["layer"] == layer]
            passed = [r for r in mine if r["status"] == "passing"]
            print(
                f"- {owner:18s} {cells[layer]:5s} records={len(mine)} passing={len(passed)}"
                + ("   NO TESTS YET" if not mine else "")
            )
            if not mine:
                missing_roles.append(owner)
        if missing_roles:
            print(
                f"# ROLES WITHOUT TESTS: {', '.join(missing_roles)} - every agent "
                "must design, develop and run its own tests"
            )
        gaps = test_gaps(root)
        for area, layer, why in gaps:
            print(f"# GAP {area}/{layer}: {why}")
        return 1 if gaps else 0

    return _tests_list(args, root, records)


def _tests_list(args, root: Path, records: list) -> int:
    if not records:
        print(f"# no test records yet ({tests_path(root)})")
        print(
            "# each layer is added by its owning role: "
            "tests add --layer unit --area <a> --command '<cmd>'"
        )
        return 0
    if args.layer:
        records = [r for r in records if r["layer"] == args.layer]
    print(f"# Tests ({root})")
    for r in records:
        print(
            f"- {r['id']} [{r['layer']}/{r['area']}] {r['status']:8s} "
            f"owner={r['owner'] or '-'} by={r['by'] or '-'}"
        )
        if r["command"]:
            print(f"    cmd: {r['command']}")
        if r["evidence"]:
            print(f"    evidence: {r['evidence']}")
    gaps = test_gaps(root)
    if gaps:
        print(f"# {len(gaps)} coverage gap(s): see `tests plan`")
    return 0


def cmd_testplan_unused(args) -> int:
    root = project_root(args)
    plan = parse_testplan(testplan_path(root))
    print(f"# Test plan ({testplan_path(root)})")
    if not plan:
        print(f"# default required layers for any area: {', '.join(DEFAULT_REQUIRED_LAYERS)}")
    for area in sorted(plan):
        print(f"- {area:20s} {', '.join(plan[area])}")
    return 0


# --------------------------------------------------------------------------- #
# Audit trail: append-only hash-chained ledger + provenance + external export
#
# Every mutation writes one JSON line to Ledger.jsonl:
#   {ts, n, actor, role, action, target, detail, rev, prev, hash}
# hash = sha256(prev_hash + canonical_json(record)) so the chain is tamper-evident.
# A third party can verify the chain, the record digests and the git revision
# without trusting the team: `teamwork.py ledger export`, then re-run the checks.
# --------------------------------------------------------------------------- #

F_LEDGER = "Ledger.jsonl"
F_HEAD = "LedgerHead.json"
F_MANIFEST = "AuditManifest.json"
# The generated manifest is AuditManifest.md; AuditReport.md belongs to the
# Security Auditor's findings report and must never be overwritten.
F_AUDITREPORT = "AuditManifest.md"

LEDGER_ACTIONS = (
    "memory.add",
    "memory.update",
    "memory.touch",
    "memory.forget",
    "memory.promote",
    "memory.drop",
    "memory.merge",
    "memory.evict",
    "task.add",
    "task.claim",
    "task.status",
    "task.evidence",
    "task.reclaim",
    "selfcheck",
    "review.pass",
    "review.fail",
    "pr.open",
    "pr.merge",
    "branch.start",
    "branch.retire",
    "criteria.add",
    "criteria.verify",
    "tests.add",
    "tests.run",
    "dispute.open",
    "dispute.round",
    "dispute.escalate",
    "dispute.sign",
    "dispute.resolve",
    "decision.add",
    "commit",
    "ledger.export",
)


def ledger_path(root: Path) -> Path:
    return root / F_LEDGER


def ledger_head_path(root: Path) -> Path:
    return root / DIR_RUNTIME / F_HEAD


def _canon(record: dict) -> str:
    import json

    body = {k: v for k, v in record.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(prev: str, record: dict) -> str:
    import hashlib

    return hashlib.sha256((prev + _canon(record)).encode("utf-8")).hexdigest()


def _clean_detail(detail) -> str:
    text = " ".join(str(detail or "").split())
    return text[:400]


def _ledger_tail(root: Path):
    """(prev_hash, n) of the last complete record, scanning the file itself.

    The file is the source of truth; the head cache is only a fast path.
    """
    import json

    path = ledger_path(root)
    prev, n = "", 0
    if not path.exists():
        return prev, n
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue  # a torn line is skipped, never fatal
        if not isinstance(rec, dict):
            continue
        prev, n = rec.get("hash", prev), n + 1
    return prev, n


def _trim_torn_tail(path: Path) -> int:
    """Drop unparseable trailing lines before appending a new record.

    A crash during ``write`` can leave a partial line without a newline. The
    next append would concatenate onto it and permanently break the chain, so
    the torn tail is removed first. A corrupt line in the *middle* is never
    removed: that is tampering, and ``ledger verify`` must report it.
    """
    import json

    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    dropped = 0
    while lines:
        try:
            rec = json.loads(lines[-1])
        except ValueError:
            rec = None
        if isinstance(rec, dict):
            break
        lines.pop()
        dropped += 1
    if dropped or not text.endswith("\n"):
        atomic_write(path, "\n".join(lines) + "\n")
    return dropped


def ledger_append(
    root: Path,
    action: str,
    actor: str = "",
    target: str = "",
    detail: str = "",
    rev: str = "",
    role: str = "",
    _locked: bool = False,
) -> dict:
    """Append one tamper-evident record under a dedicated lock.

    The lock serialises read-prev -> append -> head-write, so concurrent writers
    can neither fork the chain nor desynchronise the head cache. Callers already
    holding ``ledger.lock`` pass ``_locked=True`` instead of deadlocking.
    """
    import json

    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ledger_head_path(root)
    ctx = (
        contextlib.nullcontext()
        if _locked
        else lock(root / DIR_RUNTIME / DIR_LOCKS / "ledger.lock")
    )
    with ctx:
        dropped = _trim_torn_tail(path)
        if dropped:
            print(
                f"teamwork: WARNING dropped {dropped} torn trailing ledger line(s) "
                "before appending (a crash artefact; run `ledger verify`)",
                file=sys.stderr,
            )
        prev, n = _ledger_tail(root)
        record = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "n": n + 1,
            "actor": actor or "system",
            "role": role or (resolve_role(actor) if actor and actor != "system" else ""),
            "action": action,
            "target": target,
            "detail": _clean_detail(detail),
            "rev": rev or "",
            "prev": prev,
        }
        record["hash"] = _digest(prev, record)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        atomic_write(head, json.dumps({"n": record["n"], "hash": record["hash"]}) + "\n")
    return record


def ledger_read(root: Path) -> list:
    import json

    path = ledger_path(root)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            record = None
        if not isinstance(record, dict):
            out.append(
                {
                    "n": 0,
                    "ts": "",
                    "actor": "<corrupt>",
                    "role": "",
                    "action": "corrupt",
                    "target": "",
                    "detail": line[:80],
                    "rev": "",
                    "hash": "",
                    "prev": "",
                }
            )
            continue
        out.append(record)
    return out


def ledger_cache_behind(root: Path) -> bool:
    """True when the head cache lags the file (a crash artefact, not tampering)."""
    import json

    head = ledger_head_path(root)
    if not head.exists():
        return False
    try:
        cached = int(json.loads(head.read_text(encoding="utf-8")).get("n", 0))
    except (ValueError, OSError, TypeError):
        return False
    return cached < len(ledger_read(root))


def ledger_verify(root: Path, reconcile: bool = False, _locked: bool = False) -> list:
    """Verify the chain. Returns [] when intact, else a list of problems.

    A head cache that is merely *behind* the file is a crash artefact, not
    tampering: it is reconciled (optionally rewritten). A cache that is *ahead*
    of the file means records were removed: that is reported.
    """
    if reconcile and not _locked:
        with lock(root / DIR_RUNTIME / DIR_LOCKS / "ledger.lock"):
            return ledger_verify(root, reconcile=True, _locked=True)
    problems = []
    prev = ""
    records = ledger_read(root)
    for i, r in enumerate(records, 1):
        if r.get("action") == "corrupt":
            problems.append(f"record {i}: unreadable line in the ledger")
            # Do not reset `prev`: the next complete record still links to the
            # last good hash, so a torn line must not be reported as a chain fork.
            continue
        if r.get("prev", "") != prev:
            problems.append(f"record {i}: prev hash mismatch (chain broken)")
        expect = _digest(prev, {k: v for k, v in r.items() if k != "hash"})
        if r.get("hash") != expect:
            problems.append(f"record {i} ({r.get('action')}): digest mismatch (record altered)")
        prev = r.get("hash", "")
    head = ledger_head_path(root)
    if head.exists():
        try:
            import json

            data = json.loads(head.read_text(encoding="utf-8"))
            cached_n = int(data.get("n", 0))
            if cached_n and not records:
                problems.append(
                    f"the ledger is empty but the head cache knows "
                    f"{cached_n} record(s): the trail was deleted"
                )
            if records and cached_n > len(records):
                problems.append(
                    f"head cache knows {cached_n} records but the ledger has "
                    f"{len(records)}: records were removed (truncated)"
                )
            elif records and (
                data.get("hash") != records[-1].get("hash") or cached_n != len(records)
            ):
                if reconcile:
                    atomic_write(
                        head, json.dumps({"n": len(records), "hash": records[-1]["hash"]}) + "\n"
                    )
                else:
                    problems.append(
                        "head cache is behind the ledger (benign crash "
                        "artefact): re-run with --reconcile"
                    )
        except (ValueError, OSError, TypeError):
            problems.append("head cache is unreadable")
    # external anchor: the last exported checkpoint must not be ahead of us
    manifest = docs_dir(root) / F_MANIFEST
    if manifest.exists():
        try:
            import json

            m = json.loads(manifest.read_text(encoding="utf-8"))
            recorded = int(m.get("ledger", {}).get("records", 0))
            manifest_team = str(m.get("team_id") or "")
            current_team = team_identity(root)
            # Only an export from *this* workspace instance anchors this ledger.
            # A manifest without a team id is a legacy export and is not enforced.
            if manifest_team and manifest_team == current_team and recorded > len(records):
                problems.append(
                    f"the last audit export recorded {recorded} records, "
                    f"the ledger has {len(records)}: truncated after export"
                )
        except (ValueError, OSError, TypeError):
            pass
    return problems


def cmd_ledger_repair(args) -> int:
    """Repair a torn tail: drop unreadable/partial trailing lines and log it."""
    root = project_root(args)
    actor, arole = validate_actor(root, args.by, "repairer")
    if arole not in ("ceo", "reviewer") and not args.force:
        die(
            f"only the CEO or a Reviewer may repair the audit trail (you are "
            f"{actor}). Use --force <reason> to override."
        )
    if args.force:
        args.force = require_reason(args.force, "repairing the audit trail")
    if not ledger_path(root).exists():
        die("no ledger to repair")
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "ledger.lock"):
        return _ledger_repair_locked(args, root, actor)


def _ledger_repair_locked(args, root: Path, actor: str) -> int:
    path = ledger_path(root)
    good, dropped = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            import json

            record = json.loads(line)
        except ValueError:
            record = None
        if not isinstance(record, dict):
            dropped.append(i)
            continue
        good.append(line)
    if not dropped:
        print("# nothing to repair: every line parses")
        problems = ledger_verify(root, reconcile=True, _locked=True)
        for pb in problems:
            print(f"- {pb}")
        return 1 if problems else 0
    atomic_write(path, "\n".join(good) + "\n")
    prev, n = _ledger_tail(root)
    atomic_write(ledger_head_path(root), json.dumps({"n": n, "hash": prev}) + "\n")
    ledger_append(
        root,
        "ledger.repair",
        actor,
        str(path),
        f"dropped {len(dropped)} unreadable line(s) at {dropped}: "
        f"{args.reason}" + (f" FORCED: {args.force}" if args.force else ""),
        _locked=True,
    )
    print(f"# repaired: dropped {len(dropped)} unreadable line(s) {dropped}")
    print(f"# reason recorded in the ledger as ledger.repair by {actor}")
    return 0


def cmd_ledger(args) -> int:
    root = project_root(args)
    if args.ledger_cmd == "repair":
        return cmd_ledger_repair(args)

    if args.ledger_cmd == "verify":
        problems = ledger_verify(root, reconcile=getattr(args, "reconcile", False))
        records = ledger_read(root)
        print(f"# Ledger verify ({ledger_path(root)})")
        print(f"# records: {len(records)} | head: {records[-1]['hash'][:16] if records else '-'}")
        if problems:
            for p in problems:
                print(f"- PROBLEM {p}")
            print("# the trail has been altered or truncated")
            return 1
        print("- chain intact, every digest matches")
        return 0

    if args.ledger_cmd == "export":
        return ledger_export(root, args)

    if args.ledger_cmd == "show":
        records = ledger_read(root)
        if args.action:
            records = [r for r in records if r.get("action", "").startswith(args.action)]
        if args.actor:
            records = [r for r in records if pascal(r.get("actor", "")) == pascal(args.actor)]
        if args.target:
            records = [
                r for r in records if args.target.upper() in str(r.get("target", "")).upper()
            ]
        tail = records[-args.tail :] if args.tail else records
        print(f"# Ledger ({len(records)} match, showing {len(tail)})")
        for r in tail:
            print(
                f"- {r.get('ts', '')} #{int(r.get('n') or 0):04d} "
                f"{r.get('action', '?'):16s} "
                f"{r.get('actor', '-'):16s} {r.get('target', '-'):10s} "
                f"{r.get('detail', '')}"
            )
        return 0

    return 0


def kind_is_governance(kind: str) -> bool:
    return kind in ("governance", "redline", "tribunal")


def cmd_decision(args) -> int:
    """Record a decision as a first-class, traceable project record."""
    root = project_root(args)
    actor, role = validate_actor(root, args.by, "decider")
    if kind_is_governance(args.kind) and role not in required_tribunal(root) and not args.force:
        die(
            f"a '{args.kind}' decision is a governance record: only "
            f"{', '.join(required_tribunal(root))} may record it (you are {actor}). "
            "Use --force <reason> to override, and it is recorded."
        )
    if not args.decision.strip():
        die("--decision is required: what was decided")
    path = docs_dir(root) / "Decisions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    kind = args.kind
    ev = one_line(args.evidence)
    if not ev:
        die(
            "--evidence is required: a decision without evidence is not auditable "
            "(give a command @rev -> result, or the document that settles it)"
        )
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "decisions.lock"):
        existing = path.read_text(encoding="utf-8") if path.exists() else "# DECISIONS\n"
        base_ident = f"D-{today_iso().replace('-', '')}-{pascal(actor)}"
        ident = base_ident
        suffix = 2
        while re.search(rf"^##\s+{re.escape(ident)}\b", existing, re.MULTILINE):
            ident = f"{base_ident}-{suffix}"
            suffix += 1
        block = [
            f"## {ident} - {one_line(args.title or args.decision[:60])}",
            "",
            f"- date: {today_iso()}",
            f"- kind: {kind}",
            f"- status: {args.status}",
            f"- deciders: {actor} ({role})",
            f"- decided by: {actor}",
            f"- task: {one_line(args.task) or '-'}",
            f"- context: {one_line(args.context) or '-'}",
            f"- options considered: {one_line(args.options) or '-'}",
            f"- decision: {one_line(args.decision)}",
            f"- why: {one_line(args.why) or '-'}",
            f"- evidence: {ev}",
            f"- falsified by: {one_line(args.falsify) or '-'}",
            f"- consequences: {one_line(args.consequences) or '-'}",
            "",
        ]
        atomic_write(path, existing.rstrip() + "\n\n" + "\n".join(block))
    ledger_append(
        root,
        "decision.add",
        actor,
        args.task or ident,
        f"{kind}: {args.decision}" + (f" FORCED: {args.force}" if args.force else ""),
        args.rev,
    )
    print(f"# {ident} recorded ({kind}) by {actor}")
    print("#   docs/Team/Decisions.md <- committed project record")
    print("#   ledger <- decision.add (tamper-evident)")
    return 0


def cmd_decision_list(args) -> int:
    root = project_root(args)
    path = docs_dir(root) / "Decisions.md"
    if not path.exists():
        print(f"# no decisions recorded ({path})")
        return 0
    print(f"# Decisions ({path})")
    blocks = re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    shown = 0
    for b in blocks:
        head = b.splitlines()[0].strip()
        if "<" in head or head.lower().startswith("sources"):
            continue  # template placeholder, not a recorded decision
        kind = next(
            (ln.split(":", 1)[1].strip() for ln in b.splitlines() if ln.startswith("- kind:")), ""
        )
        if args.kind and kind != args.kind:
            continue
        dec = next(
            (ln.split(":", 1)[1].strip() for ln in b.splitlines() if ln.startswith("- decision:")),
            "",
        )
        ev = next(
            (ln.split(":", 1)[1].strip() for ln in b.splitlines() if ln.startswith("- evidence:")),
            "",
        )
        who = next(
            (
                ln.split(":", 1)[1].strip()
                for ln in b.splitlines()
                if ln.startswith("- decided by:")
            ),
            "",
        )
        print(f"- {head}")
        print(f"    kind={kind or '-'} by={who or '-'}")
        print(f"    decision: {dec[:90]}")
        print(f"    evidence: {ev[:90]}")
        shown += 1
    if not shown:
        print("- none")
    return 0


def cmd_trace(args) -> int:
    """Follow one handle through every record: the internal audit view."""
    root = project_root(args)
    handle = args.handle.strip()
    up = handle.upper()
    print(f"# Trace {handle} ({root})")
    found = False

    for role in list_roles(root):
        for t in parse_tasks(task_file(root, role)):
            if up not in (t["id"].upper(), t["pr"].upper()):
                continue
            found = True
            print(f"\n## task {t['id']} [{t['status']}] {t['title']}  ({role})")
            for field in (
                "claimed_by",
                "area",
                "branch",
                "worktree",
                "pr",
                "review",
                "self_check",
                "review_status",
                "reviewer",
                "merge_commit",
                "evidence",
                "review_evidence",
                "forced",
            ):
                if t.get(field):
                    print(f"- {field}: {t[field]}")
            if t.get("findings"):
                print(f"- findings: {t['findings']}")
            if t.get("branch"):
                prj = work_repo(root)
                base = t.get("base") or DEFAULT_BASE
                if is_git_repo(prj) and branch_exists(prj, t["branch"]):
                    r = run_git(prj, "log", "--format=%h %an %s", f"{base}..{t['branch']}")
                    print("- commits on the branch:")
                    for line in (r.stdout.strip() or "(none)").splitlines():
                        print(f"    {line}")
    for c in parse_criteria(criteria_path(root)):
        if up == c["id"].upper():
            found = True
            print(f"\n## criterion {c['id']} [{c['status']}] {c['text']}")
            print(f"- owner: {c['owner']} | verified by: {c['verified_by']} {c['verified']}")
            print(f"- evidence: {c['evidence']}")
    for r in parse_tests(tests_path(root)):
        if up == r["id"].upper() or up == r["area"].upper():
            found = True
            print(f"\n## test {r['id']} [{r['layer']}/{r['area']}] {r['status']}")
            print(f"- owner: {r['owner']} | run by: {r['by']} | cmd: {r['command']}")
            print(f"- evidence: {r['evidence'] or '-'}")
    for r in parse_reviews(reviews_path(root)):
        if up in (r["id"].upper(), r["task"].upper()):
            found = True
            print(f"\n## PR {r['id']} [{r['status']}] {r['title']}")
            print(
                f"- author: {r['author']} | branch: {r['branch']} -> {r['base']}"
                f" | reviewer: {r['reviewer'] or '-'} | merge: {r['merge_commit'] or '-'}"
            )
            for n in r["notes"]:
                print(f"    note: {n}")
    for d in parse_disputes(disputes_path(root)):
        if up in (d["id"].upper(), (d["task"] or "").upper()):
            found = True
            print(f"\n## dispute {d['id']} [{d['status']}] {d['topic']}")
            print(
                f"- {d['raised_by']} -> {d['against']} | round {d['round']} | "
                f"escalated: {'yes' if d['escalated'] else 'no'}"
            )
            for r in d["rounds"]:
                print(f"    r{r['n']} {r['by']} {r['date']}: {r['text']}")
            if d["decision"]:
                print(f"- ruling: signed[{', '.join(d['signed'])}] {d['decision']}")

    events = [
        r
        for r in ledger_read(root)
        if up in str(r.get("target", "")).upper() or up in str(r.get("detail", "")).upper()
    ]
    if events:
        found = True
        print(f"\n## ledger events ({len(events)})")
        for r in events:
            print(
                f"- #{int(r.get('n') or 0):04d} {r.get('ts', '')} "
                f"{r.get('action', '?'):16s} {r.get('actor', '-'):16s} "
                f"{r.get('detail', '')}"
            )
    if not found:
        print(f"- nothing references {handle}")
        return 3
    print("\n# every record above is append-only; `ledger verify` proves the chain")
    return 0


def _file_digest(path: Path) -> str:
    import hashlib

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def manifest_path_hint(root: Path) -> Path:
    return docs_dir(root) / F_MANIFEST


def ledger_export(root: Path, args) -> int:
    """Emit an externally verifiable manifest of the whole trail."""
    import json

    project = project_of(root)
    problems = ledger_verify(root, reconcile=True)
    records = ledger_read(root)
    tracked = []
    for path in (
        criteria_path(root),
        tests_path(root),
        testplan_path(root),
        reviews_path(root),
        disputes_path(root),
        global_dir(root) / F_GLOBAL,
        docs_dir(root) / "Project.md",
        docs_dir(root) / "Plan.md",
        docs_dir(root) / "Architecture.md",
        docs_dir(root) / "Decisions.md",
        docs_dir(root) / "Archive.md",
    ):
        if path.exists():
            tracked.append(
                {
                    "path": str(path.relative_to(project)),
                    "sha256": _file_digest(path),
                    "bytes": path.stat().st_size,
                }
            )
    for role in list_roles(root):
        for fn in (F_SHORT, F_LONG, F_MEM_ARCHIVE, F_TASKS):
            p = role_dir(root, role) / fn
            if p.exists():
                tracked.append(
                    {
                        "path": str(p.relative_to(project)),
                        "sha256": _file_digest(p),
                        "bytes": p.stat().st_size,
                    }
                )
    git_info = {"head": "", "branch": "", "dirty": None, "lfs_files": 0}
    if is_git_repo(project):
        git_info = {
            "head": run_git(project, "rev-parse", "HEAD").stdout.strip(),
            "branch": current_branch(project),
            "dirty": bool(run_git(project, "status", "--porcelain").stdout.strip()),
            "lfs_files": len(
                [
                    ln
                    for ln in run_git(project, "lfs", "ls-files", "--name-only").stdout.splitlines()
                    if ln.strip()
                ]
            ),
        }
    # the export record is appended first, so the checkpoint in this manifest
    # matches what a verifier sees after running `ledger verify`
    export_actor = "system"
    if getattr(args, "by", ""):
        export_actor, _er = validate_actor(root, args.by, "exporter")
    ledger_append(
        root,
        "ledger.export",
        export_actor,
        str(manifest_path_hint(root)),
        f"manifest export ({len(records)} records before this event)",
    )
    records = ledger_read(root)
    problems = ledger_verify(root, reconcile=True)
    external = [a for a in tracked if not a["path"].startswith(".pi/")]
    internal = [a for a in tracked if a["path"].startswith(".pi/")]
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "team": root.name,
        "team_id": team_identity(root) or ensure_team_identity(root),
        # Never embed the absolute checkout path: the manifest is committed and
        # published, and a machine path is both a privacy leak and useless to a
        # verifier on another host.
        "project": project.name,
        "ledger": {
            "records": len(records),
            "head": records[-1]["hash"] if records else "",
            "verified": not problems,
            "problems": problems,
        },
        "git": git_info,
        "artifacts": sorted(external, key=lambda x: x["path"]),
        "local_state": sorted(internal, key=lambda x: x["path"]),
        "how_to_verify": [
            "1. teamwork.py ledger verify   # recompute the sha256 chain over Ledger.jsonl",
            "2. compare the recomputed head hash with ledger.head above "
            "(a rebuilt or truncated ledger cannot reproduce it)",
            "3. sha256sum each artifact in this manifest",
            "4. git cat-file -t <git.head>   # the reviewed revision still exists",
            "5. teamwork.py trace <T-id|AC-id|P-id>   # follow any single claim",
            "note: artifacts are committed project output and are checkable by "
            "anyone; local_state is hidden working state, only checkable on the "
            "machine that produced it. Ledger.jsonl carries its own chain, so it is "
            "represented by ledger.head rather than a digest.",
        ],
    }
    out_dir = docs_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / F_MANIFEST
    report_path = out_dir / F_AUDITREPORT
    if args.dry_run:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    atomic_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# Audit report",
        "",
        f"- generated: {manifest['generated_at']}",
        f"- team: {manifest['team']}",
        f"- ledger: {manifest['ledger']['records']} records, "
        f"chain verified: {manifest['ledger']['verified']}",
        f"- head hash: `{manifest['ledger']['head'][:32]}`",
        f"- git: {manifest['git']['head'][:12] or '(none)'} on "
        f"{manifest['git']['branch'] or '-'}, dirty: {manifest['git']['dirty']}",
        f"- externally verifiable artifacts: {len(manifest['artifacts'])}",
        f"- local-only state files: {len(manifest.get('local_state', []))}",
        "",
        "## Verification (external, no trust required)",
        "",
        "```sh",
        "teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl",
        "sha256sum -c <(jq -r '.artifacts[] | \"\\(.sha256)  \\(.path)\"' "
        "docs/Team/AuditManifest.json)",
        "teamwork.py trace <T-id>     # follow any claim end to end",
        "```",
        "",
        "## Artifacts",
        "",
        "| path | bytes | sha256 |",
        "|---|---|---|",
    ]
    for a in manifest["artifacts"]:
        lines.append(f"| {a['path']} | {a['bytes']} | `{a['sha256'][:16]}…` |")
    if problems:
        lines += ["", "## PROBLEMS", ""] + [f"- {p}" for p in problems]
    atomic_write(report_path, "\n".join(lines).rstrip() + "\n")
    print(f"# manifest: {manifest_path.relative_to(project)}")
    print(f"# report:   {report_path.relative_to(project)}")
    print(f"# ledger records: {len(records)} | chain verified: {not problems}")
    if problems:
        for p in problems:
            print(f"- PROBLEM {p}")
        return 1
    return 0


# --------------------------------------------------------------------------- #
# Team skills: agents extract repeated, consistency-critical flows into a skill
# inside the project and share it with the peers of the same role.
#
# Location: <project>/.agents/skills/<kebab-name>/SKILL.md
#   - committed project output, so every instance (and every worktree) sees it
#   - Pi discovers project .agents/skills/ from the working directory upward
# Registry: <team>/Skills.md (who owns it, who was told, current state)
# --------------------------------------------------------------------------- #

F_SKILLS = "Skills.md"
SKILLS_DIR = (".agents", "skills")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SKILLS_HEADER = (
    "# Team skills - extracted, shared flows\n\n"
    "> A skill is created when a flow is repetitive, widely reused and must stay\n"
    "> consistent across instances of a role. The file lives in the project\n"
    "> (`.agents/skills/<name>/SKILL.md`) so every agent and worktree sees it.\n"
    "> Manage with `teamwork.py skill ...`.\n\n"
    "Related: [team map](TeamMap.md) | [tests](Tests.md) | [criteria](Criteria.md) | "
    "[reviews](Reviews.md)\n"
)


def skills_dir(root: Path) -> Path:
    """Where team skills are written: the work tree this agent is actually in."""
    return work_repo(root).joinpath(*SKILLS_DIR)


def skill_file(root: Path, rel: str) -> Path:
    """Locate a registered skill file from either the work tree or the project."""
    for base in (work_repo(root), project_of(root)):
        p = base / rel
        if p.exists():
            return p
    return work_repo(root) / rel


def skills_path(root: Path) -> Path:
    return root / F_SKILLS


def new_skill(name: str, owner_role: str, description: str, by: str = "", path: str = "") -> dict:
    return {
        "id": "",
        "name": one_line(name),
        "owner_role": one_line(owner_role),
        "status": "draft",
        "description": one_line(description),
        "created_by": one_line(by),
        "path": one_line(path),
        "created": today_iso(),
        "updated": today_iso(),
        "shared_with": "",
        "notes": [],
    }


def parse_skills(path: Path) -> list:
    if not path.exists():
        return []
    out, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(S-\d+)\s*(?:·|:)?\s*(.*)$", raw)
        if m:
            if cur:
                out.append(cur)
            cur = new_skill(m.group(2).strip(), "", "")
            cur["id"] = m.group(1)
            continue
        if cur is None:
            continue
        mm = META_RE.match(raw)
        if not mm:
            continue
        field, value = mm.group(1), mm.group(2).strip()
        if field in cur:
            cur[field] = value
        elif field == "note":
            cur["notes"].append(value)
    if cur:
        out.append(cur)
    return out


def render_skills(items: list) -> str:
    assign_ids(items, "S-")
    out = [SKILLS_HEADER, ""]
    for s in items:
        out.append(f"## {s['id']} · {one_line(s['name'])}")
        for field in (
            "name",
            "status",
            "owner_role",
            "created_by",
            "path",
            "created",
            "updated",
            "shared_with",
        ):
            out.append(f"- {field}: {one_line(s.get(field, ''))}")
        out.append("")
        out.append(f"- description: {one_line(s['description'])}")
        for n in s["notes"]:
            out.append(f"- note: {one_line(n)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_skills(path: Path, items: list) -> None:
    atomic_write(path, render_skills(items))


def find_skill(items: list, handle: str):
    want = (handle or "").strip().lower()
    for i, s in enumerate(items):
        if s["id"].lower() == want or s["name"].lower() == want:
            return i
    for i, s in enumerate(items):
        if want and want in s["name"].lower():
            return i
    return None


def skill_body(name: str, owner_role: str, description: str, body: str, by: str) -> str:
    """A skill file that is safe to share: it cannot replace the team rules."""
    return f"""---
name: {name}
description: "{description.strip()}"
---

# {name}

Owner role: **{owner_role}** (created by {by} on {today_iso()}).

Use this skill when: {description.strip()}

## Why this exists

This flow is repetitive, widely reused and must stay consistent across every
{owner_role} instance. Extracted once so it is executed the same way every time.

## Steps

{body.strip() or "1. <fill in the steps this skill standardises>"}

## Evidence

Every run records command + revision + observed result, as the team requires.

## Guardrails

- This skill does not replace `AGENTS.md`, the red lines, or the quality gates.
  If it conflicts with them, they win and this file must be fixed.
- It never bypasses: self-check, independent review, the PR, or the Reviewer-only
  merge. It may not weaken or skip a test layer.
- Changing this skill is normal work: branch, commit with the fixed message style,
  PR, review, merge. Never edit it on `main`.
"""


def cmd_skill(args) -> int:
    root = project_root(args)
    path = skills_path(root)
    items = parse_skills(path)

    if args.skill_cmd == "create":
        name = (args.name or "").strip().lower()
        if not SKILL_NAME_RE.match(name):
            die(f"skill name '{args.name}' must be kebab-case (a-z, 0-9, dashes)")
        if find_skill(items, name) is not None:
            die(f"skill '{name}' is already registered; update it instead")
        actor, arole = validate_actor(root, args.by, "author")
        owner = resolve_role(args.role or arole)
        if not instances_of(root, owner):
            die(f"no {owner} instance exists to own this skill; add one or pick another --role")
        if not (args.description or "").strip():
            die("--for '<when to use it>' is required: it is the skill description")
        body = args.body or ""
        if args.body_file:
            try:
                body = Path(args.body_file).read_text(encoding="utf-8")
            except OSError as exc:
                die(f"cannot read --body-file: {exc}")
        prj = work_repo(root)
        if is_git_repo(prj) and current_branch(prj) == DEFAULT_BASE and not args.allow_main:
            die(
                f"refusing to create a team skill on {DEFAULT_BASE}: it is project "
                "output and must be committed on a task branch.\n"
                "  teamwork.py branch start --agent <you> --task <T-id>\n"
                "  ... then create, commit, PR, review, merge.",
                2,
            )
        target_dir = skills_dir(root) / name
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "SKILL.md"
        if target.exists() and not args.force:
            die(f"{target} already exists; edit it on a branch instead")
        atomic_write(target, skill_body(name, owner, args.description, body, actor))
        canonical = f"{'/'.join(SKILLS_DIR)}/{name}/SKILL.md"
        rec = new_skill(name, owner, args.description, actor, canonical)
        rec["notes"].append(f"created by {actor}")
        items.append(rec)
        write_skills(path, items)
        ledger_append(root, "skill.create", actor, name, f"{owner} skill: {args.description[:90]}")
        print(f"# {rec['id']} skill '{name}' for the {owner} role")
        print(f"#   file: {rec['path']} (project output: commit it on your branch)")
        print(f"#   share it: teamwork.py skill share {name} --by {actor}")
        return 0

    if args.skill_cmd == "share":
        idx = find_skill(items, args.name)
        if idx is None:
            die(f"no skill '{args.name}'")
        s = items[idx]
        actor, arole = validate_actor(root, args.by, "sharer")
        roles = [r.strip() for r in (args.to or s["owner_role"]).split(",") if r.strip()]
        told = []
        for r in roles:
            for inst in instances_of(root, r):
                if pascal(inst) == pascal(actor):
                    continue
                inbox = agent_dir(root, inst) / F_INBOX
                note = [
                    "",
                    f"## {today_iso()} skill shared: {s['name']}",
                    f"- from: {actor} ({arole})",
                    f"- owner role: {s['owner_role']}",
                    f"- when to use: {s['description']}",
                    f"- path: {s['path']}",
                    f"- read it before doing this kind of {s['owner_role']} work, "
                    "and follow it exactly",
                    "",
                ]
                with inbox.open("a", encoding="utf-8", newline="\n") as fh:
                    fh.write("\n".join(note))
                told.append(inst)
        s["status"] = "shared"
        s["shared_with"] = ", ".join(told) if told else s.get("shared_with", "")
        s["updated"] = today_iso()
        s["notes"].append(f"shared by {actor} with: {', '.join(told) or 'nobody'}")
        write_skills(path, items)
        ledger_append(
            root,
            "skill.share",
            actor,
            s["name"],
            f"told: {', '.join(told) or 'nobody'} ({','.join(roles)})",
        )
        print(f"# shared '{s['name']}' with {len(told)} instance(s): {', '.join(told) or 'none'}")
        if s["path"] and not skill_file(root, s["path"]).exists():
            print(f"# WARNING the skill file is missing: {s['path']}")
        return 0

    if args.skill_cmd == "candidates":
        rows = []
        for role in list_roles(root):
            per_area = {}
            for t in parse_tasks(task_file(root, role)):
                if not t.get("area") or t["status"] not in ("done", "review"):
                    continue
                per_area.setdefault(t["area"], []).append(t["title"])
            for area, titles in per_area.items():
                if len(titles) >= args.min_tasks:
                    rows.append((role, area, len(titles), titles[:3]))
        print(f"# Skill candidates ({root})")
        print(
            f"# areas with >= {args.min_tasks} finished task(s) for one role: a flow "
            "worth extracting"
        )
        if not rows:
            print("- none yet: repetition shows up after a few tasks in the same area")
        for role, area, n, titles in sorted(rows, key=lambda r: -r[2]):
            print(f"- {role}/{area}: {n} task(s), e.g. {'; '.join(titles)}")
            print(
                f"    teamwork.py skill create --name {role}-{area} --role {role} "
                f"--by <instance> --for '<when to use>' --body-file <steps.md>"
            )
        return 0

    if args.skill_cmd == "rm":
        idx = find_skill(items, args.name)
        if idx is None:
            die(f"no skill '{args.name}'")
        actor, _r = validate_actor(root, args.by, "actor")
        removed = items.pop(idx)
        write_skills(path, items)
        ledger_append(
            root,
            "skill.rm",
            actor,
            removed["name"],
            f"unregistered ({removed['path']}); delete the file on a branch",
        )
        print(
            f"# unregistered '{removed['name']}'. The file {removed['path']} still "
            "exists: delete it on a branch through the normal review flow."
        )
        return 0

    # list
    print(f"# Team skills ({path})")
    if not items:
        print("- none yet. Create one when a flow is repetitive and must stay consistent:")
        print(
            "  teamwork.py skill create --name <kebab> --role <role> --by <you> "
            "--for '<when to use>'"
        )
        return 0
    for s in items:
        exists = skill_file(root, s["path"]).exists() if s["path"] else False
        print(
            f"- {s['id']} {s['name']:24s} [{s['status']}] owner={s['owner_role']:16s} "
            f"file={'ok' if exists else 'MISSING'}"
        )
        print(f"    when: {s['description'][:90]}")
        if s["shared_with"]:
            print(f"    shared with: {s['shared_with']}")
    return 0


def cmd_identity(args) -> int:
    root = project_root(args)
    if args.audit:
        project = project_of(root)
        return audit_commit_identities(
            project,
            args.rev_range or default_audit_range(project),
            strict_authors=getattr(args, "strict_authors", False),
        )
    if args.role:
        print(identity_string(args.role))
        return 0
    print("# Role commit identities (never instance numbered)")
    roles = list_roles(root) or sorted(ROLE_DISPLAY)
    for role in roles:
        print(f"- {role:18s} {identity_string(role)}")
    print(f"# domain override: TEAMWORK_IDENTITY_DOMAIN (now {IDENTITY_DOMAIN})")
    return 0


# Bot accounts a forge may author a dependency update with. They are not team
# roles, so the role rule does not apply; the privacy scan still checks them.
BOT_IDENTITIES = {"dependabot[bot]", "github-actions[bot]", "renovate[bot]"}
_RE_BOT_EMAIL = re.compile(
    r"^(?:[0-9]+\+)?(?:dependabot|github-actions|renovate)\[bot\]@users\.noreply\.github\.com$"
)
_RE_FORGE_MERGE_SUBJECT = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")
_RE_ACTING_ROLE = re.compile(r"^Acting role:\s*(.+?)\s*$", re.MULTILINE)


def canonical_identities() -> dict:
    """email -> display name for every role the team may commit as."""
    return {role_identity(role)[1]: role_identity(role)[0] for role in ROLE_DISPLAY}


def default_audit_range(project: Path) -> str:
    if run_git(project, "rev-parse", "--verify", "--quiet", "origin/main").returncode == 0:
        return "origin/main..HEAD"
    if run_git(project, "rev-parse", "--verify", "--quiet", "HEAD~1").returncode == 0:
        return "HEAD~1..HEAD"
    return "HEAD"


def audit_commit_identities(project: Path, rev_range: str, strict_authors: bool = False) -> int:
    """Fail when a commit is not authored and committed by the acting role.

    The role that does the work commits it. A forge-created pull-request merge ref
    carries the forge account identity, so it is skipped; its own history is
    audited by the caller's range. Bot dependency updates are allowed. A public
    repository also receives outside contributions: unless ``strict_authors`` is
    set, an author outside the team's identity domain is reported as skipped
    rather than failed, while a team-domain author with the wrong role still
    fails.
    """
    if rev_range.startswith("-"):
        print(f"teamwork: invalid revision range {rev_range!r}")
        return 2
    proc = run_git(
        project, "log", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%P%x1f%B%x1e", rev_range
    )
    if proc.returncode != 0:
        print(f"teamwork: cannot read {rev_range}: {proc.stderr.strip()}")
        return 2
    canonical = canonical_identities()
    problems = []
    seen = 0
    print(f"# Commit identity audit ({rev_range})")
    for record in proc.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) < 6:
            continue
        sha, an, ae, cn, ce = parts[:5]
        parents = parts[5].split()
        body = parts[6] if len(parts) > 6 else ""
        subject = body.splitlines()[0] if body else ""
        short = sha[:12]
        if len(parents) >= 2 and _RE_FORGE_MERGE_SUBJECT.match(subject.strip()):
            print(f"- {short} skipped: forge pull-request merge ref")
            continue
        seen += 1
        reasons = []
        if an in BOT_IDENTITIES and _RE_BOT_EMAIL.match(ae) and ae not in canonical:
            print(f"- {short} ok: bot {an}")
            continue
        expected = canonical.get(ae)
        if expected is None:
            team_domain = ae.lower().endswith("@" + IDENTITY_DOMAIN.lower())
            if not strict_authors and not team_domain and an not in BOT_IDENTITIES:
                print(f"- {short} skipped: external contributor {an} <{ae}>")
                continue
            reasons.append(f"not a role mailbox: {ae}")
        elif an != expected:
            reasons.append(f"display name {an!r} does not match role {expected!r}")
        if ce != ae or cn != an:
            reasons.append(f"committer {cn} <{ce}> differs from author {an} <{ae}>")
        match = _RE_ACTING_ROLE.search(body)
        if not match:
            reasons.append("message has no 'Acting role:' line")
        elif match.group(1) != an:
            reasons.append(f"'Acting role: {match.group(1)}' does not match author {an!r}")
        if reasons:
            problems.append((short, reasons))
            for reason in reasons:
                print(f"- {short} FAIL {an} <{ae}>: {reason}")
        else:
            print(f"- {short} ok {an} <{ae}>")
    print(f"# commits: {seen} | problems: {len(problems)}")
    return 1 if problems else 0


def build_commit_message(role: str, meta: dict) -> str:
    name, _email = role_identity(role)
    typ = (meta.get("type") or "chore").lower()
    if typ not in COMMIT_TYPES:
        typ = "chore"
    area = one_line(meta.get("area") or meta.get("task") or role)
    summary = one_line(meta.get("deliverable") or meta.get("goal") or "update")
    summary = summary[:72]
    lines = [f"{typ}({area}): {summary}", ""]
    fields = [
        ("Task", meta.get("task")),
        ("Role", name),
        ("Producers", meta.get("producers")),
        ("Goal", meta.get("goal")),
        ("Deliverable", meta.get("deliverable")),
        ("Why", meta.get("why")),
        ("Status", meta.get("status")),
        ("Result", meta.get("result")),
        ("Docs", meta.get("docs")),
        ("Refs", meta.get("refs")),
    ]
    for key, value in fields:
        if value:
            lines.append(f"{key}: {one_line(value)}")
    lines += ["", f"Acting role: {name}"]
    return "\n".join(lines) + "\n"


def cmd_commit(args) -> int:
    """Stage, LFS-track and commit a coherent change-set with the fixed style."""
    root = project_root(args)
    project = work_repo(root)
    if not is_git_repo(project):
        die("not a git repository here: run `teamwork.py repo` first")

    base = DEFAULT_BASE
    here = current_branch(project)
    role = resolve_role(args.role or "developer")
    known_roles = list_roles(root)
    if known_roles and role not in known_roles:
        die(
            f"unknown role '{args.role}' for the commit identity. Known roles: "
            f"{', '.join(known_roles)}"
        )
    if args.task:
        t_role = role
        path_t = task_file(root, t_role)
        if find_task(parse_tasks(path_t), args.task) is None:
            die(
                f"no task '{args.task}' on the {t_role} queue, so this commit would "
                f"be attributed to a role that does not own the work. Commit it as "
                f"the owning role, or drop --task.",
                2,
            )
        task, _p, _r, _i = _find_task_anywhere(root, args.task, t_role)
        if task and task.get("branch") and here != task["branch"] and not args.allow_main:
            die(
                f"you are on branch '{here}' but {task['id']} belongs to "
                f"'{task['branch']}'. Switch branches before committing "
                "(one task, one branch).",
                2,
            )
    if here == base and not args.allow_main:
        die(
            f"refusing to commit directly on '{base}'. main only receives merges "
            "performed by the Reviewer.\n"
            "  start a branch for this task first:\n"
            "    teamwork.py branch start --agent <you> --task <T-id>\n"
            "  or merge through the Reviewer:\n"
            "    teamwork.py pr open ... && teamwork.py pr merge --by <another Reviewer>",
            2,
        )

    name, email = role_identity(role)

    producers = args.producers
    if not producers:
        inst = instances_of(root, role)
        claimed = []
        for r in list_roles(root):
            role_matches = resolve_role(r) == resolve_role(role)
            for t in parse_tasks(task_file(root, r)):
                if t["claimed_by"] and (role_matches or f"@{r}" in producers):
                    claimed.append(t["claimed_by"])
        producers = ", ".join(sorted({pascal(x) for x in (claimed or inst)})) or pascal(role)

    meta = {
        "type": args.type,
        "area": args.area,
        "task": args.task,
        "producers": producers,
        "goal": args.goal,
        "deliverable": args.deliverable,
        "why": args.why,
        "status": args.status,
        "result": args.result,
        "docs": args.docs,
        "refs": args.refs,
    }
    if not meta["goal"]:
        die("--goal is required: what were you asked to achieve?")
    if not meta["deliverable"]:
        die("--deliverable is required: what did you produce?")
    if not meta["status"]:
        die("--status is required: the actual state (implemented/reviewed/tested/blocked)")
    if not meta["result"]:
        die(
            "--result is required: the observed outcome, e.g. "
            "'go test ./... @a1b2c3 -> ok 53 tests'"
        )
    if not meta["why"]:
        die("--why is required: why this change is the right one")

    message = build_commit_message(role, meta)

    ensure_lfs(project, quiet=True)
    if args.paths:
        paths = [x.strip() for x in args.paths.split(",") if x.strip()]
        adds = [["git", "-C", str(project), "add", "--", p] for p in paths]
    elif args.all:
        adds = [["git", "-C", str(project), "add", "-A"]]
    else:
        die("pass --paths a,b or --all to stage the change-set")

    if args.dry_run:
        print(f"# identity: {name} <{email}>")
        print(f"# staging: {' '.join(adds[0])}")
        print("--- commit message ---")
        print(message.rstrip())
        return 0

    for cmd in adds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            die(f"git add failed: {r.stderr.strip()}")
    staged = run_git(project, "diff", "--cached", "--name-only").stdout.strip()
    if not staged:
        print("teamwork: nothing staged; nothing to commit")
        return 0
    if args.check_lfs:
        big = []
        for line in staged.splitlines():
            fp = project / line
            try:
                if (
                    fp.is_file()
                    and fp.stat().st_size > args.lfs_threshold
                    and not lfs_tracked(project, line)
                ):
                    big.append(f"{line} ({fp.stat().st_size // 1024} KiB)")
            except OSError:
                pass
        if big:
            die(
                "refusing to commit large unstaged-in-LFS file(s):\n  "
                + "\n  ".join(big)
                + "\n  add a pattern to .gitattributes (teamwork.py repo) or raise"
                " --lfs-threshold",
                2,
            )

    r = subprocess.run(
        ["git", "-C", str(project)] + git_identity_args(role) + ["commit", "-F", "-"],
        input=message,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        die(f"git commit failed: {r.stderr.strip()}")
    sha = run_git(project, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"teamwork: committed {sha} as {name} <{email}>")
    print(f"          {message.splitlines()[0]}")
    print(f"          files: {len(staged.splitlines())}")

    ledger_append(
        root,
        "commit",
        name,
        args.task or "commit",
        f"{message.splitlines()[0]} | {len(staged.splitlines())} file(s) {sha}",
        sha,
    )
    if args.task:
        role_with_task = resolve_role(role)
        path = task_file(root, role_with_task)
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role_with_task}.lock"):
            tasks = parse_tasks(path)
            idx = find_task(tasks, args.task)
            if idx is not None:
                if args.area:
                    tasks[idx]["area"] = slugify(args.area, 24)
                prev = tasks[idx].get("evidence", "")
                entry = f"commit {sha}"
                tasks[idx]["evidence"] = f"{prev}; {entry}" if prev else entry
                tasks[idx]["updated"] = today_iso()
                write_tasks(path, tasks, role_with_task)
                print(f"          recorded commit {sha} on {tasks[idx]['id']}")
    return 0


DEFAULT_PROVIDER_LIMITS = {
    "ollama-cloud": 10,
    "deepseek": 2500,
    "openai": 64,
    "anthropic": 64,
    "default": 8,
}

ACRONYMS = {
    "ceo": "CEO",
    "cto": "CTO",
    "coo": "COO",
    "cfo": "CFO",
    "pm": "PM",
    "qa": "QA",
    "ui": "UI",
    "ux": "UX",
    "api": "API",
}


def pascal(name: str) -> str:
    """developer-2 -> Developer-2 ; product-manager -> ProductManager."""
    parts = [p for p in re.split(r"[-_\s]+", (name or "").strip()) if p]
    out = []
    for part in parts:
        low = part.lower()
        if low in ACRONYMS:
            out.append(ACRONYMS[low])
        elif part.isdigit():
            out.append(part)
        else:
            out.append(part[:1].upper() + part[1:])
    if len(out) > 1 and out[-1].isdigit():
        return "-".join(out[:-1]) + "-" + out[-1]
    return "".join(out) or "Team"


def safe_component(name: str) -> str:
    """A single filesystem path component derived from a user-supplied name.

    ``pascal`` is a display helper and deliberately preserves characters; a
    name such as ``../../escape`` must never turn into a path traversal when it
    becomes a directory or a slot filename. Normal names (``Developer-1``,
    ``ProductManager``) are unchanged.
    """
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "")).strip(".-")
    return text[:80] or "Team"


def team_slug(project: Path, explicit: str = "") -> str:
    raw = explicit or os.environ.get("TEAMWORK_TEAM") or project.name
    return pascal(re.sub(r"[^A-Za-z0-9_-]+", "-", raw)) or "Team"


SLOT_TTL_MINUTES = int(os.environ.get("TEAMWORK_SLOT_TTL_MINUTES", "90"))
REVIEW_FAIL_LIMIT = int(os.environ.get("TEAMWORK_REVIEW_FAIL_LIMIT", "3"))
SHORT_CAP = int(os.environ.get("TEAMWORK_SHORT_CAP", "24"))
LONG_CAP = int(os.environ.get("TEAMWORK_LONG_CAP", "64"))
ARCHIVE_CAP = int(os.environ.get("TEAMWORK_ARCHIVE_CAP", "256"))
STALE_DAYS = int(os.environ.get("TEAMWORK_STALE_DAYS", "3"))
MIN_USES = int(os.environ.get("TEAMWORK_MIN_USES", "2"))
PROMOTE_MIN_IMPORTANCE = int(os.environ.get("TEAMWORK_PROMOTE_MIN_IMPORTANCE", "2"))

# Shared project documents: single owner, single canonical path, no duplicates.
# code first, tests second, docs third - see PRIORITY in the skill.
DOCS = {
    "Project.md": "CEO",
    "Plan.md": "ProjectManager",
    "Board.md": "ProjectManager",
    "Decisions.md": "Architect",
    "Architecture.md": "Architect",
    "Research.md": "ProductManager",
    "Design.md": "Designer",
    "Risks.md": "COO",
    "Costs.md": "CFO",
    "Release.md": "Release Engineer",
    "Archive.md": "CEO",
}
CODE_DIRS = ("src", "lib", "cmd", "internal", "app", "packages", "crates", "rust")
TEST_HINTS = ("test", "tests", "spec", "specs", "e2e", "integration")

# Files/dirs the team must never commit: local working state, caches, secrets.
GITIGNORE_LINES = (
    "# --- teamwork: local working state (never commit) ---",
    ".pi/",
    "# --- teamwork: scratch and editor noise ---",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.orig",
    "*.rej",
    "*.swp",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    "# --- teamwork: secrets ---",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "*.key",
    "# --- teamwork: caches / build output (keep them on disk, just uncommitted) ---",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    "dist/",
    "build/",
    "target/",
    ".venv/",
    "venv/",
    "coverage/",
    ".coverage",
)

# Only these are removed by `clean`; everything else is left alone.
SCRATCH_DIRS = (DIR_SCRATCH,)
SCRATCH_PATTERNS = ("*.tmp", "*.temp", "*.bak", "*.orig", "*.rej", "*.log")

# --------------------------------------------------------------------------- #
# Disputes: independent decisions, rebuttal, 3-round cap, CEO+CTO+CFO tribunal
# --------------------------------------------------------------------------- #

MAX_ROUNDS = int(os.environ.get("TEAMWORK_MAX_DISPUTE_ROUNDS", "3"))
TRIBUNAL = ("ceo", "cto", "cfo")
TRIBUNAL_MIN_SIGNERS = 2
DISPUTE_HEADER = (
    "# DISPUTES - design/decision challenges\n\n"
    "> Every non-trivial decision needs an evidence chain. When you find a design\n"
    "> or decision unreasonable, open a dispute here with counter-evidence.\n"
    "> Max {rounds} rounds between the two agents; after that the CEO + CTO + CFO\n"
    "> tribunal rules and the ruling is binding (record it in docs/Team/Decisions.md).\n"
)
DISPUTE_RE = re.compile(r"^##\s+(D-\d+)\s*(?:·|:)?\s*(.*)$")
ROUND_RE = re.compile(r"^-\s+r(\d+)\s+(\S+)\s+(\S+):\s*(.*)$")


def new_dispute(
    topic: str,
    raised_by: str = "",
    against: str = "",
    evidence: str = "",
    position: str = "",
    task: str = "",
) -> dict:
    return {
        "id": "",
        "topic": one_line(topic),
        "status": "open",
        "raised_by": one_line(raised_by),
        "against": one_line(against),
        "task": one_line(task),
        "round": 0,
        "escalated": False,
        "created": today_iso(),
        "updated": today_iso(),
        "evidence": one_line(evidence),
        "position": one_line(position),
        "rounds": [],
        "signed": [],
        "decision": "",
    }


def parse_disputes(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    cur = None
    section = "meta"
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = DISPUTE_RE.match(raw)
        if m:
            if cur:
                out.append(cur)
            cur = new_dispute(m.group(2))
            cur["id"] = m.group(1)
            section = "meta"
            continue
        if cur is None:
            continue
        if raw.startswith("### "):
            section = raw[4:].strip().lower()
            continue
        if section == "rounds":
            rm = ROUND_RE.match(raw)
            if rm:
                cur["rounds"].append(
                    {
                        "n": int(rm.group(1)),
                        "by": rm.group(2),
                        "date": rm.group(3),
                        "text": rm.group(4).strip(),
                    }
                )
                cur["round"] = max(cur["round"], int(rm.group(1)))
            continue
        if section == "ruling":
            if raw.startswith("- signed:"):
                cur["signed"] = [s.strip() for s in raw.split(":", 1)[1].split(",") if s.strip()]
            elif raw.startswith("- decision:"):
                cur["decision"] = raw.split(":", 1)[1].strip()
            continue
        mm = META_RE.match(raw)
        if mm:
            field, value = mm.group(1), mm.group(2).strip()
            if field in (
                "status",
                "raised_by",
                "against",
                "task",
                "created",
                "updated",
                "evidence",
                "position",
            ):
                cur[field] = value
            elif field == "round":
                try:
                    cur["round"] = int(value)
                except ValueError:
                    pass
            elif field == "escalated":
                cur["escalated"] = value.lower() in ("yes", "true", "1")
    if cur:
        out.append(cur)
    return out


def render_disputes(disputes: list) -> str:
    assign_ids(disputes, "D-")
    out = [DISPUTE_HEADER.format(rounds=MAX_ROUNDS), ""]
    for d in sorted(disputes, key=lambda x: x["id"]):
        out.append(f"## {d['id']} · {one_line(d['topic']) or 'dispute'}")
        for field, value in (
            ("status", d["status"]),
            ("raised_by", d["raised_by"]),
            ("against", d["against"]),
            ("task", d["task"]),
            ("round", str(d["round"])),
            ("escalated", "yes" if d["escalated"] else "no"),
            ("created", d["created"]),
            ("updated", d["updated"]),
        ):
            out.append(f"- {field}: {one_line(value)}")
        out.append("")
        if d["position"]:
            out.append(f"- position: {one_line(d['position'])}")
        if d["evidence"]:
            out.append(f"- evidence: {one_line(d['evidence'])}")
        out.append("")
        out.append("### rounds")
        for r in d["rounds"]:
            out.append(
                f"- r{r['n']} {one_line(r['by'])} {one_line(r['date'])}: {one_line(r['text'])}"
            )
        out.append("")
        out.append("### ruling")
        out.append(f"- signed: {', '.join(one_line(s) for s in d['signed'])}")
        out.append(f"- decision: {one_line(d['decision'])}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_disputes(path: Path, disputes: list) -> None:
    atomic_write(path, render_disputes(disputes))


def disputes_path(root: Path) -> Path:
    return root / F_DISPUTES


def find_dispute(disputes: list, handle: str):
    if re.fullmatch(r"D-\d+", (handle or "").upper()):
        for i, d in enumerate(disputes):
            if d["id"].upper() == handle.upper():
                return i
        return None
    for i, d in enumerate(disputes):
        if handle.lower() in (d["topic"] + " " + d["position"]).lower():
            return i
    return None


ROLE_ALIASES = {
    "dev": "developer",
    "developer": "developer",
    "qa": "tester",
    "test": "tester",
    "tester": "tester",
    "design": "designer",
    "designer": "designer",
    "arch": "architect",
    "architect": "architect",
    "software-architect": "architect",
    "pm": "project-manager",
    "project-manager": "project-manager",
    "product-manager": "product-manager",
    "po": "product-manager",
    "ceo": "ceo",
    "cto": "cto",
    "rel": "release-engineer",
    "release-engineer": "release-engineer",
    "devops": "release-engineer",
    "sre": "release-engineer",
    "writer": "technical-writer",
    "tech-writer": "technical-writer",
    "technical-writer": "technical-writer",
    "docs": "technical-writer",
    "data": "data-engineer",
    "data-engineer": "data-engineer",
    "dba": "data-engineer",
    "coo": "coo",
    "cfo": "cfo",
    "reviewer": "reviewer",
    "security-auditor": "security-auditor",
}

# Cross-links every generated markdown file carries, relative to its own dir.
# Depth: .pi/Teamwork/Teams/<Team>/Roles/<Role>/ = 5 below the project root;
#        .pi/Teamwork/Teams/<Team>/Agents/<Instance>/ = 6.
ROLE_LINKS = (
    "Related: [task queue]({tasks}) | [short-term]({short}) | "
    "[long-term]({long}) | [memory archive]({mem_archive}) | "
    "[global memory]({global_mem}) | [team map]({map}) | "
    "[project]({project}) | [plan]({plan}) | "
    "[architecture]({architecture}) | [archive ledger]({archive})"
)
AGENT_LINKS = (
    "Related: [role charter]({role}) | [shared queue]({tasks}) | "
    "[shared short-term]({short}) | [shared long-term]({long}) | "
    "[shared memory archive]({mem_archive}) | "
    "[worklog]({worklog}) | [inbox]({inbox}) | "
    "[global memory]({global_mem}) | [team map]({map}) | "
    "[project]({project}) | [plan]({plan})"
)


TASK_RE = re.compile(r"^##\s+(T-\d+)\s*(?:·|:)?\s*(.*)$")
ENTRY_RE = re.compile(r"^##\s+(M-\d+)\s*(?:·|:)?\s*(.*)$")
META_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
STATUSES = ("todo", "doing", "selfcheck", "review", "blocked", "done", "dropped")
TASK_HEADER = (
    "# Task queue - {owner} (shared by every {owner} instance)\n\n"
    "> Priority ordered (P0 highest). `task next <instance>` atomically claims the\n"
    "> highest-priority unblocked task and records who is on it, so two instances\n"
    "> never pick the same work. Lifecycle: `doing -> selfcheck -> review -> done`;\n"
    "> a passed review is archived to docs/Team/Archive.md.\n\n" + ROLE_LINKS + "\n"
)


HEADERS = {
    F_SHORT: (
        "# Short-term memory - {owner} (shared by every {owner} instance)\n\n"
        "> Working memory. Loaded at task start, updated continuously. Entries not\n"
        "> used for {stale} days consolidate into long-term memory automatically.\n\n"
        + ROLE_LINKS
        + "\n"
    ),
    F_LONG: (
        "# Long-term memory - {owner} (shared by every {owner} instance)\n\n"
        "> Never loaded automatically. Query with "
        '`teamwork.py recall "<query>" --agent {owner}`.\n'
        "> Capped at {cap} entries; the least important overflow is archived.\n\n"
        + ROLE_LINKS
        + "\n"
    ),
    F_MEM_ARCHIVE: (
        "# Archived memory - {owner} (shared)\n\n"
        "> Overflow evicted from long-term memory. Searchable, never loaded.\n\n"
        + ROLE_LINKS
        + "\n"
    ),
    F_GLOBAL: (
        "# Global memory (CEO-owned)\n\n"
        "> Shared facts, interfaces and conventions for every agent. Read this\n"
        "> before asking a question another agent may have already answered.\n"
        "> Only the CEO writes here; propose additions through the CEO.\n\n"
        "Related: [disputes]({disputes}) | [team map]({map}) | "
        "[project]({project}) | [decisions]({decisions}) | "
        "[archive ledger]({archive})\n"
    ),
    F_GLOBAL_ARCHIVE: (
        "# Global memory archive\n\n"
        "> Overflow evicted from global memory. Searchable, never loaded.\n\n"
        "Related: [global memory]({global_mem}) | [team map]({map}) | "
        "[project]({project}) | [archive ledger]({archive})\n"
    ),
    F_TASKS: TASK_HEADER,
}


def new_task(
    title: str,
    priority: str = "P2",
    shared: str = "",
    deps: str = "",
    tags: str = "",
    status: str = "todo",
    body: str = "",
    evidence: str = "",
    review: str = "required",
) -> dict:
    priority = (priority or "P2").upper()
    if priority not in PRIORITY_ORDER:
        priority = "P2"
    return {
        "id": "",
        "title": one_line(title),
        "priority": priority,
        "status": status if status in STATUSES else "todo",
        "deps": one_line(deps),
        "shared": one_line(shared),
        "tags": one_line(tags),
        "area": "",
        "evidence": one_line(evidence),
        "review": review if review in ("required", "na") else "required",
        "review_status": "na" if review == "na" else "pending",
        "self_check": "na" if review == "na" else "pending",
        "self_note": "",
        "review_evidence": "",
        "reviewer": "",
        "claimed_by": "",
        "branch": "",
        "base": "",
        "worktree": "",
        "pr": "",
        "merge_commit": "",
        "review_fails": 0,
        "findings": "",
        "created": today_iso(),
        "updated": today_iso(),
        "body": body_text(body),
    }


def parse_tasks(path: Path) -> list:
    if not path.exists():
        return []
    tasks = []
    current = None
    in_body = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TASK_RE.match(raw)
        if m:
            if current:
                tasks.append(current)
            current = new_task(m.group(2))
            current["id"] = m.group(1)
            in_body = False
            continue
        if current is None:
            continue
        if not raw.strip():
            # The renderer puts one blank line between metadata and body. From
            # here on nothing is metadata: a body line such as
            # ``- status: done`` must never forge the task state.
            if in_body:
                current["body"] = current["body"] + "\n"
            else:
                in_body = True
            continue
        if not in_body:
            mm = META_RE.match(raw)
            if mm:
                field, value = mm.group(1), mm.group(2).strip()
                if field in (
                    "priority",
                    "status",
                    "deps",
                    "shared",
                    "tags",
                    "created",
                    "updated",
                    "evidence",
                    "review",
                    "review_status",
                    "reviewer",
                    "findings",
                    "claimed_by",
                    "self_check",
                    "self_note",
                    "review_evidence",
                    "branch",
                    "base",
                    "worktree",
                    "pr",
                    "merge_commit",
                    "forced",
                    "area",
                    "review_fails",
                ):
                    current[field] = value
                continue
            in_body = True
        current["body"] = (current["body"] + "\n" + raw).strip()
    if current:
        tasks.append(current)
    return [t for t in tasks if t["title"] or t["body"]]


def render_tasks(tasks: list, owner: str, path: Path = None) -> str:
    assign_ids(tasks, "T-")
    ordered = sorted(tasks, key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["id"]))
    out = [header_for(F_TASKS, owner, path), ""]
    for t in ordered:
        out.append(f"## {t['id']} · {one_line(t['title']) or 'task'}")
        meta = [
            ("priority", t["priority"]),
            ("status", t["status"]),
            ("deps", t["deps"]),
            ("shared", t["shared"]),
            ("tags", t["tags"]),
            ("area", t.get("area", "")),
            ("review", t.get("review", "required")),
            ("review_status", t.get("review_status", "pending")),
            ("self_check", t.get("self_check", "pending")),
            ("self_note", t.get("self_note", "")),
            ("reviewer", t.get("reviewer", "")),
            ("review_evidence", t.get("review_evidence", "")),
            ("claimed_by", t.get("claimed_by", "")),
            ("branch", t.get("branch", "")),
            ("base", t.get("base", "")),
            ("worktree", t.get("worktree", "")),
            ("pr", t.get("pr", "")),
            ("merge_commit", t.get("merge_commit", "")),
            ("review_fails", str(t.get("review_fails") or 0)),
            ("forced", t.get("forced", "")),
            ("evidence", t.get("evidence", "")),
            ("findings", t.get("findings", "")),
            ("created", t["created"]),
            ("updated", t["updated"]),
        ]
        for field, value in meta:
            out.append(f"- {field}: {one_line(value)}")
        out.append("")
        if t["body"]:
            out.append(body_text(t["body"]))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_tasks(path: Path, tasks: list, owner: str) -> None:
    atomic_write(path, render_tasks(tasks, owner, path))


def task_file(root: Path, agent: str) -> Path:
    """The role's shared queue. Any instance of the role may claim from it."""
    role = resolve_role(agent)
    d = role_dir(root, role)
    if not d.is_dir() and not agents_dir(root).is_dir():
        die("no workspace here: run `teamwork.py init` first")
    if agents_dir(root).is_dir() and not d.is_dir():
        known = list_roles(root)
        if role not in known:
            die(
                f"no '{role}' role in this team. Known roles: "
                + (", ".join(known) if known else "(none)")
            )
    d.mkdir(parents=True, exist_ok=True)
    return d / F_TASKS


def merge_tasks(dst: list, incoming: list) -> tuple:
    """Fold duplicate tasks (same lowercased title) into one."""
    index = {t["title"].strip().lower(): t for t in dst if t["title"]}
    added = 0
    for src in incoming:
        key = src["title"].strip().lower()
        if key in index and key:
            existing = index[key]
            if PRIORITY_ORDER.get(src["priority"], 9) < PRIORITY_ORDER.get(existing["priority"], 9):
                existing["priority"] = src["priority"]
            for field, value in src.items():
                if field in ("id", "title", "priority", "created", "updated"):
                    continue
                if value in ("", None, [], 0) or value == "pending":
                    continue
                if not existing.get(field):
                    existing[field] = value
            if src["updated"] >= existing["updated"]:
                existing["updated"] = src["updated"]
            if existing["status"] in ("todo",) and src["status"] not in ("todo", "dropped"):
                existing["status"] = src["status"]
            continue
        dst.append(dict(src))
        if key:
            index[key] = dst[-1]
        added += 1
    return dst, added


def find_task(tasks: list, handle: str):
    if re.fullmatch(r"T-\d+", handle.upper()):
        wanted = handle.upper()
        for i, t in enumerate(tasks):
            if t["id"].upper() == wanted:
                return i
        return None
    for i, t in enumerate(tasks):
        if t["title"].lower() == handle.lower():
            return i
    for i, t in enumerate(tasks):
        if handle.lower() in (t["title"] + " " + t["body"] + " " + t["shared"]).lower():
            return i
    return None


def dep_satisfied(root: Path, dep: str, cache: dict) -> bool:
    dep = dep.strip()
    if not dep:
        return True
    if ":" in dep:
        other_agent, other_id = dep.split(":", 1)
        other_agent, other_id = other_agent.strip(), other_id.strip()
        key = ("x", other_agent, other_id)
        if key not in cache:
            path = role_dir(root, other_agent) / F_TASKS
            tasks = parse_tasks(path)
            idx = find_task(tasks, other_id)
            cache[key] = bool(idx is not None and tasks[idx]["status"] == "done")
        return cache[key]
    key = ("l", dep.lower())
    if key not in cache:
        cache[key] = None
    return cache[key] is True  # filled by caller for local deps


def local_dep_map(tasks: list) -> dict:
    by_title = {}
    for t in tasks:
        by_title[t["id"].lower()] = t["status"]
        if t["title"]:
            by_title[t["title"].lower()] = t["status"]
    return by_title


def executable(t: dict, lookup: dict, cache: dict, root: Path) -> bool:
    if t["status"] != "todo":
        return False
    for dep in [d for d in re.split(r"[,\s]+", t["deps"]) if d.strip()]:
        if ":" in dep:
            if not dep_satisfied(root, dep, cache):
                return False
        else:
            if lookup.get(dep.lower()) != "done":
                return False
    return True


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def today() -> date:
    return date.today()


def today_iso() -> str:
    return today().isoformat()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return today()


def days_since(value: str) -> int:
    return max((today() - parse_date(value)).days, 0)


LOCK_TIMEOUT = float(os.environ.get("TEAMWORK_LOCK_TIMEOUT", "60"))
LOCK_STALE_SECONDS = float(os.environ.get("TEAMWORK_LOCK_STALE_SECONDS", "300"))


def _lock_owner_stale(path: Path) -> bool:
    """True only when the lock is clearly abandoned: old AND its owner is gone."""
    try:
        age = time.time() - path.stat().st_mtime
        body = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if age < LOCK_STALE_SECONDS:
        return False
    pid = int(body.split(".", 1)[0]) if body.split(".", 1)[0].isdigit() else 0
    if pid <= 0:
        return True
    # Portable liveness probe: on Windows os.kill(pid, 0) is not a probe, so
    # this goes through the audited helper in teamwork.portable.
    return not pid_alive(pid)


@contextlib.contextmanager
def lock(path: Path, timeout: float = None):
    """Exclusive lock via O_CREAT|O_EXCL. Never steals a live lock, and only
    removes the lock file if this process owns it."""
    if timeout is None:
        timeout = LOCK_TIMEOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}.{time.time():.6f}"
    deadline = time.monotonic() + max(timeout, 0.0)
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, token.encode())
            os.close(fd)
            break
        except FileExistsError:
            if _lock_owner_stale(path):
                try:
                    os.unlink(str(path))
                    continue
                except OSError:
                    pass
            if time.monotonic() > deadline:
                die(
                    f"timed out after {int(timeout)}s waiting for {path.name}. "
                    "Another agent holds it. Wait, or clear it only if the owner "
                    "is gone. Never delete a lock that is still in use.",
                    4,
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            if path.read_text(encoding="utf-8").strip() == token:
                path.unlink()
        except OSError:
            pass


def atomic_write(path: Path, text: str) -> None:
    """Write via a unique temp file in the same directory, then rename.

    Windows rejects ``os.replace`` while another process has the target open, so
    the rename is retried briefly. The original mode is preserved because
    ``mkstemp`` creates a 0600 file, which would otherwise make a previously
    group-readable workspace file private after the first rewrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            mode = 0o644
    else:
        # Respect the caller's umask instead of forcing a world-readable file.
        current_umask = os.umask(0)
        os.umask(current_umask)
        mode = 0o666 & ~current_umask
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline_for()) as fh:
            fh.write(text)
        try:
            os.chmod(tmp, mode)
        except OSError:
            pass
        for attempt in range(5):
            try:
                os.replace(tmp, str(path))
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
            except OSError:
                # Windows file-sharing violations are not always PermissionError.
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_lf(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` with LF newlines on every platform and every Python >= 3.9.

    ``Path.write_text(..., newline=...)`` only exists from Python 3.10, and this
    package supports 3.9 (CI runs the matrix on 3.9), so the file is opened here
    directly. On Windows the default text mode would translate ``\n`` to CRLF and
    a clone would no longer be byte-identical across platforms.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"teamwork: {msg}", file=sys.stderr)
    raise SystemExit(code)


# --------------------------------------------------------------------------- #
# Workspace
# --------------------------------------------------------------------------- #


def project_path(args) -> Path:
    if getattr(args, "project", None):
        return Path(args.project).expanduser().resolve()
    return Path.cwd()


def work_repo(root: Path, cwd: Path = None) -> Path:
    """The git work tree this command should act on.

    Inside one of our per-instance worktrees that worktree is the answer;
    otherwise it is the project that owns the team tree.
    """
    cwd = (cwd or Path.cwd()).resolve()
    wt_root = root / DIR_RUNTIME / DIR_WORKTREES
    if wt_root.is_dir():
        for parent in [cwd, *cwd.parents]:
            try:
                rel = parent.relative_to(wt_root)
            except ValueError:
                continue
            if rel.parts:
                cand = wt_root / rel.parts[0]
                if (cand / ".git").exists():
                    return cand
    return project_of(root)


def team_root_from_cwd(cwd: Path) -> Path:
    """If we are inside one of our own worktrees, use the team that owns it.

    `<team>/Runtime/Worktrees/<Instance>/...` -> `<team>`; anything else -> None.
    Without this, running a command from a worktree would look for (and create)
    a second, unrelated team tree.
    """
    for parent in [cwd, *cwd.parents]:
        if parent.name == DIR_WORKTREES and parent.parent.name == DIR_RUNTIME:
            candidate = parent.parent.parent
            if (candidate / DIR_ROLES).is_dir() or (candidate / F_MAP).exists():
                return candidate
    return None


def project_root(args) -> Path:
    """The current team's hidden tree:
    <project>/.pi/Teamwork/Teams/<Team>/"""
    if os.environ.get("TEAMWORK_ROOT"):
        return Path(os.environ["TEAMWORK_ROOT"]).expanduser().resolve()
    if not getattr(args, "project", None):
        found = team_root_from_cwd(Path.cwd().resolve())
        if found is not None:
            return found
    project = project_path(args)
    slug = team_slug(project, getattr(args, "team", "") or "")
    return (project / TEAM_ROOT_DIR / TEAMS_SUBDIR / slug).resolve()


def teams_root_unused(project: Path) -> Path:
    return project / TEAM_ROOT_DIR / TEAMS_SUBDIR


def agents_dir(root: Path) -> Path:
    return root / DIR_AGENTS


def agent_dir(root: Path, agent: str) -> Path:
    """An instance directory: private scratch, artifacts, reports, worklog."""
    return agents_dir(root) / safe_component(pascal(agent))


def roles_dir(root: Path) -> Path:
    return root / DIR_ROLES


def role_dir(root: Path, role: str) -> Path:
    """A role directory: memory and the task list, SHARED by every instance of
    that role. developer-1 and developer-2 share one memory and one queue."""
    return roles_dir(root) / safe_component(pascal(resolve_role(role)))


def global_dir(root: Path) -> Path:
    return root / DIR_GLOBAL


def project_of(root: Path) -> Path:
    """<project>/.pi/Teamwork/Teams/<Team> -> <project>."""
    return root.parents[3]


def docs_dir(root: Path) -> Path:
    """Committed project output. The team's own tree stays in .pi/Teamwork."""
    return project_of(root).joinpath(*DIR_DOCS)


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


_ALIAS_NORM = {_norm_key(k): v for k, v in ROLE_ALIASES.items()}


def resolve_role(name: str) -> str:
    """Map any spelling to the canonical role slug.

    Accepts instance names, PascalCase directory names and aliases:
    Developer-2 -> developer, ProductManager -> product-manager, dev -> developer.
    """
    raw = (name or "").strip()
    n = _norm_key(raw)
    if n in _ALIAS_NORM:
        return _ALIAS_NORM[n]
    n2 = re.sub(r"\d+$", "", n)
    if n2 in _ALIAS_NORM:
        return _ALIAS_NORM[n2]
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or raw.lower()


def list_agents(root: Path) -> list:
    """Instance names (developer-1, developer-2, ...)."""
    d = agents_dir(root)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def list_roles(root: Path) -> list:
    """Canonical role slugs that own a shared memory + task queue."""
    d = roles_dir(root)
    if not d.is_dir():
        return []
    return sorted({resolve_role(p.name) for p in d.iterdir() if p.is_dir()})


def instances_of(root: Path, role: str) -> list:
    role = resolve_role(role)
    return [n for n in list_agents(root) if resolve_role(n) == role]


# --------------------------------------------------------------------------- #
# Entry parsing / serialising
# --------------------------------------------------------------------------- #


def new_entry(
    body: str,
    key: str = "",
    importance: int = 2,
    tags: str = "",
    pinned: bool = False,
    by: str = "",
    src: str = "",
    rev: str = "",
) -> dict:
    return {
        "id": "",
        "key": one_line(key),
        "importance": max(0, min(int(importance), 5)),
        "uses": 0,
        "created": today_iso(),
        "last_used": today_iso(),
        "tags": one_line(tags),
        "pinned": bool(pinned),
        "body": body_text(body),
        # provenance: who recorded it, for what, at which revision
        "by": one_line(by),
        "src": one_line(src),
        "rev": one_line(rev),
    }


def parse_memory(path: Path) -> list:
    if not path.exists():
        return []
    entries = []
    current = None
    in_body = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ENTRY_RE.match(raw)
        if m:
            if current:
                entries.append(current)
            current = new_entry("")
            current["id"] = m.group(1)
            current["key"] = m.group(2).strip()
            in_body = False
            continue
        if current is None:
            continue
        if not raw.strip():
            if in_body:
                current["body"] = current["body"] + "\n"
            else:
                in_body = True
            continue
        if not in_body:
            mm = META_RE.match(raw)
            if mm:
                field, value = mm.group(1), mm.group(2).strip()
                if field == "importance":
                    try:
                        current["importance"] = int(value)
                    except ValueError:
                        pass
                elif field == "uses":
                    try:
                        current["uses"] = int(value)
                    except ValueError:
                        pass
                elif field in ("created", "last_used", "tags", "key", "by", "src", "rev"):
                    current[field] = value
                elif field == "pinned":
                    current["pinned"] = value.lower() in ("yes", "true", "1")
                continue
            in_body = True
        current["body"] = (current["body"] + "\n" + raw).strip()
    if current:
        entries.append(current)
    return [e for e in entries if e["body"] or e["key"]]


def team_root_from(path: Path) -> Path:
    """Recover the team root from any generated file inside the team tree.

    Roles/<Role>/X -> root ; Agents/<I>/X -> root ; Global/X -> root ; root/X -> root
    """
    parent = path.parent
    if parent.parent.name in (DIR_ROLES, DIR_AGENTS):
        return parent.parent.parent
    if parent.name == DIR_GLOBAL:
        return parent.parent
    return parent


def _rel(path: Path, target: Path) -> str:
    return os.path.relpath(target, start=path.parent).replace(os.sep, "/")


def link_fields(path: Path, owner: str) -> dict:
    """Relative links that stay correct at any depth in the team tree."""
    root = team_root_from(path)
    role = resolve_role(owner)
    docs = docs_dir(root) if root.parent.name == TEAMS_SUBDIR else root
    return {
        "tasks": _rel(path, role_dir(root, role) / F_TASKS),
        "short": _rel(path, role_dir(root, role) / F_SHORT),
        "long": _rel(path, role_dir(root, role) / F_LONG),
        "mem_archive": _rel(path, role_dir(root, role) / F_MEM_ARCHIVE),
        "role": _rel(path, role_dir(root, role) / F_ROLE),
        "global_mem": _rel(path, global_dir(root) / F_GLOBAL),
        "global_archive": _rel(path, global_dir(root) / F_GLOBAL_ARCHIVE),
        "disputes": _rel(path, root / F_DISPUTES),
        "map": _rel(path, root / F_MAP),
        "project": _rel(path, docs / "Project.md"),
        "plan": _rel(path, docs / "Plan.md"),
        "architecture": _rel(path, docs / "Architecture.md"),
        "decisions": _rel(path, docs / "Decisions.md"),
        "archive": _rel(path, docs / "Archive.md"),
        "board": _rel(path, docs / "Board.md"),
        "worklog": _rel(path, path.parent / F_WORKLOG),
        "inbox": _rel(path, path.parent / F_INBOX),
        "Role": pascal(role),
    }


def header_for(filename: str, owner: str, path: Path = None) -> str:
    """Render a file header; link fields are real relative paths when we know the
    file's location (which every writer does)."""
    tpl = HEADERS.get(filename, "# Memory - {owner}\n")
    if path is None:
        die("internal: header_for needs the file path so its links resolve")
    fields = link_fields(path, owner)
    fields.update(owner=owner, cap=LONG_CAP, stale=STALE_DAYS)
    return tpl.format(**fields)


def render(entries: list, filename: str, owner: str, path: Path = None) -> str:
    assign_ids(entries, "M-")
    out = [header_for(filename, owner, path), ""]
    for e in entries:
        label = one_line(e["key"]) or "note"
        out.append(f"## {e['id']} · {label}")
        meta = [
            ("key", e["key"]),
            ("importance", str(e["importance"])),
            ("uses", str(e["uses"])),
            ("created", e["created"]),
            ("last_used", e["last_used"]),
            ("tags", e["tags"]),
            ("pinned", "yes" if e["pinned"] else "no"),
            ("by", e.get("by", "")),
            ("src", e.get("src", "")),
            ("rev", e.get("rev", "")),
        ]
        for field, value in meta:
            out.append(f"- {field}: {one_line(value)}")
        out.append("")
        out.append(body_text(e["body"]).strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_memory(path: Path, entries: list, filename: str, owner: str) -> None:
    atomic_write(path, render(entries, filename, owner, path))


def score(entry: dict) -> int:
    d = days_since(entry["last_used"])
    recency = 3 if d <= 1 else 2 if d <= 3 else 1 if d <= 7 else 0
    return (
        entry["importance"] * 10
        + min(entry["uses"], 12) * 3
        + recency
        + (100 if entry["pinned"] else 0)
    )


def assign_ids(items: list, prefix: str) -> None:
    """Keep existing ids stable; allocate fresh, collision-free ids for the rest."""
    used = set()
    for it in items:
        i = it.get("id", "")
        if i and i not in used:
            used.add(i)
        else:
            it["id"] = ""
    counter = 0
    for it in items:
        if it["id"]:
            try:
                counter = max(counter, int(it["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass
    for it in items:
        if it["id"]:
            continue
        while True:
            counter += 1
            candidate = f"{prefix}{counter:04d}"
            if candidate not in used:
                break
        it["id"] = candidate
        used.add(candidate)


def merge_entries(target: list, incoming: list, prefix: str = "M-") -> tuple:
    """Merge incoming into target by key. Returns (target, merged, added)."""
    merged = 0
    added = 0
    index = {}
    for e in target:
        if e["key"]:
            index.setdefault(e["key"], e)
    for src in incoming:
        existing = index.get(src["key"]) if src["key"] else None
        if existing is None:
            copy = dict(src)
            copy["id"] = ""  # reassigned by render/assign_ids
            target.append(copy)
            added += 1
            if src["key"]:
                index[src["key"]] = target[-1]
            continue
        existing["importance"] = max(existing["importance"], src["importance"])
        existing["uses"] = existing["uses"] + src["uses"]
        existing["pinned"] = existing["pinned"] or src["pinned"]
        if parse_date(src["last_used"]) >= parse_date(existing["last_used"]):
            existing["last_used"] = src["last_used"]
            existing["body"] = src["body"] or existing["body"]
        existing["tags"] = ",".join(
            sorted({t for t in (existing["tags"] + "," + src["tags"]).split(",") if t.strip()})
        )
        merged += 1
    return target, merged, added


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def cmd_init(args) -> int:
    root = project_root(args)
    project = project_of(root)
    names = [n.strip() for n in (args.agents or "").split(",") if n.strip()]
    if not names:
        names = ["ceo"]
    root.mkdir(parents=True, exist_ok=True)
    (root / DIR_RUNTIME / DIR_LOCKS).mkdir(parents=True, exist_ok=True)
    (root / DIR_RUNTIME / DIR_SLOTS).mkdir(parents=True, exist_ok=True)
    pfile = providers_path(root)
    if not pfile.exists():
        import json

        write_lf(pfile, json.dumps(DEFAULT_PROVIDER_LIMITS, indent=2) + "\n")
    ensure_team_identity(root)
    global_dir(root).mkdir(parents=True, exist_ok=True)

    gi = global_dir(root) / ".gitignore"
    if not gi.exists():
        write_lf(gi, "*\n!.gitignore\n")

    gpath = global_dir(root) / F_GLOBAL
    if not gpath.exists():
        write_memory(gpath, [], F_GLOBAL, "all agents")

    # records are never destroyed: --force re-scaffolds only what is missing
    dpath = disputes_path(root)
    if not dpath.exists():
        write_disputes(dpath, [])
    cpath = criteria_path(root)
    if not cpath.exists():
        write_criteria(cpath, [])
    rpath = reviews_path(root)
    if not rpath.exists():
        write_reviews(rpath, [])
    tpath = tests_path(root)
    if not tpath.exists():
        write_tests(tpath, [])
    ppath = testplan_path(root)
    if not ppath.exists():
        write_testplan(ppath, {})
    skpath = skills_path(root)
    if not skpath.exists():
        write_skills(skpath, [])
    if not ledger_path(root).exists():
        ledger_append(
            root,
            "decision.add",
            "system",
            "bootstrap",
            f"team '{root.name}' initialised with {len(names)} agent(s)",
        )
        ledger_append(root, "ledger.export", "system", "init", "ledger seeded at bootstrap")

    # --- shared project documents (one owner, one canonical path) --------- #
    # Committed project output, under <project>/docs/Team/.
    public = docs_dir(root)
    public.mkdir(parents=True, exist_ok=True)
    src_docs = TEMPLATES_DIR / "Docs"
    for filename, owner in DOCS.items():
        p = public / filename
        if p.exists():
            continue
        src = src_docs / filename
        if src.exists():
            write_lf(p, src.read_text(encoding="utf-8"))
        else:
            write_lf(p, f"# {filename[:-3]}\n\nOwner: {owner}\n")
    readme = root / F_MAP
    if not readme.exists():
        src = TEMPLATES_DIR / DIR_TEAM_MAP_TPL
        text = src.read_text(encoding="utf-8") if src.exists() else "# Team workspace\n"
        write_lf(
            readme,
            text.replace("{project}", str(project))
            .replace("{skill}", str(SKILL_DIR))
            .replace("{docs}", str(public)),
        )

    created = []
    roles_seen = []
    for name in names:
        role = resolve_role(name)
        # role scope: memory + task queue, shared by every instance of the role
        rd = role_dir(root, role)
        rd.mkdir(parents=True, exist_ok=True)
        for filename in (F_SHORT, F_LONG, F_MEM_ARCHIVE):
            p = rd / filename
            if not p.exists():
                write_memory(p, [], filename, role)
        tp = rd / F_TASKS
        if not tp.exists():
            write_tasks(tp, [], role)
        if role not in roles_seen:
            roles_seen.append(role)

        # instance scope: private charter copy, worklog, inbox, scratch, outputs
        d = agent_dir(root, name)
        for sub in (DIR_ARTIFACTS, DIR_SCRATCH, DIR_REPORTS):
            (d / sub).mkdir(parents=True, exist_ok=True)
        role_file = ROLES_DIR / f"{role}.md"
        shared_charter = rd / F_ROLE
        if role_file.exists() and (args.force or not shared_charter.exists()):
            write_lf(
                shared_charter,
                role_file.read_text(encoding="utf-8").replace(
                    "{references}", str(SKILL_DIR / "references")
                ),
            )
        elif not shared_charter.exists():
            write_lf(
                shared_charter,
                f"# Role: {role}\n\n"
                f"No bundled charter found for '{role}'. Derive your duties from the\n"
                f"task packet, report blockers to the CEO, and keep to your lane.\n",
            )
        brief = d / F_START
        if args.force or not brief.exists():
            write_lf(brief, start_here(name, role, root, docs_dir(root)))
        for extra in (F_WORKLOG, F_INBOX):
            p = d / extra
            if not p.exists():
                write_lf(
                    p,
                    f"# {extra[:-3]} - {name} ({role})\n\n"
                    f"> Private to this instance. The {role} memory and task queue\n"
                    f"> are shared with every other {role} instance.\n\n"
                    + AGENT_LINKS.format(**link_fields(d / extra, name))
                    + "\n",
                )
        migrate_instance_memory(root, name, role)
        created.append(name)

    print(f"teamwork: workspace ready at {root}")
    print(f"teamwork: global memory {gpath}")
    print("teamwork: memory + task lists are per ROLE (shared by its instances)")
    for role in roles_seen:
        inst = instances_of(root, role)
        print(f"  - {role:16s} shared: {role_dir(root, role)}  instances: {', '.join(inst)}")
    if "ceo" not in created:
        print("teamwork: note - no 'ceo' agent directory; the CEO is the leader session.")
    roles_now = [resolve_role(n) for n in created]
    if len(instances_of(root, "reviewer")) == 1:
        print(
            "teamwork: note - one Reviewer instance: it will verify and merge the "
            "same PR (recorded as an exception). Add reviewer-2 to separate the "
            "two duties."
        )
    for required, why in (
        ("reviewer", "nothing can pass review or be merged"),
        ("architect", "no one freezes interfaces"),
    ):
        if required not in roles_now:
            print(
                f"teamwork: WARNING no '{required}' in the roster: {why}. "
                f"Add one: init --agents ...,{required}"
            )

    try:
        cmd_agents_md(argparse.Namespace(project=str(project)))
    except SystemExit:
        pass

    if not args.no_git:
        print()
        ensure_repo(project, commit=True)
        print(
            "teamwork: code/tests/docs live in the repo and are committed;\n"
            "           .pi/ working state stays local and uncommitted."
        )
    return 0


def migrate_instance_memory(root: Path, name: str, role: str) -> int:
    """Fold legacy per-instance memory/tasks into the shared role directory."""
    moved = 0
    inst = agent_dir(root, name)
    rd = role_dir(root, role)
    legacy_charter = inst / F_ROLE
    if legacy_charter.exists():
        if not (rd / F_ROLE).exists():
            shutil.move(str(legacy_charter), str(rd / F_ROLE))
        else:
            legacy_charter.unlink()
    for filename in (F_SHORT, F_LONG, F_MEM_ARCHIVE):
        src = inst / filename
        if not src.exists():
            continue
        entries = parse_memory(src)
        dst = rd / filename
        if entries:
            merged, _, _ = merge_entries(parse_memory(dst), entries)
            write_memory(dst, merged, filename, role)
            moved += len(entries)
        src.unlink()
    src_tasks = inst / F_TASKS
    if src_tasks.exists():
        tasks = parse_tasks(src_tasks)
        if tasks:
            dst = rd / F_TASKS
            merged, added = merge_tasks(parse_tasks(dst), tasks)
            write_tasks(dst, merged, role)
            moved += added
        src_tasks.unlink()
    return moved


def start_here(name: str, role: str, root: Path, docs: Path) -> str:
    global_mem = global_dir(root) / F_GLOBAL
    agents_md = project_of(root) / "AGENTS.md"
    script = _resources.self_invocation()
    disputes = disputes_path(root)
    charter = role_dir(root, role) / F_ROLE
    return f"""# START HERE - {name} ({role})

You are the **{role}** of an autonomous team. The user talks only to the CEO;
you talk to the CEO and, when needed, to peers.

## Startup routine (every time you are activated)

1. Read the project constitution: `{agents_md}` (team rules, red lines,
   evidence gate) and your shared role charter (one copy for every {role}
   instance): `{charter}`.
2. Load the ROLE's short-term memory into context (shared with every {role}
   instance): `{script} load {name}`
3. `{script} task next {name}` - atomically claims the highest-priority
   unblocked task from the shared {role} queue for you, and marks it as yours.
   Do not wait for peers; do not take a task another instance has claimed.
4. Before asking anyone, check shared memory:
   `{script} recall "<topic>" --global` (file: `{global_mem}`).
5. Skim `{docs}/Plan.md` and `{docs}/Board.md` for your lane; open disputes are
   recorded in `{disputes}`.

## While working

- **Take a concurrency slot before starting a model-heavy task**, and release it
  when the task ends. Never exceed the provider cap.
  `{script} slot acquire --agent {name} --provider ollama-cloud --task <T-id>`
  `{script} slot renew --agent {name}` (every ~60 min on a long task)
  `{script} slot release --agent {name}`
  At the cap, do work needing no slot or fan out on another provider - never block.
  Check availability with `{script} parallel`.
- **Reuse before you recompute**: read global/long-term memory, the shared docs
  and existing artifacts first. Cite a verified result on the same revision
  instead of re-running it. Hand the next task to an already-running lane rather
  than spawning a new one.
- One writer per file. Stay inside your component/interface boundary.
- **Evidence or UNVERIFIED.** Cite command + revision + observed result for
  every claim. Never invent test results, paths, flags, approvals or facts.
- Red lines (destructive commands, secrets, external/irreversible actions,
  test weakening, scope violations): STOP and escalate to the CEO. See
  `{agents_md}`.
- Your **memory and task queue are shared by every {role} instance** - write
  facts once, for the whole role: `{script} remember {name} "<fact>" --key <slug>`.
  Only `Artifacts/`, `Reports/`, `WorkLog.md` and `Scratch/` are private to you.
- Keep the shared queue current: `{script} task add/set/next {name}`; check what
  peers hold with `{script} task list {role}` before starting something new.
- **Decide independently on evidence**, never on deference or imagination. If a
  design or decision looks unreasonable, challenge its owner with counter-data
  instead of silently complying or working around it:
  `{script} dispute open --by {name} --against <owner> --topic "..." --evidence "..."`.
  At most {{max_rounds}} rounds, then the dispute goes to the CEO + CTO + CFO
  tribunal, whose ruling is final and binding.
- Never ask the user anything. Put it in `Inbox.md` or the team mailbox and keep
  working elsewhere.

## Finishing a task: commit, self-check, then review

Three steps, in order. You cannot skip any of them.

1. Work on your OWN branch and commit there. Never commit on `main` (the tool
   refuses it), and never leave the deliverable uncommitted - a reviewer cannot
   pass work that is not on a revision.
   `{script} branch start --agent {name} --task <T-id>`
   `{script} commit --role {role} --type <feat|fix|test|docs|design|research|refactor|chore> \\
       --task <T-id> --area <area> --goal "<what was asked>" \\
       --deliverable "<what you produced>" --why "<why this change>" \\
       --status "<actual state>" --result "<command @rev -> observed result>" --all`
   Then clean your `scratch/` (`{script} clean --all`).
2. **Your own review and test.** Re-read your diff, check edge cases, error
   paths, regressions and docs, and actually *run* something.
   You also own a test layer: make sure there is a `tests` record for the `{role}`
   layer and that it passes (`{script} tests list --layer <your layer>`), because
   `loop` will not let the team finish without it. If the layer is missing, add your
   own record and run it:
   `{script} tests add --layer <your layer> --area <area> --owner {name}`
   `{script} tests run <TS-id> --by {name} --result pass --evidence "<cmd @rev -> result>"`
   `{script} task set {name} <T-id> --status selfcheck`
   then
   `{script} selfcheck {name} <T-id> --by {name} \\
       --note "<what you re-read and why it is sound>" \\
       --test "<self-test command @rev -> observed result>"`
   If your own check finds a problem, use `--result fail` - the task returns to
   `doing`. A pass records the self-check and submits the task for review.
3. **Independent review by a Reviewer instance** (ask the CEO which one is
   assigned to you), who re-verifies from scratch:
   `{script} review {role} <T-id> --by <Reviewer instance> --result pass|fail ...`
   A fail comes back to you with findings; fix, self-check and re-submit. Failures
   are counted: at 3 the Reviewer must open a dispute and the tribunal rules, so do
   not loop silently - escalate when you and the Reviewer genuinely disagree.
   On a pass the result is archived to `{docs}/Archive.md`, and a *different*
   Reviewer merges it into `main`.
4. `{script} consolidate --agent {name}`
5. Report to the CEO: task id, status, artifact path, evidence, blockers, next.
6. Immediately run `task next {name}` and start the next executable task. Stop
   only when no executable task exists for your role.
""".replace("{max_rounds}", str(MAX_ROUNDS))


def cmd_load(args) -> int:
    root = project_root(args)
    role = resolve_role(args.agent)
    d = role_dir(root, role)
    if not d.is_dir() and not agents_dir(root).is_dir():
        die(f"unknown role '{role}' (run init or check `agents`)")
    consolidate_agent(root, role, dry_run=False, quiet=True)
    limit = args.limit or SHORT_CAP
    entries = parse_memory(d / F_SHORT)
    entries.sort(key=lambda e: parse_date(e["last_used"]), reverse=True)
    keep = entries[:limit]
    gcount = len(parse_memory(global_dir(root) / F_GLOBAL))
    inst = instances_of(root, role)
    print(
        f"# Short-term memory loaded for {args.agent} -> shared {role} memory"
        f" ({len(keep)}/{len(entries)} entries)"
    )
    print(f"# shared by: {', '.join(inst) or role}")
    print(
        f"# Long-term entries are NOT loaded; query them with:"
        f' teamwork.py recall "<query>" --agent {role}'
    )
    print(
        f"# Global shared memory has {gcount} entries; read with:"
        f' teamwork.py recall "<query>" --global'
    )
    print()
    for e in keep:
        print(
            f"- [{e['key'] or 'note'}] importance={e['importance']} uses={e['uses']}"
            f" last_used={e['last_used']}: {e['body']}"
        )
    if not keep:
        print("- (empty: this is your first task or memory was just consolidated)")
    return 0


def _memory_path(root: Path, agent: str, layer: str) -> tuple:
    role = resolve_role(agent)
    d = role_dir(root, role)
    if not d.is_dir() and not agents_dir(root).is_dir():
        die("no workspace here: run `teamwork.py init` first")
    d.mkdir(parents=True, exist_ok=True)
    filename = F_SHORT if layer == "short" else F_LONG
    return d / filename, filename


def cmd_remember(args) -> int:
    root = project_root(args)
    path, filename = _memory_path(root, args.agent, args.layer)
    if not args.text.strip():
        die("empty memory text")
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{resolve_role(args.agent)}.lock"):
        entries = parse_memory(path)
        entry = new_entry(
            args.text,
            args.key,
            args.importance,
            args.tags,
            args.pin,
            by=args.by or "",
            src=args.src or "",
            rev=args.rev or "",
        )
        entries, merged, added = merge_entries(entries, [entry])
        write_memory(path, entries, filename, args.agent)
    ledger_append(
        root,
        "memory.add" if added else "memory.update",
        args.by or args.agent,
        args.key or args.agent,
        f"{'added' if added else 'updated'} {args.layer} entry: {args.text[:80]}",
        args.rev,
    )
    consolidate_agent(root, args.agent, dry_run=False, quiet=True)
    print(f"teamwork: remembered {added} new / {merged} merged entry in {path}")
    return 0


def cmd_global(args) -> int:
    root = project_root(args)
    path = global_dir(root) / F_GLOBAL
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "global.lock"):
        entries = parse_memory(path)
        entry = new_entry(args.text, args.key, args.importance, args.tags, args.pin)
        entries, merged, added = merge_entries(entries, [entry])
        entries.sort(key=score, reverse=True)
        pinned = [e for e in entries if e["pinned"]]
        rest = [e for e in entries if not e["pinned"]]
        cap = max(LONG_CAP - len(pinned), 0)
        if len(rest) > cap:
            archive_path = global_dir(root) / F_GLOBAL_ARCHIVE
            archived = parse_memory(archive_path)
            archived, _, _ = merge_entries(archived, rest[cap:])
            archived.sort(key=score, reverse=True)
            write_memory(archive_path, archived[:ARCHIVE_CAP], F_GLOBAL_ARCHIVE, "all agents")
            rest = rest[:cap]
        write_memory(path, pinned + rest, F_GLOBAL, "all agents")
    ledger_append(
        root,
        "memory.global",
        "ceo",
        args.key or "global",
        f"{added} new / {merged} merged: {args.text[:80]}",
    )
    print(f"teamwork: global memory {added} new / {merged} merged ({path})")
    return 0


def cmd_recall(args) -> int:
    root = project_root(args)
    if args.query:
        try:
            pattern = re.compile(args.query, re.IGNORECASE)
        except re.error as exc:
            die(
                f"invalid query pattern {args.query!r}: {exc}. "
                "Pass a plain text query or a valid regex."
            )
    else:
        pattern = None
    targets = []  # (owner_label, path, filename)
    if args.global_ or args.all:
        for f in sorted(global_dir(root).glob("*.md")):
            targets.append(("global", f, f.name))
    if args.all:
        for name in list_roles(root):
            for f in (role_dir(root, name) / F_LONG, role_dir(root, name) / F_SHORT):
                targets.append((name, f, f.name))
    elif args.agent:
        role = resolve_role(args.agent)
        for layer in (
            ["short"]
            if args.layer == "short"
            else ["long"]
            if args.layer == "long"
            else ["short", "long"]
        ):
            f = role_dir(root, role) / (F_SHORT if layer == "short" else F_LONG)
            targets.append((role, f, f.name))
    if not targets:
        die("nothing to search: pass --agent A, --global, or --all")

    total = 0
    for owner, path, filename in targets:
        entries = parse_memory(path)
        hits = [
            e
            for e in entries
            if pattern is None
            or pattern.search(e["body"])
            or pattern.search(e["key"])
            or pattern.search(e["tags"])
        ]
        if not hits:
            continue
        print(f"## {owner} / {filename}")
        for e in hits:
            print(
                f"- [{e['key'] or 'note'}] importance={e['importance']} "
                f"uses={e['uses']} last_used={e['last_used']}: {e['body']}"
            )
            total += 1
        print()
    if total == 0:
        print(f"teamwork: no memory matched {args.query!r}")
    return 0


def _find_entry(entries: list, handle: str):
    if re.fullmatch(r"M-\d+", handle.upper()):
        wanted = handle.upper()
        for i, e in enumerate(entries):
            if e["id"].upper() == wanted:
                return i
        return None
    for i, e in enumerate(entries):
        if e["key"] == handle:
            return i
    for i, e in enumerate(entries):
        if handle.lower() in (e["key"] + " " + e["body"]).lower():
            return i
    return None


def cmd_touch(args) -> int:
    root = project_root(args)
    path, filename = _memory_path(root, args.agent, args.layer)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{resolve_role(args.agent)}.lock"):
        entries = parse_memory(path)
        idx = _find_entry(entries, args.handle)
        if idx is None:
            die(f"no entry '{args.handle}' in {path}")
        entries[idx]["uses"] += 1
        entries[idx]["last_used"] = today_iso()
        write_memory(path, entries, filename, args.agent)
    ledger_append(
        root,
        "memory.touch",
        args.agent,
        entries[idx]["key"] or args.handle,
        f"uses={entries[idx]['uses']}",
    )
    print(f"teamwork: touched {entries[idx]['key'] or args.handle} (uses={entries[idx]['uses']})")
    return 0


def cmd_forget(args) -> int:
    root = project_root(args)
    path, filename = _memory_path(root, args.agent, args.layer)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{resolve_role(args.agent)}.lock"):
        entries = parse_memory(path)
        idx = _find_entry(entries, args.handle)
        if idx is None:
            die(f"no entry '{args.handle}' in {path}")
        removed = entries.pop(idx)
        write_memory(path, entries, filename, args.agent)
    ledger_append(
        root,
        "memory.forget",
        args.agent,
        removed["key"] or args.handle,
        f"removed: {(removed.get('body') or '')[:80]}",
    )
    print(f"teamwork: forgot {removed['key'] or args.handle}")
    return 0


def consolidate_agent(root: Path, agent: str, dry_run: bool = False, quiet: bool = False) -> dict:
    role = resolve_role(agent)
    agent = role
    d = role_dir(root, role)
    short_path = d / F_SHORT
    long_path = d / F_LONG
    arch_path = d / F_MEM_ARCHIVE

    lock_path = root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"
    ctx = contextlib.nullcontext() if dry_run else lock(lock_path)
    with ctx:
        return _consolidate_locked(
            root, role, agent, d, short_path, long_path, arch_path, dry_run, quiet
        )


def _consolidate_locked(
    root: Path,
    role: str,
    agent: str,
    d: Path,
    short_path: Path,
    long_path: Path,
    arch_path: Path,
    dry_run: bool,
    quiet: bool,
) -> dict:
    short = parse_memory(short_path)
    long_entries = parse_memory(long_path)
    archive = parse_memory(arch_path)

    promoted, dropped, keep_short = [], [], []
    for e in short:
        stale = days_since(e["last_used"]) >= STALE_DAYS and e["uses"] < MIN_USES
        if e["pinned"] or not stale:
            keep_short.append(e)
        elif e["importance"] >= PROMOTE_MIN_IMPORTANCE:
            promoted.append(e)
        else:
            dropped.append(e)

    if len(keep_short) > SHORT_CAP:
        keep_short.sort(key=score, reverse=True)
        overflow = keep_short[SHORT_CAP:]
        keep_short = keep_short[:SHORT_CAP]
        for e in overflow:
            (promoted if e["importance"] >= PROMOTE_MIN_IMPORTANCE else dropped).append(e)

    long_entries, merged, added = merge_entries(long_entries, promoted)

    evicted = []
    pinned = [e for e in long_entries if e["pinned"]]
    rest = sorted((e for e in long_entries if not e["pinned"]), key=score, reverse=True)
    cap = max(LONG_CAP - len(pinned), 0)
    if len(rest) > cap:
        evicted = rest[cap:]
        rest = rest[:cap]
        archive, _, _ = merge_entries(archive, evicted)
        archive.sort(key=score, reverse=True)
        if len(archive) > ARCHIVE_CAP:
            archive_dropped = len(archive) - ARCHIVE_CAP
            archive = archive[:ARCHIVE_CAP]
            (root / DIR_RUNTIME).mkdir(parents=True, exist_ok=True)
            with (root / DIR_RUNTIME / "MemoryLog.md").open(
                "a", encoding="utf-8", newline="\n"
            ) as fh:
                fh.write(
                    f"- {today_iso()} {agent}: evicted {archive_dropped} archive "
                    f"entr(y/ies) beyond ARCHIVE_CAP={ARCHIVE_CAP}\n"
                )
    long_entries = pinned + rest

    if not dry_run:
        for e in promoted:
            ledger_append(
                root,
                "memory.promote",
                agent,
                e.get("key") or e.get("id"),
                f"short -> long ({e.get('importance')}): {(e.get('body') or '')[:70]}",
            )
        for e in dropped:
            ledger_append(
                root,
                "memory.drop",
                agent,
                e.get("key") or e.get("id"),
                f"dropped from short-term (stale, low value): {(e.get('body') or '')[:70]}",
            )
        if merged:
            ledger_append(
                root, "memory.merge", agent, agent, f"{merged} entry/entries merged by key"
            )
        for e in evicted:
            ledger_append(
                root,
                "memory.evict",
                agent,
                e.get("key") or e.get("id"),
                f"long -> archive (cap {LONG_CAP}): {(e.get('body') or '')[:70]}",
            )
        write_memory(short_path, keep_short, F_SHORT, agent)
        write_memory(long_path, long_entries, F_LONG, agent)
        if evicted:
            write_memory(arch_path, archive, F_MEM_ARCHIVE, agent)

    report = {
        "agent": agent,
        "short": len(keep_short),
        "long": len(long_entries),
        "promoted": len(promoted),
        "dropped": len(dropped),
        "evicted": len(evicted),
        "merged": merged,
        "added": added,
    }
    if not quiet:
        print(
            f"teamwork: {agent}: short={report['short']} long={report['long']} "
            f"promoted={report['promoted']} dropped={report['dropped']} "
            f"evicted={report['evicted']} merged={report['merged']}"
        )
    return report


def cmd_consolidate(args) -> int:
    root = project_root(args)
    names = list_roles(root) if (args.all or not args.agent) else [resolve_role(args.agent)]
    if not names:
        die("no agents in this workspace")
    for name in names:
        consolidate_agent(root, name, dry_run=args.dry_run)
    return 0


def cmd_stats(args) -> int:
    root = project_root(args)
    names = list_roles(root) if (args.all or not args.agent) else [resolve_role(args.agent)]
    if not names:
        die("no agents in this workspace")
    print(f"# teamwork memory stats ({root})")
    print("# memory and task lists are per ROLE, shared by all its instances")
    print(
        f"# caps: short={SHORT_CAP} long={LONG_CAP} archive={ARCHIVE_CAP} "
        f"stale_days={STALE_DAYS} min_uses={MIN_USES} v{VERSION}"
    )
    total = 0
    for name in names:
        d = role_dir(root, name)
        s = len(parse_memory(d / F_SHORT))
        long_n = len(parse_memory(d / F_LONG))
        a = len(parse_memory(d / F_MEM_ARCHIVE))
        total += s + long_n + a
        flag = ""
        if s > SHORT_CAP:
            flag += " SHORT-OVER"
        if long_n > LONG_CAP:
            flag += " LONG-OVER"
        print(
            f"- {name:24s} role={resolve_role(name):16s} short={s:3d} "
            f"long={long_n:3d} archive={a:3d}{flag}"
        )
    g = len(parse_memory(global_dir(root) / F_GLOBAL))
    print(f"- {'global':24s} role={'shared':16s} entries={g}")
    print(f"# total private entries: {total}")
    return 0


def cmd_agents(args) -> int:
    root = project_root(args)
    roles = list_roles(root)
    if not roles and not list_agents(root):
        print("teamwork: no workspace here (run `teamwork.py init`)")
        return 0
    for role in roles:
        inst = instances_of(root, role)
        print(
            f"{role:20s} instances={len(inst):2d} "
            f"[{', '.join(inst) if inst else '-'}]  "
            f"mem={len(parse_memory(role_dir(root, role) / F_SHORT))}"
            f"/{len(parse_memory(role_dir(root, role) / F_LONG))} "
            f"tasks={len(parse_tasks(task_file(root, role)))}"
        )
    return 0


# --------------------------------------------------------------------------- #
# Git repository bootstrap + cleanup
# --------------------------------------------------------------------------- #


def run_git(project: Path, *argv: str):
    return subprocess.run(["git", "-C", str(project), *argv], capture_output=True, text=True)


def is_git_repo(project: Path) -> bool:
    r = run_git(project, "rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def ensure_gitignore(project: Path) -> list:
    """Add the teamwork entries that are missing. Never removes lines."""
    path = project / ".gitignore"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    have = {line.strip() for line in existing}
    added = [line for line in GITIGNORE_LINES if line.strip() not in have]
    if added:
        text = "\n".join(existing).rstrip() + "\n"
        if text.strip():
            text += "\n"
        text += "\n".join(added) + "\n"
        write_lf(path, text)
    return added


def ensure_repo(project: Path, commit: bool = True, quiet: bool = False) -> int:
    created = False
    if not is_git_repo(project):
        project.mkdir(parents=True, exist_ok=True)
        r = run_git(project, "init", "-b", "main")
        if r.returncode != 0:  # older git without -b
            r = run_git(project, "init")
        if r.returncode != 0:
            die(f"git init failed: {r.stderr.strip()}")
        created = True
        if not quiet:
            print(f"teamwork: created git repository at {project}")
    else:
        if not quiet:
            print(f"teamwork: git repository already present at {project}")

    added = ensure_gitignore(project)
    if added and not quiet:
        print(f"teamwork: added {len(added)} rule(s) to .gitignore")

    ensure_lfs(project, quiet=quiet)
    # A plain `git commit` must never inherit the operator's personal identity.
    # Set the repo-local fallback to the CEO role mailbox unless the repository
    # already has its own identity.
    toplevel = run_git(project, "rev-parse", "--show-toplevel").stdout.strip()
    at_toplevel = bool(toplevel) and Path(toplevel).resolve() == project.resolve()
    if at_toplevel:
        local_email = run_git(project, "config", "--local", "user.email").stdout.strip()
        local_name = run_git(project, "config", "--local", "user.name").stdout.strip()
        if not local_email:
            name, email = role_identity("ceo")
            run_git(project, "config", "--local", "user.email", email)
            if not local_name:
                run_git(project, "config", "--local", "user.name", name)
    elif not quiet:
        print(
            f"teamwork: NOTE {project} is inside the git worktree {toplevel}; "
            "the team uses that repository and will not rewrite its local identity."
        )
    has_identity = True  # team commits always carry the ROLE identity

    if commit and not created and is_git_repo(project):
        head = run_git(project, "rev-parse", "--verify", "--quiet", "HEAD")
        if head.returncode != 0:
            created = True  # empty repository: make the bootstrap commit too
            if not quiet:
                print("teamwork: empty repository detected: making the initial commit")
    if commit and created and has_identity:
        run_git(project, "add", "-A")
        msg = build_commit_message(
            "ceo",
            {
                "type": "chore",
                "area": "repo",
                "task": "-",
                "producers": "CEO",
                "goal": "give the team a repository to archive staged project updates",
                "deliverable": "git repository, .gitignore, .gitattributes (Git LFS rules)",
                "why": "staged project output must be versioned and large binaries stored via LFS",
                "status": "initialised",
                "result": "git init + initial commit @HEAD",
            },
        )
        r = subprocess.run(
            ["git", "-C", str(project)] + git_identity_args("ceo") + ["commit", "-q", "-F", "-"],
            input=msg,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and not quiet:
            sha = run_git(project, "rev-parse", "--short", "HEAD").stdout.strip()
            print(f"teamwork: initial commit {sha}")
        elif r.returncode != 0 and not quiet:
            print(f"teamwork: initial commit skipped: {r.stderr.strip().splitlines()[:1]}")
    return 0


def cmd_repo(args) -> int:
    root = project_root(args)
    project = project_of(root)
    ensure_repo(project, commit=not args.no_commit)
    r = run_git(project, "status", "--short", "--branch")
    print("teamwork: git status")
    for line in r.stdout.splitlines():
        print(f"  {line}")
    print("teamwork: team commits use the ROLE identity, e.g. " + identity_string("developer"))
    print("teamwork: commit with `teamwork.py commit --role <role> --task <T-id> ...`")
    return 0


def cmd_clean(args) -> int:
    """Remove scratch/temp files inside the team tree. Never touches tracked files."""
    root = project_root(args)
    project = project_of(root)
    if not root.exists():
        die(f"no workspace at {root}")
    tracked = set()
    if is_git_repo(project):
        r = run_git(project, "ls-files", "-z")
        tracked = {p for p in r.stdout.split("\0") if p}
    removed = []
    freed = 0
    for agent in list_agents(root):
        for sub in SCRATCH_DIRS:
            d = agent_dir(root, agent) / sub
            if not d.is_dir():
                continue
            for p in d.rglob("*"):
                if not p.is_file():
                    continue
                rel = p.relative_to(project).as_posix()
                if rel in tracked:
                    continue
                if not args.all and not any(p.match(pat) for pat in SCRATCH_PATTERNS):
                    continue
                try:
                    freed += p.stat().st_size
                    removed.append(rel)
                    if not args.dry_run:
                        p.unlink()
                except OSError:
                    pass
    # workspace-wide stray temp files (never memory, tasks or docs)
    for p in list(root.rglob("*.tmp")) + list(root.rglob("*.temp")):
        rel = p.relative_to(project).as_posix()
        if rel in tracked:
            continue
        try:
            freed += p.stat().st_size
            removed.append(rel)
            if not args.dry_run:
                p.unlink()
        except OSError:
            pass
    verb = "would remove" if args.dry_run else "removed"
    print(f"teamwork: {verb} {len(removed)} scratch/temp file(s), {freed / 1024:.1f} KiB")
    for rel in removed[: args.limit]:
        print(f"  - {rel}")
    if len(removed) > args.limit:
        print(f"  ... and {len(removed) - args.limit} more")
    if not args.all:
        print("teamwork: only temp patterns were removed; pass --all to empty scratch/ entirely.")
    return 0


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #


def cmd_task_add(args) -> int:
    root = project_root(args)
    role = resolve_role(args.agent)
    path = task_file(root, role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        t = new_task(
            args.title,
            args.priority,
            args.shared,
            args.deps,
            args.tags,
            args.status,
            args.body or "",
            args.evidence,
            "na" if args.no_review else "required",
        )
        if args.claimed_by:
            t["claimed_by"] = check_claimant(root, args.claimed_by, "claim", role)
        wanted = t["title"].strip().lower()
        for existing in tasks:
            if existing["title"].strip().lower() == wanted:
                print(
                    f"teamwork: {role} queue already has {existing['id']}: "
                    f"{existing['title']} - not duplicated"
                )
                return 0
        tasks.append(t)
        write_tasks(path, tasks, role)
    ledger_append(
        root, "task.add", args.agent, t["id"], f"[{t['priority']}] {t['title']}", "", role
    )
    print(
        f"teamwork: {role} queue + {t['id']} [{t['priority']}] {t['title']}"
        + (f" [for {t['claimed_by']}]" if t["claimed_by"] else "")
    )
    return 0


def _print_task(t: dict, prefix: str = "-") -> None:
    dep = f" deps={t['deps']}" if t["deps"] else ""
    shared = f" shared={t['shared']}" if t["shared"] else ""
    area = f" area={t['area']}" if t.get("area") else ""
    print(f"{prefix} {t['id']} [{t['priority']}/{t['status']}] {t['title']}{dep}{shared}{area}")
    if t.get("evidence"):
        print(f"    evidence: {t['evidence']}")
    if t["body"]:
        for line in t["body"].splitlines():
            print(f"    {line}")


def cmd_task_list(args) -> int:
    root = project_root(args)
    if not args.all and not args.agent:
        die("pass an agent name or --all")
    targets = list_roles(root) if args.all else [resolve_role(args.agent)]
    for name in targets:
        tasks = parse_tasks(task_file(root, name))
        if args.status:
            tasks = [t for t in tasks if t["status"] == args.status]
        if not tasks:
            continue
        lookup = local_dep_map(parse_tasks(task_file(root, name)))
        cache = {}
        tasks = sorted(
            tasks, key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["created"], t["id"])
        )
        inst = instances_of(root, name)
        print(f"## {name} (shared queue; instances: {', '.join(inst) or '-'})")
        for t in tasks:
            ready = "READY" if executable(t, lookup, cache, root) else t["status"]
            _print_task(t, "-")
            print(f"    -> {ready}")
        print()
    return 0


def cmd_task_next(args) -> int:
    """Highest-priority executable task in the ROLE queue; claims it by default."""
    root = project_root(args)
    role = resolve_role(args.agent)
    path = task_file(root, role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        lookup = local_dep_map(tasks)
        cache = {}
        ready = [t for t in tasks if executable(t, lookup, cache, root)]
        if not ready:
            blocked = [t for t in tasks if t["status"] in ("todo", "doing", "selfcheck")]
            print(
                f"teamwork: {args.agent} ({role}) has no unclaimed executable task"
                f" ({len(blocked)} open: blocked, claimed or in progress)"
            )
            for t in sorted(blocked, key=lambda t: PRIORITY_ORDER.get(t["priority"], 9)):
                _print_task(t)
            return 3
        ready.sort(key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["created"], t["id"]))
        best = ready[0]
        if not args.peek:
            best["status"] = "doing"
            best["claimed_by"] = check_claimant(root, args.agent, "claim", role)
            best["updated"] = today_iso()
            write_tasks(path, tasks, role)
    if not args.peek:
        ledger_append(
            root,
            "task.claim",
            args.agent,
            best["id"],
            f"claimed {role} task: {best['title']}",
            "",
            role,
        )
    suffix = "" if args.peek else f"  (claimed by {args.agent})"
    print(
        f"NEXT for {args.agent} ({role} shared queue): {best['id']} "
        f"[{best['priority']}] {best['title']}{suffix}"
    )
    if best.get("evidence"):
        print(f"    previous evidence: {best['evidence']}")
    for line in best["body"].splitlines():
        print(f"    {line}")
    return 0


def cmd_task_set(args) -> int:
    root = project_root(args)
    role = resolve_role(args.agent)
    path = task_file(root, role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        idx = find_task(tasks, args.handle)
        if idx is None:
            die(f"no task '{args.handle}' for {args.agent}")
        t = tasks[idx]
        if args.force:
            t["forced"] = (t.get("forced", "") + f" | {args.force}").strip(" |")
        if args.status:
            if args.status not in STATUSES:
                die(f"status must be one of {', '.join(STATUSES)}")
            if args.status == "doing" and not t.get("claimed_by"):
                if pascal(args.agent) != pascal(role):
                    t["claimed_by"] = check_claimant(root, args.agent, "claim", role)
            if args.status in ("done", "dropped") and not t.get("claimed_by"):
                if pascal(args.agent) != pascal(role):
                    t["claimed_by"] = check_claimant(root, args.agent, "claim", role)
            t["status"] = args.status
        if getattr(args, "claimed_by", None) is not None:
            if str(args.claimed_by).strip():
                t["claimed_by"] = check_claimant(root, args.claimed_by, "claim", role)
            else:
                t["claimed_by"] = ""
        if args.priority:
            t["priority"] = args.priority.upper()
        if args.deps is not None:
            t["deps"] = args.deps
        if args.title:
            t["title"] = args.title
        if args.evidence is not None:
            t["evidence"] = args.evidence.strip()
        if args.force and not str(args.force).strip():
            die(
                "--force needs a reason: --force '<why this gate must be bypassed>'. "
                "It is recorded on the task and reported by `audit`.",
                2,
            )
        # Anti-hallucination gate: `done` requires recorded evidence.
        if args.status == "done" and not t.get("evidence") and not args.force:
            die(
                "refusing to mark done without evidence.\n"
                "  Evidence must be a command + revision + observed result, or an\n"
                "  artifact path, e.g.\n"
                f"  task set {args.agent} {t['id']} --status done \\\n"
                "      --evidence 'go test ./...@$(git rev-parse --short HEAD) -> ok 42 tests'\n"
                "  Use --force only for a genuine non-code task, and say why in --body.",
                2,
            )
        # Self-check gate: review and test your own work before submitting it.
        if (
            args.status == "review"
            and t.get("review", "required") != "na"
            and t.get("self_check") != "passed"
            and not args.force
        ):
            die(
                f"refusing to submit {t['id']} for review: run your own self-review and\n"
                "  self-test first.\n"
                f"  1) {args.agent}: task set {args.agent} {t['id']} --status selfcheck\n"
                f"  2) {args.agent}: selfcheck {args.agent} {t['id']} --by {args.agent} \\\n"
                "       --note '<what you re-read: edge cases, regressions, docs>' \\\n"
                "       --test '<self-test command @rev -> observed result>'\n"
                "  Step 2 records the self-check and submits the task for review.",
                2,
            )
        # Independent-review gate: a deliverable is closed by the Reviewer, not
        # by its author.
        if (
            args.status == "done"
            and t.get("review", "required") != "na"
            and t.get("review_status") != "passed"
            and not args.force
        ):
            die(
                f"refusing to close {t['id']}: it needs an independent review.\n"
                f"  1) {args.agent}: task set {args.agent} {t['id']} --status review\n"
                f"  2) reviewer: review {args.agent} {t['id']} --by <Reviewer instance> \\\n"
                "       --result fail --findings '<what is wrong, with evidence>'\n"
                f"  3) reviewer: review {args.agent} {t['id']} --by <Reviewer instance> \\\n"
                "       --result pass --evidence '<verification command @rev -> result>'\n"
                "  Use --force only for a chore that is explicitly review=na.",
                2,
            )
        t["updated"] = today_iso()
        write_tasks(path, tasks, args.agent)
    ledger_append(
        root,
        "task.status",
        args.agent,
        t["id"],
        f"{t['status']} [{t['priority']}] {t['title']}"
        + (f" area={t['area']}" if t.get("area") else "")
        + (f" FORCED: {t['forced']}" if t.get("forced") else ""),
        "",
        role,
    )
    print(
        f"teamwork: {role} {t['id']} -> {t['status']} [{t['priority']}] {t['title']}"
        + (f" [{t['claimed_by']}]" if t.get("claimed_by") else "")
    )
    if t.get("evidence"):
        print(f"          evidence: {t['evidence']}")
    return 0


def cmd_task_reclaim(args) -> int:
    """Return a stuck task to the pool so another instance can take it."""
    root = project_root(args)
    role = resolve_role(args.agent)
    path = task_file(root, role)
    actor, arole = validate_actor(root, args.by, "claimant")
    if arole != role:
        die(f"{actor} is {arole}, not {role}; only the task's own role can reclaim it")
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        idx = find_task(tasks, args.handle)
        if idx is None:
            die(f"no task '{args.handle}' for {role}")
        t = tasks[idx]
        previous = t.get("claimed_by") or "-"
        t["status"] = "todo"
        t["claimed_by"] = ""
        t["branch"] = t.get("branch") or ""
        t["updated"] = today_iso()
        prev_note = t.get("findings", "")
        t["findings"] = (
            prev_note + f" | reclaimed from {previous} by {actor}: {args.reason}"
        ).strip(" |")
        write_tasks(path, tasks, role)
    ledger_append(
        root, "task.reclaim", actor, t["id"], f"reclaimed from {previous}: {args.reason}", "", role
    )
    print(f"# {role} {t['id']} reclaimed from {previous} by {actor}")
    print(f"#   reason: {args.reason}")
    print(
        f"#   next: teamwork.py task next {actor}  (or branch start --agent {actor} "
        f"--task {t['id']})"
    )
    if t.get("branch"):
        print(f"#   note: branch {t['branch']} still exists; the new owner continues on it")
    return 0


def cmd_task_rm(args) -> int:
    root = project_root(args)
    role = resolve_role(args.agent)
    actor, arole = validate_actor(root, args.by, "actor")
    if arole != role and not args.force:
        die(f"only the {role} role may remove its own task (you are {actor})")
    if args.force:
        args.force = require_reason(args.force, "removing another role's task")
    path = task_file(root, role)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        idx = find_task(tasks, args.handle)
        if idx is None:
            die(f"no task '{args.handle}' for {args.agent}")
        removed = tasks.pop(idx)
        write_tasks(path, tasks, role)
    ledger_append(
        root,
        "task.rm",
        actor,
        removed["id"],
        f"removed {removed['title']}" + (f" FORCED: {args.force}" if args.force else ""),
        "",
        role,
    )
    print(f"teamwork: {role} removed {removed['id']} {removed['title']}")
    return 0


# --------------------------------------------------------------------------- #
# Concurrency: provider limits and a file-based slot semaphore
# --------------------------------------------------------------------------- #


def providers_path(root: Path) -> Path:
    return root / F_SETTINGS


SETTINGS_NON_PROVIDER = ("PulseMinutes", "Criteria")


def load_providers(root: Path) -> dict:
    limits = dict(DEFAULT_PROVIDER_LIMITS)
    path = providers_path(root)
    if path.exists():
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if str(k) in SETTINGS_NON_PROVIDER:
                        continue
                    try:
                        limits[str(k)] = int(v)
                    except (TypeError, ValueError):
                        pass
        except (ValueError, OSError):
            pass
    env = os.environ.get("TEAMWORK_PROVIDER_LIMITS", "")
    for pair in env.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            try:
                limits[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return limits


def slots_dir(root: Path, provider: str) -> Path:
    return root / DIR_RUNTIME / DIR_SLOTS / safe_component(provider)


def slot_file(root: Path, provider: str, agent: str) -> Path:
    return slots_dir(root, provider) / f"{safe_component(agent)}.slot"


def slot_renewed(root: Path, provider: str, agent: str) -> float:
    f = slot_file(root, provider, agent)
    if not f.exists():
        return 0.0
    try:
        parts = f.read_text(encoding="utf-8").strip().split("|")
        return float(parts[2]) if len(parts) > 2 else 0.0
    except (OSError, ValueError):
        return 0.0


def reap_slots(root: Path, provider: str = "") -> list:
    """Expire leases: the holder stopped renewing (died, crashed or finished
    without releasing). A slot is a lease with a TTL, not a process lock, so the
    budget stays honest across many short-lived CLI calls."""
    reaped = []
    base = root / DIR_RUNTIME / DIR_SLOTS
    if not base.is_dir():
        return reaped
    providers = [provider] if provider else sorted(p.name for p in base.iterdir() if p.is_dir())
    for prov in providers:
        for f in slots_dir(root, prov).glob("*.slot"):
            try:
                parts = f.read_text(encoding="utf-8").strip().split("|")
                renewed = float(parts[2]) if len(parts) > 2 else 0.0
            except (OSError, ValueError):
                renewed = 0.0
            age_min = (time.time() - renewed) / 60 if renewed else 1e9
            if age_min > SLOT_TTL_MINUTES:
                try:
                    f.unlink()
                    reaped.append(f"{prov}/{f.stem}")
                except OSError:
                    pass
    return reaped


def used_slots(root: Path, provider: str) -> list:
    d = slots_dir(root, provider)
    return sorted(f.stem for f in d.glob("*.slot")) if d.is_dir() else []


def _slot_rows(root: Path, provider: str, limit: int = 6) -> str:
    agents = used_slots(root, provider)
    rows = []
    for agent in agents[:limit]:
        age = (time.time() - slot_renewed(root, provider, agent)) / 60
        rows.append(f"{agent}({age:.0f}m)")
    if len(agents) > limit:
        rows.append(f"+{len(agents) - limit} more")
    return ", ".join(rows)


def find_slot_provider(root: Path, agent: str) -> str:
    """Which provider currently leases a slot to this agent (if any)."""
    base = root / DIR_RUNTIME / DIR_SLOTS
    if not base.is_dir():
        return ""
    wanted = safe_component(agent)
    for prov in sorted(p.name for p in base.iterdir() if p.is_dir()):
        if wanted in used_slots(root, prov):
            return prov
    return ""


def _slot_release(args, root: Path, provider: str, cap: int) -> int:
    f = slot_file(root, provider, args.agent)
    if not f.exists() and not args.force:
        print(f"# {args.agent} holds no {provider} slot")
        return 0
    try:
        f.unlink()
    except OSError as exc:
        die(f"could not release {f}: {exc}")
    print(
        f"# released {provider} slot for {args.agent}"
        f" ({len(used_slots(root, provider))}/{cap} used)"
    )
    return 0


def _slot_renew(args, root: Path, provider: str) -> int:
    f = slot_file(root, provider, args.agent)
    if not f.exists():
        die(f"{args.agent} holds no {provider} slot (acquire first)")
    parts = f.read_text(encoding="utf-8").strip().split("|")
    while len(parts) < 4:
        parts.append("-")
    parts[2] = f"{time.time():.3f}"
    write_lf(f, "|".join(parts) + "\n")
    print(f"# renewed {provider} slot for {args.agent} (TTL {SLOT_TTL_MINUTES}m)")
    return 0


def cmd_slot(args) -> int:
    root = project_root(args)
    limits = load_providers(root)
    agent = getattr(args, "agent", "") or ""
    provider = args.provider or (find_slot_provider(root, agent) if agent else "")
    provider = provider or os.environ.get("TEAMWORK_PROVIDER") or "ollama-cloud"
    cap = limits.get(provider, limits.get("default", 8))

    if args.slot_cmd == "list":
        reaped = reap_slots(root)
        base = root / DIR_RUNTIME / DIR_SLOTS
        provs = (
            sorted({*limits, *(p.name for p in base.iterdir() if p.is_dir())})
            if base.is_dir()
            else sorted(limits)
        )
        for prov in provs:
            if prov == "default" or (args.provider and prov != args.provider):
                continue
            used = used_slots(root, prov)
            limit = limits.get(prov, limits.get("default", 8))
            print(
                f"- {prov:16s} {len(used):>4d}/{limit:<5d} free={max(limit - len(used), 0)}"
                + (f"  [{_slot_rows(root, prov)}]" if used else "")
            )
        print(f"# lease TTL {SLOT_TTL_MINUTES}m; renew while working, release when done")
        if reaped:
            print(f"# reaped {len(reaped)} expired lease(s)")
        return 0

    if args.slot_cmd == "reap":
        reaped = reap_slots(root, args.provider or "")
        print(
            f"# reaped {len(reaped)} expired lease(s)"
            + (f": {', '.join(reaped)}" if reaped else "")
        )
        return 0

    if args.slot_cmd == "release":
        if args.by:
            actor, arole = validate_actor(root, args.by, "releaser")
            if pascal(actor) != pascal(args.agent) and arole != "ceo" and not args.force:
                die(
                    f"{actor} cannot release {args.agent}'s lease; only the holder or "
                    "the CEO can. Use --force <reason> to override."
                )
            if args.force:
                args.force = require_reason(args.force, "releasing another lane's lease")
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"slots-{provider}.lock"):
            return _slot_release(args, root, provider, cap)
    # (removed: unreachable release0 branch)

    if args.slot_cmd == "renew":
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"slots-{provider}.lock"):
            return _slot_renew(args, root, provider)

    # acquire
    check_claimant(root, agent, "slot holder")
    deadline = time.monotonic() + max(args.wait, 0)
    lock_path = root / DIR_RUNTIME / DIR_LOCKS / f"slots-{provider}.lock"
    while True:
        with lock(lock_path):
            reaped = reap_slots(root, provider)
            used = used_slots(root, provider)
            if safe_component(args.agent) in used:
                f = slot_file(root, provider, args.agent)
                parts = f.read_text(encoding="utf-8").strip().split("|")
                while len(parts) < 4:
                    parts.append("-")
                parts[2] = f"{time.time():.3f}"
                write_lf(f, "|".join(parts) + "\n")
                print(f"# {args.agent} already held a {provider} slot; renewed ({len(used)}/{cap})")
                return 0
            if len(used) < cap:
                d = slots_dir(root, provider)
                d.mkdir(parents=True, exist_ok=True)
                now = f"{time.time():.3f}"
                write_lf(
                    slot_file(root, provider, args.agent),
                    f"{safe_component(args.agent)}|{now}|{now}|{args.task or '-'}\n",
                )
                print(
                    f"# acquired {provider} slot for {args.agent}"
                    f" ({len(used) + 1}/{cap} used, {cap - len(used) - 1} free)"
                )
                if reaped:
                    print(f"# reaped {len(reaped)} expired lease(s) first")
                return 0
        if time.monotonic() >= deadline:
            die(
                f"{provider} is at its concurrency cap ({len(used)}/{cap}).\n"
                f"  Do not block a lane. Options:\n"
                f"  - do work needing no slot (read, plan, review a peer's output);\n"
                f"  - fan out elsewhere: slot acquire --agent {args.agent} "
                "--provider deepseek;\n"
                f"  - release finished lanes: slot release --agent <other>;\n"
                f"  - raise the cap in {providers_path(root)} if the provider allows it.",
                3,
            )
        time.sleep(1.0)


# --------------------------------------------------------------------------- #
# CEO pulse: periodic wake-up, idle lanes, immediate dispatch
# --------------------------------------------------------------------------- #


def busy_instances(root: Path) -> set:
    """Instances that are working: they hold a slot or an active task."""
    busy = set()
    for role in list_roles(root):
        for t in parse_tasks(task_file(root, role)):
            if t["status"] in ("doing", "selfcheck") and t.get("claimed_by"):
                busy.add(pascal(t["claimed_by"]))
    providers = set(load_providers(root))
    slots_root = root / DIR_RUNTIME / DIR_SLOTS
    if slots_root.is_dir():
        providers |= {p.name for p in slots_root.iterdir() if p.is_dir()}
    for prov in providers:
        if prov == "default":
            continue
        for agent in used_slots(root, prov):
            busy.add(pascal(agent))
    return busy


def idle_instances(root: Path) -> list:
    busy = busy_instances(root)
    return [a for a in list_agents(root) if pascal(a) not in busy]


def _ready_for_role(root: Path, role: str) -> list:
    tasks = parse_tasks(task_file(root, role))
    lookup = local_dep_map(tasks)
    cache = {}
    ready = [t for t in tasks if executable(t, lookup, cache, root)]
    ready.sort(key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["created"], t["id"]))
    return ready


def awaiting_review(root: Path) -> list:
    out = []
    for name in list_roles(root):
        for t in parse_tasks(task_file(root, name)):
            if (
                t.get("review", "required") != "na"
                and t.get("review_status") != "passed"
                and t["status"] in ("review", "done")
            ):
                out.append((name, t))
    return out


def team_identity(root: Path) -> str:
    """The random id of this workspace instance, if it has one."""
    return str(_load_settings(root).get("TeamId") or "")


def ensure_team_identity(root: Path) -> str:
    """Create the workspace id once. A re-created workspace gets a new id so an
    old committed audit manifest cannot be mistaken for this ledger's history."""
    import json
    import uuid

    data = dict(_load_settings(root))
    if not data.get("TeamId"):
        data["TeamId"] = uuid.uuid4().hex
        atomic_write(providers_path(root), json.dumps(data, indent=2, sort_keys=True) + "\n")
    return str(data["TeamId"])


def _load_settings(root: Path) -> dict:
    path = providers_path(root)
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def load_pulse_minutes(root: Path) -> int:
    try:
        return int(_load_settings(root).get("PulseMinutes", 5))
    except (TypeError, ValueError):
        return 5


def set_pulse_minutes(root: Path, minutes: int) -> None:
    import json

    data = dict(_load_settings(root))
    data["PulseMinutes"] = minutes
    atomic_write(providers_path(root), json.dumps(data, indent=2) + "\n")


def stale_claims(root: Path, minutes: int = None) -> list:
    """Claims whose owner has no live lease and has not updated for the TTL.

    A task's ``updated`` field has day granularity, so it cannot express a
    90-minute lease. Comparing a midnight-based age against the slot TTL made
    every task updated earlier today look abandoned after 01:30; this compares
    whole days instead and stays conservative.
    """
    limit = minutes if minutes is not None else SLOT_TTL_MINUTES
    limit_days = max(1, (max(limit, 0) + 1439) // 1440)
    out = []
    for role, t in iter_tasks(root, statuses=("doing", "selfcheck")):
        if not t.get("claimed_by"):
            continue
        age_days = days_since(t["updated"]) if t.get("updated") else 0
        if find_slot_provider(root, t["claimed_by"]):
            continue
        if age_days >= limit_days:
            out.append((role, t, age_days * 1440))
    return out


def cmd_pulse(args) -> int:
    """CEO wake-up: find idle lanes and hand them runnable work immediately."""
    root = project_root(args)
    if args.interval is not None:
        set_pulse_minutes(root, args.interval)
    minutes = load_pulse_minutes(root)
    reap_slots(root)

    idle = idle_instances(root)
    busy = busy_instances(root)
    awaiting = awaiting_review(root)

    ready_by_role = {}
    for role in list_roles(root):
        items = _ready_for_role(root, role)
        if items:
            ready_by_role[role] = items

    print(f"# Pulse ({root})")
    print(f"# interval: every {minutes} min | {len(busy)} busy, {len(idle)} idle lane(s)")
    print()

    print(f"## idle lanes ({len(idle)})")
    if idle:
        by_role = {}
        for a in idle:
            by_role.setdefault(resolve_role(a), []).append(a)
        for role, inst in sorted(by_role.items()):
            ready = len(ready_by_role.get(role, []))
            print(f"- {role:16s} idle={', '.join(inst)}  ready_work={ready}")
    else:
        print("- none (every lane is working)")
    print()

    print("## ready work by role")
    total_ready = 0
    for role, items in sorted(ready_by_role.items()):
        total_ready += len(items)
        top = items[0]
        print(
            f"- {role:16s} {len(items):3d} ready  next: {top['id']} "
            f"[{top['priority']}] {top['title']}"
        )
    if not ready_by_role:
        print("- none")
    print(f"- awaiting independent review: {len(awaiting)}")
    print()

    # assignments: match idle instances to ready work of their own role
    plan = []
    idle_by_role = {}
    for a in idle:
        idle_by_role.setdefault(resolve_role(a), []).append(a)
    for role, inst_list in sorted(idle_by_role.items()):
        items = list(ready_by_role.get(role, []))
        if role == "reviewer" and awaiting:
            plan.append(
                ("reviewer", inst_list[0], None, f"{len(awaiting)} deliverable(s) to review")
            )
            inst_list = inst_list[1:]
        for inst, task in zip(inst_list, items):
            plan.append((role, inst, task, task["title"]))

    print("## dispatch plan")
    if not plan:
        print("- nothing to dispatch")
    for role, inst, task, title in plan:
        tid = task["id"] if task else "Review"
        print(f"- {inst:16s} <- {tid} [{role}] {title}")
    print()

    if args.commit and plan:
        applied = []
        for role, inst, task, _title in plan:
            if task is None:
                continue
            path = task_file(root, role)
            with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
                tasks = parse_tasks(path)
                idx = find_task(tasks, task["id"])
                if idx is None or tasks[idx]["status"] != "todo":
                    continue
                tasks[idx]["status"] = "doing"
                tasks[idx]["claimed_by"] = inst
                tasks[idx]["updated"] = today_iso()
                write_tasks(path, tasks, role)
                applied.append((inst, task["id"]))
        print(
            f"# applied {len(applied)} assignment(s)"
            + (f": {', '.join(f'{i}<-{t}' for i, t in applied)}" if applied else "")
        )
    elif plan and not args.commit:
        print("# dry run: add --commit to apply these assignments")
    print()

    stale = stale_claims(root)
    if stale:
        print("## abandoned claims (no lease, no update)")
        for role, t, age in stale[:6]:
            print(
                f"- {role} {t['id']} held by {t['claimed_by']} for {age // 60}h+: "
                f"reclaim with `task reclaim {role} {t['id']} --as <other> "
                "--reason 'owner silent'`"
            )
        print()

    print("## CEO next actions")
    print("- assign the plan above to the idle lanes and tell each to start now")
    if awaiting:
        print(f"- the Reviewer has {len(awaiting)} deliverable(s) waiting; it is a lane too")
    if total_ready > len(idle):
        print(
            f"- {total_ready - len(idle)} ready task(s) have no free lane: queue by priority, "
            "release finished leases or fan out on deepseek"
        )
    if not idle and not total_ready:
        print("- nothing to dispatch: check blocked tasks and open disputes")
    print(
        f"- re-arm this pulse: schedule the next wake every {minutes} min "
        "(see the /teamwork skill: schedule_prompt)"
    )
    return 0 if plan else 3


def cmd_parallel(args) -> int:
    """How much parallelism is available right now, and what to start."""
    root = project_root(args)
    limits = load_providers(root)
    reap_slots(root)
    print(f"# Parallelism plan ({root})")
    print()
    print("## provider slots")
    total_free = 0
    for prov, cap in sorted(limits.items()):
        if prov == "default":
            continue
        used = used_slots(root, prov)
        free = max(cap - len(used), 0)
        total_free += free
        print(f"- {prov:16s} used={len(used):<4d} cap={cap:<5d} free={free}")
    print(f"- TOTAL free slots: {total_free}")
    print()

    ready_by_role = {}
    ready_total = 0
    for name in list_roles(root):
        tasks = parse_tasks(task_file(root, name))
        lookup = local_dep_map(tasks)
        cache = {}
        for t in tasks:
            if executable(t, lookup, cache, root):
                role = resolve_role(name)
                ready_by_role.setdefault(role, []).append(
                    (t["priority"], name, t["id"], t["title"])
                )
                ready_total += 1
    print("## executable work")
    if not ready_by_role:
        print("- none (nothing unblocked)")
    for role, items in sorted(ready_by_role.items()):
        items.sort()
        print(
            f"- {role:16s} {len(items)} ready"
            + f"  next: {items[0][1]}/{items[0][2]} [{items[0][0]}] {items[0][3]}"
        )
    print(f"- TOTAL ready tasks: {ready_total}")
    print()

    awaiting = 0
    for name in list_roles(root):
        for t in parse_tasks(task_file(root, name)):
            if (
                t.get("review", "required") != "na"
                and t.get("review_status") != "passed"
                and t["status"] in ("review", "done")
            ):
                awaiting += 1
    print("## guidance")
    focused = (
        "ollama-cloud"
        if "ollama-cloud" in limits
        else next((p for p in limits if p != "default"), "ollama-cloud")
    )
    focused_free = max(limits.get(focused, 8) - len(used_slots(root, focused)), 0)
    bulk = "deepseek" if "deepseek" in limits else focused
    bulk_free = max(limits.get(bulk, 0) - len(used_slots(root, bulk)), 0)
    running = sum(len(used_slots(root, p)) for p in limits if p != "default")
    lanes = min(ready_total, focused_free + bulk_free)
    print(f"- focused reasoning lanes ({focused}): {focused_free} free")
    print(f"- bulk fanout lanes ({bulk}): {bulk_free} free")
    print(f"- start up to {lanes} new lane(s) now (ready tasks: {ready_total})")
    if running:
        print(
            f"- {running} lane(s) already hold a slot: hand the next task to a"
            " running lane before spawning another (keeps memory and context warm)"
        )
    if awaiting:
        print(f"- {awaiting} deliverable(s) await review; the Reviewer is a lane too")
    if ready_total > lanes:
        print("- more ready work than slots: queue it by priority, do not oversubscribe")
    print(
        "- independent sub-tasks only: one writer per file, no two agents on the"
        " same file, and never more lanes than the provider cap allows"
    )
    return 0


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BARE_URL_RE = re.compile(r"(?<![(\"'])(https?://[^\s<>)\]]+)")
FENCE_RE = re.compile(r"^\s*(```|~~~).*?^\s*\1.*?$", re.S | re.M)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
PLACEHOLDER_RE = re.compile(r"[<>{}\[\]]|full-url|example\.com|your-|\.\.\.")


def strip_code(text: str) -> str:
    """Drop fenced blocks and inline code so examples are not link-checked."""
    text = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


SKIP_DIRS = {
    ".git",
    ".pi",
    "node_modules",
    "target",
    "dist",
    "build",
    "site",
    "htmlcov",
    ".tox",
    ".nox",
    ".eggs",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "doi:", "ftp://")


def iter_markdown(project: Path) -> list:
    """Every markdown file a human might read, excluding caches and dependencies."""
    out = []
    for p in project.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def _link_targets(path: Path):
    text = strip_code(path.read_text(encoding="utf-8", errors="replace"))
    for m in LINK_RE.finditer(text):
        yield m.group(1).strip(), m.group(2).strip()


def _resolve(path: Path, target: str) -> Path:
    target = target.split("#", 1)[0].strip()
    return (path.parent / target).resolve()


def link_report(project: Path, root: Path) -> dict:
    """Broken internal links, malformed/bare external links, missing back-links."""
    broken, external_bad, bare = [], [], []
    graph = {}
    files = iter_markdown(project)
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = strip_code(raw)
        rel = path.relative_to(project).as_posix()
        outs = set()
        for label, target in _link_targets(path):
            if target.startswith("#"):
                continue
            if target.startswith(EXTERNAL_SCHEMES):
                if PLACEHOLDER_RE.search(target):
                    continue  # template placeholder, not a real citation
                host = re.sub(r"^[a-z]+://", "", target).split("/")[0]
                if "." not in host and "localhost" not in host:
                    external_bad.append((rel, label, target))
                continue
            if target.startswith(("www.", "doi:")) or target.startswith("//"):
                external_bad.append((rel, label, target))
                continue
            if target.startswith("/"):
                broken.append((rel, label, target, "absolute path - use a relative link"))
                continue
            resolved = _resolve(path, target)
            if not resolved.exists():
                broken.append((rel, label, target, "target does not exist"))
                continue
            if resolved.suffix == ".md":
                try:
                    outs.add(resolved.relative_to(project).as_posix())
                except ValueError:
                    pass
        graph[rel] = outs
        # Strip link destinations before looking for bare URLs: a URL that is
        # already a markdown target is not a bare URL, and a bare duplicate of a
        # linked URL must still be reported.
        text_without_links = LINK_RE.sub("", text)
        for m in BARE_URL_RE.finditer(text_without_links):
            url = m.group(1).rstrip(".,;")
            bare.append((rel, url))

    # reciprocity only among committed, human-facing documents
    committed = set()
    for path in files:
        rel = path.relative_to(project).as_posix()
        if rel.startswith("docs/") or rel == "AGENTS.md":
            committed.add(rel)
    missing_back = []
    for src, outs in graph.items():
        if src not in committed:
            continue
        for dst in outs:
            if dst in committed and src not in graph.get(dst, set()):
                missing_back.append((src, dst))

    return {
        "files": [f.relative_to(project).as_posix() for f in files],
        "broken": broken,
        "external_bad": external_bad,
        "bare": bare,
        "missing_back": sorted(set(missing_back)),
        "links": sum(len(v) for v in graph.values()),
    }


def cmd_links(args) -> int:
    root = project_root(args)
    project = project_of(root)
    rep = link_report(project, root)
    issues = len(rep["broken"]) + len(rep["external_bad"]) + len(rep["bare"])
    if not args.no_reciprocity:
        issues += len(rep["missing_back"])
    print(f"# Link check ({project})")
    print(f"# {len(rep['files'])} markdown file(s), {rep['links']} internal link(s)")
    print()
    print("## broken internal links")
    for rel, label, target, why in rep["broken"]:
        print(f"- {rel}: [{label}]({target}) - {why}")
    if not rep["broken"]:
        print("- none")
    print()
    print("## external links that are not valid direct URLs")
    for rel, label, target in rep["external_bad"]:
        print(f"- {rel}: [{label}]({target}) - use a full https:// URL")
    if not rep["external_bad"]:
        print("- none")
    print()
    print("## bare URLs (wrap them as [title](url))")
    for rel, url in rep["bare"]:
        print(f"- {rel}: {url}")
    if not rep["bare"]:
        print("- none")
    print()
    if not args.no_reciprocity:
        print("## missing back-links (docs must reference each other both ways)")
        for src, dst in rep["missing_back"]:
            print(f"- {src} links to {dst} but {dst} does not link back")
        if not rep["missing_back"]:
            print("- none")
        print()
    print(f"# issues: {issues}")
    return 1 if issues else 0


# --------------------------------------------------------------------------- #
# The completion gates, in one place.
#
# `loop` (may the team stop?) and `audit` (is the team healthy?) both read this
# single report, so the documented stop condition and the enforced one can never
# drift apart again.
# --------------------------------------------------------------------------- #


def iter_tasks(root: Path, statuses=None):
    """Yield (role, task) for every task on every role queue."""
    for role in list_roles(root):
        for t in parse_tasks(task_file(root, role)):
            if statuses is None or t["status"] in statuses:
                yield role, t


def all_tasks(root: Path) -> list:
    return list(iter_tasks(root))


def idle_test_roles(root: Path, records: list = None) -> list:
    """Staffed roles that have designed no test of their own layer yet."""
    records = records if records is not None else parse_tests(tests_path(root))
    return [
        owner
        for layer in TEST_LAYERS
        if (owner := LAYER_OWNER[layer])
        and instances_of(root, owner)
        and not any(r["layer"] == layer for r in records)
    ]


def _section(key: str, title: str):
    return {"key": key, "title": title, "lines": [], "blockers": []}


def gate_report(root: Path, stale_days: int = 2) -> dict:
    """Every completion gate, with the detail a human needs to act on it."""
    docs = docs_dir(root)
    sections = []
    names = list_roles(root)
    tasks = all_tasks(root)

    # 1 - acceptance criteria -------------------------------------------------
    s = _section("criteria", "acceptance criteria (machine records)")
    criteria = parse_criteria(criteria_path(root))
    if not criteria:
        s["lines"].append(
            "NO CRITERIA RECORDED: the CEO writes them with "
            "`criteria add --id AC-1 --text '...' --owner <role> --by ceo`"
        )
        s["blockers"].append("no acceptance criteria recorded")
    else:
        done = 0
        for c in criteria:
            if c["status"] == "verified":
                done += 1
                s["lines"].append(
                    f"[x] {c['id']} {c['text']} "
                    f"({c['verified_by']} {c['verified']}: {c['evidence']})"
                )
            else:
                s["lines"].append(f"[ ] {c['id']} {c['text']} (status={c['status']})")
        if done != len(criteria):
            s["blockers"].append(f"{len(criteria) - done} acceptance criteria unverified")
    unchecked = []
    for fname in ("Project.md", "Plan.md"):
        fpath = docs / fname
        if not fpath.exists():
            continue
        for line in fpath.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(("- [ ]", "* [ ]")):
                unchecked.append(f"{fname}: {line.strip()[5:].strip()[:80]}")
    if unchecked:
        s["lines"].append(
            f"human view: {len(unchecked)} unchecked box(es) in the "
            "project docs (advisory; `criteria` is the gate)"
        )
    sections.append(s)

    # 2 - layered tests -------------------------------------------------------
    s = _section("tests", "test layers (each owned and run by its own role)")
    records = parse_tests(tests_path(root))
    if not records:
        s["lines"].append(
            "NO TEST RECORDS: each layer is added by its owning role: "
            "`tests add --layer <" + "|".join(TEST_LAYERS) + ">`"
        )
        s["blockers"].append("no layered test records")
    else:
        for r in records:
            mark = {"passing": "[x]", "failing": "[!]", "pending": "[ ]", "na": "[-]"}.get(
                r["status"], "[?]"
            )
            s["lines"].append(
                f"{mark} {r['id']} {r['layer']}/{r['area']} "
                f"owner={r['owner']} by={r['by'] or '-'}"
                + (f"  {r['evidence']}" if r["evidence"] else "")
            )
        failing = [r for r in records if r["status"] == "failing"]
        if failing:
            s["blockers"].append(f"{len(failing)} test layer(s) failing")
        unknown_tests = [r for r in records if r["status"] not in TEST_STATUSES]
        if unknown_tests:
            s["lines"].append("UNKNOWN TEST STATUS: " + ", ".join(r["id"] for r in unknown_tests))
            s["blockers"].append(f"{len(unknown_tests)} test record(s) have an unknown status")
    gaps = test_gaps(root)
    for area, layer, why in gaps:
        s["lines"].append(f"GAP {area}/{layer}: {why}")
    if gaps:
        s["blockers"].append(f"{len(gaps)} required test layer(s) missing or not passing")
    idle = idle_test_roles(root, records)
    has_work = bool(areas_in_use(root)) or bool(records)
    if idle and has_work:
        s["lines"].append(
            f"every staffed role must test its own layer; no tests yet from: {', '.join(idle)}"
        )
        s["blockers"].append(f"{len(idle)} role(s) have not designed or run any test")
    elif idle:
        s["lines"].append(
            f"{len(idle)} role(s) have no tests yet; nothing to test until work starts"
        )
    sections.append(s)

    # 3 - work in flight ------------------------------------------------------
    s = _section("work", "work in flight")
    buckets = {k: [] for k in ("todo", "doing", "selfcheck", "blocked", "review")}
    invalid = []
    for role, t in tasks:
        if t["status"] in buckets:
            buckets[t["status"]].append((role, t))
        elif t["status"] not in ("done", "dropped"):
            # A typo or a hand-edited/forged value must never make a task
            # invisible to the stop gate.
            invalid.append((role, t))
    open_work = 0
    for status, items in buckets.items():
        open_work += len(items)
        s["lines"].append(f"{status}: {len(items)}")
        for role, t in sorted(items, key=lambda x: PRIORITY_ORDER.get(x[1]["priority"], 9))[:6]:
            s["lines"].append(f"    {role} {t['id']} [{t['priority']}] {t['title']}")
    if open_work:
        s["blockers"].append(f"{open_work} task(s) not finished")
    for role, t in invalid:
        s["lines"].append(f"INVALID STATUS {role} {t['id']} status={t['status']!r} {t['title']}")
    if invalid:
        s["blockers"].append(f"{len(invalid)} task(s) have an unknown status")
    sections.append(s)

    # 4 - awaiting review -----------------------------------------------------
    s = _section("review", "awaiting independent review")
    awaiting = [
        (r, t)
        for r, t in tasks
        if t.get("review", "required") != "na"
        and t.get("review_status") != "passed"
        and t["status"] in ("review", "done")
    ]
    if awaiting:
        for role, t in sorted(awaiting, key=lambda x: PRIORITY_ORDER.get(x[1]["priority"], 9)):
            s["lines"].append(
                f"{role} {t['id']} {t['title']} (review_status={t.get('review_status', 'pending')})"
            )
        s["blockers"].append(f"{len(awaiting)} deliverable(s) not review-passed")
    else:
        s["lines"].append("none")
    sections.append(s)

    # 5 - review churn (a failing loop must escalate, not spin) ---------------
    s = _section("churn", "review churn")
    churn = [
        (r, t)
        for r, t in tasks
        if int(t.get("review_fails") or 0) >= REVIEW_FAIL_LIMIT
        and t["status"] not in ("done", "dropped")
    ]
    disputes = parse_disputes(disputes_path(root))
    for role, t in churn:
        escalated = any(
            d["task"] and d["task"].upper() == t["id"].upper() and d["status"] != "resolved"
            for d in disputes
        )
        s["lines"].append(
            f"{role} {t['id']} has failed review "
            f"{t['review_fails']}x ({t['title']})" + (" - dispute open" if escalated else "")
        )
        if not escalated:
            s["blockers"].append(
                f"{t['id']} failed review {t['review_fails']}x without a dispute: escalate it"
            )
    if not churn:
        s["lines"].append("none")
    sections.append(s)

    # 6 - branches -----------------------------------------------------------
    s = _section("branches", "branches (merge and retire)")
    project = project_of(root)
    unmerged, leftover = [], []
    if is_git_repo(project):
        for role, t in tasks:
            b = t.get("branch")
            if not b or t["status"] == "dropped":
                continue
            if t.get("merge_commit"):
                if branch_exists(project, b):
                    leftover.append((role, t))
            else:
                unmerged.append((role, t))
        for role, t in unmerged[:8]:
            s["lines"].append(
                f"UNMERGED {role} {t['id']} [{t['status']}] {t['branch']} "
                f"pr={t.get('pr') or '-'} review={t.get('review_status')}"
            )
        for role, t in leftover[:8]:
            s["lines"].append(
                f"STILL OPEN {role} {t['id']} {t['branch']} merged at "
                f"{t['merge_commit']}: retire it "
                "(`pr merge --pr <id> --by <Reviewer> --delete-branch`)"
            )
        if unmerged:
            s["blockers"].append(f"{len(unmerged)} branch(es) not merged into {DEFAULT_BASE}")
        if leftover:
            s["blockers"].append(f"{len(leftover)} merged branch(es) not deleted")
    if not s["lines"]:
        s["lines"].append("none")
    sections.append(s)

    # 7 - overrides, provenance, liveness ------------------------------------
    s = _section("integrity", "gate overrides, provenance and liveness")
    forced, unprovenanced, silent = [], [], []
    for role, t in tasks:
        if t.get("forced"):
            forced.append(f"{t['id']} ({role}): {t['forced']}")
        if (
            t["status"] in ("doing", "selfcheck")
            and t.get("claimed_by")
            and days_since(t["updated"]) >= stale_days
        ):
            lease = find_slot_provider(root, t["claimed_by"])
            silent.append(
                f"{role} {t['id']} held by {t['claimed_by']} with no update "
                f"for {days_since(t['updated'])}d"
                + (f" (lease {lease})" if lease else " (no lease)")
                + f": reclaim with `task reclaim {role} {t['id']} --as "
                "<other> --reason ...`"
            )
    sources = [
        (role, role_dir(root, role) / F_SHORT, role_dir(root, role) / F_LONG) for role in names
    ]
    sources.append(("global", global_dir(root) / F_GLOBAL, None))
    for owner, short_p, long_p in sources:
        for f in (short_p, long_p):
            if f is None:
                continue
            for e in parse_memory(f):
                if e.get("body") and not e.get("by"):
                    unprovenanced.append(f"{owner}/{e.get('key') or e.get('id')}")
    for x in forced[:6]:
        s["lines"].append(f"FORCED {x}")
    if unprovenanced:
        s["lines"].append(
            f"{len(unprovenanced)} memory entr(y/ies) without `by` "
            f"provenance, e.g. {', '.join(unprovenanced[:3])}"
        )
    for x in silent[:6]:
        s["lines"].append(x)
    if forced:
        s["blockers"].append(f"{len(forced)} gate override(s) in force")
    if unprovenanced:
        s["blockers"].append(f"{len(unprovenanced)} memory entr(y/ies) lack provenance")
    if silent:
        s["lines"].append(
            f"{len(silent)} task(s) look abandoned; reclaim them or release the claim"
        )
    if not s["lines"]:
        s["lines"].append("none")
    sections.append(s)

    # 8 - disputes -----------------------------------------------------------
    s = _section("disputes", "open disputes")
    open_disputes = [d for d in disputes if d["status"] != "resolved"]
    for d in open_disputes:
        s["lines"].append(
            f"{d['id']} round={d['round']}/{MAX_ROUNDS} "
            f"{'ESCALATED ' if d['escalated'] else ''}{d['topic']}"
        )
    if open_disputes:
        s["blockers"].append(f"{len(open_disputes)} unresolved dispute(s)")
        tribunal_needed = [d for d in open_disputes if d["escalated"] or d["round"] >= MAX_ROUNDS]
        if tribunal_needed:
            s["blockers"].append(
                f"{len(tribunal_needed)} dispute(s) need the "
                f"tribunal: {', '.join(required_tribunal(root))}"
            )
    else:
        s["lines"].append("none")
    sections.append(s)

    # 8b - roster gaps (a missing instance silently removes a layer) ----------
    s = _section("roster", "roster gaps")
    for role in names:
        if not instances_of(root, role):
            s["lines"].append(
                f"the {role} role has state but no instance: add one or the layer stays untested"
            )
    if not s["lines"]:
        s["lines"].append("none")
    sections.append(s)

    # 9 - audit trail --------------------------------------------------------
    s = _section("ledger", "audit trail")
    if ledger_cache_behind(root):
        s["lines"].append(
            "NOTE the head cache lagged the ledger (a crash artefact); "
            "it was repaired - mention it in the risk register if it "
            "recurs"
        )
    problems = ledger_verify(root, reconcile=True)
    records_n = len(ledger_read(root))
    if problems or not records_n:
        for pb in problems or ["ledger is empty"]:
            s["lines"].append(f"PROBLEM {pb}")
        s["blockers"].append("the audit trail is missing or altered")
    else:
        s["lines"].append(f"{records_n} records, chain intact")
    sections.append(s)

    return {
        "sections": sections,
        "blockers": [b for sec in sections for b in sec["blockers"]],
        "forced": forced,
        "silent": silent,
        "unprovenanced": unprovenanced,
    }


def cmd_loop(args) -> int:
    """Stop-condition check: may the team stop, or must the loop continue?"""
    root = project_root(args)
    report = gate_report(root)
    print(f"# Loop status ({root})")
    print()
    for sec in report["sections"]:
        print(f"## {sec['title']}")
        for line in sec["lines"]:
            print(f"- {line}")
        print()
    blockers = report["blockers"]
    print(
        "> CONTINUE"
        if blockers
        else "> STOP - all goals verified; the CEO can write the final report"
    )
    for b in blockers:
        print(f"  ! {b}")
    return 1 if blockers else 0


# --------------------------------------------------------------------------- #
# Archive: the accepted-results ledger (committed project output)
# --------------------------------------------------------------------------- #

ARCHIVE_HEADER = (
    "# ARCHIVE - accepted results\n\n"
    "Owner: CEO. Appended automatically when a task passes independent review. The\n"
    "team's evidence ledger: what shipped, by whom, verified how, at which revision.\n"
    "Gate order: owner self-check -> Reviewer verdict -> entry below.\n"
)


def archive_path(root: Path) -> Path:
    return docs_dir(root) / "Archive.md"


def archive_append(root: Path, owner: str, t: dict) -> str:
    path = archive_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"## {t['id']} · {t['title']}  ({owner})",
        f"- date: {today_iso()}",
        f"- priority: {t['priority']}",
        f"- owner: {owner} role (work by: {t.get('claimed_by') or owner})",
        f"- reviewer: {t.get('reviewer') or 'reviewer'}",
        f"- task / issue: {t.get('shared') or '-'}",
        f"- area: {t.get('area') or '-'}",
        f"- self-check: {t.get('self_note') or '-'}",
        f"- author evidence: {t.get('evidence') or '-'}",
        f"- reviewer evidence: {t.get('review_evidence') or '-'}",
        f"- findings history: {t.get('findings') or '-'}",
        f"- branch / merge: {t.get('branch') or '-'} / {t.get('merge_commit') or 'pending'}",
        "",
    ]
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "archive.lock"):
        if not path.exists():
            write_lf(path, ARCHIVE_HEADER + "\n")
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            if not path.read_text(encoding="utf-8").endswith("\n\n"):
                fh.write("\n")
            fh.write("\n".join(lines))
    return str(path.relative_to(project_of(root)))


def find_review_role_unused(root: Path, handle: str):
    """(role, task) for a task id / title across every role queue."""
    for role in list_roles(root):
        tasks = parse_tasks(task_file(root, role))
        idx = find_task(tasks, handle)
        if idx is not None:
            return role, tasks[idx], tasks, task_file(root, role), idx
    return None, None, None, None, None


def cmd_review(args) -> int:
    root = project_root(args)
    if args.queue:
        return _review_queue(root)
    if not (args.agent and args.handle):
        die("usage: review <role> <T-id> --by <Reviewer> --result pass|fail [--evidence ...]")
    role = resolve_role(args.agent)
    path = task_file(root, role)
    reviewer, rrole = validate_actor(root, args.by or "reviewer", "reviewer", allow_role=False)
    if rrole != "reviewer":
        die(f"only the Reviewer role may review a deliverable (you passed {reviewer}).")
    if args.result not in ("pass", "fail"):
        die("--result must be pass or fail")
    if args.result == "fail" and not args.findings.strip():
        die("a fail needs --findings '<what is wrong, with evidence>'")
    if args.force:
        args.force = require_reason(args.force, "the review gate")
    if args.result == "pass" and not (args.evidence or "").strip() and not args.force:
        die(
            "a pass needs the REVIEWER's own evidence:\n"
            "  --evidence '<verify command> @<rev> -> <result>'\n"
            "  The author's evidence is not independent verification."
        )

    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        idx = find_task(tasks, args.handle)
        if idx is None:
            die(f"no task '{args.handle}' for {role}")
        t = tasks[idx]
        if t.get("review", "required") == "na":
            print(f"teamwork: {t['id']} is review=na; nothing to review")
            return 0
        if pascal(t.get("claimed_by") or "") == pascal(reviewer):
            die(
                f"{reviewer} produced {t['id']} and cannot review it; "
                "an independent instance must review."
            )
        if args.result == "pass" and not args.force:
            if not t.get("claimed_by"):
                die(
                    f"refusing to pass {t['id']}: no author is recorded (claimed_by is "
                    "empty), so independence cannot be checked.",
                    2,
                )
            if t.get("pr"):
                with lock(root / DIR_RUNTIME / DIR_LOCKS / "reviews.lock"):
                    prs_now = parse_reviews(reviews_path(root))
                    pidx_now = find_pr_exact(prs_now, t["pr"])
                if pidx_now is not None and pascal(prs_now[pidx_now].get("author") or "") == pascal(
                    reviewer
                ):
                    die(
                        f"{reviewer} is the author of {prs_now[pidx_now]['id']} and cannot "
                        "pass its review; a different Reviewer must verify it.",
                        2,
                    )

        project = project_of(root)
        if args.result == "pass" and not args.force:
            if t.get("self_check") != "passed":
                die(
                    f"refusing to pass {t['id']}: the author's self-check is "
                    f"{t.get('self_check')}. A reviewer cannot replace the author's "
                    "own review.",
                    2,
                )
            if t.get("status") != "review":
                die(
                    f"refusing to pass {t['id']}: status is {t['status']}, not 'review'. "
                    "The author must submit it first.",
                    2,
                )
            if t.get("branch") and not t.get("pr"):
                die(
                    f"refusing to pass {t['id']}: it works on branch {t['branch']} but "
                    "has no PR, so the branch could never be merged. Ask the owner to "
                    f"run 'pr open --agent {t.get('claimed_by') or role} "
                    f"--task {t['id']}' first.",
                    2,
                )
            if is_git_repo(project) and t.get("branch"):
                if not branch_exists(project, t["branch"]):
                    die(f"refusing to pass: branch {t['branch']} no longer exists", 2)
                docs_prefix = "/".join(DIR_DOCS)
                review_root = branch_worktree(project, t["branch"])
                if review_root is None and current_branch(project) == t["branch"]:
                    review_root = project
                if review_root is not None:
                    dirty = [
                        ln[3:].strip()
                        for ln in run_git(review_root, "status", "--porcelain").stdout.splitlines()
                        if ln.strip()
                    ]
                    dirty = [
                        d
                        for d in dirty
                        if not (d == docs_prefix or d.startswith(docs_prefix + "/"))
                    ]
                    if dirty:
                        die(
                            "refusing to pass: the artifact is not committed on its "
                            "branch:\n  "
                            + "\n  ".join(dirty)
                            + "\n  Review binds to a revision; the author must commit.",
                            2,
                        )

        t["reviewer"] = reviewer
        t["updated"] = today_iso()
        archived = None
        if args.result == "pass":
            t["review_evidence"] = args.evidence.strip()
            t["review_status"] = "passed"
            t["status"] = "done"
            if args.force:
                t["forced"] = (
                    t.get("forced", "") + f" | review pass forced by {reviewer}: {args.force}"
                ).strip(" |")
        if args.result == "fail":
            prev = t.get("findings", "")
            t["findings"] = (prev + " | " + args.findings).strip(" |")
            t["review_status"] = "failed"
            t["status"] = "doing"
            t["review_fails"] = int(t.get("review_fails") or 0) + 1
        write_tasks(path, tasks, role)

        with lock(root / DIR_RUNTIME / DIR_LOCKS / "reviews.lock"):
            prs = parse_reviews(reviews_path(root))
            pidx = find_pr(prs, t.get("pr") or t["id"]) if t.get("pr") else None
            if pidx is not None:
                prs[pidx]["status"] = "approved" if args.result == "pass" else "changes-requested"
                prs[pidx]["reviewer"] = reviewer
                prs[pidx]["updated"] = today_iso()
                prs[pidx]["notes"].append(
                    f"{args.result} by {reviewer}: "
                    + ((t.get("review_evidence") or "") if args.result == "pass" else args.findings)
                )
                write_reviews(reviews_path(root), prs)
        if args.result == "pass":
            archived = archive_append(root, role, t)

    ledger_append(
        root,
        "review.pass" if args.result == "pass" else "review.fail",
        reviewer,
        t["id"],
        (t.get("review_evidence") or t.get("findings") or "")[:150],
        "",
        role,
    )
    if args.result == "fail" and t.get("merge_commit"):
        ledger_append(
            root,
            "review.reopen",
            reviewer,
            t["id"],
            f"reopens work merged at {t['merge_commit']}: {args.findings[:110]}",
        )
    if t.get("pr"):
        print(
            f"          PR {t['pr']}: "
            + (
                f"approved - merge with: teamwork.py pr merge --pr {t['pr']} "
                "--by <another-Reviewer>"
                if args.result == "pass"
                else "changes requested - fix and re-submit"
            )
        )
    if args.result == "pass":
        print(
            f"teamwork: REVIEW PASS {role} {t['id']} by {reviewer}: {t['title']}"
            + (f" [work by {t['claimed_by']}]" if t.get("claimed_by") else "")
        )
        print(f"          reviewer evidence: {t.get('review_evidence')}")
        print(f"          archived to: {archived}")
    else:
        print(
            f"teamwork: REVIEW FAIL {role} {t['id']} by {reviewer}: {t['title']}"
            + (f" [work by {t['claimed_by']}]" if t.get("claimed_by") else "")
        )
        print(f"          findings: {t['findings']}")
        if t.get("merge_commit"):
            print(
                f"          !! this REOPENS work already merged at "
                f"{t['merge_commit']} ({t.get('pr')}): the fix needs a new branch, "
                "PR and review (logged as review.reopen)"
            )
        print(
            f"          -> contact {t.get('claimed_by') or role} now: fix the "
            "findings, self-check again, re-submit the PR, then request re-review."
        )
        if int(t.get("review_fails") or 0) >= REVIEW_FAIL_LIMIT:
            print(
                f"          !! failure #{t['review_fails']} for {t['id']}: the loop "
                "must not spin. Open a dispute so the tribunal decides:\n"
                f"             dispute open --by {reviewer} --against "
                f"{t.get('claimed_by') or role} --topic 'review loop on {t['id']}' "
                f"--evidence '{(args.findings or '')[:80]}' --task {t['id']}"
            )
    return 0


def _review_queue(root: Path) -> int:
    rows = []
    for name in list_roles(root):
        for t in parse_tasks(task_file(root, name)):
            if t.get("review", "required") == "na":
                continue
            if t.get("review_status") == "passed" or t["status"] == "dropped":
                continue
            rows.append((PRIORITY_ORDER.get(t["priority"], 9), name, t))
    print(f"# Reviewer queue ({root})")
    if not rows:
        print("- nothing awaiting review")
        return 0
    rows.sort(key=lambda r: (r[0], r[1], r[2]["id"]))
    for _prio, name, t in rows:
        print(
            f"- {name} {t['id']} [{t['priority']}/{t['status']}] {t['title']}"
            f"  review_status={t.get('review_status', 'pending')}"
            f" self_check={t.get('self_check', 'pending')}"
            + (f" branch={t['branch']}" if t.get("branch") else "")
            + (f" pr={t['pr']}" if t.get("pr") else "")
        )
        if t.get("evidence"):
            print(f"    author evidence: {t['evidence']}")
        if t.get("findings"):
            print(f"    findings so far: {t['findings']}")
    print()
    print(f"# {len(rows)} deliverable(s) to review")
    print("# verify independently, then")
    print(
        "#   review <role> <T-id> --by <Reviewer> --result pass --evidence '<cmd @rev -> result>'"
    )
    print("#   review <role> <T-id> --by <Reviewer> --result fail --findings '<defect + evidence>'")
    return 0


def cmd_selfcheck(args) -> int:
    """Author's own review + test, mandatory before submitting for review."""
    root = project_root(args)
    role = resolve_role(args.agent)
    path = task_file(root, role)
    actor, arole = validate_actor(root, args.by or args.agent, "self-check actor")
    if arole != role and not args.force:
        die(
            f"{actor} is {arole}; only the owning {role} role may self-check a "
            f"{role} task. Use --force <reason> only to hand the work over deliberately.",
            2,
        )
    if args.result not in ("pass", "fail"):
        die("--result must be pass or fail")
    if not args.note.strip():
        die("a self-check needs --note '<what you re-read and why it is sound>'")
    if args.force:
        args.force = require_reason(args.force, "the self-check ownership rule")
    if args.result == "pass" and not args.test.strip():
        die(
            "a passing self-check needs --test '<command @rev -> observed result>'\n"
            "  Reading your own diff is not a test. Run something."
        )
    with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
        tasks = parse_tasks(path)
        idx = find_task(tasks, args.handle)
        if idx is None:
            die(f"no task '{args.handle}' for {role}")
        t = tasks[idx]
        claimant = t.get("claimed_by") or ""
        if not claimant:
            t["claimed_by"] = actor
        elif pascal(claimant) != pascal(actor) and not args.force:
            die(
                f"{t['id']} is claimed by {claimant}; the instance doing the work "
                f"self-checks it (you passed {actor}). Use --force <reason> only to "
                "hand the work over deliberately.",
                2,
            )
        if t.get("review", "required") == "na":
            print(f"teamwork: {t['id']} is review=na; self-check not required")
            return 0
        note = f"[{args.result}] {args.note.strip()}"
        if args.test.strip():
            note += f" | test: {args.test.strip()}"
        prev = t.get("self_note", "")
        t["self_note"] = (prev + " || " + note).strip(" |") if prev else note
        t["updated"] = today_iso()
        if args.result == "pass":
            t["self_check"] = "passed"
            t["status"] = "review"
        else:
            t["self_check"] = "failed"
            t["status"] = "doing"
        write_tasks(path, tasks, role)
    if args.force:
        t_forced = (t.get("forced", "") + f" | self-check by {actor}: {args.force}").strip(" |")
        with lock(root / DIR_RUNTIME / DIR_LOCKS / f"role-{role}.lock"):
            tasks2 = parse_tasks(path)
            i2 = find_task(tasks2, args.handle)
            if i2 is not None:
                tasks2[i2]["forced"] = t_forced
                write_tasks(path, tasks2, role)
    ledger_append(
        root,
        "selfcheck",
        actor,
        t["id"],
        f"{args.result}: {t.get('self_note', '')[:120]}"
        + (f" FORCED: {args.force}" if args.force else ""),
        "",
        role,
    )
    if args.result == "pass":
        print(f"teamwork: SELF-CHECK PASS {role} {t['id']} by {actor}: {t['title']}")
        print(f"          note: {t['self_note']}")
        print(
            "          -> submitted for independent review; the Reviewer will "
            "verify it and may still fail it."
        )
    else:
        print(f"teamwork: SELF-CHECK FAIL {role} {t['id']} by {actor}: {t['title']}")
        print(f"          note: {t['self_note']}")
        print("          -> task returned to doing; fix it and self-check again.")
    return 0


def cmd_archive(args) -> int:
    root = project_root(args)
    path = archive_path(root)
    if not path.exists():
        print(f"# no archive yet ({path.relative_to(project_of(root))})")
        print("# entries are appended automatically when a review passes")
        return 0
    text = path.read_text(encoding="utf-8")
    if args.agent:
        role = resolve_role(args.agent)
        blocks = text.split("\n## ")
        hits = [
            b
            for b in blocks[1:]
            if f"({role})" in b.split("\n", 1)[0] or f"({role}-" in b.split("\n", 1)[0]
        ]
        print(f"# Archived results for {role} ({path.relative_to(project_of(root))})")
        for b in hits:
            print("\n## " + b.rstrip())
        if not hits:
            print("- none")
        return 0
    print(text.rstrip())
    return 0


def cmd_board(args) -> int:
    """One line per role: status counts, the next executable task, slot usage."""
    root = project_root(args)
    names = list_roles(root)
    print("# priority-ordered; READY = todo with all dependencies done")
    print("# one shared queue per ROLE; several instances may serve it")
    print()
    for name in names:
        tasks = parse_tasks(task_file(root, name))
        inst = instances_of(root, name)
        label = f"{name:16s} ({len(inst)} instance{'s' if len(inst) != 1 else ''})"
        if not tasks:
            print(f"- {label} (empty)")
            continue
        counts = {}
        for t in tasks:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
        lookup = local_dep_map(tasks)
        cache = {}
        ready = sorted(
            (t for t in tasks if executable(t, lookup, cache, root)),
            key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["created"]),
        )
        summary = " ".join(f"{k}={counts[k]}" for k in STATUSES if counts.get(k))
        print(f"- {label} {summary}")
        if ready:
            top = ready[0]
            print(
                f"  next={top['id']} [{top['priority']}] {top['title']}"
                + f" claimed_by={top.get('claimed_by') or 'pool'}"
            )
        else:
            print("  next=- (idle or all blocked)")
    limits = load_providers(root)
    reap_slots(root)
    slots = " · ".join(
        f"{p} {len(used_slots(root, p))}/{c}" for p, c in sorted(limits.items()) if p != "default"
    )
    print()
    print(f"# slots: {slots}")
    print("# parallelism: teamwork.py parallel    idle lanes: teamwork.py pulse")
    return 0


def cmd_audit(args) -> int:
    """Anti-hallucination / integrity audit of the whole workspace."""
    root = project_root(args)
    names = list_roles(root)
    if not names:
        die("no agents in this workspace")
    problems = 0

    problems += _audit_section(root, names, args)
    problems += _audit_submitted_for_review_without_a_self_chec(root, names, args)
    problems += _audit_done_without_evidence_fabricated_complet(root, names, args)
    problems += _audit_possible_duplicate_tasks_across_agents(root, names, args)
    problems += _audit_memory_caps(root, names, args)
    problems += _audit_blocked_tasks(root, names, args)
    problems += _audit_stale_in_progress(root, names, args)
    problems += _audit_deliverables_awaiting_independent_review(root, names, args)
    problems += _audit_open_disputes_design_decision_challenges(root, names, args)
    problems += _audit_forced_gate_overrides(root, names, args)
    problems += _audit_roster_gaps_roles_with_no_instance(root, names, args)
    problems += _audit_ownership_sanity_phantom_agents_silent_o(root, names, args)
    problems += _audit_branch_pr_flow(root, names, args)
    problems += _audit_red_lines(root, names, args)
    problems += _audit_team_skills(root, names, args)
    problems += _audit_completion_gates_shared_with_loop(root, names, args)
    problems += _audit_audit_trail_append_only_hash_chained(root, names, args)
    problems += _audit_layered_tests(root, names, args)
    problems += _audit_merged_branches_still_open(root, names, args)
    problems += _audit_git_archival_lfs_large_files(root, names, args)
    problems += _audit_markdown_link_health_broken_malformed_ba(root, names, args)

    print(f"# problems found: {problems}")
    return 1 if problems else 0


def redlines_path(root: Path) -> Path:
    return global_dir(root) / F_REDLINES


def cmd_redline(args) -> int:
    """Record a refused red-line action, or close a resolved one."""
    root = project_root(args)
    path = redlines_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    actor, arole = validate_actor(root, args.by, "reporter")
    if args.redline_cmd == "close" and arole != "ceo" and not args.force:
        die(
            f"only the CEO closes a red line: it records that the user authorized "
            f"the action (you are {actor}). Use --force <reason> to override."
        )
    if args.redline_cmd == "close" and args.force:
        args.force = require_reason(args.force, "closing a red line")
    if args.redline_cmd == "record":
        if not args.action.strip() or not args.why.strip():
            die("--action and --why are required: what was refused and why it is a red line")
        block = [
            f"## RL-{today_iso()} · {args.by}",
            f"- date: {today_iso()}",
            f"- status: {args.authorized if args.authorized else 'refused'}",
            f"- reported by: {actor} ({arole})",
            f"- attempted action: {args.action}",
            f"- why it is a red line: {args.why}",
            f"- safe alternative: {args.alternative or '-'}",
            f"- user authorization: {args.authorized or 'none (the action stays refused)'}",
            "",
        ]
        if not path.exists():
            write_lf(
                path,
                "# Red lines - attempted and refused actions\n\n"
                "> A red line is never crossed silently: the refusal is\n"
                "> recorded here, escalated to the CEO, and audited.\n\n"
                "Related: [team map](../TeamMap.md) | "
                "[disputes](../Disputes.md)\n",
            )
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(block))
        ledger_append(
            root,
            "redline.record",
            actor,
            args.action[:60],
            f"{args.why[:80]} | authorized: {args.authorized or 'no'}",
        )
        print(f"# red line recorded by {actor}")
        print(f"#   {args.action[:80]}")
        print(f"#   status: {args.authorized or 'refused'} (escalate to the CEO)")
        return 0
    # close
    if not path.exists():
        print("# no red lines recorded")
        return 0
    text = path.read_text(encoding="utf-8")
    if args.id not in text:
        die(f"no red line '{args.id}'")
    text = text.replace(f"## {args.id}", f"## {args.id} [closed by {actor}]")
    atomic_write(path, text)
    ledger_append(
        root,
        "redline.close",
        actor,
        args.id,
        (args.reason or "resolved") + (f" FORCED: {args.force}" if args.force else ""),
    )
    print(f"# {args.id} closed by {actor}")
    return 0


def _audit_section(root: Path, names: list, args) -> int:
    hits = 0
    print(f"# Teamwork audit ({root})")
    print()
    return hits


def _audit_submitted_for_review_without_a_self_chec(root: Path, names: list, args) -> int:
    print("## submitted for review without a self-check (skipped their own test)")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if (
                t.get("review", "required") != "na"
                and t.get("self_check") not in ("passed", "na")
                and t["status"] in ("review", "done")
            ):
                print(
                    f"- {name} {t['id']} [{t['status']}] {t['title']} "
                    f"self_check={t.get('self_check', 'pending')}"
                )
                hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_done_without_evidence_fabricated_complet(root: Path, names: list, args) -> int:
    print("## done without evidence (fabricated-completion risk)")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if t["status"] == "done" and not t.get("evidence"):
                print(f"- {name} {t['id']} {t['title']}")
                hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_stale_in_progress(root: Path, names: list, args) -> int:
    print(f"## in progress with no update for >= {args.stale_days} days")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if (
                t["status"] in ("doing", "blocked", "review")
                and days_since(t["updated"]) >= args.stale_days
            ):
                print(
                    f"- {name} {t['id']} [{t['status']}] {t['title']} "
                    f"(updated {t['updated']}, {days_since(t['updated'])}d)"
                )
                hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_possible_duplicate_tasks_across_agents(root: Path, names: list, args) -> int:
    print("## possible duplicate tasks across agents")
    items = []
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if t["status"] in ("done", "dropped"):
                continue
            words = {w for w in re.findall(r"[a-z0-9]+", t["title"].lower()) if len(w) > 3}
            items.append((name, t, words))
    hits = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            n1, t1, w1 = items[i]
            n2, t2, w2 = items[j]
            if not w1 or not w2:
                continue
            jaccard = len(w1 & w2) / len(w1 | w2)
            if jaccard >= 0.6:
                print(
                    f"- {int(jaccard * 100)}% similar: {n1}:{t1['id']} "
                    f"{t1['title']!r}  <->  {n2}:{t2['id']} {t2['title']!r}"
                )
                hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_memory_caps(root: Path, names: list, args) -> int:
    print("## memory caps")
    hits = 0
    for name in names:
        d = role_dir(root, name)
        s = len(parse_memory(d / F_SHORT))
        long_n = len(parse_memory(d / F_LONG))
        if s > SHORT_CAP or long_n > LONG_CAP:
            print(
                f"- {name} short={s}/{SHORT_CAP} long={long_n}/{LONG_CAP} "
                f"(run: consolidate --agent {name})"
            )
            hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_blocked_tasks(root: Path, names: list, args) -> int:
    print("## blocked tasks")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if t["status"] == "blocked":
                print(f"- {name} {t['id']} {t['title']} deps={t['deps'] or '-'}")
                hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_deliverables_awaiting_independent_review(root: Path, names: list, args) -> int:
    print("## deliverables awaiting independent review")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if (
                t.get("review", "required") != "na"
                and t.get("review_status") != "passed"
                and t["status"] in ("review", "done")
            ):
                print(
                    f"- {name} {t['id']} [{t['status']}] {t['title']} "
                    f"review_status={t.get('review_status', 'pending')}"
                )
                hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_open_disputes_design_decision_challenges(root: Path, names: list, args) -> int:
    print("## open disputes (design/decision challenges)")
    disputes = parse_disputes(disputes_path(root))
    open_d = [d for d in disputes if d["status"] != "resolved"]
    hits = 0
    for d in open_d:
        flag = ""
        if d["escalated"] or d["round"] >= MAX_ROUNDS:
            flag = "  <-- TRIBUNAL REQUIRED (CEO+CTO+CFO)"
        stale = days_since(d["updated"]) >= args.stale_days
        print(
            f"- {d['id']} round={d['round']}/{MAX_ROUNDS} "
            f"{d['raised_by']} -> {d['against']}: {d['topic']}"
            + (f" (no update {days_since(d['updated'])}d)" if stale else "")
            + flag
        )
        hits += 1
    if not hits:
        print("- none")
    print()
    return hits


def _audit_forced_gate_overrides(root: Path, names: list, args) -> int:
    print("## forced gate overrides")
    hits = 0
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            if t.get("forced"):
                print(f"- {name} {t['id']}: {t['forced']}")
                hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_roster_gaps_roles_with_no_instance(root: Path, names: list, args) -> int:
    print("## roster gaps (roles with no instance)")
    hits = 0
    for role in list_roles(root):
        if not instances_of(root, role):
            print(
                f"- the {role} role has a memory/queue but no instance: its layer "
                "and duties cannot be performed (add an instance or accept that the "
                "layer is not required)"
            )
            hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_ownership_sanity_phantom_agents_silent_o(root: Path, names: list, args) -> int:
    print("## ownership sanity (phantom agents, silent owners)")
    hits = 0
    known = {pascal(i) for i in known_instances(root)}
    for name in names:
        for t in parse_tasks(task_file(root, name)):
            cb = t.get("claimed_by")
            if not cb or pascal(cb) in known:
                continue
            if pascal(cb) == pascal(name) and instances_of(root, name):
                continue  # the role itself = shared pool, not a phantom
            print(
                f"- {name} {t['id']} claimed by unknown agent '{cb}' "
                "(no such instance; fix with 'task reclaim' or reassign)"
            )
            hits += 1
            if (
                t["status"] in ("doing", "selfcheck")
                and cb
                and days_since(t["updated"]) >= args.stale_days
            ):
                lease = find_slot_provider(root, cb)
                print(
                    f"- {name} {t['id']} held by {cb} with no update for "
                    f"{days_since(t['updated'])}d"
                    + (f" (lease: {lease})" if lease else " (no lease)")
                    + f": reclaim with 'task reclaim {name} {t['id']} --as <other> "
                    "--reason ...'"
                )
                hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_branch_pr_flow(root: Path, names: list, args) -> int:
    print("## branch / PR flow")
    project_a = project_of(root)
    hits = 0
    if is_git_repo(project_a):
        prs = parse_reviews(reviews_path(root))
        for role in names:
            for t in parse_tasks(task_file(root, role)):
                if t.get("branch") and t["status"] in ("review", "done") and not t.get("pr"):
                    print(
                        f"- {role} {t['id']} is {t['status']} on branch {t['branch']} "
                        "with no PR: run `pr open`"
                    )
                    hits += 1
                if t.get("pr") and t["status"] == "done" and not t.get("merge_commit"):
                    print(f"- {role} {t['id']} PR {t['pr']} approved but not merged")
                    hits += 1
        for pr in prs:
            if pr["status"] == "approved" and days_since(pr["updated"]) >= args.stale_days:
                print(f"- {pr['id']} approved {days_since(pr['updated'])}d ago, not merged")
                hits += 1
            if pr["status"] == "open" and days_since(pr["updated"]) >= args.stale_days:
                print(f"- {pr['id']} open {days_since(pr['updated'])}d with no verdict")
                hits += 1
        bootstrap = {"AGENTS.md", ".gitignore", ".gitattributes"}
        pending = []
        for ln in run_git(project_a, "status", "--porcelain").stdout.splitlines():
            if not ln.strip():
                continue
            path = ln[3:].strip().strip('"')
            if ln.startswith("??") and path in bootstrap:
                continue  # the CEO commits the constitution during bootstrap
            pending.append(path)
        if current_branch(project_a) == DEFAULT_BASE and pending:
            print(
                f"- uncommitted changes on {DEFAULT_BASE}: work belongs on a task branch "
                f"({', '.join(pending[:3])})"
            )
            hits += 1
    else:
        print("- no git repository: run `teamwork.py repo`")
        hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_red_lines(root: Path, names: list, args) -> int:
    print("## red lines")
    rl = redlines_path(root)
    hits = 0
    if rl.exists():
        for block in re.split(r"^## ", rl.read_text(encoding="utf-8"), flags=re.M)[1:]:
            head = block.splitlines()[0].strip()
            if "[closed by" in head or "<" in head:
                continue
            reason = next(
                (
                    ln.split(":", 1)[1].strip()
                    for ln in block.splitlines()
                    if ln.startswith("- why it is a red line:")
                ),
                "",
            )
            print(f"- UNRESOLVED {head}: {reason[:70]}")
            hits += 1
    if not rl.exists():
        print("- none recorded (good: nothing has hit a red line)")
    if not hits:
        print("- no unresolved refusals")
    return hits


def _audit_team_skills(root: Path, names: list, args) -> int:
    print("## team skills")
    hits = 0
    skill_items = parse_skills(skills_path(root))
    for s in skill_items:
        fp = skill_file(root, s["path"]) if s["path"] else None
        if fp is None or not fp.exists():
            print(
                f"- {s['id']} '{s['name']}' is registered but its file is missing "
                f"({s['path'] or 'no path'})"
            )
            hits += 1
        elif s["status"] == "draft":
            print(
                f"- '{s['name']}' is still a draft: share it so peers reuse it "
                f"(skill share {s['name']} --by <you>)"
            )
            hits += 1
    if not skill_items:
        roles_with_areas = {}
        for role in names:
            for t in parse_tasks(task_file(root, role)):
                if t.get("area") and t["status"] in ("done", "review"):
                    roles_with_areas.setdefault((role, t["area"]), 0)
                    roles_with_areas[(role, t["area"])] += 1
        hot = [k for k, v in roles_with_areas.items() if v >= 3]
        if hot:
            print(
                f"- {len(hot)} repeated flow(s) look worth extracting, e.g. "
                + ", ".join(f"{r}/{a} ({roles_with_areas[(r, a)]} tasks)" for r, a in hot[:3])
            )
            print("    teamwork.py skill candidates")
    if not hits:
        print("- ok")
    print()
    return hits


def _audit_completion_gates_shared_with_loop(root: Path, names: list, args) -> int:
    hits = 0
    print("## completion gates (shared with `loop`)")
    gates = gate_report(root, stale_days=args.stale_days)
    if gates["blockers"] and all_tasks(root):
        for b in gates["blockers"]:
            print(f"- BLOCKER {b}")
        hits += len(gates["blockers"])
    elif gates["blockers"]:
        print(
            f"- {len(gates['blockers'])} gate(s) open, but no work has started yet: "
            + "; ".join(gates["blockers"])
        )
    else:
        print("- none: the team may stop")
    print()
    return hits


def _audit_audit_trail_append_only_hash_chained(root: Path, names: list, args) -> int:
    print("## audit trail (append-only, hash-chained)")
    hits = 0
    if ledger_cache_behind(root):
        print("- NOTE the head cache lagged the ledger (a crash artefact); it was repaired")
        ledger_verify(root, reconcile=True)
    problems_ledger = ledger_verify(root, reconcile=True)
    records = ledger_read(root)
    if not records:
        print("- no ledger records: initialise with `init` (or the trail was deleted)")
        hits += 1
    for pb in problems_ledger:
        print(f"- PROBLEM {pb}")
        hits += 1
    if records and not problems_ledger:
        print(f"- {len(records)} records, chain intact, head {records[-1]['hash'][:16]}")
    manifest = docs_dir(root) / F_MANIFEST
    if manifest.exists():
        try:
            import json

            mdata = json.loads(manifest.read_text(encoding="utf-8"))
            recorded = int(mdata.get("ledger", {}).get("records", 0))
            manifest_team = str(mdata.get("team_id") or "")
            current_team = team_identity(root)
            if manifest_team and manifest_team == current_team and recorded > len(records):
                print(
                    f"- the ledger has FEWER records ({len(records)}) than the last "
                    f"audit export recorded ({recorded}): it was truncated"
                )
                hits += 1
        except (ValueError, OSError, TypeError):
            pass
    unprovenanced = [
        r
        for role in names
        for r in parse_memory(role_dir(root, role) / F_SHORT)
        + parse_memory(role_dir(root, role) / F_LONG)
        if r.get("body") and not r.get("by")
    ]
    if unprovenanced:
        print(
            f"- {len(unprovenanced)} memory entr(y/ies) have no `by` provenance "
            "(who recorded it); record provenance with "
            "`remember --by <instance> --src <task> --rev <sha>`"
        )
        hits += 1
    decisions = docs_dir(root) / "Decisions.md"
    if decisions.exists():
        body = decisions.read_text(encoding="utf-8")
        blocks = re.split(r"^## ", body, flags=re.M)[1:]
        bad = []
        for b in blocks:
            head = b.splitlines()[0].strip()
            if "<" in head or head.lower().startswith("sources"):
                continue
            if "- evidence:" not in b or b.split("- evidence:", 1)[1].splitlines()[0].strip() in (
                "",
                "-",
            ):
                bad.append(head[:60])
        if bad:
            print(f"- {len(bad)} decision(s) without evidence: {', '.join(bad[:3])}")
            hits += 1
    if not hits:
        print("- ok")
    return hits


def _audit_layered_tests(root: Path, names: list, args) -> int:
    print("## layered tests")
    hits = 0
    records = parse_tests(tests_path(root))
    for r in records:
        if r["status"] == "failing":
            print(
                f"- {r['id']} {r['layer']}/{r['area']} FAILING (owner {r['owner']}): "
                f"{r['evidence']}"
            )
            hits += 1
    cmds = {}
    for r in records:
        if r["command"]:
            cmds.setdefault(r["command"].strip(), []).append(r)
    for cmd, rs in cmds.items():
        if len(rs) > 1:
            who = ", ".join(f"{x['id']}({x['layer']})" for x in rs)
            print(
                f"- the same command runs in several layers: {who} -> '{cmd[:60]}' "
                "(duplicate testing; keep one)"
            )
            hits += 1
    for area, layer, why in test_gaps(root):
        print(f"- coverage gap {area}/{layer}: {why}")
        hits += 1
    has_work = bool(areas_in_use(root)) or records
    idle = idle_test_roles(root, records)
    if idle and has_work:
        for who in idle:
            print(
                f"- the {who} role has designed no tests; every agent owns and runs its own layer"
            )
            hits += 1
    elif idle:
        print(
            f"- informational: {len(idle)} role(s) have no tests yet "
            f"({', '.join(idle)}); nothing to test until work starts"
        )
    if not hits:
        print("- none")
    return hits


def _audit_merged_branches_still_open(root: Path, names: list, args) -> int:
    print("## merged branches still open")
    hits = 0
    if is_git_repo(project_of(root)):
        for name in names:
            for t in parse_tasks(task_file(root, name)):
                b = t.get("branch")
                if b and t.get("merge_commit") and branch_exists(project_of(root), b):
                    print(
                        f"- {name} {t['id']} {b} merged at {t['merge_commit']} but the "
                        "branch still exists; delete it"
                    )
                    hits += 1
    if not hits:
        print("- none")
    return hits


def _audit_git_archival_lfs_large_files(root: Path, names: list, args) -> int:
    print("## git archival (LFS + large files)")
    project = project_of(root)
    hits = 0
    if is_git_repo(project):
        attrs = project / ".gitattributes"
        if not attrs.exists() or "filter=lfs" not in attrs.read_text(encoding="utf-8"):
            print("- .gitattributes has no Git LFS rules: run `teamwork.py repo`")
            hits += 1
        else:
            big = []
            for p_ in project.rglob("*"):
                if not p_.is_file() or any(
                    part in {".git", ".pi"} | SKIP_DIRS for part in p_.parts
                ):
                    continue
                try:
                    if p_.stat().st_size >= 1_000_000:
                        big.append(p_.relative_to(project).as_posix())
                except OSError:
                    pass
            untracked = [b for b in big if not lfs_tracked(project, b)]
            if untracked:
                print(
                    f"- {len(untracked)} large file(s) not LFS-tracked, e.g. "
                    + ", ".join(untracked[:3])
                )
                hits += 1
            else:
                print(f"- LFS rules present; {len(big)} large file(s), all tracked")
    else:
        print("- no git repository yet: run `teamwork.py repo`")
        hits += 1
    if not hits:
        print("- ok")
    return hits


def _audit_markdown_link_health_broken_malformed_ba(root: Path, names: list, args) -> int:
    hits = 0
    print("## markdown link health (broken / malformed / bare / missing back-links)")
    rep = link_report(project_of(root), root)
    link_issues = (
        len(rep["broken"]) + len(rep["external_bad"]) + len(rep["bare"]) + len(rep["missing_back"])
    )
    if link_issues:
        print(f"- {link_issues} issue(s); run `teamwork.py links` for the list")
    else:
        print("- none")
    hits += link_issues
    print()
    return hits


def _print_dispute(d: dict) -> None:
    print(
        f"- {d['id']} [{d['status']}] round={d['round']}/{MAX_ROUNDS} "
        f"escalated={'yes' if d['escalated'] else 'no'}"
    )
    print(f"    topic:  {d['topic']}")
    print(
        f"    raised: {d['raised_by']} -> {d['against']}"
        + (f"  task={d['task']}" if d["task"] else "")
    )
    if d["position"]:
        print(f"    claim:  {d['position']}")
    if d["evidence"]:
        print(f"    evidence: {d['evidence']}")
    for r in d["rounds"]:
        print(f"    r{r['n']} {r['by']} ({r['date']}): {r['text']}")
    if d["signed"] or d["decision"]:
        print(f"    ruling: signed=[{', '.join(d['signed'])}] {d['decision']}")


def required_tribunal(root: Path, dispute: dict = None) -> list:
    """CEO plus whichever of CTO/CFO are staffed.

    If the CEO is a party to the dispute, the Reviewer joins as an independent
    arbiter, so the tribunal never rules on the CEO's own case.
    """
    members = ["ceo"]
    for role in ("cto", "cfo"):
        if instances_of(root, role):
            members.append(role)
    if dispute:
        parties = {
            resolve_role(dispute.get("raised_by") or ""),
            resolve_role(dispute.get("against") or ""),
        }
        if "ceo" in parties and instances_of(root, "reviewer"):
            members.append("reviewer")
    return members


def _dispute_tribunal_notice(d: dict) -> None:
    print("teamwork: this dispute needs the tribunal - escalate it now.")
    print(f"  {d['id']}: {d['topic']}")
    print(f"  1) python3 teamwork.py dispute escalate {d['id']} --by {d['raised_by']}")
    print("  2) the tribunal discusses and each signs:")
    print(f"     dispute sign {d['id']} --by ceo|cto|cfo")
    print(f"  3) dispute resolve {d['id']} --by ceo --decision '<binding ruling>'")
    print("  4) record the ruling in docs/Team/Decisions.md")
    print("  The ruling is final: the losing side implements it and says so in its report.")


def cmd_dispute_open(args) -> int:
    root = project_root(args)
    by, _r = validate_actor(root, args.by, "raiser")
    against, _r2 = validate_actor(root, args.against, "opponent")
    args.by, args.against = by, against
    path = disputes_path(root)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "disputes.lock"):
        disputes = parse_disputes(path)
        if args.against == args.by:
            die("a dispute must be raised against another agent")
        d = new_dispute(args.topic, args.by, args.against, args.evidence, args.position, args.task)
        if args.evidence:
            d["rounds"].append({"n": 1, "by": args.by, "date": today_iso(), "text": args.evidence})
            d["round"] = 1
        disputes.append(d)
        write_disputes(path, disputes)
    ledger_append(
        root,
        "dispute.open",
        args.by,
        d["id"],
        f"-> {args.against}: {args.topic} | {args.evidence[:90]}",
    )
    print(f"teamwork: opened {d['id']} {args.by} -> {args.against}: {d['topic']}")
    if not args.evidence:
        print(
            "teamwork: WARNING no evidence recorded. A challenge without"
            " counter-evidence is an opinion, not a dispute."
        )
    return 0


def cmd_dispute_round(args) -> int:
    root = project_root(args)
    actor, _r = validate_actor(root, args.by, "respondent")
    args.by = actor
    path = disputes_path(root)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "disputes.lock"):
        disputes = parse_disputes(path)
        idx = find_dispute(disputes, args.id)
        if idx is None:
            die(f"no dispute '{args.id}'")
        d = disputes[idx]
        if d["status"] == "resolved":
            die(f"{d['id']} is resolved; open a new dispute if you disagree")
        next_round = d["round"] + 1
        if next_round > MAX_ROUNDS:
            d["escalated"] = True
            d["updated"] = today_iso()
            write_disputes(path, disputes)
            _dispute_tribunal_notice(d)
            return 2
        d["rounds"].append(
            {"n": next_round, "by": args.by, "date": today_iso(), "text": args.message}
        )
        d["round"] = next_round
        d["updated"] = today_iso()
        write_disputes(path, disputes)
    ledger_append(
        root, "dispute.round", args.by, d["id"], f"r{next_round}/{MAX_ROUNDS}: {args.message[:120]}"
    )
    print(f"teamwork: {d['id']} round {next_round}/{MAX_ROUNDS} by {args.by}")
    if next_round >= MAX_ROUNDS:
        print("teamwork: this was the final round. If the two of you still disagree, escalate now.")
        _dispute_tribunal_notice(d)
    return 0


def cmd_dispute_escalate(args) -> int:
    root = project_root(args)
    actor, _r = validate_actor(root, args.by, "escalator")
    args.by = actor
    path = disputes_path(root)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "disputes.lock"):
        disputes = parse_disputes(path)
        idx = find_dispute(disputes, args.id)
        if idx is None:
            die(f"no dispute '{args.id}'")
        d = disputes[idx]
        d["escalated"] = True
        d["status"] = "escalated"
        d["updated"] = today_iso()
        write_disputes(path, disputes)
    ledger_append(root, "dispute.escalate", args.by, d["id"], f"to the tribunal: {d['topic']}")
    print(f"teamwork: {d['id']} escalated by {args.by} to the CEO+CTO+CFO tribunal")
    _dispute_tribunal_notice(d)
    return 0


def cmd_dispute_sign(args) -> int:
    root = project_root(args)
    actor, arole = validate_actor(root, args.by, "tribunal signer")
    args.by = actor
    path = disputes_path(root)
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "disputes.lock"):
        disputes = parse_disputes(path)
        idx = find_dispute(disputes, args.id)
        if idx is None:
            die(f"no dispute '{args.id}'")
        d = disputes[idx]
        if not d["escalated"] and d["status"] != "escalated":
            die(f"{d['id']} is not escalated; the two agents resolve it themselves")
        who = arole
        members = required_tribunal(root, d)
        if who not in members:
            die(f"only the tribunal may sign: {', '.join(members)}")
        if who not in d["signed"]:
            d["signed"].append(who)
        d["updated"] = today_iso()
        write_disputes(path, disputes)
    missing = [r for r in required_tribunal(root, d) if r not in d["signed"]]
    ledger_append(root, "dispute.sign", who, d["id"], f"signed: {d['signed']}")
    print(
        f"teamwork: {d['id']} signed by {who}; signed={d['signed']}"
        + (f"; still missing {missing}" if missing else "; tribunal complete")
    )
    return 0


def cmd_dispute_resolve(args) -> int:
    root = project_root(args)
    actor, arole = validate_actor(root, args.by, "tribunal member")
    args.by = actor
    if arole not in required_tribunal(root):
        die(f"only the tribunal may resolve: {', '.join(required_tribunal(root))}")
    path = disputes_path(root)
    _resolve_actor_role = arole
    with lock(root / DIR_RUNTIME / DIR_LOCKS / "disputes.lock"):
        disputes = parse_disputes(path)
        idx = find_dispute(disputes, args.id)
        if idx is None:
            die(f"no dispute '{args.id}'")
        d = disputes[idx]
        who = resolve_role(args.by)
        if d["escalated"]:
            members = required_tribunal(root, d)
            missing = [r for r in members if r not in d["signed"]]
            if missing and not args.force:
                die(
                    f"{d['id']} is an escalated dispute: "
                    f"{', '.join(members)} must sign first (missing: "
                    f"{', '.join(missing)})"
                )
        elif who != "ceo":
            die(
                f"{d['id']} is not escalated: only the CEO resolves it (you are "
                f"{who}). Escalate it first if it needs the tribunal."
            )
        d["status"] = "resolved"
        d["decision"] = args.decision.strip()
        d["updated"] = today_iso()
        write_disputes(path, disputes)
    ledger_append(
        root,
        "dispute.resolve",
        who,
        d["id"],
        f"{d['decision'][:150]}" + (f" FORCED (unsigned): {args.force}" if args.force else ""),
    )
    print(f"teamwork: {d['id']} resolved by {who}: {d['decision']}")
    print(
        "teamwork: record this ruling in docs/Team/Decisions.md"
        " and notify both sides; it is binding."
    )
    return 0


def cmd_dispute_list(args) -> int:
    root = project_root(args)
    disputes = parse_disputes(disputes_path(root))
    if args.open:
        disputes = [d for d in disputes if d["status"] != "resolved"]
    if not disputes:
        print("teamwork: no disputes" + (" open" if args.open else ""))
        return 0
    print(f"# Disputes ({root})  max {MAX_ROUNDS} rounds, then CEO+CTO+CFO tribunal")
    print()
    for d in disputes:
        _print_dispute(d)
    return 0


def cmd_map(args) -> int:
    """Print the workspace map + where code/tests actually live in this repo."""
    root = project_root(args)
    project = project_of(root)
    reap_slots(root)
    limits = load_providers(root)
    print(f"# Team map  ({root})")
    slots_line = " · ".join(
        f"{prov} {len(used_slots(root, prov))}/{cap}"
        for prov, cap in sorted(limits.items())
        if prov != "default"
    )
    print(f"# concurrency slots: {slots_line}")
    print(f"# committed project docs: {docs_dir(root)}")
    print()
    print("project docs (committed, one owner each, no duplicates)")
    for filename, owner in DOCS.items():
        mark = "x" if (docs_dir(root) / filename).exists() else " "
        print(f"  [{mark}] {filename:20s} owner={owner}")
    print()
    print("shared")
    for rel in (f"{DIR_GLOBAL}/{F_GLOBAL}", f"{DIR_GLOBAL}/{F_GLOBAL_ARCHIVE}"):
        mark = "x" if (root / rel).exists() else " "
        print(f"  [{mark}] {rel}  (read-only except the CEO)")
    disputes = parse_disputes(disputes_path(root))
    open_d = [d for d in disputes if d["status"] != "resolved"]
    print(
        f"  [{'x' if disputes_path(root).exists() else ' '}] {F_DISPUTES}"
        f"  open={len(open_d)}"
        + (f"  escalated={sum(1 for d in open_d if d['escalated'])}" if open_d else "")
    )
    print()
    print("roles (shared memory + queue) and their instances (private scratch)")
    for role in list_roles(root):
        d = role_dir(root, role)
        open_tasks = [
            t
            for t in parse_tasks(d / F_TASKS)
            if t["status"] in ("todo", "doing", "blocked", "review", "selfcheck")
        ]
        s = len(parse_memory(d / F_SHORT))
        long_n = len(parse_memory(d / F_LONG))
        inst = instances_of(root, role)
        print(
            f"  {role:16s} open={len(open_tasks):2d} mem(short/long)={s}/{long_n}  "
            f"instances={len(inst)} [{', '.join(inst) or '-'}]"
        )
    print()
    print("repository layout detected")
    code = [d for d in CODE_DIRS if (project / d).is_dir()]
    tests = (
        [
            d
            for d in project.iterdir()
            if d.is_dir() and any(h in d.name.lower() for h in TEST_HINTS)
        ]
        if project.is_dir()
        else []
    )
    print(f"  code:  {', '.join(code) if code else '(none matched - inspect the repo)'}")
    print(
        f"  tests: {', '.join(sorted(p.name for p in tests)) if tests else '(none matched - inspect the repo)'}"
    )
    print("  rule:  code first, tests second, docs third; run dev/test/design in parallel.")
    return 0


# --------------------------------------------------------------------------- #
# AGENTS.md
# --------------------------------------------------------------------------- #

BEGIN = "<!-- BEGIN teamwork -->"
END = "<!-- END teamwork -->"


def cmd_agents_md(args) -> int:
    project = getattr(args, "project", None)
    base = Path(project).expanduser().resolve() if project else Path.cwd()
    target = base / "AGENTS.md"
    template = TEMPLATES_DIR / "AGENTS.md"
    if not template.exists():
        die(f"missing template {template}")
    block = template.read_text(encoding="utf-8").strip()
    # AGENTS.md is committed and may be published: substitute a portable command,
    # never a machine path (``portable_invocation``). ``self_invocation`` returns
    # an absolute path and is reserved for the private ``.pi/`` state.
    block = block.replace("<script>", _resources.portable_invocation())
    managed = f"{BEGIN}\n{block}\n{END}"
    if not target.exists():
        write_lf(target, managed + "\n")
        print(f"teamwork: created {target}")
        return 0
    text = target.read_text(encoding="utf-8")
    if BEGIN in text and END in text:
        pre = text.split(BEGIN)[0]
        post = text.split(END, 1)[1]
        write_lf(target, pre + managed + post)
        print(f"teamwork: updated teamwork section in {target}")
    else:
        write_lf(target, text.rstrip() + "\n\n" + managed + "\n")
        print(f"teamwork: appended teamwork section to {target}")
    return 0


def cmd_version(args) -> int:
    """`teamwork version` / `teamwork --version`."""
    print(f"teamwork {VERSION}")
    return 0


def cmd_selftest(args) -> int:
    """Offline, no-network smoke test of this installation.

    Used by CI and by `make verify`: it checks that the bundled skill assets
    resolve, that the core helpers behave, and that a workspace can be
    initialised and read back. It writes only inside a temporary directory.
    """
    import tempfile

    checks = []

    def check(label, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report, never traceback
            checks.append((label, False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append((label, True, "ok"))

    def _bundle():
        wanted = (
            "SKILL.md",
            "templates/AGENTS.md",
            "roles/developer.md",
            "references/Engineering.md",
        )
        missing = [name for name in wanted if not _resources.has_asset(name)]
        if missing:
            raise AssertionError("missing bundled asset(s): " + ", ".join(missing))

    def _helpers():
        if slugify("Hello, World!") != "hello-world":
            raise AssertionError(f"slugify -> {slugify('Hello, World!')!r}")
        if pascal("product-manager") != "ProductManager":
            raise AssertionError(f"pascal -> {pascal('product-manager')!r}")
        if not role_identity("developer")[1].endswith("@" + IDENTITY_DOMAIN):
            raise AssertionError("role_identity uses the wrong domain")
        prev = "0" * 64
        if _digest(prev, {"a": 1}) == _digest(prev, {"a": 2}):
            raise AssertionError("ledger digest ignores the record body")
        if pid_alive(os.getpid()) is not True:
            raise AssertionError("pid_alive(current process) should be True")

    check("bundled skill assets", _bundle)
    check("core helpers", _helpers)

    with tempfile.TemporaryDirectory(prefix="teamwork-selftest-") as tmp:
        project = Path(tmp) / "Sample Project"
        project.mkdir()
        team = "Selftest"

        def _workspace():
            ns = argparse.Namespace(
                project=str(project),
                team=team,
                agents="ceo,developer-1,reviewer-1",
                force=False,
                no_git=True,
            )
            if cmd_init(ns) != 0:
                raise AssertionError("init returned a non-zero exit code")
            root = project / TEAM_ROOT_DIR / TEAMS_SUBDIR / team
            for name in (
                "Roles/Developer/" + F_TASKS,
                F_CRITERIA,
                "Tests.md",
                "Global/" + F_GLOBAL,
            ):
                if not (root / name).exists():
                    raise AssertionError(f"init did not create {name}")

        check("workspace init", _workspace)

        def _task_roundtrip():
            root = project / TEAM_ROOT_DIR / TEAMS_SUBDIR / team
            path = task_file(root, "developer")
            tasks = parse_tasks(path) if path.exists() else []
            tasks.append(new_task("selftest task", priority="P0"))
            write_tasks(path, tasks, "developer")
            again = parse_tasks(path)
            if not again or again[-1]["title"] != "selftest task":
                raise AssertionError("task queue round-trip failed")

        check("task queue round-trip", _task_roundtrip)

        def _gate():
            root = project / TEAM_ROOT_DIR / TEAMS_SUBDIR / team
            report = gate_report(root)
            if "blockers" not in report or "sections" not in report:
                raise AssertionError("gate_report shape changed")
            if not report["blockers"]:
                raise AssertionError("an empty workspace should still block STOP")

        check("stop-condition gate", _gate)

    width = max(len(c[0]) for c in checks)
    for label, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label.ljust(width)}  {detail}")
    failed = [c for c in checks if not c[1]]
    print()
    print(f"teamwork selftest: {len(checks) - len(failed)}/{len(checks)} checks passed")
    print(f"  version:   {VERSION}")
    print(f"  python:    {sys.version.split()[0]} ({os.name})")
    print(f"  skill:     {SKILL_DIR}")
    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# Imaging: is a text-to-image / image-to-image model available, and which one?
#
# Policy: the Designer's charter (roles/designer.md), Visual assets section.
# The probe is deliberately OFFLINE: it reads environment variables and PATH
# only, never the network, so it cannot leak a prompt, cannot hang, and cannot
# claim a model that is not there.
# --------------------------------------------------------------------------- #

# Ranked best-first per provider (quality over speed and cost). "Best quality"
# means the first generally available model listed. Checked 2026-10-17; add a new
# provider with a source and a date before using it - an unknown provider is
# never assumed to be the best.
IMAGE_MODEL_RANKING = {
    "openai": ("gpt-image-1", "dall-e-3"),
    "google": (
        "imagen-4.0-ultra-generate-001",
        "imagen-4.0-generate-001",
        "gemini-2.5-flash-image",
    ),
    "black-forest-labs": ("flux-1.1-pro", "flux-1-dev", "flux-1-schnell"),
    "stability": ("stable-image-ultra", "sd3.5-large", "sd3.5-medium"),
    "replicate": (
        "black-forest-labs/flux-1.1-pro",
        "stability-ai/stable-diffusion-3.5-large",
    ),
    "local": ("qwen-image-2.1", "sdxl", "sd3.5-large"),
    "ollama-cloud": (),  # text/vision INPUT only as of 2026-10-17
}

# Ambient-credential detection order. A provider is only selected when it has a
# ranked image model, so holding an OpenAI key does not pretend to be a model.
IMAGE_PROVIDER_PRIORITY = (
    "openai",
    "google",
    "black-forest-labs",
    "stability",
    "replicate",
    "local",
    "ollama-cloud",
)

IMAGE_PROVIDER_CREDENTIALS = {
    "openai": ("OPENAI_API_KEY",),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "black-forest-labs": ("BFL_API_KEY", "BLACK_FOREST_LABS_API_KEY"),
    "stability": ("STABILITY_API_KEY",),
    "replicate": ("REPLICATE_API_TOKEN",),
    "ollama-cloud": ("OLLAMA_API_KEY",),
}

IMAGE_FALLBACK_HINT = (
    "no cloud image model detected: fall back to a local model, then to a "
    "hand-authored SVG (roles/designer.md, fallback ladder). Do not stall, and "
    "do not report an image that was never generated."
)


def detect_image_provider(env=None) -> str:
    """First provider in priority order that is configured and has a model."""
    env = os.environ if env is None else env
    for provider in IMAGE_PROVIDER_PRIORITY:
        if provider == "local":
            if shutil.which("qimg") or any(key.startswith("QIMG_") for key in env):
                return provider
            continue
        if not IMAGE_MODEL_RANKING.get(provider):
            continue
        if any(env.get(name) for name in IMAGE_PROVIDER_CREDENTIALS.get(provider, ())):
            return provider
    return ""


def resolve_image_model(env=None) -> dict:
    """Decide which image generator to use, without touching the network."""
    env = os.environ if env is None else env
    override = (env.get("TEAMWORK_IMAGE_MODEL") or "").strip()
    if override:
        provider = (env.get("TEAMWORK_IMAGE_PROVIDER") or "custom").strip() or "custom"
        return {
            "provider": provider,
            "model": override,
            "ranked": [],
            "source": "TEAMWORK_IMAGE_MODEL override",
            "fallback": "",
        }
    explicit = (env.get("TEAMWORK_IMAGE_PROVIDER") or "").strip()
    if explicit:
        ranked = list(IMAGE_MODEL_RANKING.get(explicit, ()))
        return {
            "provider": explicit,
            "model": ranked[0] if ranked else "",
            "ranked": ranked,
            "source": "TEAMWORK_IMAGE_PROVIDER",
            "fallback": "" if ranked else IMAGE_FALLBACK_HINT,
        }
    provider = detect_image_provider(env)
    ranked = list(IMAGE_MODEL_RANKING.get(provider, ()))
    return {
        "provider": provider,
        "model": ranked[0] if ranked else "",
        "ranked": ranked,
        "source": "ambient environment" if provider else "none detected",
        "fallback": "" if provider else IMAGE_FALLBACK_HINT,
    }


def cmd_imaging(args) -> int:
    """`teamwork imaging probe` - which image model, if any, is available."""
    import json

    decision = resolve_image_model()
    if getattr(args, "json", False):
        print(json.dumps({"command": "imaging.probe", **decision}, indent=2))
        return 0
    print("# imaging probe (offline: environment + PATH only)")
    print(f"  provider:  {decision['provider'] or '-'}")
    print(f"  model:     {decision['model'] or '-'}")
    print(f"  source:    {decision['source']}")
    if decision["ranked"]:
        print("  ranked:    " + " > ".join(decision["ranked"]))
    if decision["model"]:
        print("  supports:  text-to-image, image-to-image")
    else:
        print("  supports:  none")
    if decision["fallback"]:
        print(f"  fallback:  {decision['fallback']}")
    print(
        "  policy:    roles/designer.md (plan, 4+ candidates, visual review,"
        " improvement, privacy and licence red lines)"
    )
    return 0


# --------------------------------------------------------------------------- #
# Per-agent model configuration
#
# The team is a skill, not an application: every agent runs through its own LLM
# API, and the model is a property of the AGENT, not of the project. A role may
# have a default and an instance may override it, so a cheap model can drive the
# mechanical lanes while a strong one drives the Reviewer.
# --------------------------------------------------------------------------- #


def load_model_config(root: Path) -> dict:
    """Return ``{"roles": {...}, "agents": {...}}`` from Settings.json."""
    path = providers_path(root)
    data = {}
    if path.exists():
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    models = data.get("Models") if isinstance(data, dict) else None
    if not isinstance(models, dict):
        models = {}
    return {
        "roles": dict(models.get("roles") or {}),
        "agents": dict(models.get("agents") or {}),
    }


def save_model_config(root: Path, config: dict) -> None:
    """Persist the model map without disturbing the provider caps or the pulse."""
    import json

    path = providers_path(root)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data["Models"] = {"roles": config["roles"], "agents": config["agents"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    write_lf(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def resolved_model(root: Path, agent: str) -> dict:
    """The model the given instance should use: agent override, else role default."""
    config = load_model_config(root)
    if agent in config["agents"]:
        return dict(config["agents"][agent], source="agent")
    role = resolve_role(agent) if agent else ""
    if role and role in config["roles"]:
        return dict(config["roles"][role], source="role")
    return {"provider": "", "model": "", "source": "unset"}


# --------------------------------------------------------------------------- #
# Automatic model routing: best quality per lane at the lowest cost
#
# The skill ships no model ids. It reads the runtime environment - which agent
# host is running and which models that host already exposes - and routes the
# STRONG model to the lanes where a mistake is expensive and the ECONOMY model to
# the mechanical lanes. Nothing is invented: a lane with no available model is
# reported as `unset` with the exact variable to set.
# --------------------------------------------------------------------------- #

AGENT_HOSTS = {
    "pi": ("PI_SESSION_ID", "PI_PROVIDER", "PI_MODEL"),
    "claude": ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "ANTHROPIC_MODEL"),
    "opencode": ("OPENCODE_CONFIG", "OPENCODE_MODEL", "OPENCODE_SESSION"),
    "codex": ("CODEX_HOME", "CODEX_MODEL", "OPENAI_MODEL"),
    "cursor": ("CURSOR_TRACE_ID", "CURSOR_MODEL"),
    "gemini": ("GEMINI_CLI", "GEMINI_MODEL"),
    "unknown": (),
}

#: Lanes where a wrong answer is expensive get the strongest model available;
#: everything else runs on the economy tier. One entry per role id.
LANE_TIER = {
    "reviewer": "strong",
    "architect": "strong",
    "security-auditor": "strong",
    "ceo": "strong",
    "cto": "strong",
    "developer": "economy",
    "tester": "economy",
    "technical-writer": "economy",
    "designer": "economy",
    "release-engineer": "economy",
    "project-manager": "economy",
    "product-manager": "economy",
    "coo": "economy",
    "cfo": "economy",
    "data-engineer": "economy",
}


def detect_agent_host(env=None) -> str:
    """Which agent host is running us, from the environment it exports.

    ``TEAMWORK_AGENT_HOST`` wins when set: detection is inference, and an explicit
    override is how you make it deterministic (CI, a wrapper script, or a host
    whose markers are ambiguous).
    """
    env = os.environ if env is None else env
    override = (env.get("TEAMWORK_AGENT_HOST") or "").strip().lower()
    if override:
        return override
    for host, markers in AGENT_HOSTS.items():
        if any(env.get(marker) for marker in markers):
            return host
    return "unknown"


def host_default_model(env=None) -> str:
    """The model the host is already configured with, if it advertises one."""
    env = os.environ if env is None else env
    for var in (
        "TEAMWORK_MODEL_STRONG",
        "ANTHROPIC_MODEL",
        "PI_MODEL",
        "OPENCODE_MODEL",
        "CODEX_MODEL",
        "CURSOR_MODEL",
        "GEMINI_MODEL",
        "OPENAI_MODEL",
    ):
        value = (env.get(var) or "").strip()
        if value:
            return value
    return ""


def resolve_model_plan(root: Path, env=None) -> dict:
    """Route every staffed role to a model: strong lanes first, cost last."""
    env = os.environ if env is None else env
    host = detect_agent_host(env)
    strong = (env.get("TEAMWORK_MODEL_STRONG") or "").strip() or host_default_model(env)
    economy = (env.get("TEAMWORK_MODEL_ECONOMY") or "").strip() or (
        env.get("TEAMWORK_MODEL_STRONG") or ""
    ).strip()
    provider = (env.get("TEAMWORK_MODEL_PROVIDER") or "").strip() or (
        env.get("PI_PROVIDER") or ""
    ).strip()
    assignments, missing = {}, []
    for role in sorted(list_roles(root)):
        tier = LANE_TIER.get(role, "economy")
        model = strong if tier == "strong" else (economy or strong)
        if not model:
            missing.append(role)
            continue
        assignments[role] = {"provider": provider, "model": model, "tier": tier}
    notes = [f"host: {host}"]
    if missing:
        notes.append(
            "no model found in the environment for: "
            + ", ".join(missing)
            + " - set TEAMWORK_MODEL_STRONG (and optionally "
            "TEAMWORK_MODEL_ECONOMY), or use `model set`"
        )
    else:
        notes.append("every lane routed: strong -> decision lanes, economy -> mechanical lanes")
    return {
        "host": host,
        "provider": provider,
        "strong": strong,
        "economy": economy or strong,
        "assignments": assignments,
        "notes": notes,
    }


def cmd_model_auto(args) -> int:
    """`teamwork model auto [--apply] [--json]` - cost-aware automatic routing."""
    import json

    root = project_root(args)
    plan = resolve_model_plan(root)
    if getattr(args, "json", False):
        print(json.dumps({"command": "model.auto", **plan}, indent=2, sort_keys=True))
    else:
        print(f"# model auto (host: {plan['host']})")
        for role, entry in sorted(plan["assignments"].items()):
            print(f"- {role:18s} {entry['tier']:8s} {entry['model']}")
        for note in plan["notes"]:
            print(f"# {note}")
    if not getattr(args, "apply", False):
        if not getattr(args, "json", False):
            print("# dry run: rerun with --apply to write these into Settings.json")
        return 0
    if not plan["assignments"]:
        die("nothing to apply: no model found in the environment")
    config = load_model_config(root)
    for role, entry in plan["assignments"].items():
        config["roles"][role] = {"provider": entry["provider"], "model": entry["model"]}
    save_model_config(root, config)
    ledger_append(
        root,
        "model.auto",
        plan["host"],
        f"{len(plan['assignments'])} lanes",
        f"strong={plan['strong'] or '-'} economy={plan['economy'] or '-'}",
    )
    print(f"# applied to {len(plan['assignments'])} lanes")
    return 0


def cmd_model(args) -> int:
    """`teamwork model set|get|list` - configure the LLM of each agent."""
    root = project_root(args)
    config = load_model_config(root)
    if args.model_cmd == "auto":
        return cmd_model_auto(args)
    if args.model_cmd == "set":
        provider = (args.provider or "").strip()
        model = (args.model or "").strip()
        if not provider and not model:
            die("give at least --provider or --model")
        entry = {"provider": one_line(provider), "model": one_line(model)}
        wanted = pascal(args.agent)
        instance = next(
            (i for i in known_instances(root) if pascal(i) == wanted),
            "",
        )
        if instance:
            target, key = config["agents"], instance
        else:
            target, key = config["roles"], resolve_role(args.agent)
        if not key:
            die("name an agent or a role (e.g. reviewer-1, reviewer)")
        target[key] = entry
        save_model_config(root, config)
        print(f"# model for {key}: provider={provider or '-'} model={model or '-'}")
        ledger_append(
            root, "model.set", key, provider or model, f"{provider or '-'}/{model or '-'}"
        )
        return 0
    if args.model_cmd == "get":
        decision = resolved_model(root, args.agent)
        print(
            f"# {args.agent}: provider={decision['provider'] or '-'} "
            f"model={decision['model'] or '-'} ({decision['source']})"
        )
        return 0
    rows = [(a, resolved_model(root, a)) for a in known_instances(root)]
    for agent, d in sorted(rows):
        print(
            f"- {agent:22s} provider={d['provider'] or '-':14s} "
            f"model={d['model'] or '-':22s} ({d['source']})"
        )
    if not rows:
        print("- no agents yet")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    # `--project` is accepted both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--project", default=argparse.SUPPRESS, help="project directory (default: cwd)"
    )
    common.add_argument(
        "--team", default=argparse.SUPPRESS, help="team name (default: the project directory name)"
    )
    p = argparse.ArgumentParser(
        prog="teamwork.py",
        description="Workspace and memory manager for the /teamwork skill.",
        parents=[common],
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"teamwork {VERSION}",
        help="print the version and exit",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    _parsers_workspace(sub, common)
    _parsers_memory(sub, common)
    _parsers_task(sub, common)
    _parsers_quality(sub, common)
    _parsers_integration(sub, common)
    _parsers_governance(sub, common)
    _parsers_audit(sub, common)
    _parsers_scheduling(sub, common)
    _parsers_meta(sub, common)
    _parsers_model(sub, common)
    return p


def _parsers_workspace(sub, common) -> None:
    """`workspace` command surface."""

    s = sub.add_parser("init", parents=[common], help="create the team workspace and memory files")
    s.add_argument(
        "--agents",
        default="",
        help="comma-separated agent instance names, e.g. "
        "ceo,cto,coo,cfo,architect,product-manager,project-manager,"
        "designer-1,developer-1,tester-1",
    )
    s.add_argument("--force", action="store_true", help="overwrite existing files")
    s.add_argument("--no-git", action="store_true", help="do not create/check the git repository")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser(
        "consolidate",
        parents=[common],
        help="promote stale short-term entries, evict long-term overflow",
    )
    s.add_argument("--agent")
    s.add_argument("--all", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_consolidate)

    s = sub.add_parser("stats", parents=[common], help="memory sizes and cap violations")
    s.add_argument("--agent")
    s.add_argument("--all", action="store_true")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("agents", parents=[common], help="list agent directories")
    s.set_defaults(func=cmd_agents)

    # --- tasks ----------------------------------------------------------- #
    st = sub.add_parser("task", parents=[common], help="manage an agent's priority task list")
    tsub = st.add_subparsers(dest="task_cmd", required=True)

    s = tsub.add_parser("add", parents=[common], help="add a task to the ROLE's shared queue")
    s.add_argument("agent", help="role or instance; a role adds unclaimed work")
    s.add_argument("title")
    s.add_argument("--priority", default="P2", choices=list(PRIORITY_ORDER))
    s.add_argument(
        "--status",
        default="todo",
        choices=["todo", "doing", "blocked"],
        help="new tasks cannot start as review/done: the gates own those",
    )
    s.add_argument("--deps", default="", help="comma list; cross-role as role:T-0001")
    s.add_argument("--shared", default="", help="shared board / issue / PR reference")
    s.add_argument("--tags", default="")
    s.add_argument("--body", default="", help="acceptance criteria / notes")
    s.add_argument("--evidence", default="")
    s.add_argument(
        "--claimed-by",
        default="",
        dest="claimed_by",
        help="assign to a specific instance (default: role pool)",
    )
    s.add_argument(
        "--no-review",
        action="store_true",
        help="mark as a chore that does not need Reviewer sign-off",
    )
    s.set_defaults(func=cmd_task_add)

    s = tsub.add_parser("list", parents=[common], help="list tasks, priority ordered")
    s.add_argument("agent", nargs="?", default="")
    s.add_argument("--all", action="store_true")
    s.add_argument("--status", choices=list(STATUSES))
    s.set_defaults(func=cmd_task_list)

    s = tsub.add_parser(
        "next", parents=[common], help="claim the highest-priority executable task of the role"
    )
    s.add_argument("agent")
    s.add_argument("--peek", action="store_true", help="do not claim it")
    s.set_defaults(func=cmd_task_next)

    s = tsub.add_parser("set", parents=[common], help="update status / priority / deps")
    s.add_argument("agent")
    s.add_argument("handle", help="T-0002, exact title, or substring")
    s.add_argument(
        "--claimed-by", default=None, dest="claimed_by", help="which instance is working on it"
    )
    s.add_argument("--status", choices=list(STATUSES))
    s.add_argument("--priority", choices=list(PRIORITY_ORDER))
    s.add_argument("--deps", default=None)
    s.add_argument("--title", default=None)
    s.add_argument(
        "--evidence", default=None, help="command + revision + observed result, or artifact path"
    )
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="override evidence/self-check/review gates; a reason is "
        "required and is recorded and audited",
    )
    s.set_defaults(func=cmd_task_set)

    s = tsub.add_parser(
        "reclaim", parents=[common], help="take back a task whose owner went silent"
    )
    s.add_argument("agent", help="role or instance, identifies the queue")
    s.add_argument("handle")
    s.add_argument("--as", dest="by", required=True, help="instance taking it over")
    s.add_argument("--reason", required=True)
    s.set_defaults(func=cmd_task_reclaim)

    s = tsub.add_parser("rm", parents=[common], help="remove a task (own role only)")
    s.add_argument("agent")
    s.add_argument("handle")
    s.add_argument("--by", required=True)
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_task_rm)

    s = sub.add_parser(
        "board", parents=[common], help="cross-agent board with counts and next task"
    )
    s.set_defaults(func=cmd_board)

    s = sub.add_parser(
        "parallel", parents=[common], help="free slots, ready work, and how many lanes to start"
    )
    s.set_defaults(func=cmd_parallel)

    s = sub.add_parser("map", parents=[common], help="print the workspace map and repo layout")
    s.set_defaults(func=cmd_map)

    # --- disputes -------------------------------------------------------- #
    sd = sub.add_parser(
        "dispute", parents=[common], help="challenge a design/decision with counter-evidence"
    )
    dsub = sd.add_subparsers(dest="dispute_cmd", required=True)

    s = dsub.add_parser("open", parents=[common], help="raise a dispute")
    s.add_argument("--by", required=True)
    s.add_argument("--against", required=True)
    s.add_argument("--topic", required=True)
    s.add_argument("--evidence", default="", help="data / command / measurement")
    s.add_argument("--position", default="", help="what you claim and why")
    s.add_argument("--task", default="")
    s.set_defaults(func=cmd_dispute_open)

    s = dsub.add_parser(
        "round", parents=[common], help="add a rebuttal round (capped, then tribunal)"
    )
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--message", required=True)
    s.set_defaults(func=cmd_dispute_round)

    s = dsub.add_parser(
        "escalate", parents=[common], help="send an unresolved dispute to CEO+CTO+CFO"
    )
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.set_defaults(func=cmd_dispute_escalate)

    s = dsub.add_parser("sign", parents=[common], help="tribunal member signs the ruling")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.set_defaults(func=cmd_dispute_sign)

    s = dsub.add_parser("resolve", parents=[common], help="record the binding ruling")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--decision", required=True)
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="override the tribunal signature requirement; reason required",
    )
    s.set_defaults(func=cmd_dispute_resolve)

    s = dsub.add_parser("list", parents=[common], help="list disputes")
    s.add_argument("--open", action="store_true")
    s.set_defaults(func=cmd_dispute_list)

    s = sub.add_parser(
        "repo", parents=[common], help="ensure a git repository exists and report status"
    )
    s.add_argument("--no-commit", action="store_true", help="do not create the initial commit")
    s.set_defaults(func=cmd_repo)

    s = sub.add_parser(
        "clean", parents=[common], help="remove scratch/temp files (never tracked files)"
    )
    s.add_argument(
        "--all", action="store_true", help="empty scratch/ entirely, not just temp patterns"
    )
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_clean)

    s = sub.add_parser(
        "agents-md", parents=[common], help="create/update the managed teamwork block in AGENTS.md"
    )
    s.set_defaults(func=cmd_agents_md)


def _parsers_memory(sub, common) -> None:
    """`memory` command surface."""
    s = sub.add_parser(
        "load", parents=[common], help="print the ROLE's short-term memory (startup context)"
    )
    s.add_argument("agent", help="role or instance name (memory is per role)")
    s.add_argument("--limit", type=int, default=0)
    s.set_defaults(func=cmd_load)

    s = sub.add_parser(
        "remember", parents=[common], help="add/update an entry in the ROLE's shared memory"
    )
    s.add_argument("agent", help="role or instance name (memory is per role)")
    s.add_argument("--by", default="", help="who records it (instance)")
    s.add_argument("--src", default="", help="what it comes from (task, doc, run)")
    s.add_argument("--rev", default="", help="revision it was verified at")
    s.add_argument("text")
    s.add_argument("--layer", choices=["short", "long"], default="short")
    s.add_argument("--key", default="")
    s.add_argument("--importance", type=int, default=2)
    s.add_argument("--tags", default="")
    s.add_argument("--pin", action="store_true")
    s.set_defaults(func=cmd_remember)

    s = sub.add_parser(
        "global", parents=[common], help="add/update an entry in global shared memory"
    )
    s.add_argument("text")
    s.add_argument("--key", default="")
    s.add_argument("--importance", type=int, default=3)
    s.add_argument("--tags", default="")
    s.add_argument("--pin", action="store_true")
    s.set_defaults(func=cmd_global)

    s = sub.add_parser("recall", parents=[common], help="search memory")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--agent")
    s.add_argument("--all", action="store_true", help="every agent + global")
    s.add_argument("--global", dest="global_", action="store_true")
    s.add_argument("--layer", choices=["both", "short", "long"], default="both")
    s.set_defaults(func=cmd_recall)

    s = sub.add_parser("touch", parents=[common], help="mark an entry as used")
    s.add_argument("agent")
    s.add_argument("handle", help="M-0003 or key or substring")
    s.add_argument("--layer", choices=["short", "long"], default="short")
    s.set_defaults(func=cmd_touch)

    s = sub.add_parser("forget", parents=[common], help="delete an entry")
    s.add_argument("agent")
    s.add_argument("handle")
    s.add_argument("--layer", choices=["short", "long"], default="short")
    s.set_defaults(func=cmd_forget)


def _parsers_task(sub, common) -> None:
    """`task` command surface."""


def _parsers_quality(sub, common) -> None:
    """`quality` command surface."""
    s = sub.add_parser(
        "review", parents=[common], help="Reviewer: independent second review of a deliverable"
    )
    s.add_argument("agent", nargs="?", help="owner of the deliverable")
    s.add_argument("handle", nargs="?", help="T-0002, title or substring")
    s.add_argument("--queue", action="store_true", help="list everything awaiting review")
    s.add_argument("--by", default="reviewer")
    s.add_argument("--result", choices=["pass", "fail"])
    s.add_argument("--evidence", default="", help="verification command @rev -> result")
    s.add_argument("--findings", default="", help="what is wrong, with evidence")
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="override the review gates; reason required and recorded",
    )
    s.set_defaults(func=cmd_review)

    s = sub.add_parser(
        "selfcheck",
        parents=[common],
        help="author's own review + test before submitting for review",
    )
    s.add_argument("agent")
    s.add_argument("handle")
    s.add_argument("--by", default="")
    s.add_argument("--result", choices=["pass", "fail"], default="pass")
    s.add_argument("--note", default="", help="what you re-read and why it is sound")
    s.add_argument("--test", default="", help="self-test command @rev -> observed result")
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="override the self-check ownership rule; reason required",
    )
    s.set_defaults(func=cmd_selfcheck)

    s = sub.add_parser(
        "archive", parents=[common], help="show the reviewed-result archive (evidence ledger)"
    )
    s.add_argument("--agent")
    s.set_defaults(func=cmd_archive)

    s = sub.add_parser(
        "criteria", parents=[common], help="acceptance criteria as records (the STOP condition)"
    )
    csub = s.add_subparsers(dest="criteria_cmd", required=True)
    s = csub.add_parser("add", parents=[common], help="add a criterion")
    s.add_argument("--id", required=True, help="AC-1, AC-login, ...")
    s.add_argument("--text", required=True, help="verifiable statement")
    s.add_argument("--owner", required=True, help="role/instance accountable for it")
    s.add_argument("--by", required=True, help="who records it (provenance)")
    s.set_defaults(func=cmd_criteria)
    s = csub.add_parser("verify", parents=[common], help="mark verified with independent evidence")
    s.add_argument("id")
    s.add_argument("--by", required=True, help="verifier (not the owner)")
    s.add_argument(
        "--evidence", default="", help="'<cmd> @<rev> -> <result>', or omit when using --test"
    )
    s.add_argument(
        "--test", default="", help="TS-id of a passing test record that verifies this criterion"
    )
    s.add_argument("--rev", default="")
    s.set_defaults(func=cmd_criteria)
    s = csub.add_parser("reopen", parents=[common], help="clear a verification")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--reason", default="")
    s.set_defaults(func=cmd_criteria)
    s = csub.add_parser("rm", parents=[common], help="remove a criterion (CEO only)")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_criteria)
    s = csub.add_parser("list", parents=[common], help="show criteria and status")
    s.set_defaults(func=cmd_criteria)

    s = sub.add_parser(
        "tests", parents=[common], help="layered tests, each owned and run by its own role"
    )
    tsub2 = s.add_subparsers(dest="tests_cmd", required=True)
    s = tsub2.add_parser("add", parents=[common], help="declare a layer for an area")
    s.add_argument("--layer", required=True, choices=list(TEST_LAYERS))
    s.add_argument("--area", default="")
    s.add_argument("--owner", default="")
    s.add_argument("--task", default="")
    s.add_argument("--command", default="")
    s.add_argument("--no-owner-check", action="store_true")
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="declare another role's layer; reason required",
    )
    s.set_defaults(func=cmd_tests)
    s = tsub2.add_parser("run", parents=[common], help="record a layer run")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--result", choices=["pass", "fail"], required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--rev", default="")
    s.add_argument("--command", default="")
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_tests)
    s = tsub2.add_parser(
        "require", parents=[common], help="declare which layers an area must cover"
    )
    s.add_argument("--area", required=True)
    s.add_argument("--layers", required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--reason", default="")
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_tests)
    s = tsub2.add_parser("rm", parents=[common], help="remove a test record")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_tests)
    s = tsub2.add_parser("plan", parents=[common], help="coverage matrix and gaps")
    s.set_defaults(func=cmd_tests)
    s = tsub2.add_parser("list", parents=[common], help="list test records")
    s.add_argument("--layer", default="")
    s.set_defaults(func=cmd_tests)


def _parsers_integration(sub, common) -> None:
    """`integration` command surface."""
    s = sub.add_parser(
        "branch", parents=[common], help="work on your own branch; main only receives merges"
    )
    bsub = s.add_subparsers(dest="branch_cmd", required=True)
    s = bsub.add_parser("start", parents=[common], help="create/switch to the task branch")
    s.add_argument("--agent", required=True)
    s.add_argument("--task", required=True)
    s.add_argument("--base", default="")
    s.add_argument("--worktree", action="store_true")
    s.set_defaults(func=cmd_branch)
    s = bsub.add_parser("list", parents=[common], help="branches with PR/merge state")
    s.set_defaults(func=cmd_branch)

    s = sub.add_parser("pr", parents=[common], help="open/list/merge pull requests")
    psub = s.add_subparsers(dest="pr_cmd", required=True)
    s = psub.add_parser("open", parents=[common], help="submit a PR to the Reviewer")
    s.add_argument("--agent", required=True)
    s.add_argument("--task", required=True)
    s.add_argument("--title", default="")
    s.add_argument("--summary", default="")
    s.add_argument("--base", default="")
    s.add_argument("--push", action="store_true", help="push the branch if a remote exists")
    s.set_defaults(func=cmd_pr)
    s = psub.add_parser("list", parents=[common], help="the Reviewer's PR inbox")
    s.add_argument("--open", action="store_true")
    s.set_defaults(func=cmd_pr)
    s = psub.add_parser("merge", parents=[common], help="Reviewer: merge an approved PR")
    s.add_argument("--pr", required=True)
    s.add_argument("--by", default="reviewer")
    s.add_argument("--squash", action="store_true")
    s.add_argument(
        "--keep-branch",
        action="store_true",
        help="keep the branch after merging (default: it is deleted)",
    )
    s.add_argument(
        "--delete-branch",
        action="store_true",
        help="delete the merged branch (this is the default)",
    )
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="emergency override of the review gate; reason required",
    )
    s.set_defaults(func=cmd_pr)

    s = sub.add_parser(
        "identity",
        parents=[common],
        help="role commit identity, e.g. Developer <developer@agents.nidvue.com>",
    )
    s.add_argument("--role", default="")
    s.add_argument(
        "--audit",
        action="store_true",
        help="fail when a commit is not authored and committed by the acting role",
    )
    s.add_argument(
        "--range",
        dest="rev_range",
        default="",
        metavar="REV..REV",
        help="revision range for --audit (default: origin/main..HEAD)",
    )
    s.add_argument(
        "--strict-authors",
        action="store_true",
        help="also fail commits authored outside the team identity domain",
    )
    s.set_defaults(func=cmd_identity)

    s = sub.add_parser(
        "commit", parents=[common], help="commit a change-set with the fixed style + role identity"
    )
    s.add_argument("--role", default="developer")
    s.add_argument("--type", default="chore", choices=list(COMMIT_TYPES))
    s.add_argument("--area", default="")
    s.add_argument("--task", default="")
    s.add_argument("--producers", default="")
    s.add_argument("--goal", default="")
    s.add_argument("--deliverable", default="")
    s.add_argument("--why", default="")
    s.add_argument("--status", default="")
    s.add_argument("--result", default="")
    s.add_argument("--docs", default="")
    s.add_argument("--refs", default="")
    s.add_argument("--paths", default="", help="comma-separated paths to stage")
    s.add_argument("--all", action="store_true", help="stage every change")
    s.add_argument(
        "--allow-main",
        action="store_true",
        help="override the main-branch protection (rare, explain why)",
    )
    s.add_argument("--dry-run", action="store_true")
    s.add_argument(
        "--no-check-lfs",
        action="store_false",
        dest="check_lfs",
        help="skip the large-file LFS check (default: it is enforced)",
    )
    s.add_argument(
        "--lfs-threshold",
        type=int,
        default=1_000_000,
        help="bytes above which a file must be LFS-tracked",
    )
    s.set_defaults(func=cmd_commit)


def _parsers_governance(sub, common) -> None:
    """`governance` command surface."""
    s = sub.add_parser(
        "decision", parents=[common], help="record a decision with provenance and evidence"
    )
    dsub = s.add_subparsers(dest="decision_cmd", required=True)
    s = dsub.add_parser("add", parents=[common], help="append a decision to docs/Team/Decisions.md")
    s.add_argument("--by", required=True)
    s.add_argument(
        "--kind",
        default="technical",
        choices=["technical", "governance", "redline", "tribunal", "scope", "cost", "process"],
    )
    s.add_argument("--title", default="")
    s.add_argument("--decision", required=True)
    s.add_argument("--why", default="")
    s.add_argument("--evidence", default="")
    s.add_argument("--context", default="")
    s.add_argument("--options", default="")
    s.add_argument("--falsify", default="")
    s.add_argument("--consequences", default="")
    s.add_argument("--task", default="")
    s.add_argument("--rev", default="")
    s.add_argument(
        "--status", default="accepted", choices=["proposed", "accepted", "superseded", "rejected"]
    )
    s.add_argument(
        "--force",
        default="",
        metavar="REASON",
        help="record a governance decision from another role",
    )
    s.set_defaults(func=cmd_decision)
    s = dsub.add_parser("list", parents=[common], help="list recorded decisions")
    s.add_argument("--kind", default="")
    s.set_defaults(func=cmd_decision_list)

    s = sub.add_parser(
        "skill", parents=[common], help="create/share a reusable team skill with same-role peers"
    )
    ssub = s.add_subparsers(dest="skill_cmd", required=True)
    s = ssub.add_parser("create", parents=[common], help="extract a repeated flow")
    s.add_argument("--name", required=True, help="kebab-case name")
    s.add_argument("--role", default="", help="owning role (default: yours)")
    s.add_argument("--for", dest="description", required=True, help="when to use this skill")
    s.add_argument("--by", required=True)
    s.add_argument("--body", default="")
    s.add_argument("--body-file", default="")
    s.add_argument("--force", action="store_true")
    s.add_argument(
        "--allow-main", action="store_true", help="override the branch guard (rare, explain why)"
    )
    s.set_defaults(func=cmd_skill)
    s = ssub.add_parser("share", parents=[common], help="notify same-role peers so they reuse it")
    s.add_argument("name")
    s.add_argument("--by", required=True)
    s.add_argument("--to", default="", help="comma roles; default the owner role")
    s.set_defaults(func=cmd_skill)
    s = ssub.add_parser(
        "candidates", parents=[common], help="find flows worth extracting (repeated per role/area)"
    )
    s.add_argument("--min-tasks", type=int, default=3)
    s.set_defaults(func=cmd_skill)
    s = ssub.add_parser("rm", parents=[common], help="unregister a skill")
    s.add_argument("name")
    s.add_argument("--by", required=True)
    s.set_defaults(func=cmd_skill)
    s = ssub.add_parser("list", parents=[common], help="list team skills")
    s.set_defaults(func=cmd_skill)

    s = sub.add_parser(
        "redline",
        parents=[common],
        help="record a refused red-line action (never crossed silently)",
    )
    rsub = s.add_subparsers(dest="redline_cmd", required=True)
    s = rsub.add_parser("record", parents=[common], help="record a refusal")
    s.add_argument("--by", required=True)
    s.add_argument("--action", required=True)
    s.add_argument("--why", required=True)
    s.add_argument("--alternative", default="")
    s.add_argument("--authorized", default="")
    s.set_defaults(func=cmd_redline)
    s = rsub.add_parser("close", parents=[common], help="close a resolved red line")
    s.add_argument("id")
    s.add_argument("--by", required=True)
    s.add_argument("--reason", default="")
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_redline)


def _parsers_audit(sub, common) -> None:
    """`audit` command surface."""
    s = sub.add_parser(
        "links", parents=[common], help="check markdown cross-links, URLs and back-links"
    )
    s.add_argument(
        "--no-reciprocity", action="store_true", help="skip the bidirectional back-link requirement"
    )
    s.set_defaults(func=cmd_links)

    s = sub.add_parser(
        "audit", parents=[common], help="find fabricated completions, stale work, duplicates"
    )
    s.add_argument("--stale-days", type=int, default=2)
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("ledger", parents=[common], help="append-only audit trail (hash-chained)")
    lsub = s.add_subparsers(dest="ledger_cmd", required=True)
    s = lsub.add_parser("show", parents=[common], help="inspect the trail")
    s.add_argument("--tail", type=int, default=40)
    s.add_argument("--action", default="")
    s.add_argument("--actor", default="")
    s.add_argument("--target", default="")
    s.set_defaults(func=cmd_ledger)
    s = lsub.add_parser("verify", parents=[common], help="recompute the hash chain")
    s.add_argument(
        "--reconcile", action="store_true", help="repair a head cache left behind by a crash"
    )
    s.set_defaults(func=cmd_ledger)
    s = lsub.add_parser("repair", parents=[common], help="drop a torn tail and record the repair")
    s.add_argument("--by", required=True)
    s.add_argument("--reason", required=True)
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_ledger)
    s = lsub.add_parser(
        "export", parents=[common], help="write an externally verifiable audit manifest"
    )
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--by", default="", help="who exports it (provenance)")
    s.set_defaults(func=cmd_ledger)

    s = sub.add_parser(
        "trace", parents=[common], help="follow one task/criterion/test/PR through every record"
    )
    s.add_argument("handle")
    s.set_defaults(func=cmd_trace)


def _parsers_scheduling(sub, common) -> None:
    """`scheduling` command surface."""
    s = sub.add_parser("loop", parents=[common], help="stop-condition check: may the team stop?")
    s.set_defaults(func=cmd_loop)

    s = sub.add_parser("slot", parents=[common], help="reserve/release a provider concurrency slot")
    ssub = s.add_subparsers(dest="slot_cmd", required=True)
    s = ssub.add_parser(
        "acquire", parents=[common], help="take a slot (blocks until free or --wait)"
    )
    s.add_argument("--agent", required=True)
    s.add_argument("--provider", default="")
    s.add_argument("--task", default="")
    s.add_argument("--wait", type=int, default=0, help="seconds to wait for a free slot")
    s.set_defaults(func=cmd_slot)
    s = ssub.add_parser("release", parents=[common], help="give a slot back")
    s.add_argument("--agent", required=True)
    s.add_argument("--provider", default="")
    s.add_argument("--by", default="", help="who releases it (holder or CEO)")
    s.add_argument("--force", default="", metavar="REASON")
    s.set_defaults(func=cmd_slot)
    s = ssub.add_parser("list", parents=[common], help="slots per provider")
    s.add_argument("--provider", default="")
    s.set_defaults(func=cmd_slot)
    s = ssub.add_parser("renew", parents=[common], help="extend the lease while still working")
    s.add_argument("--agent", required=True)
    s.add_argument("--provider", default="")
    s.set_defaults(func=cmd_slot)

    s = ssub.add_parser("reap", parents=[common], help="drop dead/stale slots")
    s.add_argument("--provider", default="")
    s.set_defaults(func=cmd_slot)

    s = sub.add_parser(
        "pulse", parents=[common], help="CEO wake-up: idle lanes + ready work + dispatch plan"
    )
    s.add_argument("--commit", action="store_true", help="assign the plan to the idle lanes now")
    s.add_argument("--interval", type=int, default=None, help="store the pulse interval in minutes")
    s.set_defaults(func=cmd_pulse)


def _parsers_model(sub, common) -> None:
    """`model` command surface - the LLM each agent runs on."""
    s = sub.add_parser(
        "model",
        parents=[common],
        help="configure the LLM model of each agent (per role or instance)",
    )
    msub = s.add_subparsers(dest="model_cmd", required=True)
    p = msub.add_parser("set", parents=[common], help="set a role or instance model")
    p.add_argument("agent")
    p.add_argument("--provider", default="")
    p.add_argument("--model", default="")
    p.set_defaults(func=cmd_model)
    p = msub.add_parser("get", parents=[common], help="show the effective model")
    p.add_argument("agent")
    p.set_defaults(func=cmd_model)
    p = msub.add_parser("list", parents=[common], help="every agent and its model")
    p.set_defaults(func=cmd_model)
    p = msub.add_parser(
        "auto", parents=[common], help="route every lane to the best model the environment offers"
    )
    p.add_argument(
        "--apply", action="store_true", help="write the plan into Settings.json (default: dry run)"
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_model)


def _parsers_meta(sub, common) -> None:
    """`version`, `selftest` and `imaging` command surface."""
    s = sub.add_parser("version", parents=[common], help="print the version and exit")
    s.set_defaults(func=cmd_version)

    s = sub.add_parser(
        "selftest", parents=[common], help="offline smoke test of the install (no network)"
    )
    s.set_defaults(func=cmd_selftest)

    s = sub.add_parser(
        "imaging",
        parents=[common],
        help="image-generation capability: which text-to-image / image-to-image model is available",
    )
    isub = s.add_subparsers(dest="imaging_cmd", required=True)
    p = isub.add_parser(
        "probe", parents=[common], help="offline probe of the best available image model"
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_imaging)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SystemExit:
        raise
    except (OSError, ValueError, KeyError, IndexError) as exc:
        # Malformed workspace state must produce one actionable line, never a
        # traceback that hides the real gate state.
        print(
            f"teamwork: {type(exc).__name__}: {exc}. "
            "Inspect the workspace with `teamwork audit` and `teamwork ledger verify`.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
