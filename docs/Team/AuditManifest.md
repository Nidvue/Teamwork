# Audit report

- generated: 2026-10-19T02:09:01
- team: Teamwork
- ledger: 184 records, chain verified: True
- head hash: `bdf747c63f97609c8e17eddbb52742c0`
- git: 4cd8afc78e9c on ceo/t-0017-close-m5-mark-the-board-done-and-export, dirty: True
- externally verifiable artifacts: 5
- local-only state files: 22

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 10157 | `30a601b72f8f76e2…` |
| docs/Team/Archive.md | 29294 | `f4577574042bf205…` |
| docs/Team/Decisions.md | 24155 | `293f23d7e4610db8…` |
| docs/Team/Plan.md | 4229 | `abd431eba676b986…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
