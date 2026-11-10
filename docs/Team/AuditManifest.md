# Audit report

- generated: 2026-10-21T18:12:39
- team: Teamwork
- ledger: 830 records, chain verified: True
- checkpoint: record #830 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `d86a57168cb3e23c643c64e018e11b3f`
- git: 2f099cf7c15c on ceo/t-0014-re-export-the-audit-manifest-at-the-push, dirty: False
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
| docs/Team/Architecture.md | 31647 | `35d72df8f505b0d1…` |
| docs/Team/Decisions.md | 160084 | `07d40c012b796c71…` |
| docs/Team/Plan.md | 17872 | `4174b8947568a170…` |
| docs/Team/Project.md | 26147 | `c94faeff4ee1b52d…` |
