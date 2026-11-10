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

DIR_RETIRED = "Retired"

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

F_TASK_ARCHIVE = "TaskArchive.md"

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
F_FEATURES = "Features.md"
F_TEAM = "Team.md"

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
    "feature",
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
    "feature": "team-leader",
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
    "feature": "feature isolation: the slice's diff, its standalone build and its frozen interface",
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
    "feature": "feat",
}

TEST_STATUSES = ("pending", "passing", "failing", "na")

F_LEDGER = "Ledger.jsonl"

F_HEAD = "LedgerHead.json"

F_MANIFEST = "AuditManifest.json"

F_AUDITREPORT = "AuditManifest.md"

F_SKILLS = "Skills.md"

F_LESSONS = "Lessons.md"

F_KNOWLEDGE = "Knowledge.md"

KNOWLEDGE_KINDS = ("fact", "experience", "preference", "gotcha", "rule")

KNOWLEDGE_TOPIC_MAX = 120
KNOWLEDGE_STATEMENT_MAX = 500

CONTEXT_ROOT = "ctx://"
CONTEXT_NAMESPACES = ("project", "role", "global")
CONTEXT_NODE_TYPES = ("dir", "doc", "skill", "knowledge", "lesson", "memory", "task")
CONTEXT_CHILD_CAP = 20
CONTEXT_HEADING_CAP = 20
CONTEXT_FIND_LIMIT = 10
CONTEXT_MEMORY_FILES = {"short": F_SHORT, "long": F_LONG, "archive": F_MEM_ARCHIVE}
CONTEXT_MEMORY_LAYERS = ("short", "long", "archive")

SKILLS_DIR = (".agents", "skills")

SKILL_PREFIX = "tw-"

DEFAULT_PROVIDER_LIMITS = {
    "ollama-cloud": 64,
    "deepseek": 2500,
    "openai": 64,
    "anthropic": 64,
    "default": 32,
}

SLOT_TTL_MINUTES = int(os.environ.get("TEAMWORK_SLOT_TTL_MINUTES", "90"))

REVIEW_FAIL_LIMIT = int(os.environ.get("TEAMWORK_REVIEW_FAIL_LIMIT", "3"))

REVIEW_LEASE_MINUTES = int(os.environ.get("TEAMWORK_REVIEW_LEASE_MINUTES", "20"))

MEMORY_LEASE_MINUTES = int(os.environ.get("TEAMWORK_MEMORY_LEASE_MINUTES", "30"))

MEMORY_STALL_MINUTES = int(os.environ.get("TEAMWORK_MEMORY_STALL_MINUTES", "15"))

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
    "Features.md": "ProjectManager",
}


FEATURE_STATES = ("proposed", "ready", "active", "done", "dropped")

FEATURE_OPEN_STATES = ("ready", "active")

FEATURE_TERMINAL_STATES = ("done", "dropped")

FEATURE_TEAM_LEADER = "team-leader"

FEATURE_SQUAD_ROLES = (
    "data-engineer",
    "designer",
    "developer",
    "technical-writer",
    "tester",
)

INDEPENDENT_LANES = (
    "reviewer",
    "security-auditor",
    "cfo",
)

FEATURE_SHARED_ROLES = (
    "architect",
    "ceo",
    "cfo",
    "coo",
    "cto",
    "project-manager",
    "release-engineer",
    "reviewer",
    "security-auditor",
)

FEATURE_GENERATED_ARTIFACTS = (
    "docs/Team/Archive.md",
    "docs/Team/AuditManifest.json",
    "docs/Team/AuditManifest.md",
    "docs/Team/Board.md",
)

FEATURE_CHECKOUT_STATE = (
    ".pi/",
    ".pytest_cache/",
    ".venv/",
    "Runtime/",
    "Scratch/",
    "__pycache__/",
    "build/",
    "dist/",
    "node_modules/",
    "site/",
)

FEATURE_RECORDS_REL = "docs/Team/Features.md"

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

ROLE_PARENT = {
    "ceo": None,
    "cto": "ceo",
    "coo": "ceo",
    "cfo": "ceo",
    "product-manager": "ceo",
    "reviewer": "ceo",
    "security-auditor": "ceo",
    "architect": "cto",
    "team-leader": "cto",
    "developer": "cto",
    "tester": "cto",
    "release-engineer": "cto",
    "data-engineer": "cto",
    "project-manager": "coo",
    "designer": "product-manager",
    "technical-writer": "product-manager",
}

ROLE_REPORT_ORDER = (
    "ceo",
    "cto",
    "architect",
    "team-leader",
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

SCAN_BLOCKING = ("error", "critical", "high")

ROSTER_TIERS = {
    "slim": (
        "ceo",
        "architect",
        "team-leader",
        "developer",
        "tester",
        "reviewer",
    ),
    "standard": (
        "ceo",
        "architect",
        "team-leader",
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
        "team-leader",
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

ROSTER_REQUIRED = ("ceo", "developer", "tester", "reviewer")

ROSTER_INSTANCE_COUNT = {"reviewer": 2, "developer": 1, "tester": 1, "team-leader": 1}

SETTINGS_NON_PROVIDER = (
    "PulseMinutes",
    "PulseMode",
    "Criteria",
    "AlwaysOnBudgetKb",
    "ReviewLeaseMinutes",
    "ReviewLeaseMaxMinutes",
    "MemoryLeaseMinutes",
    "PreflightCommand",
    "LaneMinutes",
    "LaneAttempts",
    "LaneToolBudget",
    "LanePollSeconds",
    "LaneCommand",
    "LaneHost",
    "LaneMax",
    "SwarmMinutes",
)

DEFAULT_ALWAYS_ON_BUDGET_KB = 120

DEFAULT_BASE = "main"

HOOK_STAGES = ("pre-commit", "pre-push")

HOOK_MARKER = "teamwork-managed hook"

LFS_MAX_BYTES = 1024 * 1024

REVIEW_STATUSES = ("open", "approved", "changes-requested", "merged", "closed")

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

STATUSES = ("todo", "doing", "selfcheck", "review", "blocked", "done", "dropped")
