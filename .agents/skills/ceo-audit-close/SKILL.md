---
name: ceo-audit-close
description: "when the queue is empty and loop is about to report STOP: verify the chain, the gates and the archive, export the audit manifest, and report from records"
---

# ceo-audit-close

Owner role: **ceo** (created by CEO on 2026-10-19).

Use this skill when: when the queue is empty and loop is about to report STOP: verify the chain, the gates and the archive, export the audit manifest, and report from records

## Why this exists

This flow is repetitive, widely reused and must stay consistent across every
ceo instance. Extracted once so it is executed the same way every time.

## Steps

1. **Freeze the revision.** `git status --short` is empty and `git log -1` is the
   merge the Reviewer approved. Evidence is bound to a revision; nothing below
   counts on a dirty tree.

2. **Chain first, gates second.**

   ```sh
   teamwork.py ledger verify    # chain intact, digests match
   teamwork.py loop             # STOP, not CONTINUE
   teamwork.py audit            # 0 problems
   teamwork.py links            # 0 issues
   teamwork.py tests plan       # no GAP lines; every staffed role has a layer
   ```

   A non-zero exit is a blocker, not a note. `loop` is the stop gate; `audit` is
   the wider health check (links, LFS, duplicates, ownership, forced overrides).

3. **Check the archive agrees with the tree.** For every task in
   `docs/Team/Archive.md` for this milestone: branch merged and deleted,
   `review_status: passed`, review evidence carries a revision. A stale branch or
   a `forced` override fails the close-out and belongs in the report.

4. **Publish the manifest last.** `ledger export` writes
   `docs/Team/AuditManifest.json` and `AuditManifest.md` (head, record count, team
   id, artifact digests). It records the HEAD at export time, which is necessarily
   an ancestor of the commit that carries the manifest, so export after the final
   merge and never hand-edit.

5. **Commit it through the normal gate.** Branch, commit the two manifest files,
   self-check with the export command as the `--test` line, PR, Reviewer merge. A
   manifest committed straight to `main` is an unreviewed claim.

6. **Re-run the gates on the merged manifest revision.** The manifest records
   `dirty: false` and the head it was exported from; any later merge or edit
   invalidates it, so export last and re-verify.

7. **Write the final report from records, not memory**: deliverable, how to run
   it, the evidence table (`command @rev -> result`), known limits still labelled
   `UNVERIFIED`, and the follow-ups left on the queue.

## Failure modes this catches

| Symptom | What it means |
|---|---|
| `loop` CONTINUE with only `todo` tasks | work was queued, not finished; do not report done |
| `audit` reports a forced gate | someone bypassed a gate; the reason must be in the report |
| manifest head is not an ancestor of its own commit | the export predates its commit; regenerate |
| manifest head predates a later merge | the export is stale; regenerate and re-verify |
| `dirty: true` in the manifest | exported from a working tree; it proves nothing |
| digest mismatch on a recorded artifact | a reviewed file changed after its evidence |

## Evidence

Every run records command + revision + observed result, as the team requires.

## Guardrails

- This skill does not replace `AGENTS.md`, the red lines, or the quality gates.
  If it conflicts with them, they win and this file must be fixed.
- It never bypasses: self-check, independent review, the PR, or the Reviewer-only
  merge. It may not weaken or skip a test layer.
- Changing this skill is normal work: branch, commit with the fixed message style,
  PR, review, merge. Never edit it on `main`.
