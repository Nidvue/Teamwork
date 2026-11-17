"""AC-BUS-3: the claim register refuses a duplicate and frees an expired one.

Every test runs against a temporary project root with its own bus, so the live
``.pi/Teamwork/Bus`` of this checkout is never touched.
"""

from pathlib import Path

import pytest

from teamwork import claims, engine

PROJECT = Path("proj")


@pytest.fixture
def root(tmp_path, monkeypatch):
    team = tmp_path / PROJECT / ".pi" / "Teamwork" / "Teams" / "Team"
    team.mkdir(parents=True)
    monkeypatch.delenv("TEAMWORK_ROOT", raising=False)
    monkeypatch.delenv("TEAMWORK_BUS", raising=False)
    monkeypatch.setenv("TEAMWORK_ROOT", str(team))
    return team


@pytest.fixture
def bus(root, monkeypatch, tmp_path):
    path = tmp_path / "bus"
    monkeypatch.setenv("TEAMWORK_BUS", str(path))
    return path


def clock(monkeypatch, moment):
    monkeypatch.setattr(claims, "_now", lambda: moment)


def test_bus_root_honours_the_override_and_falls_back_to_the_project(root, monkeypatch, tmp_path):
    monkeypatch.delenv("TEAMWORK_BUS", raising=False)
    assert claims.bus_root(root) == tmp_path / PROJECT / ".pi" / "Teamwork" / "Bus"
    monkeypatch.setenv("TEAMWORK_BUS", str(tmp_path / "elsewhere"))
    assert claims.bus_root(root) == tmp_path / "elsewhere"


def test_a_duplicate_is_refused_and_names_the_holder(root, bus):
    first = claims.add(root, by="Developer-3", value="src/teamwork/engine.py", kind="path")
    assert first["id"] == "C-0001"
    with pytest.raises(ValueError) as refused:
        claims.add(root, by="Developer-1", value="src/teamwork/engine.py", kind="path")
    assert "Developer-3" in str(refused.value)
    assert "C-0001" in str(refused.value)
    assert len(list(claims.claims_dir(root).glob("C-*.json"))) == 1


def test_the_same_holder_re_adding_refreshes_and_keeps_one_record(root, bus, monkeypatch):
    clock(monkeypatch, 1000.0)
    first = claims.add(root, by="Developer-3", value="src/a.py", kind="path", ttl=10)
    clock(monkeypatch, 1300.0)
    second = claims.add(root, by="Developer-3", value="src/a.py", kind="path", ttl=10)
    assert second["id"] == first["id"]
    assert second["expires_ts"] == 1900.0
    assert len(list(claims.claims_dir(root).glob("C-*.json"))) == 1


def test_an_expired_claim_stops_refusing(root, bus, monkeypatch):
    clock(monkeypatch, 1000.0)
    claims.add(root, by="Developer-3", value="src/a.py", kind="path", ttl=1)
    clock(monkeypatch, 1061.0)
    second = claims.add(root, by="Developer-1", value="src/a.py", kind="path")
    assert second["id"] == "C-0002"
    assert claims.check(root, "src/a.py")["by"] == "Developer-1"
    assert [record["id"] for record in claims.list_live(root)] == ["C-0002"]


def test_check_reports_the_live_holder_and_then_nothing(root, bus, monkeypatch):
    clock(monkeypatch, 1000.0)
    assert claims.check(root, "T-0134") is None
    claims.add(root, by="Developer-3", value="T-0134", kind="task", ttl=1)
    assert claims.check(root, "T-0134")["by"] == "Developer-3"
    clock(monkeypatch, 1061.0)
    assert claims.check(root, "T-0134") is None


def test_release_frees_the_value_and_an_unknown_id_is_not_found(root, bus):
    record = claims.add(root, by="Developer-3", value="bus", kind="area")
    assert claims.release(root, record["id"])["value"] == "bus"
    assert claims.check(root, "bus") is None
    assert claims.release(root, "C-0099") is None
    assert claims.add(root, by="Developer-1", value="bus", kind="area")["by"] == "Developer-1"


def test_an_absolute_and_a_relative_path_are_one_value(root, bus, tmp_path):
    claims.add(root, by="Developer-3", value="src/a.py", kind="path")
    absolute = str(tmp_path / PROJECT / "src" / "a.py")
    with pytest.raises(ValueError):
        claims.add(root, by="Developer-1", value=absolute, kind="path")


def test_a_claimed_directory_refuses_a_file_beneath_it_and_names_the_holder(root, bus):
    directory = claims.add(root, by="Developer-3", value="src/teamwork", kind="path")
    assert directory["id"] == "C-0001"
    with pytest.raises(ValueError) as refused:
        claims.add(root, by="Developer-1", value="src/teamwork/engine.py", kind="path")
    assert "Developer-3" in str(refused.value)
    assert "C-0001" in str(refused.value)
    assert len(list(claims.claims_dir(root).glob("C-*.json"))) == 1


def test_a_claimed_file_refuses_a_directory_above_it(root, bus):
    claims.add(root, by="Developer-3", value="src/teamwork/engine.py", kind="path")
    with pytest.raises(ValueError, match="Developer-3"):
        claims.add(root, by="Developer-1", value="src/teamwork", kind="path")
    assert len(list(claims.claims_dir(root).glob("C-*.json"))) == 1


def test_check_reports_the_directory_claim_covering_a_file(root, bus):
    claims.add(root, by="Developer-3", value="src/teamwork", kind="path")
    assert claims.check(root, "src/teamwork/engine.py")["id"] == "C-0001"
    assert claims.check(root, "src/other/engine.py") is None


def test_a_sibling_with_the_same_prefix_is_not_covered(root, bus):
    claims.add(root, by="Developer-3", value="src/teamwork", kind="path")
    sibling = claims.add(root, by="Developer-1", value="src/teamwork2/a.py", kind="path")
    assert sibling["id"] == "C-0002"
    assert claims.check(root, "src/teamwork2/a.py")["id"] == "C-0002"


def test_the_cli_refuses_a_file_under_a_claimed_directory(root, bus, capsys):
    assert engine.main(["claim", "add", "--by", "Developer-3", "--path", "src/teamwork"]) == 0
    assert "C-0001" in capsys.readouterr().out
    nested = ["claim", "add", "--by", "Developer-1", "--path", "src/teamwork/engine.py"]
    assert engine.main(nested) == 2
    refused = capsys.readouterr().out
    assert "Developer-3" in refused and "C-0001" in refused
    assert engine.main(["claim", "check", "src/teamwork/engine.py"]) == 0
    assert "C-0001" in capsys.readouterr().out


def test_a_non_path_claim_does_not_cover_a_prefix(root, bus):
    claims.add(root, by="Developer-3", value="bus", kind="area")
    assert claims.add(root, by="Developer-1", value="bus/broadcast", kind="area")["id"] == "C-0002"


def test_a_claim_needs_a_positive_ttl_and_a_value(root, bus):
    with pytest.raises(ValueError, match="--ttl"):
        claims.add(root, by="Developer-3", value="src/a.py", kind="path", ttl=0)
    with pytest.raises(ValueError, match="value"):
        claims.add(root, by="Developer-3", value="  ", kind="path")
    with pytest.raises(ValueError, match="holder"):
        claims.add(root, by=" ", value="src/a.py", kind="path")
    with pytest.raises(ValueError, match="kind"):
        claims.add(root, by="Developer-3", value="src/a.py", kind="file")


def test_the_cli_registers_the_claim_commands(root, bus, capsys):
    assert engine.main(["claim", "add", "--by", "Developer-3", "--path", "src/a.py"]) == 0
    assert "C-0001" in capsys.readouterr().out
    assert engine.main(["claim", "add", "--by", "Developer-1", "--path", "src/a.py"]) == 2
    refused = capsys.readouterr().out
    assert "Developer-3" in refused and "C-0001" in refused
    assert engine.main(["claim", "check", "src/a.py"]) == 0
    assert engine.main(["claim", "check", "src/b.py"]) == 1
    assert engine.main(["claim", "list"]) == 0
    assert "src/a.py" in capsys.readouterr().out
    assert engine.main(["claim", "release", "C-0001"]) == 0
    assert engine.main(["claim", "list"]) == 0
    assert "no live claims" in capsys.readouterr().out
    assert engine.main(["claim", "release", "C-0099"]) == 2
