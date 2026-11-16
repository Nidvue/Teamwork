# Audit report

- generated: 2026-11-16T14:42:47
- team: Teamwork
- ledger: 7952 records, chain verified: True
- checkpoint: record #7952 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `412f4f72ddbace6f6796558e841c146b`
- git: 6d3187c834a8 on ceo/t-0073-refresh-the-closing-audit-manifest-at-th, dirty: False
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
| docs/Team/Architecture.md | 191255 | `cca07afad5e2d4d9…` |
| docs/Team/Decisions.md | 434835 | `81cef4eb47d333a4…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 64083 | `47d2fc66e247dce1…` |
