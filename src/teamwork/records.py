"""The plain-markdown record layer: parse, render and find records.

The files are the trust boundary for every evidence gate, so parsing stops at
the body boundary and every scalar is written on one line.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .config import (
    ALL_LAYERS_SENTINEL,
    DEFAULT_BASE,
    DEFAULT_REQUIRED_LAYERS,
    F_GLOBAL,
    F_GLOBAL_ARCHIVE,
    F_LONG,
    F_MEM_ARCHIVE,
    F_SHORT,
    F_TASKS,
    LONG_CAP,
    MAX_ROUNDS,
    PRIORITY_ORDER,
    STALE_DAYS,
    STATUSES,
    TEST_LAYERS,
)
from .io import atomic_write, die
from .layout import (
    _rel,
    criteria_path,
    link_fields,
    reviews_path,
    role_dir,
    roles_dir,
    team_root_from,
    testplan_path,
    tests_path,
)
from .names import body_text, one_line, resolve_role

REVIEWS_HEADER = (
    "# Reviews - PRs awaiting the Reviewer\n\n"
    "> One entry per pull request. A branch may only be merged into `main` by the\n"
    "> Reviewer, after its review passed. Manage with `teamwork.py pr ...`.\n\n"
    "Related: [team map](TeamMap.md) | [disputes](Disputes.md)\n"
)

SKILLS_HEADER = (
    "# Team skills - extracted, shared flows\n\n"
    "> A skill is created when a flow is repetitive, widely reused and must stay\n"
    "> consistent across instances of a role. The file lives in the project\n"
    "> (`.agents/skills/<name>/SKILL.md`) so every agent and worktree sees it.\n"
    "> Manage with `teamwork.py skill ...`.\n\n"
    "Related: [team map](TeamMap.md) | [tests](Tests.md) | [criteria](Criteria.md) | "
    "[reviews](Reviews.md)\n"
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

DISPUTE_HEADER = (
    "# DISPUTES - design/decision challenges\n\n"
    "> Every non-trivial decision needs an evidence chain. When you find a design\n"
    "> or decision unreasonable, open a dispute here with counter-evidence.\n"
    "> Max {rounds} rounds between the two agents; after that the CEO + CTO + CFO\n"
    "> tribunal rules and the ruling is binding (record it in docs/Team/Decisions.md).\n"
)

DISPUTE_RE = re.compile(r"^##\s+(D-\d+)\s*(?:·|:)?\s*(.*)$")

ROUND_RE = re.compile(r"^-\s+r(\d+)\s+(\S+)\s+(\S+):\s*(.*)$")

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

#: Metadata the model holds as a number while ``render_tasks`` writes it as text.
#: ``new_task`` seeds these as ``int``, so without coercion in the parser a
#: round-trip silently changes their type and a reader that compares the value
#: (``t["review_fails"] >= 3``) raises ``TypeError`` on a reloaded queue only.
NUMERIC_FIELDS = frozenset({"review_fails"})

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


def _branch_matches(pr: dict, branch: str | None) -> bool:
    return not branch or (pr.get("branch") or "") == branch


def find_pr(prs: list, handle: str, branch: str | None = None):
    """Index of the PR named by ``handle`` (id, task or title).

    ``branch`` disambiguates a task that has more than one PR record - a task
    reworked after a merge keeps the old PR and gains a new branch, so matching
    on the task id alone could return the record of the branch that is already
    in the base. When it is given, only a record on that branch matches.
    """
    want = (handle or "").strip().upper()
    for i, pr in enumerate(prs):
        if pr["id"].upper() == want and _branch_matches(pr, branch):
            return i
    for i, pr in enumerate(prs):
        if pr["task"].upper() == want and _branch_matches(pr, branch):
            return i
    for i, pr in enumerate(prs):
        if want and want.lower() in pr["title"].lower() and _branch_matches(pr, branch):
            return i
    return None


def find_pr_exact(prs: list, handle: str, branch: str | None = None):
    """Exact id/task match only: a merge must never hit a fuzzy title match.

    ``branch`` narrows the match the same way ``find_pr`` does, so a merge can
    never select a PR record belonging to a different branch of the same task.
    """
    want = (handle or "").strip().upper()
    for i, pr in enumerate(prs):
        if pr["id"].upper() == want and _branch_matches(pr, branch):
            return i
    for i, pr in enumerate(prs):
        if pr["task"].upper() == want and _branch_matches(pr, branch):
            return i
    return None


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


def render_criteria(items: list, path: Path | None = None) -> str:
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
        "baseline": "",
        "artifacts": "",
        "replay": "",
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


def render_tests(records: list, path: Path | None = None) -> str:
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
            "baseline",
            "artifacts",
            "replay",
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
    plan: dict = {}
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


def render_testplan(plan: dict, path: Path | None = None) -> str:
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
    review_profile: str = "",
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
        "kind": "",
        "repro": "",
        "repro_artifacts": "",
        "repro_by": "",
        "evidence": one_line(evidence),
        "review": review if review in ("required", "na") else "required",
        "review_status": "na" if review == "na" else "pending",
        "review_profile": review_profile if review_profile in ("fast", "standard", "deep") else "",
        "self_check": "na" if review == "na" else "pending",
        "self_note": "",
        "self_artifacts": "",
        "review_evidence": "",
        "review_artifacts": "",
        "reviewer": "",
        "review_claim": "",
        "review_claim_ts": "",
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
                    "review_profile",
                    "reviewer",
                    "review_claim",
                    "review_claim_ts",
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
                    "kind",
                    "repro",
                    "repro_artifacts",
                    "repro_by",
                    "self_artifacts",
                    "review_artifacts",
                    "review_fails",
                ):
                    if field in NUMERIC_FIELDS:
                        current[field] = int(value) if value.isdigit() else 0
                    else:
                        current[field] = value
                continue
            in_body = True
        current["body"] = (current["body"] + "\n" + raw).strip()
    if current:
        tasks.append(current)
    return [t for t in tasks if t["title"] or t["body"]]


def render_tasks(tasks: list, owner: str, path: Path | None = None) -> str:
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
            ("kind", t.get("kind", "")),
            ("repro", t.get("repro", "")),
            ("repro_artifacts", t.get("repro_artifacts", "")),
            ("repro_by", t.get("repro_by", "")),
            ("review", t.get("review", "required")),
            ("review_status", t.get("review_status", "pending")),
            ("review_profile", t.get("review_profile", "")),
            ("self_check", t.get("self_check", "pending")),
            ("self_note", t.get("self_note", "")),
            ("self_artifacts", t.get("self_artifacts", "")),
            ("reviewer", t.get("reviewer", "")),
            ("review_claim", t.get("review_claim", "")),
            ("review_claim_ts", t.get("review_claim_ts", "")),
            ("review_evidence", t.get("review_evidence", "")),
            ("review_artifacts", t.get("review_artifacts", "")),
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
    """Is a dependency satisfied yet?

    A bare ``role:T-id`` waits for the whole task to be ``done``. Add ``@review``
    to release as soon as the work is *submitted* (``review`` or ``done``) and
    ``@started`` to release once the owner has picked it up, so a downstream lane
    can begin against a frozen contract instead of idling for a full review round.
    """
    dep = dep.strip()
    if not dep:
        return True
    if ":" in dep:
        other_agent, other_id = dep.split(":", 1)
        other_agent, other_id = other_agent.strip(), other_id.strip()
        mode = "done"
        if "@" in other_id:
            other_id, mode = other_id.split("@", 1)
            other_id, mode = other_id.strip(), mode.strip().lower()
        if mode not in ("done", "review", "started"):
            mode = "done"
        key = ("x", other_agent, other_id, mode)
        if key not in cache:
            path = role_dir(root, other_agent) / F_TASKS
            tasks = parse_tasks(path)
            idx = find_task(tasks, other_id)
            status = tasks[idx]["status"] if idx is not None else ""
            wanted = {
                "done": ("done",),
                "review": ("review", "done"),
                "started": ("doing", "selfcheck", "review", "done"),
            }[mode]
            cache[key] = status in wanted
        return cache[key]
    local_key = ("l", dep.lower())
    if local_key not in cache:
        cache[local_key] = None
    return cache[local_key] is True  # filled by caller for local deps


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
    for dep in split_dependencies(t["deps"]):
        if ":" in dep:
            if not dep_satisfied(root, dep, cache):
                return False
        else:
            if lookup.get(dep.lower()) != "done":
                return False
    return True


#: A dependency is a task id, optionally role-qualified and with a release mode.
DEP_RE = re.compile(r"^(?:(?P<role>[A-Za-z][A-Za-z0-9-]*):)?(?P<id>T-\d+)(?:@(?P<mode>[a-z]+))?$")

#: Statuses that keep a task in the graph a lane still has to work through.
OPEN_STATUSES = ("todo", "doing", "selfcheck", "review")


def norm_role(name: str) -> str:
    """`security-auditor`, `SecurityAuditor`, `securityauditor` - one role.

    Queue directories are PascalCase while a dependency may spell the role the
    way it is displayed, so both sides of a comparison go through this.
    """
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def split_dependencies(raw: str) -> list[str]:
    """The dependency strings of one record: comma or whitespace separated.

    ``-`` is the placeholder an empty field is sometimes rendered with, so it
    means "no dependencies" rather than a task named ``-``.
    """
    return [part for part in re.split(r"[,\s]+", raw or "") if part.strip() and part.strip() != "-"]


def dep_target(role: str, dep: str) -> tuple[str, str] | None:
    """The (normalised role, task id) a dependency points at, else ``None``.

    A bare ``T-0001`` resolves inside the queue that writes it; ``role:T-0001``
    resolves inside that role's queue, and accepts an instance spelling
    (``developer-1:T-0001``) the way ``dep_satisfied`` already does. The
    ``@review`` / ``@started`` release mode is not part of the target.
    """
    match = DEP_RE.match((dep or "").strip())
    if match is None:
        return None
    qualifier = match.group("role")
    owner = norm_role(resolve_role(qualifier)) if qualifier else norm_role(role)
    return owner, match.group("id").upper()


def load_task_queues(root: Path) -> dict[str, list[dict]]:
    """Every role queue in the team tree, keyed by normalised role name."""
    out: dict[str, list[dict]] = {}
    base = roles_dir(root)
    if not base.is_dir():
        return out
    for path in sorted(base.glob(f"*/{F_TASKS}")):
        out[norm_role(path.parent.name)] = parse_tasks(path)
    return out


def task_graph_problems(root: Path, role: str = "", tasks: list | None = None) -> list[str]:
    """Every way the task graph would be unrunnable, as one line per problem.

    The invariants `docs/Team/Plan.md` states, checked over the whole graph
    because a dependency crosses role queues and a cycle exists only in their
    union: every dependency resolves to an existing task and is not the task
    itself, no queue holds one open id twice, no dependency cycle exists, and
    every task carries a priority `task next` can order.

    ``role``/``tasks`` check a queue *as it is about to be written* - the write
    gates pass the parsed queue with the pending change already applied - so a
    refused write changes nothing on disk. Without them the queues on disk are
    checked. An empty result means the graph is safe to write.
    """
    queues = load_task_queues(root)
    if role and tasks is not None:
        queues[norm_role(role)] = list(tasks)
    known = {
        (owner, str(t.get("id") or "").upper()) for owner, items in queues.items() for t in items
    }
    problems: list[str] = []
    for owner, items in queues.items():
        problems.extend(_queue_problems(owner, items, known))
    problems.extend(_cycle_problems(queues, known))
    return list(dict.fromkeys(problems))


def _queue_problems(owner: str, tasks: list, known: set[tuple[str, str]]) -> list[str]:
    """The per-queue half of the invariants: ids, priorities and dep targets."""
    problems: list[str] = []
    open_ids: dict[str, int] = {}
    for t in tasks:
        tid = str(t.get("id") or "").upper()
        if t.get("status") in OPEN_STATUSES:
            open_ids[tid] = open_ids.get(tid, 0) + 1
        if t.get("priority") not in PRIORITY_ORDER:
            problems.append(f"{owner}:{tid} has no priority, so no lane can order or pick it")
        for dep in split_dependencies(t.get("deps", "")):
            target = dep_target(owner, dep)
            if target is None:
                problems.append(f"{owner}:{tid} depends on {dep!r}, which is not a task id")
            elif target == (owner, tid):
                problems.append(f"{owner}:{tid} depends on itself")
            elif target not in known:
                problems.append(f"{owner}:{tid} depends on {dep!r}, which names no task")
    for tid, count in open_ids.items():
        if count > 1:
            problems.append(
                f"{owner}:{tid} appears {count} times in one queue, so `task set` "
                "would act on whichever block it read first"
            )
    return problems


def _cycle_problems(queues: dict[str, list[dict]], known: set[tuple[str, str]]) -> list[str]:
    """Depth-first walk over the resolved edges; a cycle names its own path.

    A self-loop is already reported by the per-queue pass, so it is not walked
    here. Every task in a cycle is unexecutable forever, which `task next`
    reports only as "nothing to do" - hence a named path, not a count.
    """
    edges: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for owner, tasks in queues.items():
        for t in tasks:
            node = (owner, str(t.get("id") or "").upper())
            edges[node] = [
                target
                for target in (
                    dep_target(owner, dep) for dep in split_dependencies(t.get("deps", ""))
                )
                if target is not None and target in known and target != node
            ]
    found: list[str] = []
    walked: set[tuple[str, str]] = set()

    def walk(node: tuple[str, str], stack: list[tuple[str, str]]) -> None:
        if node in stack:
            loop = stack[stack.index(node) :] + [node]
            found.append("dependency cycle: " + " -> ".join(f"{role}:{tid}" for role, tid in loop))
            return
        if node in walked:
            return
        for nxt in edges.get(node, []):
            walk(nxt, [*stack, node])
        walked.add(node)

    for node in edges:
        walk(node, [])
    return list(dict.fromkeys(found))


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


def render(entries: list, filename: str, owner: str, path: Path | None = None) -> str:
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


def next_id(items: list, prefix: str) -> str:
    """The id a new record would get, without renumbering the existing ones.

    A write gate has to know the id *before* it validates the graph, or a
    dependency on the task being added looks unknown and a self-dependency
    cannot be seen at all. ``assign_ids`` allocates from the same rule.
    """
    used = {str(it.get("id") or "") for it in items}
    highest = 0
    for value in used:
        tail = value.split("-", 1)[1] if "-" in value else ""
        if tail.isdigit():
            highest = max(highest, int(tail))
    while f"{prefix}{highest + 1:04d}" in used:
        highest += 1
    return f"{prefix}{highest + 1:04d}"


def assign_ids(items: list, prefix: str) -> None:
    """Keep existing ids stable; allocate fresh, collision-free ids for the rest."""
    seen = set()
    for it in items:
        i = it.get("id", "")
        if i and i not in seen:
            seen.add(i)
        else:
            it["id"] = ""
    for it in items:
        if not it["id"]:
            it["id"] = next_id(items, prefix)


def merge_entries(target: list, incoming: list, prefix: str = "M-") -> tuple:
    """Merge incoming into target by key. Returns (target, merged, added)."""
    merged = 0
    added = 0
    index: dict = {}
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
        # Provenance is carried forward, never dropped: an entry recorded
        # without an author can still be completed by a later writer, and an
        # entry that has one keeps it. The three fields describe ONE recording
        # act, so they only travel together: a later writer who is not the
        # author must not graft their own src/rev onto someone else's record
        # (that would credit the author with a revision they never verified).
        if src.get("by"):
            if not existing.get("by"):
                for field in ("by", "src", "rev"):
                    existing[field] = src.get(field, "")
            elif existing.get("by") == src.get("by"):
                # the same author completing their own record: fill the gaps,
                # never overwrite what is already there
                for field in ("src", "rev"):
                    if not existing.get(field) and src.get(field):
                        existing[field] = src[field]
        merged += 1
    return target, merged, added


def header_for(filename: str, owner: str, path: Path | None = None) -> str:
    """Render a file header; link fields are real relative paths when we know the
    file's location (which every writer does)."""
    tpl = HEADERS.get(filename, "# Memory - {owner}\n")
    if path is None:
        die("internal: header_for needs the file path so its links resolve")
    fields = link_fields(path, owner)
    fields.update(owner=owner, cap=LONG_CAP, stale=STALE_DAYS)
    return tpl.format(**fields)


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
