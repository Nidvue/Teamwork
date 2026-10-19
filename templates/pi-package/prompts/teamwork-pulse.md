Run one teamwork pulse in this project.

1. `python3 scripts/teamwork.py pulse --commit` and read the dispatch plan.
2. For every assignment it reports, message that lane to start now.
3. For every idle lane with no matching work, give it the highest-priority
   unblocked task of its role, or fold the lane.
4. Unblock anything stuck (blocked task, open dispute, stale claim).
5. For every unclaimed deliverable in `teamwork.py review --queue`, aim a
   different Reviewer lane at it and never stack the backlog on one lane.
6. Report one short line: what moved, what is blocked, what is next.

Never stop the team while `teamwork.py loop` says CONTINUE.
