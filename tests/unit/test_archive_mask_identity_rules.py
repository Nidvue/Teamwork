"""The archive mask must cover every rule the shipped privacy gate reports (T-0007).

``engine.mask_secret_shapes`` is the only thing between a reviewer's quoted
evidence and the permanent archive. It used to mask the five credential rules
only, while ``scripts/privacy_scan.py`` also reports ``personal-email`` and
``private-domain`` - and the scanner keeps those two rules armed inside a
quotation on purpose (``_QUOTED_PATH_RULES`` covers the path *shapes* only). So
an archive entry that quoted an address was written raw, and the shipped gate
then rejected the record the engine itself had just written.

The mask replaces the ADDRESS, not the finding: the reviewer's evidence stays
readable, and a mailbox the gate accepts (a role mailbox) survives byte-identical.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

# Assembled at run time so this test file does not itself contain the strings it
# proves are redacted: the private domain the gate reports and the local part of
# the address that quotes it.
PRIVATE_DOMAIN = "zhao" + ".no"
PRIVATE_LOCAL = "qxz7v2m9"
PRIVATE_ADDRESS = PRIVATE_LOCAL + "@" + PRIVATE_DOMAIN
ROLE_MAILBOX = "developer@" + engine._privacy_scan().IDENTITY_DOMAIN


def _archive(tmp_path: Path, **fields: str) -> str:
    """Write one archive entry through the engine and return the stored record."""
    t = {
        "id": "T-9999",
        "title": "probe",
        "priority": "P0",
        "branch": "developer/t-0007-probe",
        "self_note": "-",
        "evidence": "-",
        "review_evidence": "-",
        "findings": "-",
        "merge_commit": "",
    }
    t.update(fields)
    engine.archive_append(tmp_path, "developer", t, repo=tmp_path)
    return (tmp_path / "docs" / "Team" / "Archive.md").read_text(encoding="utf-8")


def _surviving_windows(value: str, text: str, size: int = 4) -> list[str]:
    """Every run of ``size`` characters of ``value`` that still occurs in ``text``.

    A partly masked address still publishes its head and its tail, so the check
    is on the runs, not on the whole string: an address that survives in pieces
    is as leaked as one that survives whole.
    """
    return [
        value[index : index + size]
        for index in range(len(value) - size + 1)
        if value[index : index + size] in text
    ]


def test_the_mask_covers_the_identity_rules_the_gate_arms(tmp_path: Path) -> None:
    """The mask's rule set is the gate's rule set, minus the two path shapes.

    Naming the rules here is the fix; a tuple that drifts from the scanner is
    the defect that produced it, so the test pins the whole set, not only the
    two new ids.
    """
    scanner = engine._privacy_scan()
    assert set(engine.CREDENTIAL_RULES) == {
        "private-key",
        "api-token",
        "env-secret",
        "json-secret",
        "high-entropy-secret",
        "personal-email",
        "private-domain",
    }
    gate_rule_ids = {rule["id"] for rule in scanner.RULES}
    assert set(engine.CREDENTIAL_RULES) <= gate_rule_ids, "every masked rule must exist in the gate"
    # The gate silences exactly two path-shape rules inside a quotation; the
    # mask covers the other seven, so the two sets are complementary.
    assert set(engine.CREDENTIAL_RULES) | scanner._QUOTED_PATH_RULES == gate_rule_ids
    assert not set(engine.CREDENTIAL_RULES) & scanner._QUOTED_PATH_RULES


def test_an_address_in_the_evidence_is_rewritten_in_the_stored_record(tmp_path: Path) -> None:
    """The address is replaced; the finding around it stays readable."""
    text = _archive(
        tmp_path,
        evidence=f"the reviewer quoted {PRIVATE_ADDRESS} in the finding",
        review_evidence=f"measured: the tree scan reports {PRIVATE_ADDRESS}",
    )

    assert "<redacted-personal-email>" in text, "the address must be named, not merely cut"
    assert PRIVATE_ADDRESS not in text, "the raw address must never reach the archive"
    assert PRIVATE_DOMAIN not in text, "not one character of the private domain may survive"
    assert not _surviving_windows(PRIVATE_LOCAL, text), "no run of the address may survive"
    assert not _surviving_windows(PRIVATE_DOMAIN, text), "no run of the domain may survive"
    # The claim the evidence makes survives, so the record is still worth reading.
    assert "the reviewer quoted" in text
    assert "measured: the tree scan reports" in text


def test_a_role_mailbox_survives_the_mask(tmp_path: Path) -> None:
    """The gate accepts the role mailbox, so the mask must leave it alone."""
    text = _archive(
        tmp_path,
        evidence=f"author and committer are Developer <{ROLE_MAILBOX}>",
    )

    assert ROLE_MAILBOX in text, "an allowlisted role mailbox must not be redacted"
    assert "<redacted-personal-email>" not in text
    assert "<redacted-private-domain>" not in text


def test_a_credential_the_old_mask_covered_is_still_redacted(tmp_path: Path) -> None:
    """Widening the mask must not drop a rule it already covered."""
    token = "sk-" + "live-" + "0123456789abcdef0123456789abcdef"
    text = _archive(tmp_path, evidence=f"a token on the exempted line is still reported: {token}")

    assert token not in text
    assert "<redacted-api-token>" in text
    assert "still reported" in text


def test_the_record_the_engine_writes_passes_the_shipped_gate(tmp_path: Path) -> None:
    """The acceptance: an engine-written archive entry survives the shipped scan."""
    scanner = engine._privacy_scan()
    text = _archive(
        tmp_path,
        evidence=f"the reviewer quoted {PRIVATE_ADDRESS} in the finding",
        review_evidence=f"measured: the tree scan reports {PRIVATE_ADDRESS}",
        findings=f"BLOCKER - the archived evidence quotes {PRIVATE_ADDRESS} verbatim",
    )

    reported = [
        finding
        for finding in scanner.scan_lines(
            text, "docs/Team/Archive.md", "archive", scanner.RULES, ()
        )
        if finding["rule"] in {"personal-email", "private-domain"}
    ]
    assert not reported, "the gate must not report the record the engine wrote"


def test_the_mask_rewrites_the_address_without_touching_the_finding(tmp_path: Path) -> None:
    """The mask replaces the value, so the mask itself is not re-reported."""
    masked = engine.mask_secret_shapes(f"the address {PRIVATE_ADDRESS} was quoted")
    assert masked == "the address <redacted-personal-email> was quoted"
    scanner = engine._privacy_scan()
    assert not list(scanner.scan_lines(masked, "", "archive", scanner.RULES, ()))
