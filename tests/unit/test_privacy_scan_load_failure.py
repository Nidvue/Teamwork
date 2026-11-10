"""A privacy scanner that fails to load must be loud, not silent (T-0007).

``engine._privacy_scan`` loads the shipped ``scripts/privacy_scan.py`` by path.
It used to catch ``Exception`` and fall through to ``None``, and
``mask_secret_shapes`` returns the text byte-identical when the scanner is
``None`` - so a scanner that raised on import switched credential masking off in
every record the team writes, with no warning and no non-zero status.

The fix keeps the stated intent (a broken scanner must not break records) but
makes the failure visible: one ``teamwork: WARNING`` on stderr naming the
scanner path and the exception, and the reader is told masking is disabled. The
warning is latched, so it is emitted once per process, not once per record.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import engine

# Assembled at run time, so this file (which is itself scanned by the gate) does
# not contain the credential shape it proves is still masked on the normal path.
BLOB = "A1b2C3d4" + "E5f6G7h8" + "I9j0K1l2" + "M3n4O5p6"
JSON_SECRET_LINE = '{"apiKey": "' + BLOB + '"}'
JSON_SECRET_MASKED = '{"apiKey": "<redacted-json-secret>"}'

# The synthetic scanner is a real file that raises on exec, which is exactly the
# failure mode the old ``except Exception`` swallowed.
BROKEN_SCANNER = 'raise RuntimeError("synthetic loader failure")\n'


@pytest.fixture()
def scanner_state():
    """Restore the module-level cache, so a broken-load probe cannot leak."""

    saved = (engine._PRIVACY_SCAN, engine._PRIVACY_WARNED)
    yield
    engine._PRIVACY_SCAN, engine._PRIVACY_WARNED = saved


@pytest.fixture()
def broken_scanner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the loader at a ``scripts/`` bundle whose scanner raises on import."""

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    path = scripts / "privacy_scan.py"
    path.write_text(BROKEN_SCANNER, encoding="utf-8")
    monkeypatch.setattr(
        engine._resources,
        "asset",
        lambda name, *args, **kwargs: scripts if name == "scripts" else tmp_path / name,
    )
    return path


def _reset(scanner_state) -> None:  # noqa: ANN001 - fixture, forces a fresh load
    engine._PRIVACY_SCAN = engine._UNLOADED
    engine._PRIVACY_WARNED = False


def test_a_broken_scanner_warns_naming_the_path_and_the_exception(
    broken_scanner: Path, scanner_state, capsys: pytest.CaptureFixture[str]
) -> None:
    """(a) The failure is reported, and the record is still written."""
    _reset(scanner_state)
    capsys.readouterr()

    # A broken scanner must not break records: the text survives unmasked...
    assert engine.mask_secret_shapes(JSON_SECRET_LINE) == JSON_SECRET_LINE

    err = capsys.readouterr().err
    # ...but the failure is loud, and the reader is told what it means.
    assert "teamwork: WARNING" in err, f"the load failure was silent: {err!r}"
    assert str(broken_scanner) in err, f"the scanner path is not named: {err!r}"
    assert "RuntimeError" in err and "synthetic loader failure" in err, (
        f"the exception is not named: {err!r}"
    )
    assert "DISABLED" in err, f"the masking consequence is not stated: {err!r}"


def test_the_warning_is_emitted_once_not_per_record(
    broken_scanner: Path, scanner_state, capsys: pytest.CaptureFixture[str]
) -> None:
    """(c) The state is kept, so every later record does not re-warn."""
    _reset(scanner_state)
    capsys.readouterr()

    engine.mask_secret_shapes(JSON_SECRET_LINE)
    assert "teamwork: WARNING" in capsys.readouterr().err

    # Same process, a second record: the cache already holds the failure.
    engine.mask_secret_shapes(JSON_SECRET_LINE)
    assert capsys.readouterr().err == ""

    # Even a forced re-load attempt stays quiet: the latch, not just the cache,
    # carries the "already reported" state.
    engine._PRIVACY_SCAN = engine._UNLOADED
    engine.mask_secret_shapes(JSON_SECRET_LINE)
    assert capsys.readouterr().err == ""


def test_the_working_scanner_still_masks_and_stays_quiet(
    scanner_state, capsys: pytest.CaptureFixture[str]
) -> None:
    """(b) The normal path is unchanged: the same mask, and no warning."""
    _reset(scanner_state)
    capsys.readouterr()

    assert engine._privacy_scan() is not None
    assert engine.mask_secret_shapes(JSON_SECRET_LINE) == JSON_SECRET_MASKED
    # The mask still leaves what the gate accepts byte-identical.
    for line in ('{"api_key": "${API_KEY}"}', "sk-learn-pipeline", "ordinary prose."):
        assert engine.mask_secret_shapes(line) == line
    assert engine.mask_secret_shapes("") == ""

    assert capsys.readouterr().err == "", "the working scanner must not warn"
