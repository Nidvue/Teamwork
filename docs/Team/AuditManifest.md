# Audit report

- generated: 2026-11-16T00:44:17
- team: Teamwork
- ledger: 1288 records, chain verified: True
- checkpoint: record #1288 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `060909b83912858db0dcd1b01928a655`
- git: 147adff03af2 on main, dirty: True
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
| docs/Team/Decisions.md | 439674 | `b1c15142f23c7350…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 64083 | `47d2fc66e247dce1…` |
