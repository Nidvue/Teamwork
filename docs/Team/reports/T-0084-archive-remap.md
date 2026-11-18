# T-0084 - every archive merge revision re-pointed onto main's line

Owner: CEO.

Related: [Archive](../Archive.md) · [the eight rows recorded after this repair](archive-remap-2026-11-18-eight-rows.md)

## 1. Why this exists

`docs/Team/Archive.md` was carried across the 2026-11-18 reconciliation of the published
line, so its `- branch / merge:` fields named revisions of the discarded line: 560 commits
still existed but were ancestors only of `backup/main-local-20261118`, and 26 objects were
gone entirely. The guard `tests/unit/test_archive_merge_revisions.py` was therefore red on
`main` and on `origin/main`. The owner ruled (Q-0002 option 1, `D-20261118-CEO-2`) that the
record is repaired row by row rather than the guard widened.

## 2. The rule each row was re-pointed by

| Rule | Rows | What it proves |
|---|---|---|
| the one merge commit on main for this branch | 510 | `main` carries exactly one `chore(merge): merge of <branch>` for the branch the row names |
| unique identical subject on main | 47 | exactly one commit on `main` has the recorded commit's subject |
| identical subject and identical patch-id on main | 29 | one commit on `main` has the recorded commit's subject and the same `git patch-id` - the same diff |
| already an ancestor of main | 2 | the revision was already on `main`; untouched |

586 of 588 claimed rows changed value. 26 of them recorded a
revision whose object no longer exists; each is now resolved by the merge commit of the branch
its own row names.

## 3. Reproduce

```sh
git -C <repo> merge-base --is-ancestor <re-pointed> main   # exit 0 for every row below
.venv/bin/python -m pytest -q tests/unit/test_archive_merge_revisions.py   # 6 passed
```

## 4. The 26 rows whose recorded object is gone

| row | branch | lost revision | merge on main | rule |
|---|---|---|---|---|
| 619 | tester/t-0008-m26-test-audit-vacuous-tests-proved-by-m | 49e8fde7 | 4ebe9f637ee1 | the one merge commit on main for this branch |
| 620 | developer/t-0078-m26-code-audit-real-defects-broken-invar | 9de0c8b1 | 945e8a2a85cb | the one merge commit on main for this branch |
| 621 | developer-2/t-0084-panel-contract-ac-d1-d2-d3-d5-every-draw | 7e085c95 | e1e2bdde4219 | the one merge commit on main for this branch |
| 623 | releaseengineer/t-0004-release-consistency-r7-and-repository-hy | 3b7f4425 | e2b774b644a2 | the one merge commit on main for this branch |
| 624 | designer/t-0004-ac-d4-record-the-panel-design-what-the-u | 449cbd20 | b7c3c3aee076 | the one merge commit on main for this branch |
| 626 | securityauditor/t-0002-record-the-security-layer-for-the-m26-au | e5cfb54b | 27dfa42d5ae3 | the one merge commit on main for this branch |
| 628 | developer-2/t-0082-status-shows-another-role-s-task-title-s | 71d8da75 | 411b6b7d3caf | the one merge commit on main for this branch |
| 629 | developer/t-0085-unit-layer-records-for-15-areas-with-no | 85a94e26 | a9827fdf910a | the one merge commit on main for this branch |
| 630 | tester/t-0009-triage-the-41-test-layer-gaps-into-per-r | 4986d86b | 9a43f1c4c643 | the one merge commit on main for this branch |
| 632 | releaseengineer/t-0005-release-layer-record-for-area-changelog | c08da898 | 0fb73ee3bdf4 | the one merge commit on main for this branch |
| 633 | tester/t-0010-ac-m25-4-prove-an-installed-package-expo | 5164a1db | d9b1356b8fc0 | the one merge commit on main for this branch |
| 634 | technicalwriter/t-0001-m26-docs-audit-false-claims-proved-by-co | c1a0ca82 | a6ec92a15a35 | the one merge commit on main for this branch |
| 635 | developer/t-0079-release-blockers-7-failing-tests-board-d | c77cd126 | 138421c6db72 | the one merge commit on main for this branch |
| 636 | developer-3/t-0086-guard-the-cost-policy-a-test-that-no-lan | 47d6a6fa | 901e950e6cc9 | the one merge commit on main for this branch |
| 637 | technicalwriter/t-0002-link-health-on-main-10-pre-existing-brok | d1845257 | e58f715a1063 | the one merge commit on main for this branch |
| 639 | tester/t-0011-integration-layer-tests-missing-for-widg | 1e3ae139 | 3ffd73072921 | the one merge commit on main for this branch |
| 640 | developer-1/t-0092-the-lane-display-kills-the-lane-refresh | 2319ae1f | 7c0e9d43adba | the one merge commit on main for this branch |
| 641 | technicalwriter/t-0003-ship-the-operating-rule-the-ceo-decompos | 059e413c | 09cf7353127f | the one merge commit on main for this branch |
| 642 | developer-1/t-0089-a-stalled-seat-is-never-reconciled-a-cla | f37cf990 | 7abe0fdd14e6 | the one merge commit on main for this branch |
| 643 | developer-2/t-0098-the-silent-lane-watchdog-measures-log-by | 834c92bf | ce879dea1ca1 | the one merge commit on main for this branch |
| 644 | developer-1/t-0088-live-lane-scratch | 3677d16e | 4d63ea06cf80 | the one merge commit on main for this branch |
| 645 | architect/t-0003-freeze-the-lane-runtime-contract-so-a-te | 88c264bf | b3fdf6b10958 | the one merge commit on main for this branch |
| 646 | developer-2/t-0100-the-gate-role-s-startup-read-is-2624-b-o | f33b74d1 | 6f3eaea7eba0 | the one merge commit on main for this branch |
| 647 | developer-4/t-0104-a-reviewer-authors-the-merge-and-the-rec | c6d4a5e8 | 45f0ae8f8e96 | the one merge commit on main for this branch |
| 648 | developer-1/t-0099-an-open-feature-does-not-protect-its-tea | 7b9e098a | 7a75a74d4afd | the one merge commit on main for this branch |
| 649 | developer-2/t-0094-model-auto-must-refuse-a-premium-host-de | 23d905ab | 58175f802c7e | the one merge commit on main for this branch |

## 5. Every changed row

| row | branch | recorded | re-pointed | rule |
|---|---|---|---|---|
| 16 | ceo/t-0008-resolve-residual-audit-items-umask-bom-l | 858faf6 | 67ecafeb1ff7 | identical subject and identical patch-id on main |
| 17 | ceo/t-0009-fix-the-pr-merge-commit-message-acting-r | 851a304 | f3b531d4a9ae | the one merge commit on main for this branch |
| 18 | ceo/t-0010-export-the-current-audit-manifest-with-a | 2136870 | 8386ebe57c1c | the one merge commit on main for this branch |
| 19 | ceo/t-0011-split-engine-py-into-typed-modules | a2ff3d3 | eada6292f608 | the one merge commit on main for this branch |
| 20 | ceo/t-0012-skip-the-posix-umask-test-on-windows | 5273df9 | 7ebc79f2bc7d | the one merge commit on main for this branch |
| 21 | ceo/t-0013-fix-import-order-in-the-windows-skip-tes | e127a3b | 7cbc987a6723 | the one merge commit on main for this branch |
| 22 | ceo/t-0015-refresh-stale-governance-docs-against-th | 6d2f31c | 587e05ae38f4 | the one merge commit on main for this branch |
| 23 | ceo/t-0014-rebase-and-merge-the-three-open-dependab | 6d2f31c | ff247eee1096 | the one merge commit on main for this branch |
| 24 | ceo/t-0016-fix-ensure-gitignore-orphan-headers-and | 6d2f31c | 5d66ef14a978 | the one merge commit on main for this branch |
| 25 | ceo/t-0017-close-m5-mark-the-board-done-and-export | 6d2f31c | 0fc4440fca37 | the one merge commit on main for this branch |
| 26 | ceo/t-0018-record-the-m5-fix-and-dependency-bumps-i | 6d2f31c | 04be7689da80 | the one merge commit on main for this branch |
| 27 | ceo/t-0019-publish-the-closing-audit-manifest-for-t | 6d2f31c | b03a36be4047 | the one merge commit on main for this branch |
| 28 | ceo/t-0020-structured-evidence-packets-and-the-repr | 6967d70 | eef637a78073 | the one merge commit on main for this branch |
| 29 | ceo/t-0021-review-parity-baseline-and-replay-on-the | 555f294 | 1c98ae23de98 | the one merge commit on main for this branch |
| 30 | ceo/t-0024-extract-the-ceo-audit-close-out-flow-as | 089e920 | cbc239e4cdd6 | the one merge commit on main for this branch |
| 31 | ceo/t-0025-fix-the-root-hygiene-allowlist-for-the-t | a1e9164 | 67bda57b315b | the one merge commit on main for this branch |
| 32 | ceo/t-0022-tighten-repro-matching-and-cover-the-aud | a1e9164 | 6fa043ae78c7 | the one merge commit on main for this branch |
| 33 | ceo/t-0023-bind-the-d-20261019-ceo-3-evidence-to-th | 83d66db | b0fb33c67003 | the one merge commit on main for this branch |
| 34 | ceo/t-0026-close-the-m6-records-mark-t-0023-done-an | 790bb3b | 09048da16c72 | the one merge commit on main for this branch |
| 35 | developer-1/t-0001-fan-review-out-across-reviewer-lanes-pul | 4cde0ef | f598ea92e3d7 | identical subject and identical patch-id on main |
| 36 | ceo/t-0027-m7-records-final | 881123e | f477e139826d | the one merge commit on main for this branch |
| 37 | ceo/t-0031-pi-teamwork-only | fa99230 | 6c512b658046 | the one merge commit on main for this branch |
| 38 | ceo/t-0032-archive-link-hygiene | 45f3a76 | 5a849e9a85a9 | the one merge commit on main for this branch |
| 39 | architect/t-0001-system-layer-check-the-architecture-md-m | 7d4ca76 | 353688618bd5 | the one merge commit on main for this branch |
| 40 | ceo/t-0036-context-economy-loop-and-archive-listing | f398bdb | b03772c5a95c | the one merge commit on main for this branch |
| 41 | ceo/t-0038-decision-ids-collide-across-parallel-bra | f398bdb | 7527ac94341f | the one merge commit on main for this branch |
| 42 | ceo/t-0035-archive-quote-hygiene-the-merged-t-0032 | f398bdb | d58bfad6687b | the one merge commit on main for this branch |
| 43 | ceo/t-0037-roster-economy-a-slim-tier-must-be-the-d | c589d74 | 0fb78a12bcca | the one merge commit on main for this branch |
| 44 | ceo/t-0041-push-per-stage-a-merged-stage-is-pushed | a656882 | 3e82b3d65aad | the one merge commit on main for this branch |
| 45 | tester-1/t-0001-integration-test-the-context-economy-con | a656882 | ee4b625cb0d2 | the one merge commit on main for this branch |
| 46 | ceo/t-0033-provider-caps | a656882 | f1f880a442f7 | the one merge commit on main for this branch |
| 47 | ceo/t-0042-reporting-hierarchy-delivery-roles-repor | 0cf7df8 | c6cbef6f692e | the one merge commit on main for this branch |
| 48 | ceo/t-0040-r2 | 0cf7df8 | 84cbfbc77062 | the one merge commit on main for this branch |
| 49 | ceo/t-0034-gate | dfe03b5 | 94fb4b300fac | the one merge commit on main for this branch |
| 50 | ceo/t-0046-refresh-the-installed-skill-from-main | 35b75d7 | 43a639115259 | the one merge commit on main for this branch |
| 51 | ceo/t-0029-r2 | 98a5c67 | 79632e3e800c | the one merge commit on main for this branch |
| 52 | ceo/t-0045-release-gate-reads-code-scanning-alerts | 98a5c67 | c8445a79eadc | the one merge commit on main for this branch |
| 53 | securityauditor/t-0003-code-scanning-py-clear-text-logging-sens | a8e6c19 | a5eb1b9d76f3 | the one merge commit on main for this branch |
| 54 | projectmanager/t-0001-plan-graph-integrity-r2 | dfe03b5 | 9a7482eea567 | the one merge commit on main for this branch |
| 55 | ceo/t-0034-gate | dfe03b5 | 94fb4b300fac | the one merge commit on main for this branch |
| 56 | ceo/t-0043-r2 | 522c496 | 9d90e08f0255 | the one merge commit on main for this branch |
| 57 | ceo/t-0049-d-ceo-17-must-carry-a-machine-readable-e | 3845bc3 | 0977953b1241 | the one merge commit on main for this branch |
| 58 | developer-1/t-0001-fan-review-out-across-reviewer-lanes-pul | 3e502d2 | 019c2db3059d | identical subject and identical patch-id on main |
| 59 | developer-1/t-0001-fan-review-out-across-reviewer-lanes-pul | 3e502d2 | 019c2db3059d | identical subject and identical patch-id on main |
| 60 | developer-1/t-0001-fan-review-out-across-reviewer-lanes-pul | 3e502d2 | 019c2db3059d | identical subject and identical patch-id on main |
| 61 | developer-1/t-0001-fan-review-out-across-reviewer-lanes-pul | 3e502d2 | 019c2db3059d | identical subject and identical patch-id on main |
| 62 | ceo/t-0048-archived-evidence-must-not-carry-a-crede | f8215a7 | 4fb65034168b | identical subject and identical patch-id on main |
| 63 | tester/t-0001-task-graph-integration | f8215a7 | cd3018f1caac | the one merge commit on main for this branch |
| 64 | ceo/t-0050-auditreport-is-stale-it-still-claims-a-p | 2cac155 | 2bd822a39304 | the one merge commit on main for this branch |
| 65 | ceo/t-0051-windows-ci-is-red-five-portability-defec | a17aa63 | 6979dd294612 | the one merge commit on main for this branch |
| 66 | securityauditor/t-0004-triage-the-two-open-codeql-false-positiv | e848f86 | 5fd6ff4812d1 | the one merge commit on main for this branch |
| 67 | ceo/t-0052-windows-ci-round-2-the-worktree-tests-co | f310a61 | 62c57cacf532 | the one merge commit on main for this branch |
| 68 | ceo/t-0053-the-privacy-gate-cries-wolf-on-an-elided | f11606d | 87f879576470 | the one merge commit on main for this branch |
| 69 | ceo/t-0054-a-finished-task-gate-override-cannot-hol | aeaead7 | 697acac55733 | the one merge commit on main for this branch |
| 71 | productmanager/t-0001-traceability-r4 | abf031e | 1621bd8f775f | the one merge commit on main for this branch |
| 72 | releaseengineer/t-0002-release-candidate-gate-r2 | 7f2b2f8 | e1467daeaa6c | the one merge commit on main for this branch |
| 73 | ceo/t-0055-close-out-the-run-export-the-manifest-an | db6b6e2 | 4e14e410a7fe | the one merge commit on main for this branch |
| 74 | ceo/t-0056-refresh-the-traceability-state-column-ac | 756379d | c13613ad23ea | the one merge commit on main for this branch |
| 75 | ceo/t-0057-windows-ci-round-3-the-archive-guard-nee | 63dfc8a | 557d69da7e67 | the one merge commit on main for this branch |
| 76 | ceo/t-0058-tag-v1-1-0-date-the-release-section-inst | ed51f5c | 496c2a103670 | the one merge commit on main for this branch |
| 78 | ceo/t-0062-m9-0-open-the-milestone-criteria-task-gr | 9295728 | 3b32915e0a9e | the one merge commit on main for this branch |
| 79 | releaseengineer/t-0005-m9-h2-repair-docs-team-release-md-your-f | 9295728 | dea2e9c22c6d | the one merge commit on main for this branch |
| 80 | developer-1/t-0009-m9-c3-tests-r3-exception-admission-must | dc3d99a | 39ee7a7beecc | the one merge commit on main for this branch |
| 82 | architect/t-0003-m9-a2-correct-the-three-contract-defects | a4289b3 | a2aa0ab2da0e | the one merge commit on main for this branch |
| 83 | developer-2/t-0006-m9-c-unit-tests-for-every-release-consis | 6864ee1 | 3876ba191030 | the one merge commit on main for this branch |
| 84 | developer-2/t-0011-m9-p-the-ci-path-filter-contract-tests-m | 85acbcd | f2578083aac3 | the one merge commit on main for this branch |
| 85 | developer-1/t-0005-m9-b-scripts-check-release-consistency-p | 85acbcd | b4c6c87bc8eb | the one merge commit on main for this branch |
| 86 | - | 156f49b | 0f4d639c96b9 | unique identical subject on main |
| 88 | ceo/t-0059-m9-f-bump-main-to-1-1-3-and-record-the-n2 | 85acbcd | 870d2e97c021 | the one merge commit on main for this branch |
| 89 | releaseengineer/t-0003-m9-d-wire-the-consistency-gate-into-ci | c2884bc | be6cb53faab0 | unique identical subject on main |
| 90 | developer-2/t-0013-m9-r-the-r9-rule-must-not-flag-a-line-th | c2884bc | 547f7ffb50dd | the one merge commit on main for this branch |
| 91 | releaseengineer/t-0007-m9-n-release-yml-must-fetch-the-full- | c2884bc | ca95c318569c | the one merge commit on main for this branch |
| 92 | developer-3/t-0007-m9-e-makefile-target-for-the-consistency | c2884bc | 69d5f07616e9 | the one merge commit on main for this branch |
| 95 | ceo/t-0061-m9-h-repair-install-and-version-claims-i | 8b09cbc | 0abe4b98c217 | identical subject and identical patch-id on main |
| 97 | architect/t-0004-contract-amendments | dc3d99a | 8810a8d1eaf1 | the one merge commit on main for this branch |
| 98 | securityauditor/t-0005-m9-p1-privacy-gate-the-env-secret-rule-r | 3ad898d | 26caa49ba868 | the one merge commit on main for this branch |
| 99 | developer-2/t-0014-m9-p2-tests-unit-test-skill-sync-py-puts | e2eaf30 | a05e000586d2 | the one merge commit on main for this branch |
| 100 | ceo/t-0059-m9-f-bump-main-to-1-1-3-and-record-the-n | 8b09cbc | 90c8204fe3e5 | the one merge commit on main for this branch |
| 102 | releaseengineer/t-0009-m9-p1-the-release-prose-must-state-what | 8b09cbc | 49d2174c7436 | the one merge commit on main for this branch |
| 103 | developer-1/t-0015-m9-k-unit-layer-records | e6d328c | c1187748a565 | the one merge commit on main for this branch |
| 104 | tester-1/t-0004-m9-k-integration-layer-records | e6d328c | c7d503e75e27 | the one merge commit on main for this branch |
| 105 | tester/t-0002-fix-the-hardcoded-posix-path-in-tests-un | 3aedfdf | f23711ebdc5c | the one merge commit on main for this branch |
| 106 | productmanager/t-0001-write-research-md-section-8-harness2-ver | d19d782 | a7c82cd2b976 | the one merge commit on main for this branch |
| 107 | tester/t-0003-make-the-traceability-record-resolution | ee05b65 | 926b5a2f6b39 | the one merge commit on main for this branch |
| 108 | ceo/t-0001-docs-reviewer-rubric-untrusted-material | 4722940 | 8a76f2748dbc | the one merge commit on main for this branch |
| 109 | developer/t-0002-engine-git-hooks-in-loop-enforcement-uni | 4722940 | 53a85d7cde32 | the one merge commit on main for this branch |
| 110 | ceo/t-0002-docs-pass-for-the-new-surface-cli-guide | 035bac1 | 2ef20eee17e0 | the one merge commit on main for this branch |
| 112 | developer/t-0001-engine-harness-list-harness-lint-harness | 035bac1 | c9e1b0ba96ef | the one merge commit on main for this branch |
| 113 | productmanager/t-0002-clarify-the-traceability-record-resoluti | 400162c | b8d3556edacc | the one merge commit on main for this branch |
| 114 | architect/t-0001-freeze-the-harness-surface-and-hooks-cli | 177bf36 | d6fc9e41a15f | the one merge commit on main for this branch |
| 115 | ceo/t-0005-records-truth-ac-5-must-not-claim-green | 177bf36 | 5d8149f51f37 | the one merge commit on main for this branch |
| 116 | developer/t-0004-design-declare-and-run-the-unit-layer-te | eb3cb6f | fda303443799 | the one merge commit on main for this branch |
| 117 | developer/t-0005-global-memory-entries-must-be-able-to-ca | eb3cb6f | e38aaefbd34e | the one merge commit on main for this branch |
| 118 | tester/t-0001-integration-acceptance-tests-for-the-har | 81bec67 | 7c5f8e801a09 | the one merge commit on main for this branch |
| 119 | developer/t-0007-fix-the-archive-mask-it-must-cover-every | 738d2bf | 1f0fcb95a048 | the one merge commit on main for this branch |
| 120 | developer/t-0006-the-privacy-gate-false-positives-on-a-re | 738d2bf | ac9753c2f0f9 | the one merge commit on main for this branch |
| 121 | ceo/t-0008-re-review-p-0010-after-the-archive-mask | 189f4ab | 4a4a8004dea7 | the one merge commit on main for this branch |
| 122 | ceo/t-0005-records-truth-ac-5-must-not-claim-green | 177bf36 | 5d8149f51f37 | the one merge commit on main for this branch |
| 123 | productmanager/t-0003-write-the-committed-record-of-the-privac | 40e6a07 | 217463097ad0 | the one merge commit on main for this branch |
| 124 | developer/t-0008-ledger-export-must-act-on-the-work-tree | 4a747fe | 7454ad34d30d | the one merge commit on main for this branch |
| 125 | ceo/t-0009-export-the-audit-manifest-for-the-m9-mil | 57553ff | 7697978ab08f | the one merge commit on main for this branch |
| 126 | productmanager/t-0004-refresh-the-board-and-plan-for-the-m9-mi | 57553ff | 7e5b81142639 | the one merge commit on main for this branch |
| 127 | productmanager/t-0005-record-the-decision-that-a-local-history | fd21ade | da7ef3855156 | the one merge commit on main for this branch |
| 128 | securityauditor/t-0002-re-state-the-audit-report-s-disclosure-c | fd21ade | f0864d72cb64 | the one merge commit on main for this branch |
| 129 | developer/t-0009-the-dispute-panel-is-computed-at-role-le | 83a899c | f17a01381ba3 | the one merge commit on main for this branch |
| 130 | reviewer-1/t-0002-carry-the-d-0003-tribunal-ruling-into-th | 407e2e4 | 27055780dc02 | the one merge commit on main for this branch |
| 131 | productmanager/t-0006-record-the-rule-that-no-commit-message-o | f9ef8d8 | f1eb7d5598dc | the one merge commit on main for this branch |
| 132 | productmanager/t-0007-refresh-the-plan-and-board-for-the-merge | 6b60d9b | a6bfdc869e3a | the one merge commit on main for this branch |
| 133 | ceo/t-0012-re-export-the-audit-manifest-at-the-fina | 397ec98 | 5fcbecf77e93 | the one merge commit on main for this branch |
| 134 | productmanager/t-0008-extract-the-records-flow-into-a-team-ski | ca9b4da | c81987863c56 | the one merge commit on main for this branch |
| 135 | developer-1/t-0016-r3-non-semver-published-version | e55465a | fd0e76f01021 | the one merge commit on main for this branch |
| 136 | developer-2/t-0017-stale-release-url-and-r6-blind-spot | e55465a | 59fe91430eb7 | the one merge commit on main for this branch |
| 137 | ceo/t-0067-audit-flags-every-review-passed-task-as | 1e266f0 | 0c95b60cad76 | the one merge commit on main for this branch |
| 138 | reviewer-1/t-0003-m9-k-acceptance-layer-records | 8564589 | 46bca8d1fcf9 | the one merge commit on main for this branch |
| 139 | ceo/t-0066-teamwork-py-links-measures-the-main-chec | 35825b4 | a1a1840d4ac2 | the one merge commit on main for this branch |
| 140 | tester-1/t-0005-m9-k-integration-layer-for-the-links-are | ad69ca2 | 8b8fceb5c15f | identical subject and identical patch-id on main |
| 141 | developer-1/t-0018-t-0015-s-release-traceability-unit-test | 6f2a96b | 1ceb6e9babe9 | the one merge commit on main for this branch |
| 142 | tester-1/t-0005-links-integration | 6f2a96b | ec7e26c1e93b | the one merge commit on main for this branch |
| 143 | reviewer-1/t-0004-m9-k-acceptance-layer-for-the-links-area | dae1ed6 | 5df185bc358c | the one merge commit on main for this branch |
| 144 | ceo/t-0070-audit-uses-project-of-root-for-its-link | dae1ed6 | b2e4ca99f2c4 | the one merge commit on main for this branch |
| 145 | releaseengineer/t-0010-the-first-push-of-the-unpublished-local | 6f6d6f9 | 5f47c010eca1 | the one merge commit on main for this branch |
| 146 | developer-2/t-0019-docs-guide-install-md-87-documents-a-tag | edf8dde | 66125dd882a2 | the one merge commit on main for this branch |
| 148 | projectmanager/t-0002-m9-i-record-m9-on-the-plan-and-board | b61bb44 | ca6306b18a21 | the one merge commit on main for this branch |
| 149 | ceo/t-0065-reconcile-published-line | 2abed8a | f9af43ea5df0 | the one merge commit on main for this branch |
| 152 | tester-1/t-0003-m9-j-acceptance-proof-that-the-release-c | 65d2299 | 65a289b8cb20 | the one merge commit on main for this branch |
| 153 | ceo/t-0071-the-board-vs-queue-comparison-is-a-test | 9eed244 | 873940ea5a82 | the one merge commit on main for this branch |
| 154 | developer-1/t-0021-identity-gate-accepts-role-mailboxes | d0bf375 | cb07850e7cb3 | the one merge commit on main for this branch |
| 155 | ceo/t-0072-lfs-audit-skips-text-files | d0bf375 | b701f0c52962 | the one merge commit on main for this branch |
| 164 | productmanager/t-0008-extract-the-records-flow-into-a-team-ski | ca9b4da | c81987863c56 | the one merge commit on main for this branch |
| 165 | developer/t-0010-the-unborn-head-test-assumes-the-runner | ee0c19b | 5e4c18b366c4 | identical subject and identical patch-id on main |
| 166 | developer/t-0010-the-unborn-head-test-assumes-the-runner | 4012750 | a2cb4f3061ca | identical subject and identical patch-id on main |
| 167 | ceo/t-0073-the-shared-skill-registry-row-the-harnes | 0372eab | 076d0701fb7f | the one merge commit on main for this branch |
| 169 | developer/t-0011-the-windows-child-environments-drop-the | bb715e9 | f18a2ea93d0c | the one merge commit on main for this branch |
| 170 | developer/t-0012-the-platform-variable-guard-looks-the-en | 88f637b | 2838a7e8f46c | the one merge commit on main for this branch |
| 171 | ceo/t-0014-re-export-the-audit-manifest-at-the-push | 02bbc5c | d1e4892c8c06 | the one merge commit on main for this branch |
| 172 | architect/t-0003-freeze-the-lfs-threshold-scope-it-applie | fd98054 | b8715a2d530a | the one merge commit on main for this branch |
| 174 | developer-1/t-0022-m10-d1-the-checkout-is-lf-on-every-platf | 5c9777b | f6499e759f63 | the one merge commit on main for this branch |
| 175 | developer-1/t-0023-m10-d2-the-make-help-target-list-must-su | 5c9777b | de5855e283cf | the one merge commit on main for this branch |
| 176 | developer-1/t-0024-m11-d3-the-release-consistency-fixture-a | 156f49b | f6e39899ab21 | the one merge commit on main for this branch |
| 177 | - | 156f49b | 0f4d639c96b9 | unique identical subject on main |
| 178 | - | 156f49b | 0f4d639c96b9 | unique identical subject on main |
| 179 | ceo/t-0074-docs-and-tree-hygiene-update-stale-readm | 405c352 | 44db2bcc41fb | the one merge commit on main for this branch |
| 180 | architect/t-0001-code-and-logic-review-of-src-teamwork-an | 9e0a6f8 | 5b2d70646433 | the one merge commit on main for this branch |
| 181 | developer-2/t-0003-make-every-test-that-needs-an-external-t | 9e0a6f8 | ce2a420d5959 | the one merge commit on main for this branch |
| 182 | releaseengineer/t-0001-workflow-and-release-gate-integrity-work | d8b8b52 | 84488937b6e0 | the one merge commit on main for this branch |
| 183 | developer-2/t-0007-engine-py-6812-swallows-a-privacy-scan-i | d8b8b52 | d0f359c5dcec | the one merge commit on main for this branch |
| 184 | technicalwriter/t-0001-docs-truth-pass-remove-every-stale-or-se | d8b8b52 | ef9f1399691c | the one merge commit on main for this branch |
| 185 | projectmanager/t-0001-tree-census-classify-every-tracked-file | d8b8b52 | 913e819c058a | the one merge commit on main for this branch |
| 186 | developer-1/t-0001-fix-resources-self-invocation-the-return | d8b8b52 | 55d5671a314b | the one merge commit on main for this branch |
| 187 | developer-1/t-0002-guard-every-symlink-dependent-test-so-th | 47433a3 | 5d223d848d0b | the one merge commit on main for this branch |
| 188 | ceo/t-0007-record-the-m11-solid-review-engagement-i | 47433a3 | f47b99199ee2 | the one merge commit on main for this branch |
| 189 | releaseengineer/t-0007-remove-the-stale-pre-nidvue-repository-h | 223cea9 | 370511cc5fd9 | the one merge commit on main for this branch |
| 190 | technicalwriter/t-0003-describe-the-refresh-destination-agent-a | 223cea9 | ad8961575bb1 | the one merge commit on main for this branch |
| 191 | developer-2/t-0012-board-render-recipe-crashes-with-keyerro | 9ce9c90 | d78290c2e6b3 | the one merge commit on main for this branch |
| 192 | tester-1/t-0001-certify-the-suite-locally-on-this-host-a | 9ce9c90 | 7cecc43433f4 | the one merge commit on main for this branch |
| 193 | securityauditor/t-0001-security-and-privacy-posture-audit-tree | 015be01 | f2e602c826c6 | the one merge commit on main for this branch |
| 194 | developer-2/t-0006-re-point-the-board-gate-at-the-live-mile | 3b3efa1 | a582049f9d9b | the one merge commit on main for this branch |
| 195 | productmanager/t-0001-rebuild-the-traceability-matrix-for-ac-1 | 3b3efa1 | 6e49e0914708 | the one merge commit on main for this branch |
| 196 | project-manager-2/t-0003-regenerate-docs-team-board-md-from-the-l | c6e70d0 | 423d2889c4cf | identical subject and identical patch-id on main |
| 197 | developer-2/t-0013-board-gate-a-landing-task-cannot-be-stab | 051f08a | 0734a9ab29eb | the one merge commit on main for this branch |
| 198 | securityauditor/t-0003-auditreport-md-23-restated-1-finding-whe | 051f08a | b65a71d3bf61 | the one merge commit on main for this branch |
| 199 | ceo/t-0001-own-m11-intake-criteria-goal-layer-tests | 50b5517 | de0f5741d653 | the one merge commit on main for this branch |
| 200 | developer-2/t-0014-ci-on-the-pushed-revision-ffad014c0ba83817e126b3a0627a791808558e82-is-red | 2bf5e57 | 74a59ce6aa9d | identical subject and identical patch-id on main |
| 201 | tester-1/t-0002-tests-integration-test-portability-flow | 8ad0fdb | 448283e79192 | the one merge commit on main for this branch |
| 202 | developer-2/t-0016-the-t-0014-regression-test-is-interprete | 2ad4b8a | ac58eb251ef7 | the one merge commit on main for this branch |
| 203 | technicalwriter/t-0004-align-the-role-charters-with-the-constit | ce4d4b6 | ab4fd8d5c435 | the one merge commit on main for this branch |
| 204 | developer-2/t-0017-engine-batch-unused-mypy-ignore-silent-l | ce4d4b6 | fcff13a43b47 | the one merge commit on main for this branch |
| 205 | architect/t-0002-align-the-frozen-ci-contract-and-the-ci | ce4d4b6 | af9f36629c3d | the one merge commit on main for this branch |
| 206 | releaseengineer/t-0009-ci-and-release-facts-pin-ruff-privacy-on | 14134a0 | 94c0282c1876 | the one merge commit on main for this branch |
| 208 | releaseengineer/t-0010-refresh-the-release-md-drift-record-afte | 9bf3f1d | cc24638f3363 | the one merge commit on main for this branch |
| 209 | securityauditor/t-0004-refresh-the-audit-report-s-branch-protec | 9bf3f1d | 12d456781386 | the one merge commit on main for this branch |
| 210 | ceo/t-0012-record-the-m12-intake-ac-22-ac-23-and-th | 4398755 | 1827384f86ad | the one merge commit on main for this branch |
| 211 | releaseengineer/t-0011-release-yml-uploads-sha256sums-twice-dis | d38a1f7 | 190bb5ee11f5 | the one merge commit on main for this branch |
| 212 | ceo/t-0013-add-the-ac-22-ac-23-rows-to-the-traceabi | e368866 | e3bdfa149031 | the one merge commit on main for this branch |
| 213 | releaseengineer/t-0013-publish-nidvue-teamwork-to-npm-from-ever | e368866 | fabf1ee756f1 | the one merge commit on main for this branch |
| 214 | releaseengineer/t-0014-pages-rebuilds-and-deploys-from-the-rele | b072971 | 1e6b1505ef89 | the one merge commit on main for this branch |
| 215 | technicalwriter/t-0005-site-and-readme-npm-as-a-first-class-ins | 21beeca | 58656118e363 | the one merge commit on main for this branch |
| 216 | reviewer-2/tribunal-d-0004 | 21beeca | 20672cde3d49 | the one merge commit on main for this branch |
| 217 | developer-1/t-0019-record-the-release-area-s-unit-layer-fro | 21beeca | 6cfeabe7f469 | identical subject and identical patch-id on main |
| 218 | tester-1/t-0003-record-the-release-area-s-integration-la | 21beeca | 6cfeabe7f469 | identical subject and identical patch-id on main |
| 219 | projectmanager/t-0005-release-blocker-docs-team-board-md-is-st | cb19d67 | 83bdf22b8dee | the one merge commit on main for this branch |
| 220 | releaseengineer/t-0016-release-yml-publish-step-uses-write-text | fb9b28b | b9a60eb97d44 | the one merge commit on main for this branch |
| 221 | developer-1/t-0020-matrix-guard-re-runs-the-full-history-pr | 5ee24ba | 940786bae4f6 | the one merge commit on main for this branch |
| 222 | projectmanager/t-0006-release-blocker-push-of-p-0040-p-0041-do | 9e91305 | 82b32a1a5e58 | the one merge commit on main for this branch |
| 223 | technicalwriter/t-0006-docs-releases-md-names-pypi-without-the | 6e48ff2 | e57cc63769e2 | the one merge commit on main for this branch |
| 224 | ceo/t-0014-v1-4-1-the-release-build-job-must-not-sh | 34613de | bbfe353a87ef | identical subject and identical patch-id on main |
| 225 | ceo/t-0014-v1-4-1-the-release-build-job-must-not-sh | 565b828 | e7cf1282d0a8 | identical subject and identical patch-id on main |
| 226 | developer/t-0017-chore-release-bump-to-1-4-3-so-r2-is-gre | 0039e57 | 572290dd85e0 | the one merge commit on main for this branch |
| 227 | developer-4/t-0020-fix-engine-pulse-capacity-ledger-head-ca | 59d0436 | 0bf62edb0a49 | the one merge commit on main for this branch |
| 228 | developer-8/t-0027-test-release-pin-r2-strictness-and-its-d | 59d0436 | 53cbc335d80f | the one merge commit on main for this branch |
| 229 | developer/t-0015-fix-ci-the-committer-guard-audits-the-pr | 59d0436 | bf41cda3c5ae | the one merge commit on main for this branch |
| 230 | developer-6/t-0024-fix-security-privacy-allowlist-truncatio | 59d0436 | 496b17c7198b | the one merge commit on main for this branch |
| 231 | developer-5/t-0021-fix-tooling-help-must-not-build-teamwork | 59d0436 | 91242842a942 | the one merge commit on main for this branch |
| 232 | developer-7/t-0026-fix-records-reject-a-self-unknown-duplic | 92fed19 | 6d91b81d3cae | the one merge commit on main for this branch |
| 233 | architect/t-0004-record-the-decision-on-r2-semantics-on-a | 833d6f7 | c5c52a05d17a | the one merge commit on main for this branch |
| 234 | developer-9/t-0028-feat-board-a-product-producer-and-checke | 833d6f7 | 2041ec717207 | the one merge commit on main for this branch |
| 235 | developer-10/t-0032-feat-release-implement-the-r2-scope-flag | 833d6f7 | 4926346b0b98 | the one merge commit on main for this branch |
| 236 | developer-2/t-0016-feat-review-measure-submitted-work-only | 833d6f7 | d08a5b5f3749 | the one merge commit on main for this branch |
| 237 | developer-15/t-0036-fix-release-the-publish-path-must-run-th | 833d6f7 | 3e343f8c358a | the one merge commit on main for this branch |
| 240 | developer-17/t-0040-fix-records-a-blank-handle-must-be-not-f | 3828c6e | 558343318159 | the one merge commit on main for this branch |
| 241 | developer-11/t-0018-fix-coordination-an-abandoned-pr-is-one | 3828c6e | 8a939f3daff6 | the one merge commit on main for this branch |
| 242 | developer-13/t-0034-fix-privacy-the-plan-row-path-is-a-false | 3828c6e | c33c0ed00a12 | the one merge commit on main for this branch |
| 243 | developer-16/t-0037-fix-hooks-install-per-stage-chain-a-fore | 3828c6e | 8bbfd78c5504 | the one merge commit on main for this branch |
| 244 | ceo/t-0015-record-m13-in-plan-project-and-regenerat | 5f94899 | 9279df2374b2 | the one merge commit on main for this branch |
| 245 | developer-14/t-0035-fix-security-a-commit-subject-must-not-e | 5f94899 | 32cc69a22ee6 | the one merge commit on main for this branch |
| 246 | ceo/t-0017-perf-review-verify-once-credit-the-rest | 5c84fc4 | 04cadab93cb8 | the one merge commit on main for this branch |
| 247 | ceo/t-0020-chore-records-re-render-board-md-after-t | 5c84fc4 | 1d5b7aeefef1 | the one merge commit on main for this branch |
| 248 | ceo/t-0022-chore-records-final-board-render-after-t | 5c84fc4 | a0db1ba82ebf | the one merge commit on main for this branch |
| 249 | ceo/t-0023-chore-records-export-the-closing-audit-m | 5c84fc4 | 38d4b6190dc8 | the one merge commit on main for this branch |
| 250 | ceo/t-0024-chore-records-final-board-render-at-clos | 5c84fc4 | 2cb2e16b6ae2 | the one merge commit on main for this branch |
| 251 | developer/t-0044-feat-deliver-one-pre-flight-gate-so-a-re | a564ea5 | 50dedaa565dd | the one merge commit on main for this branch |
| 252 | ceo/t-0021-org-efficiency-contract-one-parent-one-f | 57de5ce | 28d8a1bad40d | the one merge commit on main for this branch |
| 253 | ceo/t-0025-chore-records-board-render-after-the-clo | 57de5ce | 0a48a440171d | the one merge commit on main for this branch |
| 254 | ceo/t-0026-chore-records-closing-board-render | 57de5ce | d157f7d9b0ab | the one merge commit on main for this branch |
| 255 | developer/t-0043-fix-board-a-generated-board-must-not-rid | 8892480 | 40c135c14f95 | the one merge commit on main for this branch |
| 256 | architect/t-0005-design-the-feature-team-model-feature-re | 65d2f87 | 624220d18675 | the one merge commit on main for this branch |
| 257 | developer/t-0042-engine-feature-teams-per-instance-team-s | cd84c52 | 9e1f3264bbae | the one merge commit on main for this branch |
| 258 | ceo/t-0018-add-the-team-leader-charter-and-redraw-t | edbe085 | 432e76ed9dc0 | the one merge commit on main for this branch |
| 259 | designer/t-0001-graphics-sweep-validate-and-refresh-ever | d0f6271 | 8e0e95e904e6 | the one merge commit on main for this branch |
| 260 | developer-2/t-0002-windows-gate-build-pi-package-py-shells | 8190ec3 | 7c5b357f6a9e | the one merge commit on main for this branch |
| 261 | technicalwriter/t-0001-doc-truth-sweep-verify-every-public-clai | 8190ec3 | 7c03aeb852b2 | the one merge commit on main for this branch |
| 262 | designer/t-0002-design-md-geometry-cells-stopped-matchin | ed02d0b | 79d752bf1e03 | the one merge commit on main for this branch |
| 263 | ceo/t-0001-skill-md-files-squash-only-merges-under | b69256a | fb8299ff22fa | the one merge commit on main for this branch |
| 264 | ceo/t-0002-three-public-surfaces-still-claim-a-squa | 3e4170a | 1b00939ced20 | the one merge commit on main for this branch |
| 265 | developer-1/t-0001-hygiene-sweep-remove-dead-files-and-comm | e12deae | e45333242412 | the one merge commit on main for this branch |
| 266 | developer-2/t-0004-release-consistency-r8-reads-any-pip-ins | e12deae | f44d73fe1ccb | the one merge commit on main for this branch |
| 267 | developer-2/t-0005-clean-all-is-team-wide-it-wipes-every-ag | d244790 | 19912ae41393 | the one merge commit on main for this branch |
| 268 | developer-3/t-0003-windows-gate-test-preflight-py-and-the-t | b107a95 | b01e3ee981bb | the one merge commit on main for this branch |
| 269 | technicalwriter/t-0002-the-clean-command-contract-changed-agent | 8225a64 | 4c36ea30eb31 | the one merge commit on main for this branch |
| 270 | architect/t-0001-record-the-system-layer-the-merged-tree | 8225a64 | 17f407aadcfb | the one merge commit on main for this branch |
| 271 | tester/t-0001-certify-the-merged-windows-gate-and-veri | 54c635f | d99d530c8dec | unique identical subject on main |
| 272 | technicalwriter/t-0003-ac-1-blocker-citation-cff-17-states-agpl | 54c635f | 8324640a5eee | the one merge commit on main for this branch |
| 273 | designer/t-0003-banner-svg-s-three-ceo-connectors-sit-at | 54c635f | 218c0cc22d5c | the one merge commit on main for this branch |
| 274 | technicalwriter-2/t-0004-skill-md-and-references-roles-md-tier-co | b6848da | f41af4eeb032 | identical subject and identical patch-id on main |
| 275 | tester/t-0001-certify-the-merged-windows-gate-and-veri | 3f84e88 | f017357ecf1f | identical subject and identical patch-id on main |
| 276 | developer-3/t-0006-board-check-is-red-at-head-queue-role-de | 3f84e88 | 9de7f3275d62 | the one merge commit on main for this branch |
| 277 | developer-4/t-0007-board-write-cannot-bootstrap-a-fresh-pro | a43b84b | a992a1da8392 | the one merge commit on main for this branch |
| 278 | ceo/t-0004-close-m14-render-the-board-write-the-pla | f752f3d | 552e85db3641 | the one merge commit on main for this branch |
| 279 | designer/t-0005-r-19-the-og-card-s-pitch-punctuation-dif | a1318a7 | 78da3c30cc33 | the one merge commit on main for this branch |
| 280 | technicalwriter/t-0005-the-og-card-was-regenerated-73000-bytes | a1318a7 | 460bce85c17b | the one merge commit on main for this branch |
| 281 | ceo/t-0005-m15-a0-charter-the-dsh-superagent-adopti | 0437819 | 7f7488e89e63 | the one merge commit on main for this branch |
| 282 | developer-2/t-0008-r-17-gitattributes-marks-docs-assets-as | 0437819 | 8b63e4391bb4 | the one merge commit on main for this branch |
| 283 | designer/t-0004-r-18-the-readme-hero-and-demo-img-tags-c | c88bc7d | 85a0a13e6933 | the one merge commit on main for this branch |
| 284 | ceo/t-0007-m15-a9-render-plan-md-m15-lanes-dependen | a2fb6fa | c2621f50677e | the one merge commit on main for this branch |
| 285 | developer-2/t-0013-m15-a1-task-intake-is-idempotent-and-car | 7bcb380 | 0e7e89af3527 | the one merge commit on main for this branch |
| 287 | designer/t-0006-r-18-residual-the-six-readme-badges-stil | 7bcb380 | 4ae8ac7a5e44 | the one merge commit on main for this branch |
| 288 | developer/t-0011-r-22-a-relative-artifact-path-resolves-a | 7bcb380 | 2309d55d9552 | the one merge commit on main for this branch |
| 289 | developer-1/t-0016-m14-layers-three-missing-unit-records-re | 7bcb380 | 3e775e8c88b8 | the one merge commit on main for this branch |
| 291 | developer-7/t-0015-m15-a2-pulse-and-task-next-honour-an-acc | 1d0ac9c | 85a6df1da6c3 | the one merge commit on main for this branch |
| 292 | developer-5/t-0017-records-render-tests-records-crashes-on | 1d0ac9c | cf49e7903fde | the one merge commit on main for this branch |
| 293 | ceo/t-0010-decisions-acceptance-is-red-6-entries-ca | 5652336 | debed0091fa7 | the one merge commit on main for this branch |
| 294 | developer-4/t-0010-r-20-the-merge-path-s-records-commit-is | 1d0ac9c | 395cdca50e2e | the one merge commit on main for this branch |
| 295 | developer-3/t-0009-r-23-no-gate-compares-the-licence-copyri | 5652336 | 402a29e4a255 | the one merge commit on main for this branch |
| 296 | developer-3/t-0018-security-the-privacy-allowlist-needs-the | cdd8f8a | 785a24efd13c | the one merge commit on main for this branch |
| 297 | developer-2/t-0019-main-gate-is-red-three-pre-existing-suit | cdd8f8a | 5049f05f6aea | the one merge commit on main for this branch |
| 298 | ceo/t-0011-security-amendment-the-windows-home-path | ffa21d8 | 16a9bdfff2e6 | the one merge commit on main for this branch |
| 299 | developer-4/t-0014-m15-a3-attention-is-a-record-and-a-task | 4e1c741 | 84700dd178a8 | the one merge commit on main for this branch |
| 300 | developer-1/t-0023-m16-a1-a-review-finding-must-name-the-sp | 4e1c741 | ee85b4a7ac9d | the one merge commit on main for this branch |
| 301 | tester/t-0002-m14-layers-four-missing-integration-reco | 4e1c741 | 47acb80a6253 | the one merge commit on main for this branch |
| 302 | ceo/t-0015-release-records-land-d-20261102-ceo-and | 5d1d6f9 | ddbeb0051c98 | the one merge commit on main for this branch |
| 304 | ceo/t-0016-post-tag-bump-main-to-1-5-1-so-the-first | 140ec19 | 7c338f1cac3b | the one merge commit on main for this branch |
| 305 | technicalwriter-2/t-0009-the-1-5-0-changelog-section-is-mangled-b | d816456 | 2df90dc6b9f7 | identical subject and identical patch-id on main |
| 306 | technicalwriter-2/t-0010-citation-cff-date-released-is-2026-10-31 | ba188fa | 70009b4cddbc | identical subject and identical patch-id on main |
| 307 | ceo/t-0017-land-the-t-0006-pass-entry-the-no-branch | ba188fa | f29f71585b1c | the one merge commit on main for this branch |
| 309 | ceo/t-0018-render-the-board-after-the-last-queue-ch | ba188fa | 7c442fa106fd | the one merge commit on main for this branch |
| 310 | developer/t-0048-fix-ci-the-committer-guard-accepts-an-al | f67b7af | 72a3d768383c | the one merge commit on main for this branch |
| 311 | ceo/t-0027-release-v1-5-1-correct-the-1-5-1-notes-f | 51ae5e4 | c58817245cc7 | the one merge commit on main for this branch |
| 312 | developer/t-0049-fix-release-the-npm-verify-window-must-o | 7484a90 | b10045cdb04f | the one merge commit on main for this branch |
| 313 | developer/t-0050-fix-release-the-npm-verify-step-must-rea | 91d6e5f | c3b111deefd8 | the one merge commit on main for this branch |
| 314 | ceo/t-0028-chore-release-bump-to-1-5-2-on-main-afte | d072da6 | c3e069b40fd7 | the one merge commit on main for this branch |
| 315 | developer/t-0045-fix-docs-the-preflight-surface-still-quo | 50c94e5 | 4f5b2a3b92ce | the one merge commit on main for this branch |
| 316 | developer/t-0046-fix-records-a-review-fail-must-record-it | d11e49c | 27f6f34d93ff | the one merge commit on main for this branch |
| 317 | developer/t-0047-fix-records-a-bulk-sweep-must-not-be-abl | 61cb4b5 | e44b66693187 | the one merge commit on main for this branch |
| 320 | ceo/t-0029-adopt-the-grok-bot-team-guide-a-team-des | 8baab4a | e624b3d0778f | the one merge commit on main for this branch |
| 321 | developer/t-0051-fix-test-make-the-npm-verify-contract-te | 094117b | 2ff826d137b6 | the one merge commit on main for this branch |
| 322 | architect/t-0007-rule-on-the-c3-always-on-class-and-the-a | a397529 | 6784879326cc | the one merge commit on main for this branch |
| 323 | developer/t-0052-fix-review-budget-counts-only-what-every | dad573f | 9dd016541f3f | the one merge commit on main for this branch |
| 324 | tester/t-0005-make-the-team-state-lint-reproducible-in | db786b5 | dcd1896cda7c | the one merge commit on main for this branch |
| 325 | ceo/t-0031-archive-closed-reviewer-task-evidence-to | 7a50ea5 | 74b369724d83 | the one merge commit on main for this branch |
| 326 | securityauditor/t-0006-re-state-docs-team-auditreport-md-with-d | 7a50ea5 | 4969a43b0318 | the one merge commit on main for this branch |
| 327 | architect/t-0006-decide-the-evidence-archive-segmentation | b0f645d | 2f33ec213131 | the one merge commit on main for this branch |
| 328 | ceo/t-0030-decide-which-skill-md-sections-are-alway | 129360f | f6311392a730 | the one merge commit on main for this branch |
| 329 | developer/t-0053-fix-deliver-preflight-must-require-an-ev | 90a58d7 | 1ed91b29522c | the one merge commit on main for this branch |
| 330 | ceo/t-0032-docs-guide-the-harness-budget-row-still | 90a58d7 | 6c86f973337f | the one merge commit on main for this branch |
| 331 | tester/t-0006-pin-document-structure-rather-than-sente | 2b74205 | 931d591e6408 | the one merge commit on main for this branch |
| 332 | tester/t-0007-integration-layer-for-t-0042-drive-the-f | 3b09e31 | e9ce9e395e2d | the one merge commit on main for this branch |
| 333 | ceo/t-0019-plan-and-board-for-feature-teams-one-sha | 7125ccd | ee41dd024ce5 | the one merge commit on main for this branch |
| 334 | architect/t-0004-m17-a1-freeze-the-lessons-tw-prefix-cont | 9db04da | a37fd69f13ca | the one merge commit on main for this branch |
| 335 | architect/t-0005-m17-a6-freeze-the-project-knowledge-stor | 15a6bbe | 38ad7156de64 | the one merge commit on main for this branch |
| 336 | developer-8/t-0031-m17-a2-implement-lessons-prefixed-team-s | 15a6bbe | ec24279a76ec | the one merge commit on main for this branch |
| 337 | architect/t-0006-m17-a10-freeze-the-openviking-style-cont | 12d706c | 441adf52d2d3 | the one merge commit on main for this branch |
| 338 | tester-2/t-0004-m17-a4-integration-acceptance-proof-of-l | 413a7f4 | 5a24ecb318e4 | the one merge commit on main for this branch |
| 339 | developer-9/t-0032-m17-a7-implement-the-project-knowledge-s | da4d5b1 | b6868497f4df | the one merge commit on main for this branch |
| 340 | developer-10/t-0034-m18-a1-token-aware-budget-archive-task-s | 0a00357 | 1ac912e8ddbd | the one merge commit on main for this branch |
| 341 | tester-3/t-0006-m18-a3-integration-acceptance-proof-of-t | e6b3c6d | 166fc210a9ca | the one merge commit on main for this branch |
| 342 | developer-8/t-0033-m17-a11-implement-the-context-tree-ctx-n | 979aaf8 | 3eb318a25f60 | the one merge commit on main for this branch |
| 343 | technicalwriter/t-0011-m17-a3-document-lessons-the-tw-skill-pre | 5a35872 | 9fc4142a607f | the one merge commit on main for this branch |
| 344 | technicalwriter/t-0013-m18-a2-document-the-throughput-contract | 5fc8ee5 | f60ff8d048ba | the one merge commit on main for this branch |
| 345 | ceo/t-0019-m17-a5-intake-criteria-records-migration | 8a8c7cb | e26ce01fc0dd | the one merge commit on main for this branch |
| 346 | ceo/t-0021-m18-a4-fix-the-privacy-history-gate-and | ae0683d | 61ca0f1adac4 | the one merge commit on main for this branch |
| 347 | tester-2/t-0005-m17-a9-integration-acceptance-proof-of-t | fdfff85 | 62c2d51503dd | the one merge commit on main for this branch |
| 348 | ceo/t-0022-integrate-origin-main-into-main-reconcil | fdfff85 | 3314a729da6e | the one merge commit on main for this branch |
| 349 | tester-2/t-0007-m18-a5-make-the-context-cli-level-assert | cdbd248 | dbe190abb331 | the one merge commit on main for this branch |
| 350 | developer-4/t-0038-m20-d1-the-identity-audit-must-accept-on | e269fa7 | 98787dee53c2 | the one merge commit on main for this branch |
| 351 | ceo/t-0024-m20-e1-resolve-dependabot-pr-31-bump-act | befe453 | ae82da792b49 | the one merge commit on main for this branch |
| 352 | technicalwriter-3/t-0015-m20-f1-research-agent-autoloop-what-team | b965cf8 | 7759a7c80d75 | identical subject and identical patch-id on main |
| 353 | developer-8/t-0039-m18-a6-make-the-lesson-knowledge-concurr | b965cf8 | f4a89769aa92 | the one merge commit on main for this branch |
| 354 | ceo/t-0025-m20-g1-release-md-still-pins-setup-pytho | 60ad60e | 4617a2291e81 | the one merge commit on main for this branch |
| 355 | ceo/t-0026-m20-h1-release-md-names-v7-1-0-which-r9 | cc5834b | 67eba0f85faa | the one merge commit on main for this branch |
| 356 | developer-3/t-0037-m20-c1-no-comments-in-code-enforced-by-t | 449268c | 140caf59592f | the one merge commit on main for this branch |
| 357 | developer-4/t-0042-m20-c2-make-lint-fails-in-a-scratch-tree | d1572b8 | 06cfd76f2e27 | the one merge commit on main for this branch |
| 358 | developer-4/t-0043-m20-c3-make-lint-is-invisible-to-the-ci | 68f39b2 | 556fa941812b | the one merge commit on main for this branch |
| 361 | ceo/t-0001-record-the-ci-failure-classes-and-green | 81e3d2e | d6aa8fed2d70 | the one merge commit on main for this branch |
| 362 | ceo/t-0002-close-merged-and-stale-local-and-remote | 721b18f | 6d2840ae2351 | the one merge commit on main for this branch |
| 363 | developer/t-0003-close-codeql-alert-4-py-incomplete-url-s | 721b18f | 37e4952541df | the one merge commit on main for this branch |
| 365 | ceo/t-0004-publish-the-closing-audit-manifest | 721b18f | b433ccb7fb57 | the one merge commit on main for this branch |
| 366 | ceo/t-0005-implement-the-self-evolution-framework-e | ca30484 | a87bfc571c23 | the one merge commit on main for this branch |
| 367 | developer-3/t-0008-restructure-readme-into-a-slim-front-doo | 989a4e5 | 56a9be3a65b2 | the one merge commit on main for this branch |
| 368 | developer/t-0002-make-the-ci-matrix-green-proof-budget-90 | 989a4e5 | a6ebf0dedcfa | the one merge commit on main for this branch |
| 369 | developer-2/t-0007-code-enforce-the-self-evolution-framewor | a44980d | b7b4df090982 | the one merge commit on main for this branch |
| 370 | developer/t-0010-restore-the-provider-cap-statement-the-r | e32ef5d | c92796794a16 | the one merge commit on main for this branch |
| 371 | ceo/t-0006-wire-evolution-md-and-tw-self-evolve-to | e32ef5d | 3224090e1307 | the one merge commit on main for this branch |
| 372 | developer-3/t-0009-drop-eol-python-3-9-3-10-and-cut-the-ci | cbb5cf0 | 96a9a9636229 | the one merge commit on main for this branch |
| 373 | developer-3/t-0014-fix-the-readme-install-acceptance-after | 70404b8 | 226b56d0c7ea | the one merge commit on main for this branch |
| 374 | developer/t-0012-make-ci-reproducible-and-bounded-one-loc | 5bff68e | 1f9060259778 | the one merge commit on main for this branch |
| 375 | ceo/t-0007-add-the-team-leader-and-the-feature-team | 6d8ade0 | 90693d1f6c32 | the one merge commit on main for this branch |
| 376 | developer-2/t-0016-trim-the-always-on-surface-under-the-122 | 106949e | 5011105ca5a8 | the one merge commit on main for this branch |
| 377 | developer-4/t-0018-restore-the-makefile-lint-contract-after | 761d2d1 | adebf4b02b33 | the one merge commit on main for this branch |
| 378 | architect/t-0001-update-architecture-13-2-and-freeze-f-00 | 761d2d1 | 618d4b5e317f | the one merge commit on main for this branch |
| 379 | developer-2/t-0019-restore-the-provider-cap-statement-in-sk | 1d03469 | d5702cd4580e | the one merge commit on main for this branch |
| 380 | developer-3/t-0013-prose-contract-tests-must-discover-pages | 1d03469 | f2f549c76e99 | the one merge commit on main for this branch |
| 381 | developer/t-0006-fix-the-branchless-archive-render-the-en | 1d03469 | a31b2aab3699 | the one merge commit on main for this branch |
| 382 | developer/t-0015-make-the-feature-team-hierarchy-visible | 8ccc9d6 | 1579bb098572 | the one merge commit on main for this branch |
| 383 | developer-2/t-0006-io-lock-stale-steal-is-check-then-unlink | b682c87 | fb8c46d63a24 | the one merge commit on main for this branch |
| 385 | ceo/t-0003-cut-the-always-on-startup-cost-rewrite-t | b682c87 | ddac3e713011 | the one merge commit on main for this branch |
| 386 | developer/t-0003-cmd-load-s-unknown-role-guard-is-dead-co | b682c87 | cc4f359c26e3 | the one merge commit on main for this branch |
| 387 | developer-3/t-0007-credential-masking-runs-only-in-archive | dfa1489 | 461a26d2fe8f | the one merge commit on main for this branch |
| 388 | developer/t-0002-test-probe-passes-records-is-not-hermeti | dfa1489 | dcce77f98356 | the one merge commit on main for this branch |
| 389 | developer-2/t-0030-privacy-scan-flags-reserved-example-doma | dfa1489 | 9a55db31f7b0 | the one merge commit on main for this branch |
| 390 | ceo/t-0010-the-always-on-cut-merged-b5a2b033862927835ca03a2ee183e0b82da961a0-renamed | 907caf0 | f792309049c6 | identical subject and identical patch-id on main |
| 391 | developer/t-0009-gitutil-run-git-has-no-timeout-refresh-f | 907caf0 | ecca53609173 | the one merge commit on main for this branch |
| 392 | ceo/t-0016-m20-records-intake-and-criteria-memory-m | 11470b8 | 0d8ac9e2d153 | the one merge commit on main for this branch |
| 393 | developer/t-0036-implement-the-agent-memory-lifecycle-mem | 5442f68 | 98b8f3596947 | the one merge commit on main for this branch |
| 394 | developer/t-0039-main-500092983b6a0b87b12355b0e3fc14da6250e080-is-red-docs-team-architectu | 1499e2d | b5408465c6f8 | identical subject and identical patch-id on main |
| 395 | developer/t-0038-land-the-engine-owned-lane-runtime-src-t | a986200 | f59a641432e7 | the one merge commit on main for this branch |
| 396 | developer/t-0040-every-spawned-lane-starts-from-task-awar | 319e6ff | 5843c74bb462 | the one merge commit on main for this branch |
| 397 | developer/t-0041-the-lane-prompt-injects-the-memory-pack | 1b299dc | 7dd0c817560f | the one merge commit on main for this branch |
| 399 | ceo/t-0017-m21-records-parallel-asynchronous-lanes | 2c37ca2 | 35155e30aacb | the one merge commit on main for this branch |
| 400 | developer/t-0042-a-lane-cannot-land-its-own-work-unattend | 9803c1a | e43405a71113 | the one merge commit on main for this branch |
| 401 | developer/t-0043-the-memory-loop-is-still-open-on-the-rea | 222d3ef | 481db482597f | the one merge commit on main for this branch |
| 402 | ceo/t-0018-m21-close-out-record-the-memory-loop-clo | c770fe5 | ba2430916e14 | the one merge commit on main for this branch |
| 403 | teamleader/t-0001-finish-feature-f-0001-prove-docs-only-pu | 1141533 | 231a7e58d71f | the one merge commit on main for this branch |
| 404 | ceo/t-0019-close-out-records-for-the-parallel-lane | e3dfc71 | 68196c6b7041 | the one merge commit on main for this branch |
| 405 | developer-2/t-0023-privacy-scanner-misses-name-base64-slack | e3dfc71 | 734c76171923 | the one merge commit on main for this branch |
| 406 | developer-2/t-0029-branch-start-worktree-returns-worktrees | e3dfc71 | 5227d655c490 | the one merge commit on main for this branch |
| 407 | developer/t-0005-preflightcommand-is-shlex-split-and-exec | e3dfc71 | d55d3b087951 | the one merge commit on main for this branch |
| 408 | developer-3/t-0014-audit-s-truncation-check-silently-skips | e3dfc71 | 7ad716a5ec74 | the one merge commit on main for this branch |
| 409 | developer-3/t-0035-the-reviewer-merge-dies-on-its-own-recor | e3dfc71 | f6524a0cfacb | the one merge commit on main for this branch |
| 410 | developer-3/t-0037-branch-start-worktree-decides-worktree-e | e3dfc71 | 27161c394891 | the one merge commit on main for this branch |
| 411 | developer-3/t-0004-harness-instance-always-on-documents-its | e3dfc71 | f0b4d0dd77ed | the one merge commit on main for this branch |
| 412 | developer-3/t-0010-clean-reports-files-as-removed-when-unli | e3dfc71 | eaa4d4be8854 | the one merge commit on main for this branch |
| 413 | developer-3/t-0011-a-bad-teamwork-integer-kills-every-comma | e3dfc71 | 2aa1f7b8cb14 | the one merge commit on main for this branch |
| 414 | developer-3/t-0013-ledger-actions-is-dead-code-and-wrong-31 | e3dfc71 | 1136bf0548c9 | the one merge commit on main for this branch |
| 415 | developer/t-0008-identity-audit-reports-a-personal-identi | e3dfc71 | 7cc2f8d46a90 | the one merge commit on main for this branch |
| 416 | tester/t-0001-systematic-audit-of-tests-vacuous-or-tau | e3dfc71 | fe95838880c4 | the one merge commit on main for this branch |
| 417 | architect/t-0002-ratify-the-architecture-md-census-pointe | e3dfc71 | 39864c77594c | the one merge commit on main for this branch |
| 418 | tester/t-0002-m20-integration-layer-pack-search-dream | e3dfc71 | 1be0eb466a10 | the one merge commit on main for this branch |
| 419 | developer-3/t-0032-amending-a-branch-after-selfcheck-perman | e3dfc71 | 46218dab5b63 | the one merge commit on main for this branch |
| 420 | developer-3/t-0018-mypy-exempts-engine-py-71-of-the-runtime | e3dfc71 | bc54cef952d0 | the one merge commit on main for this branch |
| 421 | developer/t-0046-main-is-red-on-mypy-engine-py-clean-s-re | e4270c5 | de3bd12a2422 | the one merge commit on main for this branch |
| 422 | developer-2/t-0028-ledger-record-106-was-hashed-against-an | 1141533 | c00cb8297e3b | the one merge commit on main for this branch |
| 423 | ceo/t-0013-commit-the-m19-decision-records-d-202611 | 44cb131 | 16fae7c2a704 | the one merge commit on main for this branch |
| 424 | developer/t-0047-burn-down-the-remaining-m19-audit-findin | 2db3d3a | ec2cf4df563b | the one merge commit on main for this branch |
| 425 | developer/t-0048-burn-down-2-the-task-parser-s-allow-list | 811f0a7 | df02e58b1f14 | the one merge commit on main for this branch |
| 426 | developer/t-0049-burn-down-3-remember-refuses-an-unknown | 3f8edc7 | 0678de19aa68 | the one merge commit on main for this branch |
| 427 | developer/t-0050-t-0049-added-a-second-role-guard-in-cmd | 5c53e78 | 266a0adce483 | the one merge commit on main for this branch |
| 428 | developer/t-0051-a-lane-s-rebase-silently-deleted-the-lan | 4c276cd | 07b33c39a676 | the one merge commit on main for this branch |
| 429 | developer/t-0052-burn-down-4-ledger-repair-drops-only-a-t | 290e699 | 65aa8c217be7 | the one merge commit on main for this branch |
| 430 | developer/t-0053-t-0052-s-preflight-verdict-broke-five-sh | a11375f | 3660ad18f5ba | the one merge commit on main for this branch |
| 431 | developer/t-0054-finish-the-regression-sweep-the-harness | c71eea1 | e82e85a8780d | the one merge commit on main for this branch |
| 432 | ceo/t-0020-record-the-two-tribunal-rulings-d-0001-t | 5c98ff3 | c5f3ab86fc3a | the one merge commit on main for this branch |
| 433 | ceo/t-0021-close-out-the-manifest-re-export-after-t | 371241d | 1e632fc36fc5 | the one merge commit on main for this branch |
| 434 | ceo/t-0022-commit-the-final-ledger-export-so-the-tr | 371241d | 7c6fb77a0080 | the one merge commit on main for this branch |
| 436 | developer/t-0055-the-new-pre-commit-privacy-gate-refused | f0d5a07 | c35b2f8c7738 | the one merge commit on main for this branch |
| 437 | developer/t-0056-task-set-cannot-repair-a-review-verdict | ff8b0cb | a04179285d5b | the one merge commit on main for this branch |
| 438 | developer/t-0057-task-set-cannot-clear-a-retired-branch-s | c7790b6 | e50d9a38ead4 | the one merge commit on main for this branch |
| 439 | developer/t-0058-the-two-bounded-privacy-patterns-carry-e | 3cf6cf0 | 96429cd51cee | the one merge commit on main for this branch |
| 440 | developer/t-0059-ci-is-red-on-the-lane-tests-lane-start-p | f6287df | b1abd506f84d | the one merge commit on main for this branch |
| 441 | reviewer-1/t-0004-acceptance-probes-for-the-eight-areas-th | 382512e | 9ef94b3d4dc6 | the one merge commit on main for this branch |
| 442 | developer/t-0060-the-ledger-s-only-non-destructive-repair | 1535381 | 452f8a304797 | the one merge commit on main for this branch |
| 443 | ceo/t-0023-record-the-ledger-cut-ruling-d-20261109 | d79266e | 0b007e66aa8d | the one merge commit on main for this branch |
| 444 | developer/t-0061-the-windows-test-job-hits-its-60-minute | 3b3ff4a | 3c62ff3e2bf4 | the one merge commit on main for this branch |
| 445 | developer/t-0062-the-parallel-lanes-have-no-live-picture | a18e388 | 69f63c113d88 | the one merge commit on main for this branch |
| 446 | tester/t-0004-live-proof-of-the-lane-display-start-a-r | e7dbadd | 7511f2ffee6f | the one merge commit on main for this branch |
| 447 | ceo/t-0026-make-lint-is-red-on-main-identity-audit | f89dcbf | e6f1ce3cbdb5 | the one merge commit on main for this branch |
| 448 | ceo/t-0027-swarm-is-the-default-operating-mode-puls | 99e4b80 | 8f2677e5a210 | the one merge commit on main for this branch |
| 449 | ceo/t-0029-ac-5-s-forward-map-row-claims-green-whil | 3ce0b84 | b6fa980d7f44 | the one merge commit on main for this branch |
| 450 | ceo/t-0024-review-the-tree-and-fix-the-audit-defect | 63b1494 | 7484b81489e0 | the one merge commit on main for this branch |
| 451 | ceo/t-0025-intake-brief-deep-research-the-prompt-th | 0135009 | 1fbf07ae1f89 | the one merge commit on main for this branch |
| 452 | ceo/t-0030-the-lane-display-is-shipped-but-never-lo | d3b9268 | 4f9731625ba9 | the one merge commit on main for this branch |
| 453 | ceo/t-0031-four-required-test-layers-have-no-probe | 8968aae | 2f475ad1c1c3 | the one merge commit on main for this branch |
| 455 | ceo/t-0032-record-the-windows-ci-limitation-as-a-ri | 7cb8164 | eda01b4a7184 | the one merge commit on main for this branch |
| 456 | ceo/t-0033-the-documented-roster-tier-startup-costs | 0d52f59 | 40d61ad4becf | the one merge commit on main for this branch |
| 457 | ceo/t-0034-close-out-records-export-the-audit-manif | 90049e4 | 2dfd58600394 | the one merge commit on main for this branch |
| 458 | developer/t-0061-the-windows-test-job-hits-its-60-minute | 499897c | 3c62ff3e2bf4 | the one merge commit on main for this branch |
| 459 | productmanager/t-0010-research-record-re-verify-the-article-cl | 43a9f6c | 32cdf3db0008 | unique identical subject on main |
| 460 | ceo/t-0033-m22-intake-the-frozen-memory-contract-cr | aaee030 | e56cb8d0b777 | unique identical subject on main |
| 461 | securityauditor/t-0007-privacy-and-secret-audit-of-the-memory-s | f49587d | 279c8b1b55cf | unique identical subject on main |
| 462 | developer/t-0054-memory-verify-re-resolve-record-evidence | f49587d | 279c8b1b55cf | unique identical subject on main |
| 463 | tester/t-0008-integration-layer-verify-focus-transcrip | d2f7e7e | 32d5cbf62a71 | unique identical subject on main |
| 464 | developer/t-0055-memory-verify-focus-rank-by-the-4-1-scor | d2f7e7e | 32d5cbf62a71 | unique identical subject on main |
| 465 | ceo/t-0035-declare-pi-subagents-as-an-optional-peer | 323975a | 19172feb9c5f | unique identical subject on main |
| 466 | developer/t-0056-transcript-reach-context-find-and-recall | 6415d51 | 36b6a74e0d47 | unique identical subject on main |
| 467 | developer/t-0057-memory-index-header-in-load-and-the-lane | 8e8b0b4 | 8fec4c3a480e | unique identical subject on main |
| 468 | ceo/t-0034-m22-close-out-the-measured-before-after | 43701b5 | 816958319ac2 | unique identical subject on main |
| 471 | ceo/t-0036-drop-the-last-host-plugin-dependencies-e | 9263126 | 97ca749e6b74 | unique identical subject on main |
| 472 | ceo/t-0038-remove-every-remaining-pi-subagents-refe | 9360c30 | fdd3c09d8e4b | unique identical subject on main |
| 473 | developer/t-0060-scrub-absolute-host-paths-from-the-role | 86af9a6 | f7e362d78d33 | unique identical subject on main |
| 474 | developer-2/t-0062-memory-verify-checks-only-the-first-evid | edafd8d | 3a12d0bf955c | unique identical subject on main |
| 475 | developer-1/t-0069-teamwork-py-status-compact-live-state-of | 7d2ce26 | 12e8c44f01e0 | unique identical subject on main |
| 476 | developer-2/t-0065-load-prints-the-packet-then-exits-1-on-a | 7d2ce26 | 12e8c44f01e0 | unique identical subject on main |
| 477 | developer-2/t-0066-a-purpose-built-zero-open-lesson-fixture | 781215a | 833788c96694 | unique identical subject on main |
| 478 | developer-2/t-0071-status-name-the-work-task-title-add-sche | 781215a | 833788c96694 | unique identical subject on main |
| 479 | developer-2/t-0063-tests-unit-test-memory-index-py-fails-wh | 770320f | 23ef54539d0e | unique identical subject on main |
| 480 | developer-2/t-0070-pi-extension-teamwork-status-live-agent | 770320f | 23ef54539d0e | unique identical subject on main |
| 481 | developer-1/t-0059-privacy-scan-does-not-cover-the-team-mem | a59897f | 38b8d9db882c | unique identical subject on main |
| 482 | developer/t-0061-archive-render-writes-bare-urls-so-links | a528507 | 1effc3a20132 | unique identical subject on main |
| 483 | developer/t-0058-preflight-gate-runs-in-the-main-checkout | a528507 | 1effc3a20132 | unique identical subject on main |
| 484 | tester/t-0010-integration-layer-status-contract-and-pa | a59897f | 38b8d9db882c | unique identical subject on main |
| 485 | ceo/t-0037-prove-the-plugin-free-native-fan-out-a-r | af5b7f7 | e52ed25f6bf3 | unique identical subject on main |
| 486 | securityauditor/t-0008-redact-personal-data-from-team-state-and | 65dcb26 | be6fbd4801f7 | unique identical subject on main |
| 487 | developer/t-0067-every-instance-works-in-its-own-worktree | e6c3e39 | 10a735b87744 | identical subject and identical patch-id on main |
| 488 | ceo/t-0039-ac-m22-5-describe-the-merged-memory-beha | e6c3e39 | 10a735b87744 | identical subject and identical patch-id on main |
| 489 | reviewer-1/t-0006-record-the-acceptance-layer-for-memory-a | 51fe38f | d920d6918b93 | unique identical subject on main |
| 490 | developer-1/t-0074-main-s-full-suite-is-red | 51fe38f | d920d6918b93 | unique identical subject on main |
| 491 | dev-10/t-0076-preflight-the-branch-staleness-check-and | 5e0d921 | 37943b05c768 | identical subject and identical patch-id on main |
| 492 | dev-1/t-0075-dispute-resolve-refuses-the-ceo-the-pane | 8e5d913 | 671d73afdc31 | unique identical subject on main |
| 493 | developer-1/t-0077-the-last-two-red-unit-tests | 75f7859 | 8859c8cae453 | unique identical subject on main |
| 494 | ceo/t-0078-ac-5-row-tells-the-truth-about-history | 8839d70 | 7829d89d0fd9 | unique identical subject on main |
| 495 | developer-1/t-0078-agents-can-message-each-other | 94ec52c | c60f83a019e1 | unique identical subject on main |
| 496 | developer-1/t-0079-paused-fields-and-tier-table | c526299 | bfc2c0939110 | unique identical subject on main |
| 497 | developer-1/t-0080-preset-identity | 5a15f52 | 1cbf2e7a329a | unique identical subject on main |
| 498 | developer-1/t-0081-archive-remap | 607cfb9 | d997ea266169 | unique identical subject on main |
| 499 | developer-1/t-0082-ci-identity | 2160d64 | c82bdf789c22 | unique identical subject on main |
| 500 | developer-1/t-0083-operator-identity-order | a5b1425 | 5a7ae512e71e | unique identical subject on main |
| 501 | developer-1/t-0084-team-mailbox-is-not-a-preset | 8aa693c | 098f9ca54032 | unique identical subject on main |
| 502 | developer-1/t-0085-ac5-row-proof | f801345 | 57c4560fe6e0 | unique identical subject on main |
| 503 | developer-1/t-0086-ac5-green | f0f223d | 14e44a521ec2 | unique identical subject on main |
| 504 | developer-1/t-0087-published-exemptions | f2d62e5 | f4fb16b3baed | unique identical subject on main |
| 505 | developer-1/t-0088-transcript-bound | 17fb61b | 05e2ee1a1d84 | unique identical subject on main |
| 506 | developer-1/t-0090-guard-dedup | 6fcfa75 | 0fbcf6afbab8 | the one merge commit on main for this branch |
| 507 | developer-1/t-0090-drop-opt-out | de51393 | ba25f1a37569 | the one merge commit on main for this branch |
| 508 | developer-1/t-0092-privacy-budget | a687ba6 | a2e8de21d42c | the one merge commit on main for this branch |
| 509 | developer-1/t-0093-windows-shards | 238ec7e | 6a03feea34be | the one merge commit on main for this branch |
| 510 | developer-1/t-0094-windows-render-env | 914e4f5 | 9646f1b76510 | the one merge commit on main for this branch |
| 511 | developer-1/t-0094-the-windows-shards-exposed-four-windows | 3967ce6 | 93117787dc09 | the one merge commit on main for this branch |
| 512 | developer-2/t-0096-the-suite-is-not-hermetic-against-teamwo | 865e0d1 | 4c88c2e3a676 | the one merge commit on main for this branch |
| 513 | developer-1/t-0097-m23-a-capture-the-short-layer-at-lane-ex | 167bb12 | 675375dd1ff2 | the one merge commit on main for this branch |
| 514 | architect/t-0008-freeze-the-m23-memory-contracts-short-la | 6d9f6bb | a35375db3aea | the one merge commit on main for this branch |
| 515 | dev-1/t-0103-the-windows-a-f-shard-is-cancelled-at-th | 819e58f | f9c0fca38e00 | the one merge commit on main for this branch |
| 516 | developer-2/t-0098-m23-b-promote-by-use-run-the-dream-pass | 88c26c5 | a31bd0a2ee92 | the one merge commit on main for this branch |
| 517 | developer-1/t-0104-the-privacy-history-scan-takes-15-19-min | 1d7750c | a29a298727f5 | the one merge commit on main for this branch |
| 518 | developer-2/t-0106-the-short-layer-injection-broke-two-inte | 65bf300 | 87ff9e59e511 | the one merge commit on main for this branch |
| 519 | dev-1/t-0105-the-ci-matrix-runs-the-whole-suite-five | 52dda8a | cf9fc5466b52 | the one merge commit on main for this branch |
| 520 | developer-2/t-0109-m23-d-recall-and-memory-search-do-not-re | fd64c13 | 378c40cd55de | the one merge commit on main for this branch |
| 521 | developer-1/t-0114-tests-unit-test-gitignore-bootstrap-py-h | a2c2810 | f89b61e1a241 | the one merge commit on main for this branch |
| 522 | developer-2/t-0115-commit-identity-and-message-style-must-s | 1a5495d | 758082df486b | the one merge commit on main for this branch |
| 523 | developer-1/t-0116-the-privacy-scan-flags-a-revision-path-p | 7dba319 | 1159000d47b5 | the one merge commit on main for this branch |
| 524 | developer-2/t-0117-the-identity-audit-still-demands-an-acti | afa08b4 | 66cd29905a8a | the one merge commit on main for this branch |
| 525 | developer-1/t-0118-two-tests-still-pin-the-pre-rewrite-iden | 10df6b2 | aa36064fe50d | the one merge commit on main for this branch |
| 526 | developer-2/t-0119-the-lane-proof-concurrency-test-samples | 6ac7fbb | 71ecacbc82f3 | the one merge commit on main for this branch |
| 527 | developer-1/t-0120-two-more-windows-only-failures-the-shard | 61be1c2 | 5e8a9a364b5c | the one merge commit on main for this branch |
| 528 | developer-2/t-0112-remember-accepts-a-write-with-no-by-so-t | 19596a2 | d23cb75e148b | the one merge commit on main for this branch |
| 529 | dev-1/t-0121-the-windows-integration-m-z-and-unit-p-z | 55c2af3 | 940cbe1b79ce | the one merge commit on main for this branch |
| 530 | developer-3/t-0107-close-the-census-guard-class-by-inversio | bf3b953 | 2ccc9619dd9a | the one merge commit on main for this branch |
| 531 | developer-1/t-0122-ledger-append-has-no-cross-process-seria | da927df | 9bcc36405212 | the one merge commit on main for this branch |
| 532 | developer-2/t-0100-refresh-stops-on-an-unrelated-mirror-his | f4a38ee | a6f35b8b1cd1 | the one merge commit on main for this branch |
| 533 | tester/t-0012-record-the-layer-matrix-for-the-twelve-a | 1ef5616 | 13711e4e7f8d | the one merge commit on main for this branch |
| 534 | developer-2/t-0110-pr-merge-pins-identity-with-c-only-so-an | 14682f2 | e47646de6996 | the one merge commit on main for this branch |
| 535 | tester/t-0013-record-the-remaining-integration-and-acc | c4d7eff | bab2f75b04ae | the one merge commit on main for this branch |
| 536 | developer-1/t-0123-record-the-developer-unit-layers-for-the | eae73da | df7d22af5bcf | the one merge commit on main for this branch |
| 537 | tester/t-0014-record-portability-acceptance-windows-po | a4afb84 | 03ecb12a58ef | the one merge commit on main for this branch |
| 538 | dev-1/t-0124-integration-git-heavy-is-11m48s-the-last | 56e288c | 15a3184bdf0e | the one merge commit on main for this branch |
| 539 | developer-2/t-0125-record-the-merge-identity-unit-layer | 5b1c298 | 73f2e48becd8 | the one merge commit on main for this branch |
| 540 | developer-1/t-0126-three-layer-records-use-unit-as-their-ar | ae669e5 | f27f7ee3dbf3 | the one merge commit on main for this branch |
| 541 | developer-3/t-0129-two-unit-records-run-the-same-privacy-sc | da7c496 | 2f9a2623b81d | identical subject and identical patch-id on main |
| 542 | developer-1/t-0127-the-flaky-load-determinism-test-reads-th | 4d33f8e | 8e25c6041282 | the one merge commit on main for this branch |
| 543 | developer-2/t-0128-add-a-pr-repair-command-a-stale-pr-statu | b6c9779 | 91ac4da0668e | the one merge commit on main for this branch |
| 544 | tester/t-0015-record-the-pr-repair-integration-layer | 90ad554 | c1043a78c62d | the one merge commit on main for this branch |
| 545 | ceo/t-0041-commit-the-closing-audit-manifest-throug | 9b61cd3 | 93d6fb8b75f9 | the one merge commit on main for this branch |
| 546 | ceo/t-0042-re-export-the-closing-audit-manifest-at | d1da5d3 | 286111a2960b | the one merge commit on main for this branch |
| 547 | developer-1/t-0130-status-json-and-the-pi-widget-must-show | f18be36 | eeea73c0e58d | the one merge commit on main for this branch |
| 548 | developer-2/t-0132-fold-unreleased-into-the-1-5-2-section-a | 68ff87c | 9ff462de77b6 | the one merge commit on main for this branch |
| 549 | ceo/t-0043-review-pass-dead-code-lanetoolbudget-ref | 3b60ffb | c0e75757d173 | the one merge commit on main for this branch |
| 550 | ceo/t-0044-fold-idle-instances-instance-prune-and-p | 905b001 | 7737a59fb0ef | the one merge commit on main for this branch |
| 551 | ceo/t-0045-explicit-project-must-beat-teamwork-root | 58a2bd8 | 8fc2ec238774 | the one merge commit on main for this branch |
| 552 | ceo/t-0046-streaming-dispatch-swarm-run-and-pulse-s | d5c7504 | ed68c4270858 | the one merge commit on main for this branch |
| 553 | ceo/t-0047-review-pass-align-every-dispatch-surface | 21387d4 | cea3c85d72a6 | the one merge commit on main for this branch |
| 554 | ceo/t-0048-readme-state-the-async-lane-dispatch-on | 9cb6191 | 401eee3a8e16 | the one merge commit on main for this branch |
| 555 | ceo/t-0049-reap-recycles-a-finished-lane-s-seat-and | 8464124 | 1d7901470218 | the one merge commit on main for this branch |
| 556 | ceo/t-0050-release-prep-1-5-3-add-the-compare-link | a2194e5 | abfb42627f2e | the one merge commit on main for this branch |
| 557 | ceo/t-0051-release-workflow-npm-verify-polls-past-t | 6e28deb | 8311faad203d | the one merge commit on main for this branch |
| 558 | ceo/t-0052-throughput-pass-packet-memory-once-area | 4d11aa7 | efeaf9e057b7 | the one merge commit on main for this branch |
| 559 | ceo/t-0053-ledger-verify-one-bounded-re-read-before | e2a311d | b089fe358baf | the one merge commit on main for this branch |
| 560 | ceo/t-0054-lane-proof-hold-the-fake-lane-long-enoug | c8ba79f | be6f78203d0c | the one merge commit on main for this branch |
| 561 | ceo/t-0055-rework-gates-evidence-freshness-at-prefl | ff6e7cd | c464e2bc7bd2 | the one merge commit on main for this branch |
| 562 | ceo/t-0056-adopt-sparseread-a-sparse-read-gate-with | 01f954d | 7fddc5849e0e | the one merge commit on main for this branch |
| 563 | ceo/t-0057-live-state-show-busy-work-and-live-lanes | 14813e4 | 442db47bfa44 | the one merge commit on main for this branch |
| 564 | ceo/t-0058-release-prep-1-5-4-add-the-compare-link | 2796686 | 0aa0bc83beff | the one merge commit on main for this branch |
| 565 | ceo/t-0059-fix-the-two-documentation-defects-the-au | 6334721 | abb0362c3e98 | the one merge commit on main for this branch |
| 566 | ceo/t-0060-refresh-the-audit-manifest-and-the-board | 07addb1 | b1e1beed8276 | the one merge commit on main for this branch |
| 567 | ceo/t-0061-close-the-audit-s-team-state-findings | 5678e3f | 2a2c9492d4cb | the one merge commit on main for this branch |
| 568 | ceo/t-0063-move-the-tree-to-1-5-5-after-the-v1-5-4 | b4cd368 | 2c1667d04fca | the one merge commit on main for this branch |
| 569 | ceo/t-0062-make-the-audit-s-problem-count-mean-acti | bb0b436 | 3c540c137132 | the one merge commit on main for this branch |
| 570 | ceo/t-0064-stream-each-active-agent-s-latest-comman | 1d3355c | 4ed757850195 | the one merge commit on main for this branch |
| 571 | ceo/t-0065-export-the-closing-audit-manifest-at-the | 4eea5c8 | 9de3b211f1aa | the one merge commit on main for this branch |
| 572 | ceo/t-0066-fold-the-unreleased-notes-into-1-5-5-whi | b681719 | b6d87c8635d2 | the one merge commit on main for this branch |
| 573 | ceo/t-0067-record-the-owner-s-push-and-release-auth | 3c6c9bd | 766fbab8b498 | the one merge commit on main for this branch |
| 574 | ceo/t-0068-reword-the-release-authorization-so-r9-c | dcd7679 | a1ab4f99c08f | the one merge commit on main for this branch |
| 575 | ceo/t-0069-close-a-lesson-with-a-check-not-prose | 23f8513 | 207dd10cb5fd | the one merge commit on main for this branch |
| 576 | developer/t-0063-a-test-that-dispatches-without-a-fake-la | 7f439aa1 | a819dedb92c5 | the one merge commit on main for this branch |
| 577 | ceo/t-0035-commit-the-d-20261115-ceo-4-governance-r | 494cf667 | 75287ad1425a | the one merge commit on main for this branch |
| 578 | developer/t-0064-branch-start-worktree-leaves-an-untracke | 29d20d4f | 7f647e46bc38 | the one merge commit on main for this branch |
| 579 | ceo/t-0036-commit-the-m24-renumber-the-ac-m24-crite | c824be5a | 2bc011b1bd92 | the one merge commit on main for this branch |
| 580 | tester/t-0005-retire-the-layered-test-records-that-sha | cc343480 | b622ade7c335 | identical subject and identical patch-id on main |
| 581 | developer/t-0065-one-teamwork-renderer-in-the-pi-ui-agent | 53225821 | 066caeccde47 | the one merge commit on main for this branch |
| 582 | developer/t-0066-pulse-commit-claims-a-review-failed-task | dbb42541 | 2a16b2beb2da | the one merge commit on main for this branch |
| 583 | ceo/t-0037-commit-the-d-20261115-ceo-6-release-auth | f6e62305 | ace284a9ae14 | the one merge commit on main for this branch |
| 584 | releaseengineer/t-0001-release-prep-1-5-9-the-changelog-section | 88a60cd1 | 8a5e6eca51e8 | the one merge commit on main for this branch |
| 585 | ceo/t-0038-re-render-the-board-so-no-committed-row | dbc56003 | 523099bf9db0 | the one merge commit on main for this branch |
| 587 | designer/t-0001-agent-state-widget-information-hierarchy | 830636bc | 2faaab35bc51 | the one merge commit on main for this branch |
| 588 | developer/t-0068-implement-the-redesigned-agent-state-dis | 008b126d | 2f43e97663e8 | the one merge commit on main for this branch |
| 589 | designer/t-0002-design-md-10-8-the-round-2-row-used-and | 7abfa18e | 9ba1a1adcc68 | the one merge commit on main for this branch |
| 590 | reviewer-1/t-0007-round-2-critique-design-md-10-the-agent | edc00c18 | c3e8f3967df7 | the one merge commit on main for this branch |
| 591 | developer/t-0067-a-release-task-whose-title-names-its-own | bf95dfc5 | bbc287fc5130 | the one merge commit on main for this branch |
| 592 | developer/t-0070-payload-schema-5-signals-renderer-v3-use | 5e37f092 | 1bc5bf4ba1b4 | the one merge commit on main for this branch |
| 594 | developer/t-0071-pr-base-cannot-be-re-pointed-after-the-b | 66f2a703 | 7c9a17d37417 | the one merge commit on main for this branch |
| 595 | tester/t-0006-agent-state-display-ui-layer-execute-the | 23aa21e4 | 4d02fa004cef | the one merge commit on main for this branch |
| 596 | developer/t-0072-records-commit-the-d-20261116-ceo-decisi | 5267f8ea | d0c0a84fc0b6 | the one merge commit on main for this branch |
| 597 | developer/t-0073-ship-one-skill-delete-templates-pi-packa | ad86404b | f0384f55be4e | the one merge commit on main for this branch |
| 598 | designer/t-0003-design-md-10-9-no-bar-no-percentage-a-28 | cd59fa15 | c55396110a73 | the one merge commit on main for this branch |
| 599 | developer/t-0074-renderer-v4-no-bar-no-percent-28-column | cd28c50c | 13ac62539b6b | the one merge commit on main for this branch |
| 600 | tester/t-0007-agent-state-ui-layer-round-3-prove-no-ba | 7284ad6b | 7bd920e7f30d | the one merge commit on main for this branch |
| 601 | developer/t-0076-widget-drop-the-idle-line-engine-fold-a | 926ec94c | 397ee502b087 | the one merge commit on main for this branch |
| 602 | securityauditor/t-0001-m26-security-audit-the-red-privacy-gate | a9b0ef95 | 6450ff9b9f8a | the one merge commit on main for this branch |
| 604 | developer/t-0081-widget-header-live-and-review-only-drop | 262be1e3 | 0716af6c79bb | the one merge commit on main for this branch |
| 605 | ceo/t-0070-commit-the-final-audit-manifest-at-the-c | 2ba3008a | 4f6bd15c5868 | the one merge commit on main for this branch |
| 606 | ceo/t-0071-bump-to-1-5-10-after-the-v1-5-9-tag-so-r | ea648c91 | 3a25c8981c61 | the one merge commit on main for this branch |
| 607 | ceo/t-0072-add-the-swarm-file-ownership-rule-task-f | eac3816e | bce35a401e04 | the one merge commit on main for this branch |
| 608 | ceo/t-0073-refresh-the-closing-audit-manifest-at-th | 00e04bf7 | 97e4ec201619 | the one merge commit on main for this branch |
| 609 | ceo/t-0074-update-features-md-with-file-ownership-f | e23210c9 | 13912d74de54 | the one merge commit on main for this branch |
| 610 | ceo/t-0075-update-readme-with-file-ownership-featur | 78c584ed | b45e5e41bac3 | the one merge commit on main for this branch |
| 611 | ceo/t-0076-fix-committer-guard-failure-on-v1-5-10-t | 1715c258 | 1b2a56e2f5d1 | the one merge commit on main for this branch |
| 612 | ceo/t-0078-intake-gates-record-the-prompt-with-rese | 3e74160e | 0cb1b767226d | the one merge commit on main for this branch |
| 613 | ceo/t-0079-release-prep-1-5-11-the-changelog-sectio | 31f3ce45 | fcad503e7130 | the one merge commit on main for this branch |
| 614 | ceo/t-0080-ci-fix-exempt-published-pre-rule-history | a2365a40 | 43fd77b417bf | the one merge commit on main for this branch |
| 615 | developer/t-0080-m26-security-s-1-path-traversal-on-insta | ebcff866 | e049852b8292 | the one merge commit on main for this branch |
| 616 | ceo/t-0081-commit-the-d-20261116-ceo-release-author | 0f9b26d6 | 90f0420a1762 | the one merge commit on main for this branch |
| 617 | ceo/t-0082-move-the-tree-to-1-5-12-after-the-v1-5-1 | 7d36b7ff | 08a0d929dd64 | the one merge commit on main for this branch |
| 618 | ceo/t-0083-refresh-the-closing-audit-manifest-at-th | 525b3c07 | 5c41a098a679 | the one merge commit on main for this branch |
| 619 | tester/t-0008-m26-test-audit-vacuous-tests-proved-by-m | 49e8fde7 | 4ebe9f637ee1 | the one merge commit on main for this branch |
| 620 | developer/t-0078-m26-code-audit-real-defects-broken-invar | 9de0c8b1 | 945e8a2a85cb | the one merge commit on main for this branch |
| 621 | developer-2/t-0084-panel-contract-ac-d1-d2-d3-d5-every-draw | 7e085c95 | e1e2bdde4219 | the one merge commit on main for this branch |
| 623 | releaseengineer/t-0004-release-consistency-r7-and-repository-hy | 3b7f4425 | e2b774b644a2 | the one merge commit on main for this branch |
| 624 | designer/t-0004-ac-d4-record-the-panel-design-what-the-u | 449cbd20 | b7c3c3aee076 | the one merge commit on main for this branch |
| 626 | securityauditor/t-0002-record-the-security-layer-for-the-m26-au | e5cfb54b | 27dfa42d5ae3 | the one merge commit on main for this branch |
| 628 | developer-2/t-0082-status-shows-another-role-s-task-title-s | 71d8da75 | 411b6b7d3caf | the one merge commit on main for this branch |
| 629 | developer/t-0085-unit-layer-records-for-15-areas-with-no | 85a94e26 | a9827fdf910a | the one merge commit on main for this branch |
| 630 | tester/t-0009-triage-the-41-test-layer-gaps-into-per-r | 4986d86b | 9a43f1c4c643 | the one merge commit on main for this branch |
| 632 | releaseengineer/t-0005-release-layer-record-for-area-changelog | c08da898 | 0fb73ee3bdf4 | the one merge commit on main for this branch |
| 633 | tester/t-0010-ac-m25-4-prove-an-installed-package-expo | 5164a1db | d9b1356b8fc0 | the one merge commit on main for this branch |
| 634 | technicalwriter/t-0001-m26-docs-audit-false-claims-proved-by-co | c1a0ca82 | a6ec92a15a35 | the one merge commit on main for this branch |
| 635 | developer/t-0079-release-blockers-7-failing-tests-board-d | c77cd126 | 138421c6db72 | the one merge commit on main for this branch |
| 636 | developer-3/t-0086-guard-the-cost-policy-a-test-that-no-lan | 47d6a6fa | 901e950e6cc9 | the one merge commit on main for this branch |
| 637 | technicalwriter/t-0002-link-health-on-main-10-pre-existing-brok | d1845257 | e58f715a1063 | the one merge commit on main for this branch |
| 639 | tester/t-0011-integration-layer-tests-missing-for-widg | 1e3ae139 | 3ffd73072921 | the one merge commit on main for this branch |
| 640 | developer-1/t-0092-the-lane-display-kills-the-lane-refresh | 2319ae1f | 7c0e9d43adba | the one merge commit on main for this branch |
| 641 | technicalwriter/t-0003-ship-the-operating-rule-the-ceo-decompos | 059e413c | 09cf7353127f | the one merge commit on main for this branch |
| 642 | developer-1/t-0089-a-stalled-seat-is-never-reconciled-a-cla | f37cf990 | 7abe0fdd14e6 | the one merge commit on main for this branch |
| 643 | developer-2/t-0098-the-silent-lane-watchdog-measures-log-by | 834c92bf | ce879dea1ca1 | the one merge commit on main for this branch |
| 644 | developer-1/t-0088-live-lane-scratch | 3677d16e | 4d63ea06cf80 | the one merge commit on main for this branch |
| 645 | architect/t-0003-freeze-the-lane-runtime-contract-so-a-te | 88c264bf | b3fdf6b10958 | the one merge commit on main for this branch |
| 646 | developer-2/t-0100-the-gate-role-s-startup-read-is-2624-b-o | f33b74d1 | 6f3eaea7eba0 | the one merge commit on main for this branch |
| 647 | developer-4/t-0104-a-reviewer-authors-the-merge-and-the-rec | c6d4a5e8 | 45f0ae8f8e96 | the one merge commit on main for this branch |
| 648 | developer-1/t-0099-an-open-feature-does-not-protect-its-tea | 7b9e098a | 7a75a74d4afd | the one merge commit on main for this branch |
| 649 | developer-2/t-0094-model-auto-must-refuse-a-premium-host-de | 23d905ab | 58175f802c7e | the one merge commit on main for this branch |
