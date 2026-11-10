# Audit report

- generated: 2026-11-09T12:22:50
- team: Teamwork
- ledger: 2496 records, chain verified: True
- checkpoint: record #2496 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `09b0d4bd67bd11df427bd512712fcf00`
- git: 3645a87efc6f on main, dirty: True
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
| docs/Team/Architecture.md | 181387 | `05da19a9a8b53f51…` |
| docs/Team/Decisions.md | 368016 | `eb621ecd61d4fdfd…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 61016 | `322b570fb78aff7d…` |
