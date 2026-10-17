# Remotes - repository and CI integrity on any git host

Owner: Release Engineer. The skill is remote-agnostic: the *policy* below is the
contract, and the host table says how to configure it on GitHub, GitLab,
Bitbucket, Gitea/Forgejo, Azure DevOps or a bare server. Configuration is not
optional decoration - unprotected integrity is the failure this file exists to
prevent.

## The integrity policy (host-neutral)

1. **The default branch is protected.**
   - no direct commits: every change arrives through a reviewable request;
   - no force-push and no history rewrite: an already-published commit is
     immutable (the single exception is a privacy purge, which is a CEO red line
     and is recorded);
   - no deletion of the branch or of a tag;
   - linear history: no merge commits on the default branch.
2. **Required status checks.** A merge is impossible while any required check is
   red, on the exact merged revision:
   - the test matrix (every supported OS x Python), lint, build + release
     verification, the privacy scan, and the strict docs build;
   - the checks are *required*, not advisory: "the release engineer saw it pass
     locally" is not a check;
   - require the branch to be up to date with the default branch before merge
     (strict mode), so a green run cannot be stale;
   - **a required check must always be reported.** A workflow skipped by a path
     filter produces no check run at all, so a documentation-only pull request
     would wait forever for a check that can never appear. Path filters belong on
     `push` (a cost optimisation); on `pull_request` the required workflows run
     unconditionally. This is the most common way branch protection deadlocks a
     repository.
3. **Required review.** At least one approval from a role that is not the author
   - in this team, the **Reviewer**. Self-approval is impossible; a new commit on
   the request dismisses the stale approval; the Reviewer - never the author -
   performs the merge.
4. **Merge strategy - one canonical shape.**
   - feature work: **squash** into one commit on the default branch, so history
     reads as one coherent change-set per task;
   - delete the source branch on merge;
   - releases: a tag on a commit that is already green on the default branch; never
     tag an unmerged branch, never move a published tag;
   - no `merge commit` and no `rebase merge` as a default, because they hide the
     squash boundary.
5. **Ref and secret hygiene.**
   - protected tag pattern `v*`, created only by the CEO;
   - CI least privilege: workflow default `contents: read`, each job widening only
     what it needs; attestation/OIDC only where used;
   - no secret in the tree, in a workflow log or in a prompt - the privacy scan is
     the gate, and the host secret store is the only place a value lives;
   - third-party actions/images pinned to a version (SHA pinning is the follow-up
     for anything with write permission).
6. **Verification is evidence, not assumption.** The Release Engineer records the
   protection rules, the required checks and the merge settings, and periodically
   re-reads them from the host API to detect drift. A protection change is a
   governance event: recorded in `Decisions.md` with who changed it and why.

## Host mapping

| Policy | GitHub | GitLab | Bitbucket Cloud | Gitea / Forgejo | Azure DevOps |
|---|---|---|---|---|---|
| protect default branch | branch protection / Rulesets (`PATCH .../branches/main/protection`) | protected branches | branch restrictions | branch protection | branch policies |
| no force-push / delete | `allow_force_pushes=false`, `allow_deletions=false` | "Allowed to force push" off | "Prevent rewriting history" | "Enable force push" off | "Require a merge strategy" + locks |
| required checks | `required_status_checks` (strict) | "Pipelines must succeed" | merge checks | "Require status checks" | build validation policy |
| required review | `required_pull_request_reviews` | merge request approvals | default reviewers | "Require approvals" | "Require a minimum number of reviewers" |
| dismiss stale approval | `dismiss_stale_reviews=true` | "Reset approvals on push" | merge check | "Dismiss stale approvals" | "Reset votes on new pushes" |
| squash-only, delete branch | repo `allow_squash_merge=true`, `allow_merge_commit=false`, `allow_rebase_merge=false`, `delete_branch_on_merge=true` | project merge method `ff`/squash + "Delete source branch" | merge strategy setting | "Squash merge only" | "Squash merge" + delete source branch |
| protected tags | tag protection rules / Rulesets | protected tags | (use branch restrictions on the release branch) | protected tags | tag policies via a pipeline gate |
| least-privilege CI | workflow `permissions:` | job `rules` + protected variables | pipelines `deployment` permissions | Actions permissions | pipeline permissions + variable groups |
| bare git server | `update` hook / `pre-receive` + `receive.denyNonFastForwards` | - | - | - | - |

## Minimum viable protection (what must be on)

| Setting | Value | Why |
|---|---|---|
| direct push to default branch | denied (admin bypass allowed only for an authorized purge) | review cannot be skipped |
| force-push | denied | published history is immutable |
| branch deletion | denied | the default branch cannot disappear |
| required checks | the CI matrix + privacy + docs, strict | nothing red merges |
| required approvals | >= 1, non-author, stale-dismissing | the two-stage gate is real |
| merge method | squash only | one change-set per task |
| delete branch on merge | on | no branch debt |
| tag protection | `v*`, CEO only | a release is deliberate |

## Evidence shape

```
gh api repos/<owner>/<repo>/branches/main/protection @<rev> -> required_checks=[CI, privacy, docs],
  enforce_admins=false, allow_force_pushes=false, allow_deletions=false, required_approvals=1,
  dismiss_stale_reviews=true
gh api repos/<owner>/<repo> --jq '.allow_squash_merge,.allow_merge_commit,.allow_rebase_merge,.delete_branch_on_merge'
  @<rev> -> true false false true
gh run list --workflow CI --commit <sha> @<rev> -> success (all matrix jobs)
```

## Drift check

Re-read the settings and compare with the table above; a missing or weakened
setting is a defect of the same severity as a red build, routed to the Release
Engineer and closed only with the API output as evidence. If the host cannot
express a rule, say so and record the compensating control (for example: a bare
server with a `pre-receive` hook, or a release checklist item that a human
verifies) - never leave it silently unprotected.
