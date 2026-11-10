"""Unit tests for the published privacy scanner (``scripts/privacy_scan.py``).

The scanner is the gate that keeps private data out of this repository, so the
gate itself is tested - including negative controls that prove a clean line is
*not* reported. These tests import the script directly; it is stdlib-only and has
no side effects at import time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import privacy_scan as ps  # noqa: E402  (import after sys.path setup)


def findings_for(text: str, path: str = "sample.py"):
    """Run every rule over ``text`` exactly as the scanner does."""
    return list(ps.scan_lines(text, path, "unit-test", ps.RULES, allow=[]))


def rules_hit(text: str) -> set:
    return {f["rule"] for f in findings_for(text)}


def test_planted_api_token_is_reported():
    token = "sk-" + "A1b2C3d4E5f6G7h8I9j0"  # noqa: S105 - deliberately fake
    assert "api-token" in rules_hit(f'API_KEY = "{token}"\n')


def test_planted_github_token_is_reported():
    token = "ghp_" + "0123456789abcdefghijklmnopqrstuvwxyz"
    assert "api-token" in rules_hit(f"token = {token}\n")


def test_planted_private_key_header_is_reported():
    # Assembled at runtime so the scanner does not flag this fixture file itself.
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    assert "private-key" in rules_hit(header + "\n")


def test_planted_home_path_is_reported():
    line = "path = /home/" + "realperson/projects/x"
    assert "home-path" in rules_hit(line + "\n")


def test_generic_home_user_is_not_reported():
    # CI runners legitimately use a home directory named `runner` or `user`.
    generic = "/home/" + "runner/work/repo"
    also_generic = "/home/" + "user/src"
    assert "home-path" not in rules_hit(generic + "\n")
    assert "home-path" not in rules_hit(also_generic + "\n")


def test_personal_email_is_reported():
    address = "someone@" + "private-mail.example"
    assert "personal-email" in rules_hit(f"contact: {address}\n")


def test_role_mailbox_is_allowed():
    # The project's own commit identity must never be treated as a leak.
    assert ps._email_allowed("developer@agents.nidvue.com")
    assert "personal-email" not in rules_hit("author: Developer <developer@agents.nidvue.com>\n")


def test_clean_source_lines_report_nothing():
    clean = (
        "import os\n"
        "def add(a, b):\n"
        "    return a + b\n"
        "# a comment with a url: https://github.com/VisionPZ/Teamwork\n"
        "TIMEOUT = 60\n"
        "name = 'teamwork'\n"
    )
    assert findings_for(clean) == []


def test_identical_findings_are_deduped():
    token = "sk-" + "Zz9Yy8Xx7Ww6Vv5Uu4Tt"
    raw = findings_for(f'k = "{token}"\n')
    assert len(raw) == 1
    # The same finding observed twice (e.g. tree scan + history scan) collapses.
    assert len(ps.dedupe(raw + raw)) == 1


def test_findings_on_different_lines_are_kept_separately():
    token = "sk-" + "Zz9Yy8Xx7Ww6Vv5Uu4Tt"
    raw = findings_for(f'a = "{token}"\nb = "{token}"\n')
    assert len(ps.dedupe(raw)) == 2


def test_mask_never_returns_the_whole_secret():
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    masked = ps._mask(secret)
    assert masked != secret
    assert secret not in masked


def test_summarize_counts_by_severity_and_rule():
    token = "sk-" + "Qq1Ww2Ee3Rr4Tt5Yy6Uu"
    summary = ps.summarize(findings_for(f'k = "{token}"\n'))
    assert summary["by_rule"].get("api-token") == 1
    assert summary["by_severity"].get("critical") == 1


def test_high_entropy_lookalike_is_not_a_false_positive():
    # A git SHA-256 is high entropy but is a hash, not a credential.
    sha = "9f2c" * 16
    assert "high-entropy-secret" not in rules_hit(f"digest = {sha}\n")


@pytest.mark.parametrize(
    "line",
    [
        "API_KEY = re.compile(r'x+')",
        "token = os.environ.get('TOKEN')",
        "secret = self.secret",
        "api_key = None",
    ],
)
def test_source_expressions_are_not_treated_as_secrets(line):
    assert "env-secret" not in rules_hit(line + "\n")


def test_the_role_mailbox_domain_is_allowed_and_not_private():
    """The team's own mailbox domain is legitimate, not a leak (owner decision)."""
    assert ps.IDENTITY_DOMAIN == "agents.nidvue.com"
    assert ps.IDENTITY_DOMAIN not in ps._private_domains()
    assert ps._email_allowed("ceo@" + ps.IDENTITY_DOMAIN)
    assert ps._email_allowed("developer-1@" + ps.IDENTITY_DOMAIN)


def test_the_personal_domains_are_still_private():
    private = ps._private_domains()
    assert len(private) >= 2
    for domain in private:
        assert not ps._email_allowed("someone@" + domain)
