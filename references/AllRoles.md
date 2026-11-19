# All-roles rules

Owner: every role (this file is the single home; charters point here).
Related: [Roles.md](Roles.md), [Engineering.md](Engineering.md)

Three blocks are identical for every role, so they live here once instead of in
fifteen charters. A lane packet injects this file verbatim; a charter carries the
short form and this pointer.

## 1. Working clean (all roles)

- **No comments:** the code is the comment. Write no explanatory #; only the
  directives a toolchain reads (# noqa, # type: ignore, # pragma: no
  cover, # fmt:, a shebang) are allowed. scripts/check_comments.py fails
  the gate on anything else, so rename or split the code instead of explaining
  it, and file a TODO as a tracked task.
- **Working tree:** delete temp and stale files as you go - `*.orig`, `*.rej`,
  `*.bak`, `*~`, `*.tmp`, `*.log`, `.DS_Store`, scratch copies, superseded drafts,
  empty directories. Scratch lives in your gitignored `Scratch/` and is emptied
  before the task closes. Never commit build output, caches, local state or editor
  noise. One canonical home per file, an obvious structure, and leave the tree
  cleaner than you found it.

## 2. Code standards (all roles)

- Use the language's **canonical formatter and linter** (see
  [Engineering.md](Engineering.md) for the per-language toolchain). Run the fixer
  before you commit and the checker before you submit; CI fails on unformatted or
  unlinted code.
- Type-check where the language supports it. A type error is a defect, not a style
  opinion.
- Never hand-format, never introduce a competing config, and never weaken a rule to
  pass - no blanket `noqa`, no rule removed, no directory excluded from the
  formatter. If a rule is genuinely wrong here, disable it narrowly with a reason
  and record the decision.
- **Naming:** team directories are PascalCase; file names follow the ecosystem
  (docs `Architecture.md`, components `ButtonGroup.tsx`; Python modules stay
  `lower_snake_case` because the name is the import path; `pyproject.toml` and
  friends are never renamed).
- **Commit hygiene:** commit while you work, then `git rebase -i` onto the latest
  default branch, squash `wip`/`fixup` commits and target **one commit per task**.
  Never rebase or force-push a shared branch, or anything already on the default
  branch.
- **Warnings are errors:** make the toolchain fail on them (ruff/mypy clean,
  `pytest -W error`, `--max-warnings 0`, `-D warnings`, `-Werror`), fix the cause,
  and suppress only narrowly with a reason when the cause is third-party. CI
  deprecation notices count as warnings.
- Evidence: the format/lint command and its result, on the same revision as the
  tests.

## 3. Your model (all roles)

- You run through the host's own LLM API on the model configured for **you**:
  `teamwork.py model get <you>` shows it, and an instance override beats the role
  default. The skill ships no model and calls no API itself.
- The CEO sets the lanes with `teamwork.py model auto --apply` at intake - strong
  models on the decision lanes, economy models on the mechanical ones - so quality
  lands where it compounds and cost where it does not. If you need a different
  model, ask the CEO; an agent never changes another agent's model.
- Model choice never changes the protocol: the evidence gates, the two-stage review
  and the ledger hold whatever model produced the work.
