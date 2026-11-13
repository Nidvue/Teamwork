# Audit report

- generated: 2026-11-13T11:52:57
- team: Teamwork
- ledger: 7722 records, chain verified: True
- checkpoint: record #7722 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `7ae9c37723ede632d5fc35b0bb089c2e`
- git: b368c4886698 on ceo/t-0060-refresh-the-audit-manifest-and-the-board, dirty: False
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
| docs/Team/Architecture.md | 189306 | `5d364309b9714166…` |
| docs/Team/Decisions.md | 410111 | `25a84c3831f27cd2…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 62531 | `6364baa525482e4f…` |
