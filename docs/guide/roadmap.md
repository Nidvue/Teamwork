# Roadmap - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Releases](../releases.md) · [Features](features.md) · [Alternatives](alternatives.md)

Direction, not a promise. A row moves here when the work that backs it is on the
board, and it leaves when the release that carries it is tagged.

## 1. Status

| Version | Status | Focus |
|---|---|---|
| `v1.0.0` | released | Package, skill bundle, CLI, 15 role charters, layered tests, CI/release workflows, docs site. |
| `v1.x` | current | A `v*` tag publishes the wheel, the checksums, the SBOMs and the `@nidvue/teamwork` npm package from one revision and rebuilds the site from it ([Releases](../releases.md)); the remaining step is PyPI trusted publishing. Read the newest tag with `git tag -l --sort=-v:refname` and the tree's version with `teamwork.py --version`: the two differ by design between a version bump and its tag. |
| next | exploring | More provider adapters, end-to-end worked examples, an opt-in ledger dashboard. |

The current release line is the one in `src/teamwork/version.py`. Read it from
the command, never from a copy of this page:

```console
$ python3 scripts/teamwork.py --version
$ npm view @nidvue/teamwork version
```

## 2. What "current" means between releases

A version is bumped in `src/teamwork/version.py` before it is tagged, so the
checkout can be ahead of the newest release. That is deliberate: the tag is the
publication event, not the commit that starts the work. [Releases](../releases.md)
describes the four faces of a release - the tag, the GitHub Release, the npm
package and the site - and what none of them publishes.

## 3. How a roadmap item becomes shipped work

The same gate applies to the roadmap as to code: an item is not "done" because a
page says so. It becomes shipped when a task cites the release revision, the
release pipeline publishes that revision, and the release-consistency gate agrees
the tag, the package version and the prose all name the same thing. Until then the
row says "exploring" and no surface claims otherwise.

## 4. What is explicitly not planned

- **A hosted service.** The engine runs where the agent host runs; the team never
  sends your repository to a service of ours.
- **A model.** Teamwork ships no weights and calls no LLM API itself; the host
  supplies the model, and every lane's model is configured independently.
- **Bought stars.** The project optimises the conversion inputs honestly - the
  demo, this documentation, the licence and the releases - and does not promise
  social proof it cannot earn.
- **A hosted dashboard as the only way to read the ledger.** The ledger is a file
  in the workspace and `ledger export` is the portable proof; a dashboard would be
  an optional convenience, never the source of truth.

## 5. How this page stays true

A roadmap is prose, and prose rots faster than code, so this page leans on
commands instead of dates:

| Claim | How to check it |
|---|---|
| the current release line | `python3 scripts/teamwork.py --version` |
| the newest published tag | `git tag -l --sort=-v:refname \| head -1` |
| the version the npm channel serves | `npm view @nidvue/teamwork version` |
| what the newest release carries | [Releases](../releases.md) |
| what the gate accepts as shipped | `python3 scripts/check_release_consistency.py --offline` |

There is no date column on purpose. A date that slips becomes a broken promise on
a public page; a status that names the gate cannot slip without the gate saying
so. When the next tag publishes, the "current" row changes and this page is
re-read - not rewritten from memory.

## 6. How to influence it

Open an issue with the problem, not only the proposed feature: what you were
trying to do, what the engine did, and the command that showed it. A roadmap
decision is recorded in `docs/Team/Decisions.md` with its evidence, so a direction
change is auditable in the same way as a code change. Contributions follow
[CONTRIBUTING.md](https://github.com/Nidvue/Teamwork/blob/main/CONTRIBUTING.md):
one branch per task, a real test, an independent review, and a Reviewer - never
the author - merges.
