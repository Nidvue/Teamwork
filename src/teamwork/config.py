"""Workspace paths, record names, caps and shared constants.

Everything here is data: changing a constant is the supported way to tune the
workspace, and no module imports the command layer to read it.
"""

from __future__ import annotations

import os

from . import resources as _resources

SKILL_DIR = _resources.skill_root()

ROLES_DIR = _resources.asset("roles")

TEMPLATES_DIR = _resources.asset("templates")

DIR_TEAM_MAP_TPL = "TeamMap.md"

TEAM_ROOT_DIR = ".pi/Teamwork"

TEAMS_SUBDIR = "Teams"

DIR_GLOBAL = "Global"

DIR_ROLES = "Roles"

DIR_AGENTS = "Agents"

DIR_RUNTIME = "Runtime"

DIR_LOCKS = "Locks"

DIR_SLOTS = "Slots"

DIR_ARTIFACTS = "Artifacts"

DIR_REPORTS = "Reports"

DIR_SCRATCH = "Scratch"

DIR_DOCS = ("docs", "Team")

F_SHORT = "ShortTermMemory.md"

F_LONG = "LongTermMemory.md"

F_MEM_ARCHIVE = "ArchivedMemory.md"

F_TASKS = "TaskQueue.md"

F_ROLE = "Role.md"

F_START = "StartHere.md"

F_WORKLOG = "WorkLog.md"

F_INBOX = "Inbox.md"

F_GLOBAL = "GlobalMemory.md"

F_GLOBAL_ARCHIVE = "GlobalMemoryArchive.md"

F_DISPUTES = "Disputes.md"

F_REDLINES = "RedLines.md"

F_MAP = "TeamMap.md"

F_REVIEWS = "Reviews.md"

F_CRITERIA = "Criteria.md"
F_TESTS = "Tests.md"
F_TESTPLAN = "TestPlan.md"

DIR_WORKTREES = "Worktrees"

F_SETTINGS = "Settings.json"

IDENTITY_DOMAIN = os.environ.get("TEAMWORK_IDENTITY_DOMAIN", "agents.nidvue.com")

TEST_LAYERS = (
    "goal",
    "requirements",
    "plan",
    "tech",
    "release",
    "data",
    "process",
    "cost",
    "system",
    "ui",
    "docs",
    "unit",
    "integration",
    "acceptance",
    "security",
)

LAYER_OWNER = {
    "goal": "ceo",
    "requirements": "product-manager",
    "plan": "project-manager",
    "tech": "cto",
    "release": "release-engineer",
    "data": "data-engineer",
    "process": "coo",
    "cost": "cfo",
    "system": "architect",
    "ui": "designer",
    "docs": "technical-writer",
    "unit": "developer",
    "integration": "tester",
    "acceptance": "reviewer",
    "security": "security-auditor",
}

LAYER_WHAT = {
    "goal": "black-box verification that the delivered result meets the user's objective",
    "requirements": "requirement coverage and traceability: every requirement maps to a passing check",
    "plan": "plan integrity: dependency graph, duplicate work, milestone exit criteria",
    "tech": "technology validation: toolchain and dependency upgrades, feasibility spikes, version drills",
    "release": "release tests: reproducible build, CI gates, packaging, upgrade and rollback",
    "data": "data tests: schema and migration correctness, backfill, backup and restore drills",
    "process": "process and automation tests: the documented workflow and tooling actually run",
    "cost": "cost and budget tests: metering, cap enforcement, unit-economics assertions",
    "system": "architecture-conformance tests (boundaries, dependency direction, contract, ADR)",
    "ui": "UI use-case tests (flows, component states, accessibility)",
    "docs": "documentation tests: every documented command and claim is executed as written",
    "unit": "unit tests for the code the Developer wrote",
    "integration": "integration / system / end-to-end tests",
    "acceptance": "acceptance tests over every role's output",
    "security": "security tests (auth, input handling, secrets, red lines)",
}

DEFAULT_REQUIRED_LAYERS = ("unit", "integration", "acceptance")

ALL_LAYERS_SENTINEL = "__all__"

LAYER_CELL = {
    "goal": "goal",
    "requirements": "req",
    "plan": "plan",
    "tech": "tech",
    "release": "rel",
    "data": "data",
    "process": "proc",
    "cost": "cost",
    "system": "sys",
    "ui": "ui",
    "docs": "docs",
    "unit": "unit",
    "integration": "int",
    "acceptance": "acc",
    "security": "sec",
}

TEST_STATUSES = ("pending", "passing", "failing", "na")

F_LEDGER = "Ledger.jsonl"

F_HEAD = "LedgerHead.json"

F_MANIFEST = "AuditManifest.json"

F_AUDITREPORT = "AuditManifest.md"

F_SKILLS = "Skills.md"

SKILLS_DIR = (".agents", "skills")

DEFAULT_PROVIDER_LIMITS = {
    "ollama-cloud": 64,
    "deepseek": 2500,
    "openai": 64,
    "anthropic": 64,
    "default": 32,
}

SLOT_TTL_MINUTES = int(os.environ.get("TEAMWORK_SLOT_TTL_MINUTES", "90"))

REVIEW_FAIL_LIMIT = int(os.environ.get("TEAMWORK_REVIEW_FAIL_LIMIT", "3"))

# A review claim is a short work lease, not a provider slot. A lane that dies
# mid-review must not freeze the deliverable for the 90-minute slot TTL.
REVIEW_LEASE_MINUTES = int(os.environ.get("TEAMWORK_REVIEW_LEASE_MINUTES", "20"))

# A role's shared memory has ONE revising instance at a time. The role file lock
# makes a single write atomic; this lease is what holds the pen across several
# commands, so an instance can finish one coherent memory update (`memory claim`
# ... several `remember`/`forget` ... `memory release`) before a peer interleaves
# its own view of the same file. A dead holder must not freeze the role forever,
# so the lease expires and the next writer takes it over.
MEMORY_LEASE_MINUTES = int(os.environ.get("TEAMWORK_MEMORY_LEASE_MINUTES", "30"))

# A lease that outlives this long is "slow": the role's other instances may contest
# it and the arbiter (the CTO) rules. The default is half a lease, so a normal
# multi-entry update never trips it while a stuck lane is visible well before the
# lease expires and frees itself.
MEMORY_STALL_MINUTES = int(os.environ.get("TEAMWORK_MEMORY_STALL_MINUTES", "15"))

# Who rules on a contested memory lease. The CTO owns engineering standards and the
# build and lock policy, so a stuck writer is an engineering question rather than a
# dispute between peers. The arbiter folds up the reporting line when the CTO is
# unstaffed (a slim roster), and a party never rules its own lease.
MEMORY_ARBITER_ROLE = os.environ.get("TEAMWORK_MEMORY_ARBITER", "cto")

SHORT_CAP = int(os.environ.get("TEAMWORK_SHORT_CAP", "24"))

LONG_CAP = int(os.environ.get("TEAMWORK_LONG_CAP", "64"))

ARCHIVE_CAP = int(os.environ.get("TEAMWORK_ARCHIVE_CAP", "256"))

STALE_DAYS = int(os.environ.get("TEAMWORK_STALE_DAYS", "3"))

MIN_USES = int(os.environ.get("TEAMWORK_MIN_USES", "2"))

PROMOTE_MIN_IMPORTANCE = int(os.environ.get("TEAMWORK_PROMOTE_MIN_IMPORTANCE", "2"))

DOCS = {
    "Project.md": "CEO",
    "Plan.md": "ProjectManager",
    "Board.md": "ProjectManager",
    "Decisions.md": "Architect",
    "Architecture.md": "Architect",
    "Research.md": "ProductManager",
    "Design.md": "Designer",
    "Risks.md": "COO",
    "Costs.md": "CFO",
    "Release.md": "Release Engineer",
    "Archive.md": "CEO",
}

CODE_DIRS = ("src", "lib", "cmd", "internal", "app", "packages", "crates", "rust")

TEST_HINTS = ("test", "tests", "spec", "specs", "e2e", "integration")

GITIGNORE_LINES = (
    "# --- teamwork: local working state (never commit) ---",
    ".pi/",
    "# --- teamwork: scratch and editor noise ---",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.orig",
    "*.rej",
    "*.swp",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    "# --- teamwork: secrets ---",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "*.key",
    "# --- teamwork: caches / build output (keep them on disk, just uncommitted) ---",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    "dist/",
    "build/",
    "target/",
    ".venv/",
    "venv/",
    "coverage/",
    ".coverage",
)

SCRATCH_DIRS = (DIR_SCRATCH,)

SCRATCH_PATTERNS = ("*.tmp", "*.temp", "*.bak", "*.orig", "*.rej", "*.log")

MAX_ROUNDS = int(os.environ.get("TEAMWORK_MAX_DISPUTE_ROUNDS", "3"))

TRIBUNAL = ("ceo", "cto", "cfo")

# Who each role reports to. One parent per role - a role with two managers answers
# to neither - and the CEO is the only lane that reaches the user. The parent is
# the role that owns the standard the child is judged by: technology work under the
# CTO, execution and planning under the COO, product and documentation under the
# Product Manager. Three roles stay with the CEO on purpose, because their job is
# to disagree with everyone else: the Reviewer passes and merges (it must not be
# managed by a lane whose work it reviews), the Security Auditor audits the whole
# team, CTO included, and the CFO holds the budget cap that binds every lane.
# `ROLE_PARENT` is the single source of truth; the docs, the charters, the
# AGENTS.md block and the generated StartHere brief are checked against it.
ROLE_PARENT = {
    "ceo": None,
    "cto": "ceo",
    "coo": "ceo",
    "cfo": "ceo",
    "product-manager": "ceo",
    "reviewer": "ceo",
    "security-auditor": "ceo",
    "architect": "cto",
    "developer": "cto",
    "tester": "cto",
    "release-engineer": "cto",
    "data-engineer": "cto",
    "project-manager": "coo",
    "designer": "product-manager",
    "technical-writer": "product-manager",
}

# Reporting order, parents before children: the order the tree is rendered in and
# the order an escalation walks. Kept explicit so `map`, the docs and the tests
# agree without recomputing a graph from a plain dict.
ROLE_REPORT_ORDER = (
    "ceo",
    "cto",
    "architect",
    "developer",
    "tester",
    "release-engineer",
    "data-engineer",
    "coo",
    "project-manager",
    "product-manager",
    "designer",
    "technical-writer",
    "reviewer",
    "security-auditor",
    "cfo",
)

TRIBUNAL_MIN_SIGNERS = 2

# Code-scanning findings are a release gate, not a nice-to-have: a red alert on
# the default branch means the shipped revision has a known defect. The Release
# Engineer owns the read and the routing because it already owns repository and CI
# integrity (`references/Remotes.md`); the fix lands with whoever owns the file.
# `SCAN_ROUTE` is the file-ownership map, most specific pattern first.
SCAN_OWNER_ROLE = "release-engineer"

SCAN_ROUTE = (
    (".github/**", "release-engineer"),
    ("scripts/privacy_scan.py", "security-auditor"),
    ("scripts/**", "developer"),
    ("src/**", "developer"),
    ("tests/**", "developer"),
    ("docs/guide/**", "technical-writer"),
    ("docs/Team/Architecture.md", "architect"),
    ("docs/Team/Release.md", "release-engineer"),
    ("docs/Team/AuditReport.md", "security-auditor"),
    ("docs/**", "technical-writer"),
    ("templates/**", "ceo"),
    ("roles/**", "ceo"),
    ("references/**", "ceo"),
    ("README.md", "designer"),
    ("assets/**", "designer"),
)

# A scan alert at or above this severity blocks the release gate.
SCAN_BLOCKING = ("error", "critical", "high")

# Roster tiers, cheapest first. A role earns a seat only if it owns a deliverable,
# a test layer and a decision right that no other role holds; everything else rides
# as a lane. `slim` is the default because every extra role is another charter, queue
# and memory set loaded at startup, and the gates do not need it: `staffed_layers`
# already restricts the matrix to staffed roles, and `required_tribunal` stays at or
# above TRIBUNAL_MIN_SIGNERS with the Reviewer as the neutral seat.
ROSTER_TIERS = {
    "slim": (
        "ceo",
        "architect",
        "developer",
        "tester",
        "reviewer",
    ),
    "standard": (
        "ceo",
        "architect",
        "product-manager",
        "project-manager",
        "developer",
        "tester",
        "reviewer",
        "release-engineer",
    ),
    "full": (
        "ceo",
        "cto",
        "coo",
        "cfo",
        "architect",
        "product-manager",
        "project-manager",
        "designer",
        "developer",
        "tester",
        "reviewer",
        "security-auditor",
        "release-engineer",
        "technical-writer",
        "data-engineer",
    ),
}

DEFAULT_ROSTER_TIER = "slim"

# Roles the gates cannot do without, whichever tier is chosen.
ROSTER_REQUIRED = ("ceo", "developer", "tester", "reviewer")

# Instances per role for a tier: reviewers get two so the review queue fans out
# and a sampled or high-risk deliverable gets a second independent verdict.
ROSTER_INSTANCE_COUNT = {"reviewer": 2, "developer": 1, "tester": 1}

# Settings keys that are workspace policy, not provider concurrency limits: `slot`
# reads every other key as a provider cap, so a new non-provider key must be
# listed here or it becomes a phantom provider.
SETTINGS_NON_PROVIDER = (
    "PulseMinutes",
    "Criteria",
    "AlwaysOnBudgetKb",
    "ReviewLeaseMinutes",
    "ReviewLeaseMaxMinutes",
    "MemoryLeaseMinutes",
)

# The always-on context cap, per instance, in KB: SKILL.md + the managed teamwork
# block of AGENTS.md + the role charter + the role memory. `harness budget` reads
# `AlwaysOnBudgetKb` from the team Settings.json and falls back to this.
DEFAULT_ALWAYS_ON_BUDGET_KB = 120

DEFAULT_BASE = "main"

# The two git hook stages `hooks install` writes. `status`, `uninstall` and the
# overwrite refusal all key on HOOK_MARKER, so a hook without that line is never
# touched: it belongs to someone else.
HOOK_STAGES = ("pre-commit", "pre-push")

HOOK_MARKER = "teamwork-managed hook"

# Git LFS threshold shared by the pre-commit hook and `commit --check-lfs`: one
# MiB, because "1 MB" in decimal and binary differ by 4.8% and a threshold that
# moves with the reader is not a rule (D-20261020-Architect-7).
LFS_MAX_BYTES = 1024 * 1024

REVIEW_STATUSES = ("open", "approved", "changes-requested", "merged", "closed")

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

STATUSES = ("todo", "doing", "selfcheck", "review", "blocked", "done", "dropped")
