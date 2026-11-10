"""Unit tests for the published privacy scanner (``scripts/privacy_scan.py``).

The scanner is the gate that keeps private data out of this repository, so the
gate itself is tested - including negative controls that prove a clean line is
*not* reported. These tests import the script directly; it is stdlib-only and has
no side effects at import time.
"""

from __future__ import annotations

import re
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
    for key in ("x-api-key", "apiToken", "authToken", "openaiApiKey", "private_key"):
        line = '{"' + key + '": "' + payload + '"}\n'
        assert "json-secret" in rules_hit(line), key


def test_pretty_printed_json_credential_is_reported():
    payload = "A1b2C3d4" + "E5f6G7h8" + "I9j0K1l2"
    text = '{\n  "apiKey":\n    "' + payload + '"\n}\n'
    findings = [f for f in findings_for(text) if f["rule"] == "json-secret"]
    assert findings and findings[0]["line"] == 2


def test_json_config_placeholders_are_not_reported():
    assert "json-secret" not in rules_hit('{"apiKey": "${PI_API_KEY}"}\n')
    assert "json-secret" not in rules_hit('{"token": "<your-token>"}\n')


def test_path_rules_ignore_case_differences():
    for path in (".PI/" + "agent/settings.json", ".Pi/" + "AGENT/SETTINGS.JSON"):
        assert ps.sensitive_path(path), path


def test_public_keys_and_source_keys_are_not_key_material():
    assert ps.sensitive_path("id_ed25519" + ".pub") is None
    assert ps.sensitive_path("i18n/de.key") is None
    assert ps.sensitive_path("web/content.key") is None


def test_path_findings_can_be_allowlisted():
    import re

    finding = ps.config_path_finding("tests/fixtures/secrets.json", "tree")
    assert finding is not None
    allowed = ps.config_path_finding(
        "tests/fixtures/secrets.json", "tree", [re.compile(r"fixtures/secrets\.json")]
    )
    assert allowed is None


def test_sensitive_tracked_paths_are_recognised():
    sensitive = (
        ".pi/" + "agent/auth.json",
        ".pi/" + "agent/settings.json",
        ".pi/" + "agent/sessions/2026.jsonl",
        ".claude/" + "projects/session.jsonl",
        ".claude/" + "settings.local.json",
        ".codex/" + "auth.json",
        ".codex/" + "sessions/2026.jsonl",
        ".config/" + "opencode/auth.json",
        ".aider." + "chat.history.md",
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
        ".agents/skills/teamwork/SKILL.md",
        ".claude/skills/teamwork/SKILL.md",
        ".env.example",
        ".env.dist",
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


def test_gitignore_deny_entries_are_not_agent_config_findings():
    entry = ".claude/" + "settings.local.json\n"
    assert "agent-config" in rules_hit(entry)
    assert list(ps.scan_lines(entry, ".gitignore", "unit-test", ps.RULES, allow=[])) == []


def test_forge_merge_predicate_is_narrow():
    merge = "Merge " + "a" * 40 + " into " + "b" * 40
    assert ps.is_forge_merge(merge, ["a" * 40, "b" * 40])
    # A normal two-parent merge with a human message is still scanned.
    assert not ps.is_forge_merge("Merge branch 'feature'", ["a", "b"])
    # A single-parent commit with that message is not a forge merge either.
    assert not ps.is_forge_merge(merge, ["a" * 40])


def test_gitignore_still_scans_json_credentials():
    payload = "A1b2C3d4" + "E5f6G7h8"
    line = '{"apiKey": "' + payload + '"}\n'
    assert "json-secret" in rules_hit(line)
    assert list(ps.scan_lines(line, ".gitignore", "unit-test", ps.RULES, allow=[]))
    # The deny-list exemption stays narrow: a plain host path entry is still quiet.
    deny = ".claude/" + "settings.local.json\n"
    assert list(ps.scan_lines(deny, ".gitignore", "unit-test", ps.RULES, allow=[])) == []


def test_forge_merge_identity_is_skipped_but_its_message_is_scanned(tmp_path, monkeypatch):
    import os
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "Technical Writer",
        "GIT_AUTHOR_EMAIL": "technicalwriter@agents.nidvue.com",
        "GIT_COMMITTER_NAME": "Technical Writer",
        "GIT_COMMITTER_EMAIL": "technicalwriter@agents.nidvue.com",
    }
    private = {
        "GIT_AUTHOR_NAME": "Private Person",
        "GIT_AUTHOR_EMAIL": "someone@" + "private-mail.example",
        "GIT_COMMITTER_NAME": "Private Person",
        "GIT_COMMITTER_EMAIL": "someone@" + "private-mail.example",
    }

    def run(*args, extra_env=None):
        return subprocess.run(
            args,
            cwd=repo,
            env={**env, **(extra_env or {})},
            check=True,
            capture_output=True,
            text=True,
        )

    run("git", "init", "-q", "-b", "main", ".")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-qm", "base")
    base = run("git", "rev-parse", "main").stdout.strip()

    run("git", "switch", "-qc", "feature")
    (repo / "b.txt").write_text("y", encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-qm", "feature")
    feature = run("git", "rev-parse", "feature").stdout.strip()

    token = "ghp_" + "0123456789abcdefghijklmnopqrstuvwxyz"
    message = f"Merge {feature} into {base}\n\nleaked {token}"
    run("git", "switch", "-q", "main")
    # The forge authors its merge ref with the PR account identity; deliver that
    # identity through the environment, which beats `-c user.*`.
    run("git", "merge", "--no-ff", "-m", message, "feature", extra_env=private)
    merge_sha = run("git", "rev-parse", "HEAD").stdout.strip()
    # Control: the same identity on an ordinary commit must still be reported.
    run("git", "commit", "-q", "--allow-empty", "-m", "ordinary", extra_env=private)
    control_sha = run("git", "rev-parse", "HEAD").stdout.strip()

    findings = ps.scan_commit_metadata(repo, allow=[])
    on_merge = {f["rule"] for f in findings if f.get("commit") == merge_sha}
    on_control = {f["rule"] for f in findings if f.get("commit") == control_sha}
    assert "personal-email" not in on_merge, "the forge merge identity must be skipped"
    assert "api-token" in on_merge, "the merge message must still be scanned"
    assert "personal-email" in on_control, "the control commit proves the assertion can fail"


def test_report_context_does_not_republish_a_neighbour_secret():
    first = "AAAA" + "BBBBCCCC1111222"
    second = "DDDD" + "EEEEFFFF3333444"
    text = f'{{"apiKey": "{first}", "clientSecret": "{second}"}}\n'
    findings = findings_for(text)
    assert findings
    assert all(f["context"] == "" for f in findings)


def test_paths_urls_and_digits_are_not_credentials():
    text = "PWD=/usr/local/bin\nAPI_KEY=https://api.example.com/v1/keys\nTOKEN=0000000000\n"
    assert "env-secret" not in rules_hit(text)


def test_quoted_passphrase_with_spaces_is_reported():
    passphrase = "correct " + "horse " + "battery " + "staple"
    assert "env-secret" in rules_hit(f'PASSWORD="{passphrase}"\n')


def test_base64_data_uri_and_integrity_hash_are_not_secrets():
    text = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lQn5VwAAAABJRU5ErkJggg==\n"
        "sha512-K3f8Qw9vJ2mXpLdRtYuIoPaSdFgHjKlZxCvBnM7qWeRtY=\n"
    )
    assert "high-entropy-secret" not in rules_hit(text)


def test_utf16_text_is_scanned():
    token = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"
    data = f"GITHUB_TOKEN={token}\n".encode("utf-16")
    findings = ps._scan_bytes(data, "win.ps1", "unit-test", allow=[])
    assert any(f["rule"] == "api-token" for f in findings)


def test_cat_file_batch_skips_tree_payloads_without_desync(tmp_path: Path):
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", "."], cwd=repo, check=True)
    (repo / "hello.txt").write_text("hello blob\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=A", "-c", "user.email=a@example.com", "commit", "-qm", "x"],
        cwd=repo,
        check=True,
    )
    shas = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--objects", "--all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    shas = [line.split()[0] for line in shas if line.strip()]
    blobs = ps._cat_file_batch(repo, shas)
    assert any(b"hello blob" in payload for payload in blobs.values())


def test_bom_less_utf16_text_is_scanned():
    token = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"
    data = f"GITHUB_TOKEN={token}\n".encode("utf-16-le")
    findings = ps._scan_bytes(data, "win.ps1", "unit-test", allow=[])
    assert any(f["rule"] == "api-token" for f in findings)


def test_allowlist_exempts_only_the_recorded_package_path():
    """The shipped exemption is one exact host-state prefix, not a rule switch."""
    allow = [re.compile(r"^\.pi/agent/npm$")]
    quoted = "verified against ~/.pi/agent/npm/node_modules/pi-subagents"
    assert [f for f in ps.scan_lines(quoted, "x.md", "unit-test", ps.RULES, allow)] == []

    sibling = "token stored in ~/.pi/agent/auth.json"
    hits = ps.scan_lines(sibling, "x.md", "unit-test", ps.RULES, allow)
    assert {f["rule"] for f in hits} == {"agent-config"}


def _escape_literal(text: str) -> str:
    """Escape exactly the characters that would change a regex, and nothing else.

    ``re.escape`` also escapes ``-`` and `` `` which are literal outside a class,
    so comparing against it would reject a perfectly narrow entry such as
    ``^hunter2 passphrase$`` and push authors into unreadable over-escaping.
    """
    special = set("\\^$.|?*+()[]{}")
    return "".join("\\" + ch if ch in special else ch for ch in text)


def _is_one_escaped_literal(entry: str) -> bool:
    """An exemption must be exactly one anchored, fully escaped literal.

    A class, a wildcard or an alternation would widen the exemption past the one
    string it was justified for: a trailing unescaped any-character metacharacter
    would match a sibling user name as well as the recorded one.
    """
    if not (entry.startswith("^") and entry.endswith("$")):
        return False
    body = entry[1:-1]
    if not body:
        return False
    unescaped = re.sub(r"\\(.)", r"\1", body)
    return _escape_literal(unescaped) == body


def test_shipped_allowlist_entries_are_narrow_and_justified():
    path = ROOT / ".github" / "privacy-allow.txt"
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]

    entries = [ln for ln in lines if ln and not ln.startswith("#")]
    assert entries == [
        r"^\.pi/agent/npm$",
        r"^/home/pingz$",
        r"^sk-live-0123456789abcdef0123456789abcdef$",
        r"^hunter2 passphrase$",
        r"^changeme-placeholder$",
    ]
    for entry in entries:
        assert _is_one_escaped_literal(entry), f"{entry!r} is not one escaped literal"
    # every exemption carries a reason next to it in the file
    assert any("T-0001" in ln for ln in lines if ln.startswith("#"))
    assert any("T-0034" in ln or "archived" in ln for ln in lines if ln.startswith("#"))


def test_the_narrowness_check_rejects_loose_entries():
    """Probe the predicate itself, so the guard cannot pass by accident.

    The loose forms are constructed at runtime, not written out: a document that
    spells an absolute user path is itself a privacy finding.
    """
    user = "/home/" + "operat"
    escaped = re.escape(user)
    assert _is_one_escaped_literal(r"^\.pi/agent/npm$")
    assert _is_one_escaped_literal("^" + escaped + "$")
    loose = (
        "^" + escaped + ".$",  # a wildcard where the last character is
        "^" + escaped + ".*$",  # a wildcard tail
        escaped,  # unanchored
        "^" + escaped[:-1] + "(z)?$",  # a class
        "^" + escaped + "$|^" + re.escape(".pi/agent/npm") + "$",  # alternation
        "",
    )
    for entry in loose:
        assert not _is_one_escaped_literal(entry), entry


def test_a_fabricated_probe_value_is_exempted_but_its_neighbours_are_not():
    """The three probe literals are exempt; a sibling or a real credential is not.

    Round 10 of T-0047 shipped them as one-line evidence quotes in Archive.md, so
    the values themselves reached two unpublished blobs; exempting the exact
    string keeps the exemption bounded, which this asserts in both directions.
    """
    allow = ps.load_allow(ROOT / ".github" / "privacy-allow.txt")
    probe = "sk-live-" + "0123456789abcdef0123456789abcdef"

    assert [f for f in ps.scan_lines(probe, "x.md", "unit-test", ps.RULES, allow)] == []

    # one character different is a different secret, and is still reported
    sibling = probe[:-1] + "Z"
    assert [f["rule"] for f in ps.scan_lines(sibling, "x.md", "unit-test", ps.RULES, allow)]
    # a real credential sharing the exempted line is still reported
    both = probe + " GITHUB_TOKEN=" + "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"
    rules = {f["rule"] for f in ps.scan_lines(both, "x.md", "unit-test", ps.RULES, allow)}
    assert "api-token" in rules


def _repo_with_planted_credential(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway git repo holding one planted credential, tracked."""
    import os
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    planted = "ghp_" + "0123456789abcdefghijklmnopqrstuvwxyz"
    (repo / "leak.py").write_text(f'TOKEN = "{planted}"\n', encoding="utf-8")
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "Technical Writer",
        "GIT_AUTHOR_EMAIL": "technicalwriter@agents.nidvue.com",
        "GIT_COMMITTER_NAME": "Technical Writer",
        "GIT_COMMITTER_EMAIL": "technicalwriter@agents.nidvue.com",
    }
    for args in (
        ("git", "init", "-q", "-b", "main", "."),
        ("git", "add", "."),
        ("git", "commit", "-qm", "plant"),
    ):
        subprocess.run(args, cwd=repo, env=env, check=True, capture_output=True)
    return repo, planted


def test_reveal_never_prints_the_unmasked_secret(tmp_path, capsys):
    """A log sink must never receive the value, even under ``--reveal``."""
    repo, planted = _repo_with_planted_credential(tmp_path)
    code = ps.main(["--tree", "--root", str(repo), "--reveal"])
    out, err = capsys.readouterr()
    assert code == 1, "a planted credential must still fail the scan"
    assert planted not in out, "the unmasked secret must not reach stdout"
    assert planted not in err, "the unmasked secret must not reach stderr"
    assert ps._fingerprint(planted) in out, "--reveal must yield a stable fingerprint"
    # The fingerprint is not usable as the secret and does not embed it.
    assert planted[:12] not in out


def test_plain_report_omits_the_fingerprint(tmp_path, capsys):
    """Without --reveal the fingerprint is not emitted at all."""
    repo, planted = _repo_with_planted_credential(tmp_path)
    assert ps.main(["--tree", "--root", str(repo)]) == 1
    out, err = capsys.readouterr()
    assert planted not in out + err
    assert "sha256:" not in out


def test_reveal_to_writes_a_0600_file_and_keeps_the_log_clean(tmp_path, capsys):
    """``--reveal-to`` exports the raw value to a private file, not to the log."""
    import stat

    repo, planted = _repo_with_planted_credential(tmp_path)
    export = tmp_path / "revealed.tsv"
    code = ps.main(["--tree", "--root", str(repo), "--reveal-to", str(export)])
    out, err = capsys.readouterr()
    assert code == 1
    assert planted not in out, "the export must not be echoed to stdout"
    assert planted not in err, "the export must not be echoed to stderr"
    assert "WARNING" in err, "the operator must be warned that a secret file exists"
    mode = stat.S_IMODE(export.stat().st_mode)
    assert mode == 0o600, f"reveal file must be 0600, got {oct(mode)}"
    body = export.read_text(encoding="utf-8")
    assert planted in body
    assert ps._fingerprint(planted) in body


def test_reveal_to_refuses_to_clobber_an_existing_file(tmp_path, capsys):
    """An existing path is never silently overwritten with plaintext secrets."""
    repo, planted = _repo_with_planted_credential(tmp_path)
    export = tmp_path / "revealed.tsv"
    export.write_text("keep me", encoding="utf-8")
    code = ps.main(["--tree", "--root", str(repo), "--reveal-to", str(export)])
    capsys.readouterr()
    assert code == 2, "an existing reveal path must be a usage error"
    assert export.read_text(encoding="utf-8") == "keep me"
    assert planted not in export.read_text(encoding="utf-8")


def test_an_env_secret_on_the_line_does_not_disarm_the_path_rules():
    """The quote scope is one predicate, not a name an earlier rule can rebind.

    A line carrying an environment assignment can also carry a private path. The
    first version of the scope used a name the ``env-secret`` arm reassigned, so any
    env-secret match silently switched off ``agent-config`` and ``home-path`` in
    *every* file - a real regression that review caught.
    """
    allow: list = []
    home = "/home/" + "operat" + "/x.py"
    config = ".pi" + "/agent" + "/settings.json"
    value = "hunt" + "er2 passphrase"
    for path in ("docs/Team/Archive.md", "src/mod.py", "README.md"):
        line = f'Set PASSWORD="{value}" then built {home} and {config}'
        rules = {f["rule"] for f in ps.scan_lines(line, path, "history:blob", ps.RULES, allow)}
        assert {"agent-config", "env-secret", "home-path"} <= rules, (path, sorted(rules))


def test_the_quote_scope_is_what_drops_a_quoted_path_and_only_that():
    """A quoted evidence line loses its path findings; the same path elsewhere does not.

    The scope had no test at all in its first version: deleting the skip left the
    whole suite green while a quoted line started reporting paths it must not. This
    test drives the real prefix, so removing the skip fails it.
    """
    allow: list = []
    home = "/home/" + "operat" + "/x.py"
    config = ".pi" + "/agent" + "/settings.json"

    def hits(line: str, path: str) -> set:
        return {f["rule"] for f in ps.scan_lines(line, path, "history:blob", ps.RULES, allow)}

    for prefix in (
        "- self-check: ",
        "- author evidence: ",
        "- reviewer evidence: ",
        "- findings history: ",
    ):
        quoted = hits(f"{prefix}built {home} and {config}", "docs/Team/Archive.md")
        assert not {"agent-config", "home-path"} & quoted, (prefix, sorted(quoted))

    # The same path in a document this repository authors is a real finding.
    authored = hits(f"built {home} and {config}", "docs/Team/Board.md")
    assert {"agent-config", "home-path"} <= authored, sorted(authored)

    # And the scope is confined to Archive.md: the same quoted prefix elsewhere
    # does not silence a path.
    elsewhere = hits(f"- reviewer evidence: built {home}", "docs/Team/Board.md")
    assert "home-path" in elsewhere, sorted(elsewhere)


def test_a_credential_on_a_quoted_evidence_line_is_still_reported():
    """The scope silences path shapes, never a credential rule."""
    allow: list = []
    home = "/home/" + "operat" + "/x.py"
    token = "sk-" + "live-" + "0123456789abcdef0123456789abcdef"
    line = f"- reviewer evidence: built {home} with token {token}"
    rules = {
        f["rule"]
        for f in ps.scan_lines(line, "docs/Team/Archive.md", "history:blob", ps.RULES, allow)
    }
    assert "home-path" not in rules, sorted(rules)
    assert rules - {"home-path"}, "a credential on an exempted line must still be reported"


def entry_body(entry: str) -> str:
    """The escaped literal inside `^...$`, without the anchors."""
    assert entry.startswith("^") and entry.endswith("$"), entry
    return entry[1:-1]


def test_every_shipped_allowlist_entry_matches_a_real_finding():
    """An entry that matches nothing is dead decoration for an exemption.

    The first version of this file carried a third entry for the harness session
    directory; that path only ever appears on an Archive.md quoted-evidence line,
    which the scanner already scopes, so the entry exempted nothing.

    This test covers the PATH-shaped entries, which is what the dead-entry defect
    was about: scanning the tree, each must exempt at least one finding the same
    scan reports without ``--allow``. The value-shaped entries are fabricated
    probe values that only match inside a larger line a credential rule keys on,
    so they are covered by ``test_a_fabricated_probe_value_is_exempted_but_its
    _neighbours_are_not`` instead of by a synthetic prefix here.
    """
    allow = ps.load_allow(ROOT / ".github" / "privacy-allow.txt")
    assert allow, "no allowlist entries to check"

    path_entries = [p for p in allow if re.sub(r"\\(.)", r"\1", p.pattern)[1:2] in ("/", ".")]
    assert len(path_entries) >= 2, "the path exemptions disappeared"

    # The probe value is rebuilt from each entry's own body, so this file never
    # republishes the exempted string itself.
    values: set[str] = set()
    for pattern in path_entries:
        literal = re.sub(r"\\(.)", r"\1", entry_body(pattern.pattern))
        line = f"built {literal}"
        values.update(f["match"] for f in ps.scan_lines(line, "src/mod.py", "tree", ps.RULES, []))
    for pattern in path_entries:
        assert any(pattern.search(value) for value in values), (
            f"{pattern.pattern!r} exempts no finding that the scanner reports"
        )


def test_an_exempted_value_does_not_exempt_a_sibling_name():
    """The exemption is one string: a neighbouring user name must still be reported."""
    allow = [re.compile(r"^" + re.escape("/home/" + "operat") + "$")]
    sibling = "/home/" + "operat" + "2/x.py"
    rules = {
        f["rule"] for f in ps.scan_lines(f"built {sibling}", "src/a.py", "tree", ps.RULES, allow)
    }
    assert rules == {"home-path"}
