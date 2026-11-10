"""`release-exceptions.json` admits a release its tag cannot carry - and only that.

Why this exists: rule R2 of the release gate says every published version must be
traceable from a commit, and Architecture.md section 11.4 lets a version be
published without a tag only when `release-exceptions.json` records *why*, with
measured evidence. That escape hatch is the one place a false claim of
traceability can enter the project, so the record itself has to be graded:

* it must be valid JSON with exactly the documented keys, a semver version, a
  non-empty reason and evidence and an ISO recording date (the checker's own
  `load_exceptions` is the authority, and it is loaded here by path so this test
  and the gate cannot disagree);
* the evidence must *name a measurement* - a digest, a revision, or a command -
  because "we could not push the commit" is an assertion, and the section asks
  for the artifact that proves it;
* the version it names must NOT also be tagged: an exception for a version that
  is traceable is drift, not a pass (`_stale_exceptions`);
* the version `src/teamwork/version.py` currently carries must never be
  excepted. The current version is the one about to be published; exempting it
  would let the gate publish anything.

The file is located with `git ls-files`, so moving it is a build failure here and
not a silent "no exceptions" pass: `[]` and "file not found" must never look the
same. Mutants write bad records into `tmp_path`, so the tracked file is never
touched.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
CHECKER = SCRIPTS / "check_release_consistency.py"
VERSION_FILE = "src/teamwork/version.py"
EXCEPTIONS_NAME = "release-exceptions.json"

#: Keys the record must carry, per Architecture.md section 11.4.
REQUIRED_KEYS = {"version", "reason", "evidence", "recorded"}

#: A digest, a revision or a command is a measurement; a bare sentence is not.
MEASUREMENT_RE = (
    r"sha256|sha1|\b[0-9a-f]{7,64}\b|`[^`]+`|\bgit\s+(?:rev-list|log|show|rev-parse|cat-file)\b"
    r"|\b(?:sha256sum|shasum|pytest|grep|npm\s+view)\b"
)

#: Reasons that admit nothing - they only restate that the record exists.
EMPTY_REASONS = {"n/a", "na", "none", "unknown", "not applicable", "todo", "tbd", "see above"}


def load_checker():
    """Load the gate script by path; it is a script, not an importable package."""
    spec = importlib.util.spec_from_file_location("check_release_consistency_trace", CHECKER)
    if spec is None or spec.loader is None:
        raise ImportError(f"{CHECKER}: not an importable Python file")
    module = importlib.util.module_from_spec(spec)
    # `@dataclass` resolves annotations through `sys.modules[cls.__module__]`, so the
    # module has to be registered before it executes; the checker defines dataclasses.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


@pytest.fixture(scope="module")
def checker():
    return load_checker()


#: The record's version shape is the gate's, never a local copy: `record_problems`
#: grades with the same compiled pattern `load_exceptions` enforces, so section
#: 11.4's schema and this test cannot drift apart again (T-0016 widened it to admit
#: a published-but-untaggable version such as npm's `0.0.0-stage`).
PUBLISHED_VERSION = load_checker().PUBLISHED_VERSION


def tracked_exceptions_path(repo_root: Path = REPO_ROOT) -> Path:
    """The record's location, asked of git rather than assumed."""
    result = subprocess.run(
        ["git", "ls-files", "--", f"*{EXCEPTIONS_NAME}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked, (
        f"no tracked {EXCEPTIONS_NAME}: the gate cannot admit anything, not even nothing"
    )
    assert len(tracked) == 1, (
        f"{EXCEPTIONS_NAME} is tracked at {tracked}; there must be exactly one"
    )
    return repo_root / tracked[0]


def raw_entries(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list), "the record's top level must be a JSON array"
    return data


def current_version(repo_root: Path = REPO_ROOT) -> str:
    """Read the version the way the gate does: parse `__version__`, do not guess."""
    text = (repo_root / VERSION_FILE).read_text(encoding="utf-8")
    match = __import__("re").search(r'^__version__\s*=\s*"([^"]+)"', text, __import__("re").M)
    assert match, f"{VERSION_FILE} has no __version__ literal"
    return match.group(1)


def tags(repo_root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*"], cwd=repo_root, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def record_problems(
    entries: list[dict],
    tagged: set[str],
    current: str,
    *,
    version_pattern: re.Pattern[str] = PUBLISHED_VERSION,
) -> list[str]:
    """Every reason a *record* is not a measurement, given the tags and version."""
    problems: list[str] = []

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entry {index}"
        if not isinstance(entry, dict):
            problems.append(f"{label}: not a JSON object")
            continue
        if set(entry) != REQUIRED_KEYS:
            problems.append(f"{label}: keys {sorted(entry)} != {sorted(REQUIRED_KEYS)}")
            continue
        version = entry["version"]
        if not version_pattern.fullmatch(str(version)):
            problems.append(f"{label}: version {version!r} is not an npm version")
        if version in seen:
            problems.append(f"{label}: duplicate version {version}")
        seen.add(version)
        reason = str(entry["reason"]).strip()
        if len(reason) < 20 or reason.lower().strip(" .") in EMPTY_REASONS:
            problems.append(f"{label}: reason {reason!r} admits nothing")
        evidence = str(entry["evidence"]).strip()
        if not re.search(MEASUREMENT_RE, evidence):
            problems.append(f"{label}: evidence {evidence[:60]!r} names no measurement")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry["recorded"])):
            problems.append(f"{label}: recorded {entry['recorded']!r} is not YYYY-MM-DD")
        if f"v{version}" in tagged:
            problems.append(f"{label}: {version} is tagged, so it needs no exception")
        if str(version) == current:
            problems.append(
                f"{label}: {version} is the version in the tree; it must never be excepted"
            )
    return problems


# --------------------------------------------------------------------------- #
# the real record
# --------------------------------------------------------------------------- #


def test_the_record_is_tracked_valid_json_with_the_documented_schema(checker):
    path = tracked_exceptions_path()
    entries = checker.load_exceptions(path)
    raw = raw_entries(path)
    assert len(entries) == len(raw), (
        "the checker accepted a different entry count than the file holds"
    )


def test_every_entry_names_a_measurement_and_no_exception_covers_the_current_version():
    path = tracked_exceptions_path()
    problems = record_problems(raw_entries(path), set(tags()), current_version())
    assert problems == []


def test_no_exception_names_a_version_that_is_already_tagged():
    """An exception for a traceable version is drift; the gate must say so."""
    entries = raw_entries(tracked_exceptions_path())
    assert load_checker()._stale_exceptions(entries, tags()) == []


def test_the_current_version_is_not_excepted_and_is_not_tagged():
    """The measurement that makes the previous line meaningful on this revision."""
    entries = raw_entries(tracked_exceptions_path())
    current = current_version()
    assert current not in {str(entry["version"]) for entry in entries}, current
    assert f"v{current}" not in set(tags()), f"v{current} is already tagged - bump the version"


def test_the_locator_and_the_version_reader_are_not_vacuous():
    """A missing file and `[]` must not look the same, and the version must parse."""
    assert tracked_exceptions_path().is_file()
    version = current_version()
    assert version.count(".") == 2 and version.split(".")[0].isdigit(), version
    assert tags(), "no v* tags at all would make the stale-exception rule vacuous"


# --------------------------------------------------------------------------- #
# mutants: a bad record must be rejected by the same rules
# --------------------------------------------------------------------------- #


def _entry(**overrides) -> dict:
    base = {
        "version": "1.1.1",
        "reason": "published from a workspace whose commit was never pushed, so no commit exists",
        "evidence": "payload digest 726bc547afc41ead matches no commit in git rev-list --all",
        "recorded": "2026-10-20",
    }
    base.update(overrides)
    return base


def test_the_clean_synthetic_entry_is_accepted():
    """The control: the mutant grid below is only meaningful against a clean entry."""
    assert record_problems([_entry()], {"v1.1.2"}, "1.1.5") == []


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"evidence": "the commit could not be pushed"}, "names no measurement"),
        ({"reason": "n/a"}, "admits nothing"),
        ({"version": "1.1"}, "is not an npm version"),
        ({"version": "not-a-version"}, "is not an npm version"),
        ({"recorded": "20-10-2026"}, "is not YYYY-MM-DD"),
        ({"version": "1.1.2"}, "is tagged"),
        ({"version": "1.1.5"}, "must never be excepted"),
    ],
)
def test_each_bad_field_is_reported(mutation, expected):
    problems = record_problems([_entry(**mutation)], {"v1.1.2"}, "1.1.5")
    assert any(expected in problem for problem in problems), problems


def test_a_prerelease_version_is_accepted_because_the_gate_admits_it():
    """Deliberate, not accidental: section 11.4's schema is `PUBLISHED_VERSION`.

    T-0016 widened the frozen contract so npm's staged-publish placeholder
    (`0.0.0-stage`) can be named in the record; T-0015's local `X.Y.Z` literal had
    not caught up. This case pins the widening to the gate's own pattern.
    """
    problems = record_problems([_entry(version="0.0.0-stage")], {"v1.1.2"}, "1.1.5")
    assert problems == []


def test_a_missing_key_and_a_duplicate_version_are_reported():
    missing = _entry()
    del missing["evidence"]
    assert any("keys" in problem for problem in record_problems([missing], set(), "9.9.9"))
    duplicated = record_problems([_entry(), _entry()], {"v1.1.0"}, "9.9.9")
    assert any("duplicate version" in problem for problem in duplicated), duplicated


def test_the_checker_rejects_a_bad_record_written_to_a_scratch_file(tmp_path):
    """The authority itself bites: schema drift is exit 2, not a silent pass."""
    path = tmp_path / EXCEPTIONS_NAME
    path.write_text(json.dumps([{"version": "1.1.1"}]), encoding="utf-8")
    checker = load_checker()
    with pytest.raises(checker.InputError):
        checker.load_exceptions(path)


def test_the_checker_accepts_the_empty_initial_state(tmp_path):
    """`[]` is legal; an absent file is not - the two must not be confused."""
    path = tmp_path / EXCEPTIONS_NAME
    path.write_text("[]", encoding="utf-8")
    # Loaded once: `InputError` is defined by the loaded module, and a second load
    # would produce a different class that `pytest.raises` cannot match.
    checker = load_checker()
    assert checker.load_exceptions(path) == []
    with pytest.raises(checker.InputError):
        checker.load_exceptions(tmp_path / "absent.json")


def test_a_moved_record_breaks_the_locator(tmp_path):
    """`git ls-files` is the locator: a renamed file is a failure, not an empty set."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=False)
    with pytest.raises(AssertionError):
        tracked_exceptions_path(tmp_path)
