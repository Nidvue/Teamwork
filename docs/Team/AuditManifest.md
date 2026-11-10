# Audit report

- generated: 2026-10-22T04:37:59
- team: Teamwork
- ledger: 2505 records, chain verified: True
- checkpoint: record #2505 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `387841d19515dd113e7bd59b46ac7a42`
- git: 67df036d0bbe on main, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 46

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 84747 | `dc16bfb955bc1c96…` |
| docs/Team/Decisions.md | 214847 | `54f0fe010775769a…` |
| docs/Team/Plan.md | 28324 | `bd7c44fbc11dc756…` |
| docs/Team/Project.md | 26260 | `c02716956ac739c9…` |
