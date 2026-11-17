"""The claim register: a live, expiring claim that refuses a duplicate.

Why this exists: two sessions editing one file is the collision M10 exists to
stop, and a warning after the write is a collision reported after the damage. A
claim is a record with a value (a path, a task, an area), a holder, a TTL and an
expiry. ``claim add`` refuses when a live claim already holds the value and names
the holder, so the second session learns it before it writes.

The contract, frozen as v1 (D-20261117-CEO):

* ``bus_root(root)`` - ``$TEAMWORK_BUS`` when set, else
  ``<project>/.pi/Teamwork/Bus``;
* store - ``<bus_root>/claims/C-nnnn.json``, mutated under ``<bus_root>/.lock``;
* **add** - refuses a live, unexpired claim on the same value, or on a path a
  claimed directory covers (or that covers a claimed path); the same holder
  re-adding refreshes the TTL and gets the same id back (the second-call case);
* **check** - the live holder of a value or of a path covering it, or nothing;
* **list** - the live register only, expired claims excluded;
* **release** - drop one claim by id, freeing its value.

Expiry is the garbage collection: a claim that outlives its TTL stops refusing,
so a dead session never blocks a live one and no daemon is needed.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .io import atomic_write, lock
from .layout import project_of

DIR_CLAIMS = "claims"
TTL_DEFAULT = 120
KINDS = ("path", "task", "area")
STAMP = "%Y-%m-%dT%H:%M:%S"


def bus_root(root: Path) -> Path:
    override = os.environ.get("TEAMWORK_BUS")
    if override:
        return Path(override).expanduser()
    return project_of(root) / ".pi" / "Teamwork" / "Bus"


def claims_dir(root: Path) -> Path:
    return bus_root(root) / DIR_CLAIMS


def claims_lock(root: Path) -> Path:
    return bus_root(root) / ".lock"


def _now() -> float:
    return time.time()


def _iso(stamp: float) -> str:
    return time.strftime(STAMP, time.localtime(stamp))


def _paths(root: Path) -> list:
    folder = claims_dir(root)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("C-*.json"))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(record, indent=2, sort_keys=True) + "\n")


def _records(root: Path) -> list:
    return [(path, _read(path)) for path in _paths(root)]


def live(record: dict, now: float | None = None) -> bool:
    moment = _now() if now is None else now
    return float(record.get("expires_ts") or 0) > moment


def next_id(root: Path) -> str:
    high = 0
    for path in _paths(root):
        try:
            high = max(high, int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"C-{high + 1:04d}"


def normalise(root: Path, value: str, kind: str) -> str:
    """One value per thing: an absolute and a relative path are the same claim."""
    value = value.strip()
    if kind != "path":
        return value
    base = project_of(root)
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    try:
        path = path.resolve()
        return path.relative_to(base.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def list_live(root: Path) -> list:
    now = _now()
    return [record for _, record in _records(root) if live(record, now)]


def overlaps(record: dict, value: str) -> bool:
    """A claimed directory covers every path beneath it, and vice versa."""
    held = str(record.get("value") or "").strip("/")
    new = value.strip().strip("/")
    if held == new:
        return True
    if record.get("kind") != "path":
        return False
    return held.startswith(new + "/") or new.startswith(held + "/")


def check(root: Path, value: str) -> dict | None:
    now = _now()
    raw = value.strip()
    wanted = [raw, normalise(root, raw, "path")]
    for _, record in _records(root):
        if not live(record, now):
            continue
        if record.get("value") in wanted or any(overlaps(record, v) for v in wanted):
            return record
    return None


def add(root: Path, *, by: str, value: str, kind: str = "area", ttl: int | None = None) -> dict:
    ttl = TTL_DEFAULT if ttl is None else int(ttl)
    if ttl <= 0:
        raise ValueError("--ttl must be a positive number of minutes")
    if not by.strip():
        raise ValueError("a claim needs a holder: --by <instance>")
    if not value.strip():
        raise ValueError(f"a claim needs a value: --{' or --'.join(KINDS)}")
    if kind not in KINDS:
        raise ValueError(f"unknown claim kind '{kind}'; expected one of {', '.join(KINDS)}")
    value = normalise(root, value, kind)
    now = _now()
    with lock(claims_lock(root)):
        for path, record in _records(root):
            if not live(record, now) or not overlaps(record, value):
                continue
            if record.get("value") == value and record.get("by") == by:
                record["ttl"] = ttl
                record["expires_ts"] = now + ttl * 60
                record["expires"] = _iso(record["expires_ts"])
                _write(path, record)
                return record
            if record.get("by") != by:
                raise ValueError(
                    f"{value} is claimed by {record.get('by')} ({record.get('id')}, "
                    f"expires {record.get('expires')}); release it or claim another value"
                )
        record = {
            "id": next_id(root),
            "kind": kind,
            "value": value,
            "by": by,
            "created": _iso(now),
            "created_ts": now,
            "ttl": ttl,
            "expires": _iso(now + ttl * 60),
            "expires_ts": now + ttl * 60,
        }
        _write(claims_dir(root) / f"{record['id']}.json", record)
        return record


def release(root: Path, claim_id: str) -> dict | None:
    with lock(claims_lock(root)):
        for path, record in _records(root):
            if record.get("id") != claim_id:
                continue
            path.unlink()
            return record
    return None


def add_parsers(sub, common) -> None:
    """`claim` command surface: add, check, list, release."""
    s = sub.add_parser(
        "claim",
        parents=[common],
        help="claim register: a live, expiring claim that refuses a duplicate",
    )
    csub = s.add_subparsers(dest="claim_cmd", required=True)
    p = csub.add_parser("add", parents=[common], help="take a claim, or refuse a live duplicate")
    p.add_argument("--by", required=True, help="the instance taking the claim")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--path", help="a file or directory another session must not write")
    group.add_argument("--task", help="a task id")
    group.add_argument("--area", help="an area name")
    p.add_argument("--ttl", type=int, default=TTL_DEFAULT, help="minutes until it expires")
    p.set_defaults(func=cmd_claim)
    p = csub.add_parser("check", parents=[common], help="who holds a value right now")
    p.add_argument("value")
    p.set_defaults(func=cmd_claim)
    p = csub.add_parser("list", parents=[common], help="the live claim register")
    p.add_argument("--json", action="store_true", help="one JSON object per claim")
    p.set_defaults(func=cmd_claim)
    p = csub.add_parser("release", parents=[common], help="drop a claim and free its value")
    p.add_argument("claim_id")
    p.set_defaults(func=cmd_claim)


def _kind_value(args) -> tuple:
    for kind in KINDS:
        value = getattr(args, kind, None)
        if value:
            return kind, value
    raise ValueError(f"one of {', '.join('--' + k for k in KINDS)} is required")


def cmd_claim(args) -> int:
    from . import engine

    root = engine.project_root(args)
    verb = args.claim_cmd
    if verb == "add":
        kind, value = _kind_value(args)
        try:
            record = add(root, by=args.by, value=value, kind=kind, ttl=args.ttl)
        except ValueError as exc:
            print(f"# {exc}")
            return 2
        print(
            f"{record['id']} {record['kind']} {record['value']} "
            f"held by {record['by']} until {record['expires']}"
        )
        return 0
    if verb == "check":
        held = check(root, args.value)
        if held is None:
            print(f"# {args.value.strip()} is free")
            return 1
        print(
            f"{held['id']} {held['kind']} {held['value']} "
            f"held by {held['by']} until {held['expires']}"
        )
        return 0
    if verb == "list":
        records = list_live(root)
        if not records:
            print("# no live claims")
            return 0
        for record in records:
            if args.json:
                print(json.dumps(record, sort_keys=True))
                continue
            print(
                f"{record['id']} {record['kind']} {record['value']} "
                f"held by {record['by']} until {record['expires']}"
            )
        return 0
    freed = release(root, args.claim_id)
    if freed is None:
        print(f"# no claim '{args.claim_id}'")
        return 2
    print(f"{freed['id']} released; {freed['value']} was held by {freed['by']}")
    return 0
