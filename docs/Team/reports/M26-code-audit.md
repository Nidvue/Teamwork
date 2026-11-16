# M26 code audit - src/teamwork + scripts

Owner: Developer (lane `Developer`, task T-0078)
Related: [the board](../Board.md), [the architecture](../Architecture.md), [the writing standard](../../../AGENTS.md)

Revision audited: `d6ab6d23` (`main`), worktree `Runtime/Worktrees/Developer/T-0078`.
Scope: `src/teamwork/*.py` (32 modules, 34,734 lines), `scripts/*.py` (10 files).
Audit only: no code change, no fix, no doc edit.

## 1. Sweep (proof the audit was systematic, not a sample)

| Sweep | Command | Result |
|---|---|---|
| Module inventory and size | `wc -l src/teamwork/*.py scripts/*.py \| sort -rn` | 40,086 lines; `engine.py` 20,783, `lanes.py` 2,494, `records.py` 2,296 |
| POSIX-only assumptions | `rg -n "fcntl\|os\.getuid\|os\.fork\|pwd\b\|grp\b\|os\.umask\|signal\.SIG\|/tmp\b\|os\.setsid\|select\.epoll\|resource\." src/teamwork/*.py scripts/*.py` | 8 hits, 3 classes (below) |
| Swallowed errors | `rg -n "except (Exception\|BaseException\|OSError)?\s*:\s*$" -A2 src/teamwork/*.py` | 169 `except` blocks, 6 `except OSError: pass` |
| Duplicate implementations | `rg -N -o "^\s*def (\w+)" -r '$1' src/teamwork/*.py \| awk -F: '{print $2}' \| sort \| uniq -d` | 30 function names defined in 2+ modules |
| Subprocess on a hot path | `rg -n "for .*:\s*$" -A6 src/teamwork/engine.py \| rg "subprocess\.(run\|Popen\|check_output)"` | 1 hit (`engine.py:5976`, `git add` per staged path: bounded by the change-set, not a defect) |
| Whole-file read vs bounded read | `rg -n "rglob\(" -A4 src/teamwork/*.py \| rg "read_text\|read_bytes"` | 0 hits: every tree walk reads per-file, and `gitutil.is_binary_content` reads only `BINARY_SNIFF_BYTES` (measured: 32 modules sniffed in 0.000 s) |
| Exit codes for an unknown id | 4 CLI calls against a fresh team (finding 1) | 1 vs 2, inconsistent |
| Process-global state | `io.atomic_write` umask window (appendix A) | measured, no repro: dropped |
| Unit suite | not re-run: `mypy`/`ruff` green per the task and the last green CI run at this head are the existing record; the audit needed no suite run for its findings | n/a |

Not read whole: `engine.py`, `lanes.py`, `records.py` (anchor-first `rg`, then +/-40 lines, as the task requires).

## 2. Findings, ranked

### F-1 (medium) - "unknown id" exits 1 in one record command and 2 in the other three; `K-0012` no longer reproduces

**Sides:** `src/teamwork/engine.py` (`cmd_tests_run` calls `io.die(msg)` -> code 1) vs `criteria verify`, `knowledge show`, `attention take` (argparse/`die(..., 2)` -> code 2).
**What breaks:** a script or a lane cannot branch on one code for "this id does not exist", and the recorded knowledge is now wrong about the value it documents.

Reproduction at `d6ab6d23`:

```sh
/usr/bin/python3 scripts/teamwork.py --project /tmp/twaudit/Project init
for c in "criteria verify T-9999" "knowledge show K-9999" \
         "tests run TS-9999 --by Developer --result pass --evidence x" \
         "attention take A-9999 --by Developer"; do
  /usr/bin/python3 scripts/teamwork.py --project /tmp/twaudit/Project $c >/dev/null 2>&1
  echo "exit $? <- tw $c"
done
```

Observed:

```text
exit 2 <- tw criteria verify T-9999
exit 2 <- tw knowledge show K-9999
exit 1 <- tw tests run TS-9999 --by Developer --result pass --evidence x
exit 2 <- tw attention take A-9999 --by Developer
```

`Knowledge.md` K-0012 states `criteria verify` exits 1 for an unknown id; measured here it exits **2**. So the invariant broke in both directions: the code is inconsistent and the record that documented it is stale.
**One-line fix:** one `unknown_id()` helper in `io.py` with one documented code (2 = "usage/id not found", 1 = "the store is wrong"), called by all four, plus a test per command.

### F-2 (low) - `norm_role` has two implementations and they have already diverged on the input one producer allows

**Sides:** `src/teamwork/records.py:1166` (`re.sub(..., str(name or "").lower())`, tolerant) vs `src/teamwork/board.py:121` (`re.sub(..., name.lower())`, intolerant). `records.py:1196` feeds the tolerant one from record fields; `board.py:137` (`display_role`) and `board.py:157` feed the intolerant one from the same producer family.

Reproduction at `d6ab6d23`:

```sh
PYTHONPATH=src venv/bin/python -c "
from teamwork import board, records
for v in [None, 5, 'Sec urity']:
    try: a=records.norm_role(v)
    except Exception as e: a='RAISE '+type(e).__name__
    try: b=board.norm_role(v)
    except Exception as e: b='RAISE '+type(e).__name__
    print(repr(v), '| records:', repr(a), '| board:', repr(b))"
```

Observed:

```text
None | records: '' | board: 'RAISE AttributeError'
5 | records: '5' | board: 'RAISE AttributeError'
'Sec urity' | records: 'security' | board: 'security'
```

**What breaks:** the rule "two spellings of one role are one role" now has two behaviours. `records` tolerates a record with no role (the schema permits it); `board` raises `AttributeError` - not `UnknownRole`, which is the exception `board` documents and the CLI handles - so a malformed queue record would surface as a traceback, not as the message that names the fix.
**One-line fix:** delete `board.norm_role` and import `records.norm_role` (the tolerant one is the contract); `display_role` then raises `UnknownRole` for an empty fold, which is its documented behaviour.

### F-3 (low) - `today_iso` and `slugify` are each implemented twice, and one `today_iso` bypasses the `records.today()` seam

**Sides:** `src/teamwork/attention.py:88` (`datetime.date.today().isoformat()`) vs `src/teamwork/records.py:1306` (`today().isoformat()`, the seam every other record uses); `src/teamwork/wiki.py:48` (`casefold`, no limit, fallback `"page"`) vs `src/teamwork/names.py:114` (`lower`, 40-char limit, fallback `"work"`).

Reproduction at `d6ab6d23`:

```sh
PYTHONPATH=src venv/bin/python -c "
import inspect; from teamwork import attention, records
print(inspect.getsource(attention.today_iso).strip().splitlines()[-1])
print(inspect.getsource(records.today_iso).strip().splitlines()[-1])"
```

Observed:

```text
return datetime.date.today().isoformat()
return today().isoformat()
```

**What breaks:** `records.today()` is the single date seam for every record file; the attention store's stamps do not go through it, so a frozen or injected clock moves one store and not the other. The two `slugify`s return different fallbacks (`page` vs `work`) and different truncation for the same subject.
**One-line fix:** import the `records` helpers in `attention` and `wiki`; keep one `slugify` with an explicit `limit`/`fallback` argument.

## 3. Swept and dropped (no reproduction - per the task's rule, not findings)

| Candidate | Site | Why dropped |
|---|---|---|
| `atomic_write` mutates the process-global umask outside a lock | `io.py:195-197` (`os.umask(0)` / `os.umask(current)`) | Two adjacent syscalls; a 4-thread probe found **0** wrongly-permissioned files in 16,746 creations against a 0-in-11,318 baseline (`probe(False) -> (11318, 0, [])`, `probe(True) -> (16746, 0, [])`). Window too narrow to measure; report as a latent shape, not a defect. |
| `/bin/sh` pre-commit hook with `mktemp "${TMPDIR:-/tmp}"` | `hooks.py:96,121` | Git for Windows ships `sh` and `mktemp`, and the `windows-latest` matrix jobs were not read in this budget. `UNVERIFIED` - not claimed. |
| `os.killpg` / `os.getpgid` | `gitutil.py:220`, `lanes.py:812` | Both are guarded (`os.name == "nt"` branch; `hasattr(os, "killpg")`). Correct, not a finding. |
| `engine.py:5976` `subprocess.run` inside a loop | `engine.py:5971` | The loop is over the staged paths of one change-set, not a table; bounded by the diff. Not a hot path. |
| 30 duplicate `def` names from the sweep (`find`, `walk`, `check`, `status`, `score`, `problems`, `render`, `read`, `main`, `_line_count`, `next_id`, ...) | across modules | Same-name/different-signature is normal (`sparse._line_count(text)` vs `memverify._line_count(path)`); only the pairs in F-2/F-3 have one rule with two behaviours, measured. |
| 6 `except OSError: pass` blocks | `lanes.py:1770`, `io.py:205,222`, `engine.py:5995,10527,17792` | Each swallows a best-effort cleanup/`stat` of a path it just used; none hides a gate decision. No reproduction of a lost error. |

## 4. Why the class-1 list is short

`T-0001` (M19) and the 20+ audit-derived tasks on this queue (`T-0002`, `T-0003`, `T-0006`, `T-0007`, `T-0009`, `T-0012`, `T-0022`, `T-0023`, `T-0028`, `T-0029`, `T-0030`) already closed the lock race, the credential-mask gap, the ledger fork, the worktree collision and the identity gate. The remaining measured defects are the exit-code invariant (F-1) and drift between twins (F-2, F-3) - none of them a data-loss path.
