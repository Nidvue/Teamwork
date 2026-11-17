"""Why this file exists: the security audit surface is a command, and nothing in the
integration layer executed it.

`scripts/privacy_scan.py` is the AC-5 gate: it prints one PASS/FAIL line and its exit
code is the verdict, so a scan that crashes, exits 0 on a finding, or drops the
summary line is a silent hole in the release gate. Pinned here: this checkout's tree
scans clean through the documented invocation, and a tree carrying a finding exits
non-zero and names the file. The `--history` half is not asserted here - it walks
every ref, including unmerged lanes, so it is not hermetic per lane; the security
layer owns it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "scripts" / "privacy_scan.py"
ALLOW = ROOT / ".github" / "privacy-allow.txt"


def scan(*argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCAN), *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=600,
    )


def git(cwd: Path, *argv: str) -> None:
    subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True, timeout=120)


def test_security_audit_privacy_scan_passes_the_tree_of_this_checkout() -> None:
    assert ALLOW.is_file(), "the gate command names an allow list; it must exist"
    done = scan("--tree", "--allow", str(ALLOW), cwd=ROOT)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "PASS" in done.stdout and "finding(s)" in done.stdout, done.stdout


def test_security_audit_privacy_scan_fails_and_names_the_file_it_flags(tmp_path: Path) -> None:
    personal = "first.last" + "@" + "gmail" + ".com"
    planted = tmp_path / "leak.txt"
    planted.write_text(f"contact {personal}\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    done = scan("--tree", cwd=tmp_path)
    assert done.returncode != 0, done.stdout
    assert "FAIL" in done.stdout and "leak.txt" in done.stdout, done.stdout
