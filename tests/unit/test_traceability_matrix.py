"""The requirements traceability section is a method, not a snapshot.

T-0001 (product-manager): `docs/Team/Project.md` carries a
`## Traceability - AC to task to test` section. Its first version pinned a count
and a revision that the very commit documenting them changed, left the
test-record column unchecked prose, and kept a hand-written reverse index that
contradicted the forward table. This guard asserts the properties that make the
section evidence: one table, every AC in it defined, every test record in it a
real passing record with the layer/area the row claims, and every red row owning
a gap that the gaps table defines.

Round 4 failed on the opposite defect: `state` was only checked for SPELLING, so
flipping `red (G-2)` to `green` left all eight tests green. `state` is now tied to
the gaps table in both directions (see
`test_a_green_row_is_not_blamed_by_a_gap_and_a_red_row_is`), which is the one
guard here that runs without the gitignored team tree.

That tree is the honest limit of this file: the record-resolution test reads
`.pi/Teamwork/Teams/*/Tests.md`, which is gitignored, so in CI it is skipped and
only these contradictions plus the structural checks run. It also skips in a
workspace whose tree recognizes none of the cited records (a fresh
`teamwork.py init` leaves an empty Tests.md and numbers its own `TS-0001`, so a
re-initialised team state can neither certify nor contradict a matrix written by
an older run) - and it says so with both counts instead of passing silently.
`test_the_record_check_still_fails_where_the_tree_recognizes_a_cited_record` keeps
the assertion's teeth measurable where no tree exists at all.

Two host assumptions were the guard's own defects (T-0003). `ls` exists only on a
POSIX host, so a win32 runner died with `FileNotFoundError` before it could
disagree with any row - a reporter that crashes is not a guard. `ls` is now
translated to the existence check it means (the same paths, the same exit status),
a proof whose declared host capability is absent is SKIPPED with the row and the
reason named and counted by the same arithmetic as an exemption, and any other
command this host cannot start is a disagreement naming the row - never a crash,
never a silent pass.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SECTION = "## Traceability - AC to task to test"
DOD = "## Definition of done"
# the six columns, matched as prefixes so a column may carry a hint in parentheses
COLUMNS = ["ac", "proof target", "archived task(s)", "test record", "proof command", "state"]
# task ids are per-role queues; closed ones are archived, so both are searched
QUEUE_GLOB = ".pi/Teamwork/Teams/Teamwork/Roles/*/TaskQueue.md"
ARCHIVE = "docs/Team/Archive.md"
# gitignored working state: absent in CI, present in a working checkout
TEAM_TESTS_GLOB = ".pi/Teamwork/Teams/*/Tests.md"

# Per-command budget, in seconds, for re-running one row's proof command (T-0020).
# The costliest proof in the table is the AC-5 row's full history walk
# (`privacy_scan.py --tree --history`, every blob reachable from every ref plus
# every commit's identity fields), so its runtime follows the *history*, not the
# code: a fixed 300 s budget was green at one revision and timed out at the next
# pushed one after nothing changed in this guard or in the scanner (CI run
# 40728749217, ubuntu py3.11/py3.12 and windows py3.11). The budget must therefore
# cover a COLD runner walking a history already larger than the one measured here:
# an empty object cache, no warmed `git cat-file --batch`, and a filesystem with
# antivirus interception are all slower than a developer's checkout with a local
# object store, where the same command measured 149 s over 944 commits / 6236
# objects. 900 s is ~6x that measurement, so ordinary history growth and a slower
# runner are not failures. It stays finite on purpose: a proof that hangs must
# still fail, only later, and the failure names this budget so the next reader can
# tell slow from hung.
PROOF_TIMEOUT_SECONDS = 900


def _section(project: str) -> str:
    start = project.find(SECTION)
    assert start >= 0, f"docs/Team/Project.md has no {SECTION!r} section"
    return project[start:]


def _window(project: str, heading: str) -> str:
    """The text of one `## heading` section, up to the next level-2 heading."""
    start = project.find(heading)
    assert start >= 0, f"docs/Team/Project.md has no {heading!r} section"
    rest = project[start + len(heading) :]
    end = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def _matrix_rows(section: str) -> list[list[str]]:
    """Every markdown table row of the forward matrix, as stripped cells."""
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def _matrix(section: str) -> tuple[list[str], list[list[str]]]:
    """The matrix header and its body rows (the separator row is dropped).

    Only the contiguous table under the `AC` header counts - the section holds
    other tables (layers, gaps) further down.
    """
    rows = _matrix_rows(section)
    for i, cells in enumerate(rows):
        if cells and cells[0].lower() == "ac":
            body = []
            for candidate in rows[i + 1 :]:
                if set("".join(candidate)) <= set("-: "):
                    continue
                if not re.fullmatch(r"AC-\d+", candidate[0]):
                    break
                body.append(candidate)
            return [c.lower() for c in cells], body
    # `pytest.fail` raises, but it is a callable object, so a static return-checker
    # cannot see the `NoReturn`; raising directly keeps the sentinel analysable.
    raise AssertionError(f"the traceability section has no table headed by {COLUMNS}")


def _team_tests(repo_root: Path) -> dict:
    """Parse the team tree's Tests.md, keyed by record id.

    The team tree is gitignored, so CI legitimately has no such file. That is a
    skip, never a silent pass.
    """
    paths = sorted(repo_root.glob(TEAM_TESTS_GLOB))
    if not paths:
        pytest.skip(f"no {TEAM_TESTS_GLOB} in this checkout (team tree is gitignored)")
    records: dict[str, dict] = {}
    for path in paths:
        cur = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s+(TS-\d+)\b", raw)
            if m:
                cur = records.setdefault(m.group(1), {"_path": str(path)})
                continue
            meta = re.match(r"^-\s+(\w+):\s*(.*)$", raw)
            if cur is not None and meta:
                cur[meta.group(1)] = meta.group(2).strip()
    return records


def test_the_section_pins_no_revision_and_no_census_count(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    assert not re.search(r"@[0-9a-f]{7,}", section), (
        "the traceability section pins a revision sha; it changes with the very commit "
        "that writes it - state the command that reads the revision instead"
    )
    census = re.findall(
        r"\b\d+\s+(?:acceptance criteria|ACs|acceptance)?\s*(?:test\s+)?records?\b", section
    )
    assert not census, (
        f"the traceability section pins a census {census}; counts move with every records "
        "pass - state the command that counts instead"
    )


def test_the_matrix_declares_the_six_columns_and_every_row_fills_them(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    header, body = _matrix(_section(project))
    aligned = len(header) == len(COLUMNS) and all(h.startswith(c) for h, c in zip(header, COLUMNS))
    assert aligned, f"the matrix header is {header}, expected the columns {COLUMNS}"
    assert body, "the traceability matrix has no AC rows"
    short = [r for r in body if len(r) != len(header)]
    assert not short, f"matrix rows do not fill all {len(COLUMNS)} columns: {short}"
    assert any(re.search(r"TS-\d{4}", r[3]) for r in body), (
        "no row names a test record, so the test-record column is unchecked prose"
    )


def test_the_matrix_ac_set_equals_the_definition_of_done_ac_set(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    header, body = _matrix(_section(project))
    rows = {r[0] for r in body}
    assert rows, "the traceability table names no acceptance criterion"
    defined = set(re.findall(r"\bAC-\d+\b", _window(project, DOD)))
    assert defined, f"{DOD} names no acceptance criterion"
    invented = sorted(rows - defined)
    unmapped = sorted(defined - rows)
    assert not invented and not unmapped, (
        f"the matrix and {DOD} disagree: rows name criteria the DoD never defines "
        f"{invented}; criteria the DoD defines have no row {unmapped}"
    )


def _record_problems(records: dict, cited: list) -> list[str]:
    """Every cited record the team tree does not back, one readable line each.

    Split out of the guard so its teeth survive the skip below: a workspace that
    holds none of the cited records cannot certify them (T-0003), but the moment
    one resolves, every cited record must resolve, be ``passing`` and carry the
    layer/area the row claims.
    """
    problems: list[str] = []
    for ac, rec, claim in cited:
        record = records.get(rec)
        if record is None:
            problems.append(f"{ac}: {rec} is not a record in Tests.md")
            continue
        if record.get("status") != "passing":
            problems.append(f"{ac}: {rec} has status {record.get('status')!r}, not 'passing'")
        actual = f"{record.get('layer', '')}/{record.get('area', '')}"
        if actual != claim:
            problems.append(f"{ac}: {rec} is {actual}, the row claims {claim}")
    return problems


def _recognized(records: dict, cited: list) -> list[str]:
    """The cited claims a record in this tree identifies itself with.

    Identity is the record id plus the layer/area the row claims for it - status
    is deliberately left out, so a record that flipped to ``failing`` is still
    recognised and then fails on the assertion rather than being skipped away.
    A workspace that re-ran ``teamwork.py init`` numbers its own records from
    ``TS-0001``, so an id can collide with a cited record while meaning something
    else; a colliding id under another layer/area is not identity, and nothing
    in such a tree can certify the committed matrix.
    """
    matched: list[str] = []
    for ac, rec, claim in cited:
        record = records.get(rec) or {}
        actual = f"{record.get('layer', '')}/{record.get('area', '')}"
        if record and actual == claim:
            matched.append(f"{ac}: {rec} ({claim})")
    return matched


def test_every_cited_test_record_exists_passes_and_matches_its_layer_and_area(
    repo_root: Path,
) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    _header, body = _matrix(_section(project))
    cited = []  # (ac, record id, claimed 'layer/area')
    for row in body:
        for rec, claim in re.findall(r"(TS-\d{4})(?:\s*\(([^)]*)\))?", row[3]):
            cited.append((row[0], rec, claim.strip() if claim else ""))
    assert cited, "the matrix test-record column names no record at all"
    unclaimed = sorted(f"{ac}: {rec}" for ac, rec, claim in cited if "/" not in claim)
    assert not unclaimed, (
        f"rows name records without the layer/area they claim for them: {unclaimed}"
    )
    records = _team_tests(repo_root)
    cited_ids = sorted({rec for _ac, rec, _claim in cited})
    if not _recognized(records, cited):
        pytest.skip(
            f"the team tree holds {len(records)} test record(s) and none carries an id and "
            f"layer/area claimed by the {len(cited_ids)} records cited here "
            f"({', '.join(cited_ids)}): this workspace's team state did not produce "
            "docs/Team/Project.md, so its record column cannot be certified against it - "
            "a fresh `teamwork.py init` leaves an empty Tests.md and numbers its own "
            "TS-0001, and CI has no tree at all"
        )
    problems = _record_problems(records, cited)
    assert not problems, problems


def test_the_record_check_still_fails_where_the_tree_recognizes_a_cited_record() -> None:
    """Prove the assertion above is intact: the skip must not soften it (T-0003)."""
    cited = [("AC-1", "TS-0018", "release/release")]
    good = {"TS-0018": {"status": "passing", "layer": "release", "area": "release"}}
    assert _recognized(good, cited) == ["AC-1: TS-0018 (release/release)"]
    assert _record_problems(good, cited) == []

    wrong_status = {**good, "TS-0018": {**good["TS-0018"], "status": "failing"}}
    assert _recognized(wrong_status, cited), "a status flip must still be recognised"
    assert _record_problems(wrong_status, cited) == [
        "AC-1: TS-0018 has status 'failing', not 'passing'"
    ]

    collision = {"TS-0018": {"status": "passing", "layer": "requirements", "area": "research"}}
    assert _recognized(collision, cited) == [], "an id collision is not identity"
    assert _record_problems(collision, cited) == [
        "AC-1: TS-0018 is requirements/research, the row claims release/release"
    ]

    assert _record_problems({}, cited) == ["AC-1: TS-0018 is not a record in Tests.md"]


def test_every_named_task_resolves_to_a_queue_or_the_archive(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    queues = "".join(p.read_text(encoding="utf-8") for p in repo_root.glob(QUEUE_GLOB))
    known = queues + (repo_root / ARCHIVE).read_text(encoding="utf-8")
    cited = set(re.findall(r"\bT-\d{4}\b", section))
    unresolved = sorted(t for t in cited if t not in known)
    assert not unresolved, (
        f"rows cite tasks that no role queue and no archive entry contains: {unresolved}"
    )


def test_every_named_test_file_exists(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    cited = set(re.findall(r"`(tests/[\w/]+\.py)`", section))
    missing = sorted(p for p in cited if not (repo_root / p).exists())
    assert not missing, f"rows cite test files that do not exist: {missing}"


def test_every_red_row_names_a_gap_that_the_gaps_table_defines(repo_root: Path) -> None:
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    _header, body = _matrix(section)
    states = [r[5] for r in body]
    assert states, "the matrix has no state column"
    bad = sorted({s for s in states if not re.search(r"\b(?:green|red)\b", s.lower())})
    assert not bad, f"rows use a state that is neither green nor red: {bad}"
    undefined = sorted({g for g in re.findall(r"\bG-\d+\b", section)} - set(_gaps(section)))
    assert not undefined, (
        f"the section cites gaps the gaps table never defines: {undefined} - a red row "
        "must point at an owned gap, not at prose"
    )
    unowned = sorted(r[0] for r in body if "red" in r[5].lower() and not re.search(r"G-\d+", r[5]))
    assert not unowned, f"red rows name no gap: {unowned}"


def _gaps(section: str) -> list[str]:
    """The ids of the gaps table rows (`| G-n | gap | how to read | owner |`)."""
    return re.findall(r"^\|\s*(G-\d+)\s*\|", section, re.MULTILINE)


def test_the_reverse_map_agrees_with_the_forward_table(repo_root: Path) -> None:
    """The reverse index is a second statement of the same facts - prove it equal."""
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    _header, body = _matrix(section)
    forward: dict[str, set[str]] = {}
    for row in body:
        for rec in re.findall(r"TS-\d{4}", row[3]):
            forward.setdefault(rec, set()).add(row[0])
    blocks = re.findall(r"^```\n(.*?)^```", section, re.MULTILINE | re.DOTALL)
    assert len(blocks) == 1, f"the section carries {len(blocks)} derived blocks, expected 1"
    reverse: dict[str, set[str]] = {}
    unowned = set()
    for line in blocks[0].splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(TS-\d{4}|no AC):\s*(.*)$", line.strip())
        assert m, f"the derived reverse map has an unparseable line: {line!r}"
        if m.group(1) == "no AC":
            unowned |= {u.strip() for u in m.group(2).split(",") if u.strip()}
            continue
        reverse[m.group(1)] = {a.strip() for a in m.group(2).split(",") if a.strip()}
    assert reverse, "the derived reverse map names no record"
    assert reverse == forward, (
        "the reverse map contradicts the forward table: "
        f"only in the reverse map {sorted(set(reverse) - set(forward))}, "
        f"only in the forward table {sorted(set(forward) - set(reverse))}, "
        f"AC lists differing {sorted(r for r in reverse if r in forward and reverse[r] != forward[r])}"
    )
    assert not (unowned & set(forward)), (
        f"records are listed as unowned by an AC but the forward table cites them: "
        f"{sorted(unowned & set(forward))}"
    )


def _gap_rows(section: str) -> dict[str, str]:
    """`{gap id: gap text}` from the gaps table (`| G-n | gap | how to read | owner |`)."""
    rows: dict[str, str] = {}
    for line in section.splitlines():
        m = re.match(r"^\|\s*(G-\d+)\s*\|(.*)$", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def _blames(text: str, ac: str) -> bool:
    """Does this gap row name `ac` as the thing it makes fail?

    A gap row earns the right to explain a red state only by naming the AC and a
    failure word together; naming an AC while calling it green (G-3 style, kept
    for history) is a closed gap and must not justify a current red row.
    """
    if "closed" in text.lower():
        # a gap that records its own closure explains history, not the current state
        return False
    for sentence in re.split(r"(?<=[.;])\s+", text):
        if not re.search(rf"\b{re.escape(ac)}\b", sentence):
            continue
        if re.search(r"\b(?:red|fails?|failing|FAIL|non-zero|CONTINUE|problems?)\b", sentence):
            return True
    return False


def test_a_green_row_is_not_blamed_by_a_gap_and_a_red_row_is(repo_root: Path) -> None:
    """The state column and the gaps table are one statement, checked both ways.

    Why this exists: three review rounds failed because `state` was free prose -
    only its SPELLING was checked, so flipping `red (G-2)` to `green` left every
    test green while the row asserted something the tree contradicts. No guard can
    re-run the world cheaply here, but it can refuse to let the two columns
    disagree: a `green` row may not be named by a gap as failing, and a `red` row
    must name a gap that actually blames it. A single-word edit then contradicts
    the rest of the section instead of passing silently.
    """
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    _header, body = _matrix(section)
    gaps = _gap_rows(section)
    assert gaps, "the section has no gaps table, so a red state cannot be owned"

    blamed_green: list[str] = []
    unblamed_red: list[str] = []
    for row in body:
        ac, state = row[0], row[5].lower()
        named = {g for g in re.findall(r"G-\d+", row[5])}
        blamed = {g for g, text in gaps.items() if _blames(text, ac)}
        if "red" in state:
            if not named:
                unblamed_red.append(f"{ac}: red but names no gap")
                continue
            undefined = sorted(g for g in named if g not in gaps)
            if undefined:
                unblamed_red.append(
                    f"{ac}: names {undefined}, which the gaps table does not define"
                )
            # a row may cite several related gaps; at least one must own this failure
            elif not any(_blames(gaps[g], ac) for g in named):
                unblamed_red.append(f"{ac}: names {sorted(named)}, but none of them blames {ac}")
        elif "green" in state and blamed:
            blamed_green.append(f"{ac}: called green while {sorted(blamed)} blames it")

    assert not unblamed_red, "red rows and the gaps table disagree: " + "; ".join(unblamed_red)
    assert not blamed_green, "green rows and the gaps table disagree: " + "; ".join(blamed_green)


# Why a row is not re-run here, keyed by AC id. Every exemption must name a
# REASON from `EXEMPT_REASONS`; anything else is re-run from the table's own
# proof column. A hand-kept allow-list of rows to re-run was defeated in review
# round six: deleting one row from the dict left every guard green while the
# tree contradicted that row, because the dict - not the table - decided what to
# execute. The table is the source now, and an exemption is a claim the reviewer
# can read and challenge.
EXEMPT_REASONS = {
    "self": "the proof is this pytest run, which is already the suite hosting the guard",
    "forge": "the proof reads the forge and a CI job without credentials cannot re-run it",
    "drift": "a clause reads the gitignored team tree, which drifts between runs",
    "inflight": (
        "the proof asks the live board whether the run is finished, and while this "
        "deliverable is under review the board necessarily still holds it, so the "
        "answer is green only on a merged revision"
    ),
}

# Evidence a reason must find in the row's OWN proof cell. An exemption is not a
# bare dict entry: it is a claim about what that cell reads, and the table has to
# carry the evidence for it. Round 8 failed here - adding `"AC-12": "drift"` and
# deleting `CHANGELOG.md` left the suite green while the table still called AC-12
# green and its proof (`ls LICENSE CHANGELOG.md CITATION.cff`) exited 2.
EXEMPT_EVIDENCE: dict[str, str] = {
    "self": r"\bpytest\b",
    "forge": r"\bgh\b|verify_release\.py|\bci\.ya?ml\b|\brelease\.ya?ml\b|\bCI job\b",
    "drift": r"tests plan|TEAMWORK_ROOT|team tree|\.pi/Teamwork",
    "inflight": r"teamwork\.py loop|teamwork\.py audit",
}

EXEMPT: dict[str, str] = {
    "AC-2": "self",
    "AC-3": "self",  # clause 1 is this pytest run; clause 2 is the drifting team tree
    "AC-4": "forge",
    "AC-7": "forge",
    "AC-8": "forge",
    "AC-9": "self",
    "AC-10": "self",
    "AC-11": "inflight",
    "AC-13": "self",
    "AC-15": "self",
    "AC-16": "self",
    "AC-17": "self",  # the pytest half; its `ls` half is covered by AC-12
    "AC-18": "self",
    # AC-22 and AC-23 are proved by a release run, which exists only after a tag:
    # the npm publish job's run and the Pages job of the same tag. Their proof
    # cells name the forge command and the CI job, which is what the `forge`
    # evidence pattern asks for, and neither row may be claimed green by editing
    # this dict - each is red against a gap that owns it (G-11, G-12).
    "AC-22": "forge",
    "AC-23": "forge",
}


def _proof_commands(cell: str) -> list[list[str]]:
    """Turn a human proof cell into runnable argv lists, from its code spans.

    The cell is written for a reader: ``python scripts/verify_release.py``,
    ``PYTHONPATH=src python scripts/verify_release.py``, or two clauses joined by
    ``and`` where only one is backticked. Each backticked span that names a
    program becomes one command; prose spans (``the same pytest plus ...``) run
    nothing and are covered by ``EXEMPT``. A span with no leading program is
    skipped here, and the caller reports a row that parses to no command as a
    defect rather than a silent skip.
    """
    import shlex

    commands: list[list[str]] = []
    for span in re.findall(r"`([^`]+)`", cell):
        tokens = shlex.split(span)
        prefix: list[str] = []
        while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
            prefix.append(tokens.pop(0))
        if not tokens:
            continue
        program = tokens[0]
        runnable = program in {"python", "ls", "git"} or program.endswith(".py") or "/" in program
        if runnable:
            commands.append([*prefix, *tokens])
    return commands


def _run(repo_root: Path, argv: list[str]) -> int:
    """Run one proof command from the project root and return its exit code.

    Leading ``KEY=VALUE`` tokens are exported for the child, and a script path is
    launched with this interpreter so the proof does not depend on ``python``
    meaning the same thing in every shell. The run is bounded by
    ``PROOF_TIMEOUT_SECONDS``, and exceeding it is a failure that names the budget
    rather than a bare ``TimeoutExpired``: an unfinished proof proved nothing, so
    the row's state is unsupported, and the reader has to be able to tell a budget
    that no longer covers a cold runner from a command that hangs.

    A command this host cannot start raises ``ProofUnlaunchable`` instead of the
    bare ``OSError``: the caller reports the row with the command and the reason,
    so one host-only proof cannot take the whole suite down (T-0003).
    """
    import os
    import subprocess
    import sys

    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(repo_root / "src"))
    env["PYTHONPATH"] = f"{repo_root / 'src'}{os.pathsep}{env['PYTHONPATH']}"
    tokens = list(argv)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
        key, _, value = tokens.pop(0).partition("=")
        env[key] = value
    tokens = _portable(tokens)
    # the table says `python`; that must mean the interpreter hosting this suite,
    # not whatever `python` happens to be first on PATH (a bare interpreter has no
    # dependencies and turned AC-1 red for the wrong reason in review round six)
    if tokens and tokens[0] == "python":
        tokens[0] = sys.executable
    elif tokens and tokens[0].endswith(".py"):
        tokens.insert(0, sys.executable)
    command = tokens
    try:
        completed = subprocess.run(
            command,
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=PROOF_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as expired:
        raise AssertionError(
            f"the proof command {expired.cmd!r} did not finish within "
            f"PROOF_TIMEOUT_SECONDS={PROOF_TIMEOUT_SECONDS}s, so the row it proves has "
            "no measured verdict: a hung proof must fail, so either the command is wrong "
            "or the budget no longer covers a cold runner - raise the constant, do not "
            "exempt the row"
        ) from expired
    except OSError as exc:
        raise ProofUnlaunchable(
            f"proof `{' '.join(argv)}` cannot start on this host: {exc}"
        ) from exc
    return completed.returncode


class ProofUnlaunchable(Exception):
    """A proof command this host cannot start at all (T-0003).

    Not a verdict about the tree: it is a limit of the host, so the caller reports
    the row it belongs to instead of letting the exception abort the suite.
    """


#: `ls` is the one POSIX-only program the proof table names, and its contract in a
#: proof cell is the exit status: 0 when every named path exists, non-zero when one
#: does not. A win32 host ships no `ls`, so the same paths are checked with this
#: interpreter - a deleted file still turns the row non-zero, so the translation
#: cannot certify a row the POSIX command would refuse (T-0003).
_EXISTS_CHECK = (
    "import pathlib, sys\n"
    "missing = [p for p in sys.argv[1:] if not pathlib.Path(p).exists()]\n"
    "if missing:\n"
    "    print('missing: ' + ', '.join(missing))\n"
    "sys.exit(1 if missing else 0)\n"
)


def _portable(argv: list[str]) -> list[str]:
    """The portable launcher for a POSIX-only proof program, else the command as written.

    Only `ls` is translated, and only without options: a flag changes the contract
    (a listing, a recursion, a sort order), so that shape is refused rather than
    silently reinterpreted as something it is not.
    """
    if argv and argv[0] == "ls":
        paths = argv[1:]
        if not paths or any(path.startswith("-") for path in paths):
            raise ProofUnlaunchable(
                f"`{' '.join(argv)}` needs `ls`, which this host does not ship, and the "
                "guard has no portable form for these arguments"
            )
        return ["python", "-c", _EXISTS_CHECK, *paths]
    return argv


#: A proof this host may be unable to run at all, keyed by AC, with the capability
#: that decides it. `build` is the dev extra that `scripts/verify_release.py` needs
#: to produce the sdist and the wheel: a host without that extra cannot measure the
#: row and must say so instead of reporting a defect it never found (T-0003). The
#: row is still certified in CI on every code push, by both jobs in
#: `.github/workflows/ci.yml`: the `test` job installs `.[dev]`, so the guard's own
#: run there executes this row like any other, and the `build` job runs
#: `python scripts/verify_release.py` itself with `build` installed (the same
#: command the row names). Naming the jobs, not their line numbers: those rot.
HOST_CAPABILITY: dict[str, str] = {"AC-1": "module:build"}

#: Evidence a declared capability must find in the row's OWN proof cell, so the
#: declaration is a claim about what that cell runs - not a bare dict entry that
#: could excuse any row. A capability with no pattern here fails the guard.
HOST_CAPABILITY_EVIDENCE: dict[str, str] = {
    "module:build": r"verify_release\.py|python -m build",
}


def _capability_present(capability: str) -> bool:
    """Whether this interpreter can satisfy a declared host capability."""
    import importlib.util

    kind, _, name = capability.partition(":")
    if kind != "module" or not name:
        raise AssertionError(f"unknown host capability {capability!r}: expected `module:<name>`")
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _replay(section: str, repo_root: Path) -> tuple[int, list[str], list[str]]:
    """Re-run every non-exempt row's own proof command.

    Returns ``(executed, skipped, disagreements)``. A row whose declared host
    capability is absent is SKIPPED with its reason and counted by the caller's
    arithmetic; a row that is neither exempt nor parseable, and a row whose command
    runs but disagrees with its claimed state, are disagreements. Nothing here
    raises because of the host: a reporter that crashes is not a guard (T-0003).
    """
    _header, body = _matrix(section)
    claimed = {row[0]: row[5].lower() for row in body}
    proofs = {row[0]: row[4] for row in body}
    executed = 0
    skipped: list[str] = []
    disagreements: list[str] = []

    for ac in sorted(claimed):
        if ac in EXEMPT:
            continue
        # Parse before the capability check, so a declaration excuses only a row
        # that has a command to run: a cell rewritten into prose that merely *names*
        # the proof (reviewer F2 on T-0003) is a disagreement for every row, declared
        # or not - otherwise "declared" would become a way to stop parsing a cell.
        commands = _proof_commands(proofs[ac])
        if not commands:
            disagreements.append(
                f"{ac} is neither exempt nor parseable into a command: {proofs[ac]!r}"
            )
            continue
        capability = HOST_CAPABILITY.get(ac)
        if capability and not _capability_present(capability):
            skipped.append(
                f"{ac}: host skip - {capability.partition(':')[2]!r} is not available to this "
                f"interpreter, so its proof {proofs[ac]!r} cannot be measured here"
            )
            continue
        try:
            codes = [_run(repo_root, argv) for argv in commands]
        except ProofUnlaunchable as exc:
            disagreements.append(f"{ac}: {exc}")
            continue
        executed += 1
        if "green" in claimed[ac] and any(codes):
            disagreements.append(f"{ac} is claimed green, the run exits {codes}")
        elif "green" not in claimed[ac] and not any(codes):
            disagreements.append(f"{ac} is claimed red, every clause exits 0")

    return executed, skipped, disagreements


def test_every_deterministic_state_matches_a_real_run(repo_root: Path) -> None:
    """Re-run each row's own proof command and fail when the table disagrees.

    This is the load-bearing guard, and it exists because six review rounds
    proved that any check inferable from prose can be satisfied by editing
    prose. Round 5's survivor flipped `AC-11` to `green` and rewrote its gap row
    in the same edit; round 6's survivor deleted `AC-11` from a hand-kept list of
    rows to re-run, which left every guard green while `teamwork.py loop` exited
    1 on the same tree. Both worked because something OTHER than the table chose
    what to execute. So the commands are parsed from the table's own proof
    column and nothing else: editing that dict, or emptying it, cannot narrow
    this guard.

    Deliberately bounded, and the limit is stated rather than hidden:

    - a row listed in `EXEMPT` is not re-run, and each exemption names a reason
      from `EXEMPT_REASONS` (this pytest run, the forge, the drifting team tree)
      that the row's own proof cell must evidence (`EXEMPT_EVIDENCE`), so a bare
      dict entry cannot exempt a row whose cell reads something else;
    - an exemption that names an unknown reason, or a row the table does not
      define, is a defect and fails here;
    - a row that is neither exempt nor parseable into a command is a defect too:
      silence is how the sixth round got through;
    - a row this host cannot measure is reported and counted, never crashed and
      never passed: `HOST_CAPABILITY` declares the capability, the row's own cell
      has to evidence it, and the floor arithmetic below charges the skip exactly
      like an exemption; a skip no declaration owns, or a command this host cannot
      start, is a disagreement; a declaration also excuses only a row whose cell
      still parses into a command, so prose that merely names the proof is a
      disagreement like any other unparseable cell;
    - the number of rows re-run plus the rows host-skipped must equal
      `rows - exemptions`, so exempting or skipping a row cannot lower the bar
      without the arithmetic saying so.
    """
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    section = _section(project)
    _header, body = _matrix(section)
    claimed = {row[0]: row[5].lower() for row in body}
    proofs = {row[0]: row[4] for row in body}

    reasons = set(EXEMPT_REASONS)
    unbacked_reason = sorted(reasons - set(EXEMPT_EVIDENCE))
    assert not unbacked_reason, (
        f"these reasons have no evidence pattern, so any row could claim them: {unbacked_reason}"
    )
    bad_reason = sorted(ac for ac, reason in EXEMPT.items() if reason not in reasons)
    assert not bad_reason, f"these exemptions name an unknown reason: {bad_reason}"
    unknown = sorted(set(EXEMPT) - set(claimed))
    assert not unknown, f"the table dropped rows that EXEMPT still names: {unknown}"
    # an exemption must be proved by the row it exempts, not asserted in this dict
    unjustified = sorted(
        f"{ac}: exempt as {reason!r}, but its proof cell {proofs[ac]!r} carries no such evidence"
        for ac, reason in EXEMPT.items()
        if not re.search(EXEMPT_EVIDENCE[reason], proofs[ac])
    )
    assert not unjustified, "an exemption must be justified by the table it exempts: " + "; ".join(
        unjustified
    )
    # a declared host capability is the same kind of claim: it names a row AND the
    # evidence for it lives in that row's own proof cell
    unbacked_capability = sorted(
        f"{ac}: declares {capability!r}, but its proof cell {proofs[ac]!r} carries no evidence"
        for ac, capability in HOST_CAPABILITY.items()
        if capability not in HOST_CAPABILITY_EVIDENCE
        or not re.search(HOST_CAPABILITY_EVIDENCE[capability], proofs[ac])
    )
    assert not unbacked_capability, (
        "a host capability must be justified by the row it excuses: "
        + "; ".join(unbacked_capability)
    )
    dropped_capability = sorted(set(HOST_CAPABILITY) - set(claimed))
    assert not dropped_capability, (
        f"the table dropped rows that HOST_CAPABILITY still names: {dropped_capability}"
    )

    executed, skipped, disagreements = _replay(section, repo_root)
    host_skipped = sorted(entry.split(":", 1)[0] for entry in skipped)
    undeclared = sorted(set(host_skipped) - set(HOST_CAPABILITY))
    assert not undeclared, (
        "these rows were skipped without a declared host capability, so a proof escaped "
        f"execution silently: {undeclared}"
    )
    expected = len(claimed) - len(EXEMPT)
    assert executed + len(skipped) == expected, (
        f"{executed} row(s) were re-run and {len(skipped)} host-skipped, but {len(claimed)} "
        f"rows minus {len(EXEMPT)} exemptions is {expected}: a row was skipped or the parser drifted"
    )
    assert not disagreements, "the state column disagrees with the run: " + "; ".join(disagreements)
    # A row this host cannot measure is not hidden here: the arithmetic above has
    # already charged it, and the next test states it as a skip with its AC and
    # reason - so the guard's own verdict stays a verdict about the rows it measured.


def test_a_row_this_host_cannot_measure_is_named_with_its_reason(repo_root: Path) -> None:
    """The guard's residual limit, stated instead of hidden (T-0003).

    `test_every_deterministic_state_matches_a_real_run` re-runs every row this host
    can measure and counts the rest instead of crashing on them; this test names that
    remainder. A proof whose declared host capability is absent is a SKIP carrying
    the row and the reason, so a host without the `dev` extra sees which verdict it
    does not have - and CI, which installs that extra, measures the row instead.
    """
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    _header, body = _matrix(_section(project))
    claimed = {row[0]: row[5].lower() for row in body}
    proofs = {row[0]: row[4] for row in body}
    undeclared = sorted(set(HOST_CAPABILITY) - set(claimed))
    assert not undeclared, f"HOST_CAPABILITY names rows the table no longer defines: {undeclared}"
    missing = [
        f"{ac}: {capability.partition(':')[2]!r} is not available to this interpreter, so its "
        f"proof {proofs[ac]!r} cannot be measured here"
        for ac, capability in HOST_CAPABILITY.items()
        if not _capability_present(capability)
    ]
    if missing:
        pytest.skip("; ".join(missing))


# T-0020: the re-run guard's per-command budget, proved rather than trusted. The
# defect these three tests pin was a bare `timeout=300` in `_run`: it was green at
# one revision and timed out on the next pushed one in three CI jobs, because the
# AC-5 proof walks the whole history and nothing in the guard or the scanner had
# changed. Two things had to stay true afterwards - the budget is generous enough
# that a slow cold runner is not a failure, and a proof that genuinely hangs still
# fails instead of being skipped - so each is asserted here in milliseconds rather
# than by letting the suite hang for the real budget.


def test_the_proof_budget_is_a_generous_named_constant() -> None:
    """The budget is a stated number with headroom, and still a finite one."""
    assert isinstance(PROOF_TIMEOUT_SECONDS, int) and not isinstance(PROOF_TIMEOUT_SECONDS, bool), (
        f"the proof budget must be an int number of seconds, not {PROOF_TIMEOUT_SECONDS!r}"
    )
    # 300 s is the value that timed out on CI, so the ceiling of the defect is the
    # floor of the fix; 900 is the chosen headroom over the measured history walk.
    assert PROOF_TIMEOUT_SECONDS >= 600, (
        f"PROOF_TIMEOUT_SECONDS={PROOF_TIMEOUT_SECONDS}s leaves no headroom over the "
        "300 s that timed out on a cold CI runner walking the full history"
    )
    # Finite on purpose: an unbounded or hour-long budget would turn a hung proof
    # into a stalled job instead of a failed one.
    assert PROOF_TIMEOUT_SECONDS <= 1800, (
        f"PROOF_TIMEOUT_SECONDS={PROOF_TIMEOUT_SECONDS}s is long enough that a hung "
        "proof reads as a slow one; a hang must fail well inside a CI job"
    )


def test_a_proof_command_runs_under_the_named_budget(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_run` must apply the constant - a literal left behind would not be the fix."""
    import subprocess
    import sys

    seen: dict = {}

    def fake_run(command, **kwargs):
        seen["command"] = list(command)
        seen["timeout"] = kwargs.get("timeout")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _run(repo_root, ["python", "scripts/privacy_scan.py", "--history"]) == 0
    assert seen["timeout"] == PROOF_TIMEOUT_SECONDS, (
        f"the proof ran with timeout={seen['timeout']!r}, not the named budget "
        f"{PROOF_TIMEOUT_SECONDS} - a literal in `_run` is how T-0020 happened"
    )
    # the interpreter substitution `_run` exists for must survive the budget change
    assert seen["command"][0] == sys.executable


def test_a_hung_proof_command_fails_and_names_the_budget(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A budget is not a skip: an unfinished proof fails and says which one."""
    import subprocess

    def fake_run(command, **kwargs):
        budget: float = kwargs["timeout"]
        raise subprocess.TimeoutExpired(command, budget)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AssertionError) as excinfo:
        _run(repo_root, ["python", "scripts/teamwork.py", "loop"])
    message = str(excinfo.value)
    assert f"PROOF_TIMEOUT_SECONDS={PROOF_TIMEOUT_SECONDS}s" in message, message
    assert "teamwork.py" in message, message


# T-0003: two host assumptions were the guard's own defects. It launched `ls` on a
# host that has none, so the suite died with `FileNotFoundError` before it could
# disagree with any row, and it would have measured a build proof on a host without
# the `dev` extra. Each fix is pinned here in milliseconds: the translation keeps
# the POSIX command's contract, a launch failure is a named disagreement instead of
# an exception, a skip is a declared capability with a reason, and the disagreement
# itself still has teeth.


def test_an_ls_proof_is_an_existence_check_over_the_same_paths(repo_root: Path) -> None:
    """`ls a b c` means "these exist": the translation must keep that, both ways."""
    assert _run(repo_root, ["ls", "LICENSE", "CHANGELOG.md", "CITATION.cff"]) == 0
    # a deleted path must still turn the row non-zero, or the translation would
    # certify a green row that the POSIX command refuses
    assert _run(repo_root, ["ls", "LICENSE", "no-such-proof-path-9c1f"]) != 0


def test_an_ls_proof_with_options_is_refused_not_reinterpreted() -> None:
    """A flag changes what `ls` means, so that shape is a host limit, not a check."""
    with pytest.raises(ProofUnlaunchable) as excinfo:
        _portable(["ls", "-l", "LICENSE"])
    assert "no portable form" in str(excinfo.value)


def test_a_proof_this_host_cannot_launch_is_reported_not_raised(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect: `FileNotFoundError` out of the reporter. Now the row fails, legibly."""
    import subprocess

    def fake_run(command, **kwargs):
        raise FileNotFoundError(2, "The system cannot find the file specified")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ProofUnlaunchable) as excinfo:
        _run(repo_root, ["gh", "run", "list"])
    message = str(excinfo.value)
    assert "gh run list" in message, message
    assert "cannot start on this host" in message, message


def _synthetic_matrix(proof: str, state: str) -> str:
    """One-row matrix in the shape `_matrix` reads, for the replay's own tests."""
    return (
        "| AC | proof target | archived task(s) | test record | proof command (read the run) | state |\n"
        "|---|---|---|---|---|---|\n"
        f"| AC-99 | `x` | none | none | {proof} | {state} |\n"
    )


def test_the_replay_still_fails_a_green_row_whose_command_disagrees(tmp_path: Path) -> None:
    """Teeth: the host handling must not soften the disagreement it exists around."""
    executed, skipped, disagreements = _replay(
        _synthetic_matrix('`python -c "raise SystemExit(1)"`', "green"), tmp_path
    )
    assert executed == 1, (executed, skipped, disagreements)
    assert not skipped, skipped
    assert any("AC-99 is claimed green" in line for line in disagreements), disagreements


def test_a_declared_host_capability_skips_its_row_with_a_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A row this host cannot measure is named and counted, never silently passed."""
    import sys

    monkeypatch.setattr(sys.modules[__name__], "_capability_present", lambda capability: False)
    section = (
        "| AC | proof target | archived task(s) | test record | proof command (read the run) | state |\n"
        "|---|---|---|---|---|---|\n"
        "| AC-1 | `x` | none | none | `python scripts/verify_release.py` | green |\n"
    )
    executed, skipped, disagreements = _replay(section, tmp_path)
    assert executed == 0, (executed, skipped)
    assert not disagreements, disagreements
    assert len(skipped) == 1 and skipped[0].startswith("AC-1: host skip"), skipped
    assert "'build'" in skipped[0], skipped[0]


def test_a_declared_capability_does_not_excuse_a_cell_with_no_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2: a declaration excuses a capability, never the parsing of the cell.

    With the skip applied before parsing, rewriting AC-1's cell into prose that
    merely *names* `scripts/verify_release.py` turned a defect ("neither exempt nor
    parseable") into a silent host skip. The row must stay a disagreement whatever
    its capability declares, so "declared" can never become a way to stop reading a
    cell.
    """
    import sys

    monkeypatch.setattr(sys.modules[__name__], "_capability_present", lambda capability: False)
    section = (
        "| AC | proof target | archived task(s) | test record | proof command (read the run) | state |\n"
        "|---|---|---|---|---|---|\n"
        "| AC-1 | `x` | none | none | the same verify_release.py run as AC-2 | green |\n"
    )
    executed, skipped, disagreements = _replay(section, tmp_path)
    assert executed == 0, (executed, skipped)
    assert not skipped, skipped
    assert len(disagreements) == 1, disagreements
    assert "neither exempt nor parseable" in disagreements[0], disagreements[0]


def test_an_undeclared_proof_this_host_cannot_launch_is_a_disagreement(tmp_path: Path) -> None:
    """The skip channel is closed: only a declared, evidenced capability may stop a row.

    A typo or a host-only program with no declaration must fail the guard instead of
    quietly exempting the row - that is how a row stops being executed (T-0003).
    """
    executed, skipped, disagreements = _replay(
        _synthetic_matrix("`bin/teamwork-no-such-proof-9c1f --check`", "green"), tmp_path
    )
    assert executed == 0, (executed, skipped, disagreements)
    assert not skipped, skipped
    assert any("AC-99" in line and "cannot start on this host" in line for line in disagreements), (
        disagreements
    )
