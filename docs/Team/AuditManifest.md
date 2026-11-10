# Audit report

- generated: 2026-11-10T11:59:17
- team: Teamwork
- ledger: 4418 records, chain verified: True
- checkpoint: record #4418 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `e5ab8c5ae3384bd01752f570e8897e73`
- git: 833008180f23 on main, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 38

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 181574 | `130f62e32145f831…` |
| docs/Team/Decisions.md | 375924 | `5bc66707205e0943…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 62432 | `b7c10fda3b79c301…` |
