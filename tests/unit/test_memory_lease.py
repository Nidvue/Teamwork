"""Unit tests for the role memory lease record and instance naming.

The lease is what makes "one instance of a role revises the role's shared memory
at a time" a rule instead of a convention: a small JSON state file under
``Runtime/Locks/``, read and written by the engine, with an expiry so a dead lane
cannot freeze a role for good. These tests pin the pure parts - the record's
liveness, the remaining time, the message a refused writer sees, and the name the
next instance of a role gets - without running a command.
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

from teamwork import engine


def write_claim(root: Path, role: str, **fields) -> Path:
    path = engine.memory_claim_path(root, role)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "role": role,
        "instance": "Architect-1",
        "token": "1.0",
        # Relative to now, never a fixed date: a hard-coded stamp turns "fresh"
        # into "held for hours" the moment the wall clock passes it.
        "acquired": datetime.datetime.now().isoformat(timespec="seconds"),
        "expires_ts": time.time() + 600,
        "minutes": 10,
        "explicit": True,
        "reason": "rewrite the interface notes",
    }
    record.update(fields)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def make_instance(root: Path, name: str) -> None:
    (root / "Agents" / name).mkdir(parents=True, exist_ok=True)


def make_role(root: Path, role: str) -> None:
    (root / "Roles" / engine.pascal(role)).mkdir(parents=True, exist_ok=True)


def test_the_claim_path_is_per_role_not_per_instance(tmp_path: Path) -> None:
    assert engine.memory_claim_path(tmp_path, "architect") == engine.memory_claim_path(
        tmp_path, "Architect-2"
    )
    assert engine.memory_claim_path(tmp_path, "architect").name == "memory-architect.claim"


def test_a_live_claim_is_read_back_with_its_holder(tmp_path: Path) -> None:
    write_claim(tmp_path, "architect")
    claim = engine.read_memory_claim(tmp_path, "architect")
    assert claim["instance"] == "Architect-1"
    assert claim["explicit"] is True
    assert 9 <= engine.memory_claim_remaining(claim) <= 10
    assert "Architect-1 is revising the architect memory" in engine.memory_holder_line(claim)


def test_an_expired_claim_is_free(tmp_path: Path) -> None:
    write_claim(tmp_path, "architect", expires_ts=time.time() - 1)
    assert engine.read_memory_claim(tmp_path, "architect") == {}


def test_a_missing_or_corrupt_claim_is_free(tmp_path: Path) -> None:
    assert engine.read_memory_claim(tmp_path, "architect") == {}
    path = engine.memory_claim_path(tmp_path, "architect")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert engine.read_memory_claim(tmp_path, "architect") == {}


def test_clearing_a_claim_requires_the_matching_token(tmp_path: Path) -> None:
    write_claim(tmp_path, "architect", token="mine")
    assert engine._clear_memory_claim(tmp_path, "architect", "someone-else") is False
    assert engine.read_memory_claim(tmp_path, "architect")["token"] == "mine"
    assert engine._clear_memory_claim(tmp_path, "architect", "mine") is True
    assert engine.read_memory_claim(tmp_path, "architect") == {}


def test_the_next_instance_name_never_reuses_a_name(tmp_path: Path) -> None:
    make_role(tmp_path, "architect")
    assert engine.next_instance_name(tmp_path, "architect") == "Architect"
    make_instance(tmp_path, "Architect")
    # A bare role name is that role's first instance, so the second lane is -2.
    assert engine.next_instance_name(tmp_path, "architect") == "Architect-2"
    make_instance(tmp_path, "Architect-2")
    make_instance(tmp_path, "Architect-4")
    assert engine.next_instance_name(tmp_path, "architect") == "Architect-3"


def test_a_bare_role_actor_names_the_role_pool(tmp_path: Path) -> None:
    make_role(tmp_path, "architect")
    make_instance(tmp_path, "Architect-1")
    make_instance(tmp_path, "Architect-2")
    assert engine.memory_actor(tmp_path, "architect", "") == "Architect"
    assert engine.memory_actor(tmp_path, "architect", "architect-2") == "Architect-2"


def test_one_instance_of_a_role_may_be_named_by_its_bare_role(tmp_path: Path) -> None:
    """Backward compatibility: a single-instance role still accepts its role name."""
    make_role(tmp_path, "architect")
    make_instance(tmp_path, "Architect")
    assert (
        engine.memory_actor(tmp_path, "architect", "architect", require_instance=True)
        == "Architect"
    )


def test_the_ceo_may_hold_the_pen_of_any_role(tmp_path: Path) -> None:
    make_role(tmp_path, "architect")
    make_instance(tmp_path, "Architect-1")
    assert engine.memory_actor(tmp_path, "architect", "ceo") == "CEO"


# --------------------------------------------------------------------------- #
# a stalled lease: contest, then the arbiter rules
# --------------------------------------------------------------------------- #


def test_a_lease_older_than_the_stall_threshold_is_slow(tmp_path: Path) -> None:
    started = (datetime.datetime.now() - datetime.timedelta(minutes=20)).isoformat(
        timespec="seconds"
    )
    write_claim(tmp_path, "architect", acquired=started)
    claim = engine.read_memory_claim(tmp_path, "architect")
    age = engine.memory_claim_age(claim)
    assert age is not None and age >= 20
    assert engine.memory_claim_is_slow(tmp_path, claim) is True


def test_a_fresh_lease_is_not_slow(tmp_path: Path) -> None:
    write_claim(tmp_path, "architect")
    claim = engine.read_memory_claim(tmp_path, "architect")
    assert engine.memory_claim_is_slow(tmp_path, claim) is False


def test_the_arbiter_is_the_cto_and_folds_up_when_it_is_unstaffed(tmp_path: Path) -> None:
    make_role(tmp_path, "architect")
    make_role(tmp_path, "cto")
    make_role(tmp_path, "ceo")
    make_instance(tmp_path, "CTO")
    make_instance(tmp_path, "CEO")
    assert engine.memory_arbiter(tmp_path, "architect") == ("cto", [])
    (tmp_path / "Roles" / "CTO").rmdir()
    # A slim roster has no CTO: the request folds up to the CEO and says so.
    assert engine.memory_arbiter(tmp_path, "architect") == ("ceo", ["cto"])


def test_a_party_never_rules_its_own_lease(tmp_path: Path) -> None:
    for role in ("architect", "cto", "ceo"):
        make_role(tmp_path, role)
    make_instance(tmp_path, "CTO")
    make_instance(tmp_path, "CEO")
    # A CTO's own memory goes to the CEO, and the skipped seat is stated.
    assert engine.memory_arbiter(tmp_path, "cto") == ("ceo", ["cto"])
    assert engine.memory_arbiter(tmp_path, "architect") == ("cto", [])


def test_no_seat_rules_when_the_holder_is_the_whole_chain(tmp_path: Path) -> None:
    make_role(tmp_path, "ceo")
    make_instance(tmp_path, "CEO")
    assert engine.memory_arbiter(tmp_path, "ceo") == ("", ["cto", "ceo"])
