# Releases - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](index.md) · [Installation](guide/install.md) · [Quickstart](guide/quickstart.md)

A release publishes **one tagged revision** to four faces: the git tag, a GitHub
Release, the npm package `@nidvue/teamwork`, and this site. They are not four
products - the wheel, the npm bundle and the site are all built from the tagged
tree, and the Release attaches one checksum manifest so you can prove that to
yourself instead of taking it on trust.

## 1. What a release contains

| Face | What lands | Read it from |
|---|---|---|
| **Tag** | `v<version>` on `main`. The pipeline refuses a tag whose number disagrees with `src/teamwork/version.py`, so the tag and the build cannot drift apart. | `git tag -l --sort=-v:refname \| head -1` |
| **GitHub Release** | the wheel, the sdist, **one** `SHA256SUMS` covering both artefacts and both SBOMs, `sbom.cyclonedx.json`, `sbom.spdx.json`, and a build-provenance attestation | [Releases](https://github.com/Nidvue/Teamwork/releases) - accessed 2026-10-28 |
| **npm package** | `@nidvue/teamwork`: `skills/teamwork/` - the same skill tree the clone installs - the prompts that ship beside it, and the project notices, published with `--provenance` | [npm](https://www.npmjs.com/package/@nidvue/teamwork) - accessed 2026-10-28 |
| **Site** | this documentation site, rebuilt and deployed from the tagged revision | [teamwork.nidvue.com](https://teamwork.nidvue.com/) - accessed 2026-10-28 |

`.github/workflows/release.yml` is the release pipeline: it runs the release
consistency gate before anything is built, builds and attests the artefacts,
publishes the GitHub Release and the npm package from that one revision, then runs
the same gate again so the Release it just created is checked too.
`.github/workflows/docs.yml` builds the site, and it fires on a `v*` tag as well as
on a `main` push - so the site is served from the released revision until the next
push to `main` that changes one of its own inputs, which redeploys it from `main`.

## 2. Where to get each face

```console
# the Python package (wheel) - the newest release's asset, resolved from the tag
$ tag="$(git tag -l --sort=-v:refname | head -1)"
$ python -m pip install "https://github.com/Nidvue/Teamwork/releases/download/$tag/teamwork_agents-${tag#v}-py3-none-any.whl"

# the sdist, when you build from the source archive instead
$ python -m pip install "https://github.com/Nidvue/Teamwork/releases/download/$tag/teamwork_agents-${tag#v}.tar.gz"

# the skill bundle from the npm registry
$ npm install @nidvue/teamwork

# the skill as a plain directory (the product; no package manager involved)
$ git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
$ rm -rf .agents/skills/teamwork/.git
```

None of those commands names a version: each resolves the tag or the registry
entry it needs, so this page cannot go stale between releases. The same channels
with their per-platform detail are in [Installation](guide/install.md).

## 3. How to tell which version is current

| Question | Command | Prints |
|---|---|---|
| newest released tag | `git tag -l --sort=-v:refname \| head -1` | `v<version>` |
| newest GitHub Release | `gh release view --json tagName --jq .tagName` | `v<version>` |
| newest version on npm | `npm view @nidvue/teamwork version` | `<version>` |
| the version in your checkout | `python3 scripts/teamwork.py --version` | `teamwork <version>` |

The four answers can disagree, and each difference means something:

- **Checkout vs tag.** `src/teamwork/version.py` is bumped before it is tagged, so
  between the bump and the tag the checkout is one version ahead of the newest
  release. That window is normal, not drift.
- **npm vs tag.** The registry learns about a version only when the publish step of
  the release run succeeds, so the newest tag can be a version ahead of
  `npm view @nidvue/teamwork version`. Read the registry rather than assuming; a
  version that is already there is verified instead of republished, so a re-run
  converges instead of failing.

Read the number from the command, never from a page like this one: a version printed
as prose is stale by the next release, which is exactly what the release consistency
gate (`scripts/check_release_consistency.py`, rule R6) exists to catch.

## 4. Verify a release you downloaded

```console
$ sha256sum -c SHA256SUMS     # in the directory holding every downloaded asset
$ gh attestation verify teamwork_agents-<version>-py3-none-any.whl --repo Nidvue/Teamwork
$ npm view @nidvue/teamwork@<version> version dist.integrity gitHead
```

The manifest lists **bare asset names**, because the Release flattens the asset
set: download everything into one directory and one `sha256sum -c` covers it.
`gh attestation verify` proves the file was built by this repository's
`.github/workflows/release.yml` at that tag. The npm command must name the tag's
version and the tagged commit in `gitHead` - that is what the publish step itself
checks before it reports success.

## 5. What a release does not do

| Not published | What it means for you |
|---|---|
| **PyPI** | The distribution `teamwork-agents` is **not on PyPI** (`https://pypi.org/pypi/teamwork-agents/json` returns not-found - measured 2026-10-28), so `pip install teamwork-agents`, `pipx install teamwork-agents` and `uvx --from teamwork-agents` do not resolve. The GitHub-release wheel above is the only index-free install source for the Python package. <!-- release-consistency: channel-unavailable --> |
| **A moved tag** | A published tag is immutable. The pipeline never creates, moves or re-points one, and a fix ships as a new patch release. Pin a tag when you want a fixed protocol revision - and do not expect that pin to move. |
| **A signed binary** | There is no GPG signature on the wheel. Provenance is the sigstore attestation the Release attaches, verified with `gh attestation verify`. |
| **Anything else** | No container image, no operating-system package, no hosted service. The wheel, the sdist, the two SBOMs, the npm bundle and the site are the complete set. |

## 6. Read next

- [CHANGELOG.md](https://github.com/Nidvue/Teamwork/blob/main/CHANGELOG.md) - the
  changes each released version carries, one section per tag - accessed 2026-10-28
- [Home](index.md) - what the product is, and what it is not
- [Installation](guide/install.md) - every channel with its platform notes
- [Quickstart](guide/quickstart.md) - install the skill and start a team
