# Audit report

- generated: 2026-11-12T16:02:24
- team: Teamwork
- ledger: 6821 records, chain verified: True
- checkpoint: record #6821 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `1159e38fe9ad407bebb6ae15adc342aa`
- git: 738d58cfa107 on main, dirty: False
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
| docs/Team/Architecture.md | 188338 | `5cca8792cf6b122b…` |
| docs/Team/Decisions.md | 409819 | `56ee9a8389ef24f5…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 62531 | `6364baa525482e4f…` |
