Review one teamwork deliverable as an independent Reviewer.

Claim it with `python3 scripts/teamwork.py review <role> <T-id> --claim --by <lane>`,
then in at most 12 tool calls, without editing anything:

1. Assert the revision: `git rev-parse --short <branch>` must equal the head you
   were given; record it.
2. Measure the gates yourself; never trust the author's numbers: tests, lint,
   types, links, ledger, and the privacy gate exactly as the shipped target runs
   it, with and without its allowlist.
3. Read only the diff, with `grep -n` then a +/-30 line window.
4. A claim that does not reproduce at that head is a finding with `file:line` and
   the command that shows it.
5. Record one verdict: `--result pass --evidence '<commands @sha -> results>'` or
   `--result fail --findings '<defect + file:line + command>'`. A different
   Reviewer merges; you never merge your own pass.
