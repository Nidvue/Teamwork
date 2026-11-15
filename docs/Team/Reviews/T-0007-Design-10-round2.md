# T-0007 round 2 - Design.md 10 critiqued against the payload and the pi widget API

Owner: Reviewer.
Related: Design.md section 10 (the agent-state widget spec) and T-0006 (the display-path census).
Design.md carries no back-link to this record yet: the Designer owns that edit and it is part of the routed finding.

Measured at `0fbdc4ea` on the live team: `scripts/teamwork.py status --json` -> schema 4, count 4,
counts `{busy 3, idle 1, ready 0, review 0, activated 14, retired 17, lanes_live 2, lanes_ended 138, lanes 6}`.
Every line number below is re-derived at that revision with `grep -n` in `extensions/teamwork-status.ts`.

## 1. Verdict

The round-2 row spec (10.8) is a good brief and the glyph/word rule (10.3) is right. The document is not
developer-ready: **4 of its 15 defects are already fixed at this revision and 1 is false**, its payload
contract needs an engine change it says it does not make, three of its checks measure the wrong thing, and
it still cannot answer the efficiency question it is the operator's only live surface for. Fix the sections
in 2-5 and it can be implemented by one Developer against one frozen contract.

## 2. Stale and false defects (10.7, 10.6) - measured

| # | Design.md says | at `0fbdc4ea` |
|---|---|---|
| D-9 | "overflow line pushed after the row loop and then cut by the final slice; room formula reserved only the idle line" (`:196`,`:201`,`:210`,`:214`) | `:274` `cap = BUDGET - 1 - idleLine`; `:275` `if (room < busy.length) room = Math.max(0, cap - 1)` - the overflow line **is** reserved before any row is dropped. Fixed |
| D-10 | "`MAX_LINES = 24` at `:8`"; "lane loop at `:196` runs before the room formula at `:201`" | no `MAX_LINES` exists; `:8` is `const BUDGET = 12;`; `:284` `laneRoom = hidden > 0 ? 0 : Math.min(LANE_MAX, BUDGET - lines.length)` runs **after** rows, overflow and idle. Both halves false |
| D-11 | "`task_label()` clips to 8, `text(clean, 8)` at `:132`" | `:149` `task_label`, `:16` `TASK_MAX = 6`, `text(..., TASK_MAX)`. Already 6, matching 10.2 |
| D-15 | "the header prints `activated`, `:191`" | `:283` header is `teamwork · busy · live · review`; no `activated` anywhere in the file |
| 10.6 | "`TOTAL` and `OVERFLOW` are red against the shipped renderer today" | both green by construction at `:274`-`:280`. A Tester told to "add them with the fix" adds two passing checks and reports a fix that changed nothing |
| 10.8 | "`render` at `:158`, the shipped file has no third parameter" | `:247` `render(payload, width = WIDTH_MAX, paint?: Paint)` - the third parameter exists and is threaded from `ctx.ui.theme` at `:335` |
| D-8 | "no colour is emitted at all" | `tint()` paints every glyph and row through `paint.fg`; `:335` passes the theme. Colour is emitted, 10.3's "the renderer emits no ANSI today" is false |

What survives and must be fixed: **D-12** (instance capped at 14, `:10`), **D-13** (`bar()` `:136` is 5 cells + ` 42%`),
**D-14** (no budget field in schema 4). The census needs a re-derivation pass before it is handed to a
Developer, or the fix list ships two edits for defects that are already gone (L-0029, K-0011).

## 3. Unimplementable as specified

1. **Schema 5 does not exist and the document says it does not need to.** The preamble says "consumes
   `status --json` schema 4 and changes no engine behaviour"; 10.8's contract table then requires
   `budget_seconds`, `remaining_seconds`, `remaining_text`, `activity`, `stalled`, `state: "stalled"`,
   `counts.stalled` - none is in the payload (`status --json` at `0fbdc4ea`). D-14/D-15 admit the engine
   must change. Either the header drops "changes no engine behaviour" and names the engine task and its
   owner, or the row drops the fields. As written it is a widget task that silently becomes an engine task.
2. **Two of those fields are already derivable from schema 4, so the engine change is not needed for them.**
   `left` is in `progress` today: the live Developer row carries `"attempt 2/2, 4% of 40m"` with
   `elapsed 107` -> budget 2400s, left 2293s. `stalled` is `state == "busy" && lane == ""`. D-7 lists
   `progress` (text) as "unread" and then asks for a new field to carry what it already carries. Deriving
   in the widget keeps the change to one file and keeps schema 4 a contract.
3. **The tooltip does not exist.** D-3's fix is "provider in the tooltip or dropped". `ctx.ui.setWidget`
   with `string[]` has no tooltip; a tooltip needs the component form
   (`setWidget(key, (tui, theme) => ...)`, docs `extensions.md:2922`), which must then own `render(width)`
   and `invalidate()`. Say "dropped" or change the widget kind; do not name an API the extension does not call.
4. **The width is not the extension's to know.** `terminalWidth()` reads `process.stdout.columns` and falls
   back to 100 (`:296`-`:299`); in print/RPC mode there is no TTY, so the requested width is a guess. The
   harness hands the real width to a component, not to `string[]`. So "never wrap at the requested width"
   is only true of the guessed width.
5. **`lane_lines` in 10.5's `k` is circular.** `k = min(busy + stalled, 12 - 1 - 1 - 1 - lane_lines)` while
   step 5 says lane lines are "drawn from the room left after rows + overflow + idle; first to yield" -
   lane_lines is an output of the arithmetic it is an input to, and 10.5's three derivations hand-set it
   (0, 3, 0) instead of computing it. The shipped `:284` is the only computable form (post-hoc, and it
   draws lanes last, which the document calls the defect). Restate the formula as: rows = `min(drawable,
   12 - 1 - overflow - idle)` computed first, then `lane_lines = min(3, 12 - lines.length)`.

## 4. Checks that measure the wrong thing (10.6)

- **no wrap** is `max(len(line)) <= width` - string length. `● ⚠ ◐ ⚙ ○ ⏸ ✕ ↳ ▸ █ ░ …` are ambiguous-width
  and can occupy 2 columns each; pi's own rule is `visibleWidth()`/`truncateToWidth()` and "measure visible
  terminal columns rather than string length" (docs `tui.md:24`-`26`). A row of 80 characters can be 88
  columns and wrap while this check passes.
- **`CONSERVATION`** counts `shown` as lines beginning with the busy glyph. 10.8 makes a review row's prefix
  `◐`, so every busy review lane is invisible to its own conservation check and `shown + hidden == busy`
  fails on any payload with a review lane. Count rows by "starts with `●` or `◐`", or state that the review
  lane is not a state row.
- **`no headless row`** allows `● ⚙ ○ +` and the header only. 10.8 adds `⚠ ◐ ⏸ ✕`, and 10.8 supersedes
  10.2-10.4 only - not 10.6. A Tester implementing 10.6 literally fails every stalled, paused, failed and
  review row it is supposed to be guarding. 10.6 needs the 10.8 glyph set.
- **`AGREEMENT` vs `CONSERVATION`** use the same symbol `busy` for two different numbers: 10.8 redefines
  `busy` in 10.5 as "state rows the widget must draw, which is now busy + stalled", while the header and
  footer `busy` are `counts.busy`. Two Testers implement two different assertions from one word. Name them
  `counts.busy` and `rows_expected`.

## 5. Where it still misleads the operator

1. **A zero count is omitted**, but H5 is "what is waiting for me?" answered by "review count in the header".
   `review 0` is the answer the operator needs most (nothing is waiting); omitting it makes an empty review
   queue indistinguishable from an untracked one. Print `0 review`.
2. **`role == "reviewer"` is not "this row is a review".** `:262` sets `review` from the instance's role, and
   the live payload has a `Reviewer-1` row doing its own task `T-0007`. Drawn `◐ ↳T-0007` it reads as a
   review of T-0007 by someone else. The payload cannot tell the two apart today: derive "review" from the
   claimed task's owner (`task_owner != role`) or drop the distinction from the row.
3. **The instance column is "fixed" only per frame.** `layoutFor` pads to the widest *drawn* instance; drop
   the widest seat into `+N more busy` and every remaining row's tail shifts left. The promise "the tail
   starts at the same index on every row" holds inside one frame and flickers between them. Pad to
   `max(6, widest instance in the payload)`.
4. **The model column costs 26% of an 80-column line** (21 of 80) and the activity gets 13, while the
   operator's H4 is "what is it doing right now". The payload's model is constant across every row on this
   team (`deepinfra/...DeepSeek-V4.1-Flash-1017`); the column is the last thing dropped. Make model the first
   drop (below 100) and give the activity the width.
5. **The 10.8 arithmetic is off by one.** `1+1+15+1+7+1+5+1+1+1+5+1+5+1 = 46` already contains the
   separator before the model, so the model block is 20, not 21: the activity gets `80-46-20 = 14`, not 13.
   A line built to the row template with activity 14 is exactly 80 columns (`python3 .pi/Teamwork/Teams/Teamwork/Agents/Reviewer-1/Scratch/check_row_arith.py` -> `row template with activity=14 is 80 columns; spec fixed=46; activity = 80-46-20 = 14, the doc says 13`).

## 6. What it still misses for efficiency and effectiveness

The widget answers "is it busy, on what, how long" (H1-H4) and nothing about whether the work is going
well. Every signal it needs is already in schema 4 and 10.1 declares each one unread or history:

| question | signal in the payload today | what the spec does with it |
|---|---|---|
| is this lane thrashing? | `progress` carries `attempt 2/2`; `Instance` has no attempt field but the text does | D-7 "unread", not drawn. A second attempt is the single strongest effectiveness signal on the row |
| did work just fail? | lanes carry `state: failed/timeout/lost`, `counts.lanes_ended` 138 | 10.1 "history is not drawn", but a lane that failed 30 s ago is not history; `✕`/`⏸` are in the glyph table with **no field in the schema-5 contract table to drive them** - the glyphs are undrawable as specified |
| is the estimate honest? | `progress` `4% of 40m` vs `elapsed 107` | only `left` is derived from it; nothing compares left against what the lane has actually done, so a lane stuck at 4% for 30 m looks healthy |
| what does a seat cost? | not in the payload (`model`, `provider` only) | correctly out of scope, but the document should say cost is the Board's/CFO's and not imply H3 answers it |

Minimum to make the surface judge effectiveness without new fields: draw `attempt n` in the activity
column when `progress` names an attempt > 1, and spend the `+N more busy` line's neighbour on a header
`✕<n> failed` counted from `lanes_ended` in the last hour. Both are widget-only and keep schema 4 frozen.

## 7. Scope

Reviewed: `docs/Team/Design.md` 584-882 (10.1-10.8), `extensions/teamwork-status.ts` at `0fbdc4ea`,
`scripts/teamwork.py status --json` live, pi docs `extensions.md`/`tui.md` for the widget and width API.
Not touched: no code change, no Design.md edit (Designer owns it), no test file. The findings above are
routed to the Designer as the owner of the spec and to the Developer as the owner of D-12/D-13.
