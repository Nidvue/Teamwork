# Audit report

- generated: 2026-11-13T12:37:13
- team: Teamwork
- ledger: 7821 records, chain verified: True
- checkpoint: record #7821 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `0107a88ba55fe69c7f6123c96b48837e`
- git: 1280d1597d15 on ceo/t-0065-export-the-closing-audit-manifest-at-the, dirty: False
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
| docs/Team/Architecture.md | 189556 | `fdafcd4ec0cb9cdf…` |
| docs/Team/Decisions.md | 412192 | `ffa28d8f716c5442…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 62531 | `6364baa525482e4f…` |
