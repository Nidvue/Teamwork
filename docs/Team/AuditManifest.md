# Audit report

- generated: 2026-10-29T18:08:48
- team: Teamwork
- ledger: 1558 records, chain verified: True
- checkpoint: record #1558 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `68d1d082e9fef2c4568b4fd29abfc989`
- git: 7b4ff2cc5230 on ceo/t-0023-chore-records-export-the-closing-audit-m, dirty: False
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
| docs/Team/Architecture.md | 101874 | `29a16b1899c80527…` |
| docs/Team/Decisions.md | 261977 | `46620d5ddddc5963…` |
| docs/Team/Plan.md | 74887 | `736942a510bd07f6…` |
| docs/Team/Project.md | 44089 | `a64c104ef240accd…` |
