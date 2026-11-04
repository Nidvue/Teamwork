#!/usr/bin/env python3
"""Integration probe (area records): every record survives a round trip.

The team tree under `.pi/Teamwork/Teams/<Team>/` is the team's only memory of what
was decided, done and verified. This probe reads each record family with the
engine's own reader and writes it back with the engine's own renderer, then reads
the result again: a field the renderer drops is a fact the team loses on the next
mutation, so the two parses must be equal, record for record.

It then asks the real CLI for the same records and checks that every id the files
hold is visible to the tool, and that the hash-chained ledger still verifies - a
chain that verifies trivially because it is empty is not evidence, so the probe
names the record count and fails on a ledger shorter than the history it records.

The live tree is never written: renderers return strings, and re-parses happen in
a temporary file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LEDGER_RECORDS = re.compile(r"records:\s*(\d+)")


def load_records_module(repo: Path):
    src = repo / "src"
    if not (src / "teamwork" / "records.py").is_file():
        raise SystemExit(f"no src/teamwork/records.py under {repo}")
    sys.path.insert(0, str(src))
    from teamwork import records  # noqa: PLC0415

    return records


def engine_team_root(repo: Path) -> Path | None:
    """The team tree the engine itself resolves for this checkout.

    ``teamwork.layout.team_root_from_cwd`` is the function the CLI uses to map a
    lane worktree back to the team that owns it; the probe imports it instead of
    copying its rules, so probe and tool cannot drift apart on which team is
    under test.
    """
    src = repo / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from teamwork import layout  # noqa: PLC0415

    return layout.team_root_from_cwd(repo.resolve())


def find_team(repo: Path, team: str, explicit: str | None) -> Path:
    """The live team tree: `<root>/.pi/Teamwork/Teams/<team>`, from any checkout.

    Resolution order: an explicit `--team-root`, then the engine's own worktree
    mapping, then the `.pi/Teamwork/Teams/<team>` ancestor. The last rule is what
    reaches the owning checkout from a checkout the engine does not know about.
    """
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / "Ledger.jsonl").is_file():
            raise SystemExit(f"--team-root {root} holds no Ledger.jsonl")
        return root
    found = engine_team_root(repo)
    if found is not None:
        return found
    for base in (repo, *repo.parents):
        candidate = base / ".pi" / "Teamwork" / "Teams" / team
        if (candidate / "Ledger.jsonl").is_file():
            return candidate
        if (base / "Ledger.jsonl").is_file() and (base / "Roles").is_dir():
            return base
    raise SystemExit(f"no team tree for {team} above {repo}")


def canonical(items) -> str:
    return json.dumps(items, sort_keys=True, ensure_ascii=False, default=str)


def round_trip(name: str, source: Path, parse, render) -> tuple[str, int, list[str]]:
    """parse -> render -> parse and report every field that changed."""
    original = parse(source)
    rendered = render(original, source)
    with tempfile.TemporaryDirectory() as tmp:
        again_path = Path(tmp) / source.name
        again_path.write_text(rendered, encoding="utf-8")
        again = parse(again_path)
    problems = []
    if len(again) != len(original):
        problems.append(f"{name}: {len(original)} record(s) in, {len(again)} out")
    for before, after in zip(original, again):
        lost = {k: v for k, v in before.items() if after.get(k) != v}
        if lost:
            keys = ",".join(sorted(lost))
            problems.append(f"{name} {before.get('id')}: changed after round trip -> {keys}")
        extra = sorted(set(after) - set(before))
        if extra:
            problems.append(f"{name} {before.get('id')}: new field(s) {','.join(extra)}")
    print(f"{name}: {len(original)} record(s), round trip {'ok' if not problems else 'LOSSY'}")
    return canonical(original), len(original), problems


def cli(repo: Path, team: Path, *args: str) -> tuple[int, str, str]:
    """The real CLI, told which team tree to read.

    `cwd` alone cannot name the team: a linked worktree - or any checkout whose
    directory name differs - makes the engine derive a second team from the path,
    read an empty ledger there and call every id invisible. `TEAMWORK_ROOT` is the
    engine's documented override, so the reader is pointed at the tree this probe
    resolved and the two cannot disagree about which team is under test.
    """
    run = subprocess.run(
        [sys.executable, str(repo / "scripts" / "teamwork.py"), *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "TEAMWORK_ROOT": str(team)},
    )
    return run.returncode, run.stdout, run.stderr


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    ap.add_argument("--team", default="Teamwork", help="team name (default: Teamwork)")
    ap.add_argument(
        "--team-root",
        default=None,
        help="the live team tree to read (default: resolved the way the engine resolves it)",
    )
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    team = find_team(repo, args.team, args.team_root)
    if not team.is_dir():
        raise SystemExit(f"no team tree at {team}")
    print(f"team tree: {team}")
    records = load_records_module(repo)

    problems: list[str] = []
    families: dict[str, int] = {}

    task_ids: list[str] = []
    for queue in sorted((team / "Roles").glob("*/TaskQueue.md")):
        owner = queue.parent.name
        canon, count, issues = round_trip(
            f"tasks/{owner}",
            queue,
            records.parse_tasks,
            lambda items, path, owner=owner: records.render_tasks(items, owner, path),
        )
        task_ids.extend(t["id"] for t in json.loads(canon))
        families[f"tasks/{owner}"] = count
        problems.extend(issues)

    simple = [
        ("criteria", team / "Criteria.md", records.parse_criteria, records.render_criteria),
        ("tests", team / "Tests.md", records.parse_tests, records.render_tests),
        ("testplan", team / "TestPlan.md", records.parse_testplan, records.render_testplan),
        (
            "reviews",
            team / "Reviews.md",
            records.parse_reviews,
            lambda items, _path: records.render_reviews(items),
        ),
        (
            "disputes",
            team / "Disputes.md",
            records.parse_disputes,
            lambda items, _path: records.render_disputes(items),
        ),
    ]
    parsed_ids: dict[str, list[str]] = {"tasks": task_ids}
    for name, path, parse, render in simple:
        if not path.is_file():
            print(f"{name}: absent at {path.name}")
            families[name] = 0
            parsed_ids[name] = []
            continue
        if name == "testplan":
            before = parse(path)
            again = parse_text(parse, render(before, path), path)
            if again != before:
                problems.append("testplan: required layers changed after round trip")
            print(
                f"testplan: {len(before)} area(s), round trip {'ok' if again == before else 'LOSSY'}"
            )
            families[name] = len(before)
            parsed_ids[name] = sorted(before)
            continue
        canon, count, issues = round_trip(name, path, parse, render)
        families[name] = count
        problems.extend(issues)
        parsed_ids[name] = [row["id"] for row in json.loads(canon)]

    commands = {
        "tasks": ("task", "list", "--all"),
        "criteria": ("criteria", "list"),
        "tests": ("tests", "list"),
        "reviews": ("pr", "list"),
        "disputes": ("dispute", "list"),
    }
    allowed_exit = {"criteria": {0, 1}, "disputes": {0, 1}}
    for family, command in commands.items():
        code, out, err = cli(repo, team, *command)
        if code not in allowed_exit.get(family, {0}):
            problems.append(
                f"CLI {' '.join(command)} exited {code}: {err.strip().splitlines()[-1:]}"
            )
        seen = {tok for tok in parsed_ids.get(family, []) if tok}
        missing = sorted(tok for tok in seen if tok not in out)
        if missing:
            problems.append(
                f"{family}: {len(missing)} id(s) invisible to {' '.join(command)}: {missing[:5]}"
            )
        print(
            f"cli {' '.join(command)}: exit {code}, {len(seen)} id(s) from the files,"
            f" {len(missing)} missing"
        )

    total = sum(families.values())
    print(f"records: {total} record(s) over {len(families)} families")

    code, out, _err = cli(repo, team, "ledger", "verify")
    tail = " | ".join(out.strip().splitlines()[-2:])
    found = LEDGER_RECORDS.search(out)
    verified = int(found.group(1)) if found else -1
    print(f"ledger verify: exit {code}, {verified} record(s) verified | {tail}")
    if code != 0:
        problems.append(f"ledger verify exited {code}: {tail}")
    elif verified < 1:
        problems.append(
            f"ledger verify exited 0 having verified {verified} record(s):"
            " an empty chain is not an intact ledger"
        )
    elif verified < len(task_ids):
        problems.append(
            f"ledger holds {verified} record(s) for {len(task_ids)} task record(s):"
            " the chain is shorter than the history it records"
        )

    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"RESULT FAIL records: {len(problems)} problem(s)")
        return 1
    print(f"RESULT PASS records: {total} record(s) round-tripped with no field lost, ledger intact")
    return 0


def parse_text(parse, text: str, like: Path):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / like.name
        path.write_text(text, encoding="utf-8")
        return parse(path)


if __name__ == "__main__":
    sys.exit(main())
