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
_ADDED = str(SCRIPTS) not in sys.path
if _ADDED:
    sys.path.insert(0, str(SCRIPTS))
try:
    import privacy_scan as ps  # noqa: E402  (import after sys.path setup)
finally:
    # Leaving scripts/ on sys.path would shadow the real ``teamwork`` package
    # with ``scripts/teamwork.py`` for every later test in the session.
    if _ADDED:
        sys.path.remove(str(SCRIPTS))


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
        "# a comment with a url: https://github.com/Nidvue/Teamwork\n"
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


def test_dotted_identifiers_are_not_secrets():
    """Regression: ``tokens = tokenize.generate_tokens(...)`` is code, not a key.

    CI's privacy job failed on the new hygiene test because the env-secret rule
    read the dotted callable on the right-hand side as a credential.
    """
    assert "env-secret" not in rules_hit("tokens = tokenize.generate_tokens(stream)\n")
    assert "env-secret" not in rules_hit("key = settings.api_key\n")
    assert "env-secret" not in rules_hit("token = self.client_token\n")


def test_a_real_assigned_secret_is_still_reported():
    secret = "Zx9" + "Qw8Er7Ty6Ui5Op4As3Df2Gh1Jk"
    assert "env-secret" in rules_hit(f'API_TOKEN = "{secret}"\n')


# --------------------------------------------------------------------------- #
# agent-host configuration: the local secret most likely to reach a public tree
# --------------------------------------------------------------------------- #


def test_agent_host_config_path_in_a_line_is_reported():
    # Fragmented so this test file does not trip the rule it is testing.
    line = "token_file = ~/.pi/" + "agent/auth.json\n"
    assert "agent-config" in rules_hit(line)


def test_team_workspace_path_is_not_host_config():
    line = "workspace: .pi/" + "Teamwork/Teams/Demo\n"
    assert "agent-config" not in rules_hit(line)


def test_other_agent_hosts_config_paths_are_reported():
    for path in (
        ".claude/" + "settings.local.json",
        ".codex/" + "auth.json",
        ".gemini/" + "oauth_creds.json",
    ):
        assert "agent-config" in rules_hit(f"config: {path}\n"), path


def test_json_config_with_a_live_credential_is_reported():
    payload = "A1b2C3d4" + "E5f6G7h8" + "I9j0K1l2"
    assert "json-secret" in rules_hit('{"apiKey": "' + payload + '"}\n')
    assert "json-secret" in rules_hit('{"access_token": "' + payload + '"}\n')


def test_json_config_placeholders_are_not_reported():
    assert "json-secret" not in rules_hit('{"apiKey": "${PI_API_KEY}"}\n')
    assert "json-secret" not in rules_hit('{"token": "<your-token>"}\n')


def test_sensitive_tracked_paths_are_recognised():
    sensitive = (
        ".pi/" + "agent/auth.json",
        ".pi/" + "agent/settings.json",
        ".pi/" + "agent/sessions/2026.jsonl",
        ".claude/" + "settings.local.json",
        ".codex/" + "auth.json",
        ".env",
        ".env.local",
        "credentials.json",
        "id_" + "ed25519",
        "certs/server.pem",
        ".netrc",
        "docs/.bash_history",
        ".pi/Teamwork/Teams/Demo/Ledger.jsonl",
        ".venv/lib/python3.12/site-packages/x.py",
        "node_modules/pkg/index.js",
        "site/index.html",
        "dist/teamwork_agents-1.0.0.whl",
        "__pycache__/cli.cpython-312.pyc",
        "src/cli.pyc",
        ".DS_Store",
        "docs/guide.md.orig",
        "Scratch/notes.md",
        "target/release/teamwork",
    )
    for path in sensitive:
        assert ps.sensitive_path(path), path


def test_project_files_are_not_sensitive_paths():
    allowed = (
        ".env.example",
        ".env.sample",
        "src/auth.py",
        "docs/guide/install.md",
        "tests/unit/test_privacy_scan.py",
        "assets/demo.svg",
    )
    for path in allowed:
        assert ps.sensitive_path(path) is None, path


def test_wsl_and_mounted_home_paths_are_reported():
    for line in (
        "path = /mnt/c/Users/" + "realperson/code\n",
        "path = /mnt/d/home/" + "realperson/work\n",
    ):
        assert "home-path" in rules_hit(line), line


def test_provider_keys_are_reported():
    keys = (
        "gsk_" + "A1b2C3d4E5f6G7h8I9j0K1l2",
        "xai-" + "A1b2C3d4E5f6G7h8I9j0K1l2",
        "pplx-" + "A1b2C3d4E5f6G7h8I9j0K1l2",
        "glpat-" + "A1b2C3d4E5f6G7h8I9j0",
        "hf_" + "A1b2C3d4E5f6G7h8" + "I9j0K1l2M3n4O5p6",
        "sk_live_" + "A1b2C3d4E5f6G7h8I9j0K1l2",
    )
    for key in keys:
        assert "api-token" in rules_hit(f"key = {key}\n"), key
