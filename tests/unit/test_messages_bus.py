"""The bus: broadcast addressing, the repo-rooted store, one merged inbox.

The contract under test is D-20261117-CEO (items 1-3): ``--to`` accepts ``*``,
``role:<r>``, ``team:<Name>`` and ``session:<id>``; a non-local address lands on
``$TEAMWORK_BUS`` or ``<repo>/.pi/Teamwork/Bus`` under one key per address with
the mailbox shape plus ``scope``/``sender_session``/``expires``; and a local
inbox merges team rows and bus rows in one (priority, created) order. The
per-team ``Runtime/Mailbox`` store is unchanged, so no migration is tested here.
"""

from __future__ import annotations

import json
import time

import pytest

from teamwork import messages

ROSTER = ["ceo", "developer-1", "developer-2", "tester-1"]


@pytest.fixture()
def root(tmp_path, monkeypatch):
    monkeypatch.delenv(messages.BUS_ENV, raising=False)
    return tmp_path / "repo"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("*", ("all", "*")),
        ("role:developer", ("role", "developer")),
        ("team:Other", ("team", "Other")),
        ("session:s1", ("session", "s1")),
        ("developer-1", ("instance", "developer-1")),
    ],
)
def test_an_address_parses_to_a_scope_and_a_value(text, expected):
    assert messages.parse_address(text) == expected


@pytest.mark.parametrize("text", ["channel:x", "role:", "session:  ", ""])
def test_an_unknown_or_empty_address_is_refused(text):
    with pytest.raises(ValueError):
        messages.parse_address(text)


def test_a_role_is_the_instance_name_without_its_number():
    assert messages.role_of("Developer-2") == "developer"
    assert messages.role_of("Reviewer-1") == "reviewer"
    assert messages.role_of("ceo") == "ceo"


def test_a_bare_instance_still_uses_the_team_mailbox(root):
    record = messages.send(root, sender="CEO", recipient="developer-1", subject="hi")
    local = root / "Runtime" / "Mailbox" / "Developer-1" / f"{record['id']}.json"
    assert local.is_file()
    assert not messages.bus_root(root).exists()


def test_a_star_address_fans_out_to_the_whole_roster(root):
    sent = messages.send_all(root, sender="CEO", recipient="*", subject="stand up", roster=ROSTER)
    assert [r["to"] for r in sent] == ["CEO", "Developer-1", "Developer-2", "Tester-1"]
    assert [r["id"] for r in sent] == ["M-0001"] * 4
    for record in sent:
        assert [m["id"] for m in messages.inbox(root, record["to"])] == [record["id"]]
    assert messages.counts(root, "Developer-2")["pending"] == 1


def test_a_role_address_fans_out_to_that_role_only(root):
    sent = messages.send_all(
        root, sender="CEO", recipient="role:developer", subject="pair up", roster=ROSTER
    )
    assert [r["to"] for r in sent] == ["Developer-1", "Developer-2"]
    assert messages.inbox(root, "CEO") == []
    assert messages.inbox(root, "Tester-1") == []


def test_a_broadcast_with_no_target_is_refused(root):
    with pytest.raises(ValueError):
        messages.send(root, sender="CEO", recipient="*", subject="anyone?")
    with pytest.raises(ValueError):
        messages.send(root, sender="CEO", recipient="role:designer", subject="x", roster=ROSTER)


def test_only_the_team_and_session_scopes_reach_the_bus(root):
    """`*` and `role:` resolve to instances at send time and land in the team
    mailbox; `team:` and `session:` are the bus, and the bus names its folders
    with the encoded key, so no folder carries `:` or `*`."""
    fan = messages.send_all(root, sender="CEO", recipient="*", subject="stand up", roster=ROSTER)
    assert [r["to"] for r in fan] == ["CEO", "Developer-1", "Developer-2", "Tester-1"]
    assert not messages.bus_root(root).exists()
    roles = messages.send_all(
        root, sender="CEO", recipient="role:developer", subject="pair up", roster=ROSTER
    )
    assert [r["to"] for r in roles] == ["Developer-1", "Developer-2"]
    assert not messages.bus_root(root).exists()
    messages.send(root, sender="CEO", recipient="team:Teamwork", subject="freeze")
    messages.send(root, sender="CEO", recipient="session:s9", subject="ping", session="s0")
    folders = sorted(q.name for q in messages.bus_root(root).iterdir() if q.is_dir())
    assert folders == ["session-s9", "team-Teamwork"]
    assert not any(bad in q for q in folders for bad in ("*", ":", "?", '"', "<", ">", "|"))


def test_the_default_bus_is_repo_rooted(root):
    assert messages.bus_root(root) == root / ".pi" / "Teamwork" / "Bus"


def test_the_bus_root_takes_the_env_override(root, tmp_path, monkeypatch):
    target = tmp_path / "shared-bus"
    monkeypatch.setenv(messages.BUS_ENV, str(target))
    assert messages.bus_root(root) == target
    record = messages.send(root, sender="CEO", recipient="team:Other", subject="hello")
    path = target / messages.bus_key("team", "Other") / f"{record['id']}.json"
    assert path.is_file()
    assert not (root / "Runtime").exists()


def test_a_session_address_lands_on_the_bus_not_in_a_mailbox(root):
    record = messages.send(
        root, sender="Developer-1", recipient="session:s1", subject="ping", session="s0"
    )
    assert record["scope"] == "session"
    assert record["to"] == "session:s1"
    assert record["sender_session"] == "s0"
    assert record["expires"] == ""
    path = messages.bus_dir(root, "session:s1") / f"{record['id']}.json"
    assert json.loads(path.read_text(encoding="utf-8"))["subject"] == "ping"
    assert messages.inbox(root, "Developer-1") == []


def test_bus_ids_are_per_address_and_never_reused(root):
    first = messages.send(root, sender="CEO", recipient="session:s1", subject="one")
    second = messages.send(root, sender="CEO", recipient="session:s1", subject="two")
    other = messages.send(root, sender="CEO", recipient="session:s2", subject="three")
    assert (first["id"], second["id"], other["id"]) == ("M-0001", "M-0002", "M-0001")


def test_the_inbox_merges_team_and_bus_rows_in_one_order(root):
    messages.send(
        root, sender="CEO", recipient="developer-1", subject="local normal", roster=ROSTER
    )
    messages.send(
        root, sender="Tester-1", recipient="session:s1", subject="bus urgent", priority="urgent"
    )
    keys = messages.bus_keys_for("s1")
    rows = messages.inbox(root, "Developer-1", bus_keys=keys)
    assert [r["subject"] for r in rows] == ["bus urgent", "local normal"]
    assert messages.counts(root, "Developer-1", bus_keys=keys)["pending"] == 2
    assert messages.counts(root, "Developer-1")["pending"] == 1
    assert messages.inbox(root, "Developer-1", bus_keys=messages.bus_keys_for("s2")) == (
        messages.inbox(root, "Developer-1")
    )


def test_an_expired_bus_message_leaves_the_inbox(root):
    record = messages.send(root, sender="CEO", recipient="session:s1", subject="stale", ttl_hours=1)
    path = messages.bus_dir(root, "session:s1") / f"{record['id']}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["expires"]
    assert stored["expires_ts"] > time.time()
    stored["expires_ts"] = time.time() - 5
    path.write_text(json.dumps(stored), encoding="utf-8")
    keys = messages.bus_keys_for("s1")
    assert messages.inbox(root, "Developer-1", bus_keys=keys) == []
    assert messages.counts(root, "Developer-1", bus_keys=keys)["pending"] == 0


def test_a_bus_message_is_taken_and_closed_through_its_session_key(root):
    record = messages.send(root, sender="CEO", recipient="session:s1", subject="do it")
    keys = messages.bus_keys_for("s1")
    taken = messages.take(root, "Developer-1", record["id"], "Developer-1", keys)
    assert taken["state"] == "taken"
    assert taken["taken_by"] == "Developer-1"
    with pytest.raises(ValueError):
        messages.take(root, "Developer-1", record["id"], "Developer-2", keys)
    with pytest.raises(KeyError):
        messages.take(root, "Developer-1", record["id"], "Developer-1", ())
    done = messages.finish(
        root, "Developer-1", record["id"], "Developer-1", "shipped", bus_keys=keys
    )
    assert done["state"] == "done"
    assert messages.inbox(root, "Developer-1", bus_keys=keys) == []
    assert [
        m["id"] for m in messages.inbox(root, "Developer-1", states=("done",), bus_keys=keys)
    ] == [f"{keys[0]}:{record['id']}"]


def test_bus_keys_are_the_session_and_the_team_only():
    assert messages.bus_keys_for() == ()
    assert messages.bus_keys_for("s1") == (messages.bus_key("session", "s1"),)
    assert messages.bus_keys_for("s1", "Teamwork") == (
        messages.bus_key("session", "s1"),
        messages.bus_key("team", "Teamwork"),
    )


def test_a_local_and_a_bus_row_with_the_same_id_are_both_addressable(root):
    local = messages.send(
        root, sender="CEO", recipient="developer-1", subject="local", roster=ROSTER
    )
    bus = messages.send(root, sender="Tester-1", recipient="session:s1", subject="bus")
    assert (local["id"], bus["id"]) == ("M-0001", "M-0001")
    keys = messages.bus_keys_for("s1")
    rows = messages.inbox(root, "Developer-1", bus_keys=keys)
    assert [r["id"] for r in rows] == ["M-0001", f"{keys[0]}:M-0001"]
    assert f"{keys[0]}:M-0001" in "\n".join(messages.packet_lines(root, "Developer-1", keys))
    messages.take(root, "Developer-1", f"session:s1:{bus['id']}", "Developer-1", keys)
    assert [r["id"] for r in messages.inbox(root, "Developer-1", bus_keys=keys)] == ["M-0001"]
    done = messages.finish(
        root, "Developer-1", f"{keys[0]}:{bus['id']}", "Developer-1", "closed", bus_keys=keys
    )
    assert done["state"] == "done"
    assert [r["id"] for r in messages.inbox(root, "Developer-1", bus_keys=keys)] == ["M-0001"]
    assert messages.take(root, "Developer-1", "M-0001", "Developer-1", keys)["subject"] == ("local")
    assert messages.inbox(root, "Developer-1", bus_keys=keys) == []


def test_packet_lines_open_with_the_bus_urgent_first(root):
    messages.send(root, sender="CEO", recipient="developer-1", subject="later", priority="low")
    messages.send(root, sender="Tester-1", recipient="session:s1", subject="now", priority="urgent")
    block = messages.packet_lines(root, "Developer-1", bus_keys=messages.bus_keys_for("s1"))
    assert block[0].startswith("## Messages for you (2 pending: 1 urgent")
    assert "now" in block[1]
    assert any("later" in line for line in block)
