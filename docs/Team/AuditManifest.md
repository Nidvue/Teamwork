# Audit report

- generated: 2026-11-09T01:43:50
- team: Teamwork
- ledger: 17 records, chain verified: True
- checkpoint: record #17 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `5f55df08e70bd1a2042a08aa268b375a`
- git: db8764394c7b on ceo/t-0023-record-the-ledger-cut-ruling-d-20261109, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 30

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 180681 | `9c747f1734833871…` |
| docs/Team/Decisions.md | 364812 | `fea5a897106f6ba4…` |
| docs/Team/Plan.md | 95292 | `f2b41f46c8923d09…` |
| docs/Team/Project.md | 58516 | `59e078842ed8f127…` |
