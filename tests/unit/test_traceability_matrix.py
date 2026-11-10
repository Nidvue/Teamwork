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
only these contradictions plus the structural checks run. The record claims are
therefore certified where the tree exists (a working checkout, every review) and
the table's internal consistency is certified everywhere.
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
    pytest.fail(f"the traceability section has no table headed by {COLUMNS}")


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
    problems = []
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
    assert not problems, problems


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
}

EXEMPT: dict[str, str] = {
    "AC-2": "self",
    "AC-3": "self",  # clause 1 is this pytest run; clause 2 is the drifting team tree
    "AC-4": "forge",
    "AC-7": "forge",
    "AC-8": "forge",
    "AC-9": "self",
    "AC-10": "self",
    "AC-13": "self",
    "AC-15": "self",
    "AC-16": "self",
    "AC-17": "self",  # the pytest half; its `ls` half is covered by AC-12
    "AC-18": "self",
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
    meaning the same thing in every shell.
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
    # the table says `python`; that must mean the interpreter hosting this suite,
    # not whatever `python` happens to be first on PATH (a bare interpreter has no
    # dependencies and turned AC-1 red for the wrong reason in review round six)
    if tokens and tokens[0] == "python":
        tokens[0] = sys.executable
    elif tokens and tokens[0].endswith(".py"):
        tokens.insert(0, sys.executable)
    command = tokens
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    return completed.returncode


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
    - the number of rows re-run must equal `rows - exemptions`, so exempting a
      row cannot lower the bar without the arithmetic saying so.
    """
    project = (repo_root / "docs/Team/Project.md").read_text(encoding="utf-8")
    _header, body = _matrix(_section(project))
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

    disagreements: list[str] = []
    executed = 0
    for ac in sorted(claimed):
        if ac in EXEMPT:
            continue
        commands = _proof_commands(proofs[ac])
        if not commands:
            cell = proofs[ac]
            disagreements.append(f"{ac} is neither exempt nor parseable into a command: {cell!r}")
            continue
        executed += 1
        codes = [_run(repo_root, argv) for argv in commands]
        if "green" in claimed[ac] and any(codes):
            disagreements.append(f"{ac} is claimed green, the run exits {codes}")
        elif "green" not in claimed[ac] and not any(codes):
            disagreements.append(f"{ac} is claimed red, every clause exits 0")
    expected = len(claimed) - len(EXEMPT)
    assert executed == expected, (
        f"{executed} row(s) were re-run, but {len(claimed)} rows minus {len(EXEMPT)} "
        f"exemptions is {expected}: a row was skipped or the parser drifted"
    )
    assert not disagreements, "the state column disagrees with the run: " + "; ".join(disagreements)
