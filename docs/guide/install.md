# Installation - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [CLI reference](cli.md) · [Releases](../releases.md)

Nidvue Teamwork is a **skill for your coding agent**, not a standalone app. You
install it by cloning this repository into the directory your host reads skills
from - or, where the host resolves packages from npm, by installing
`@nidvue/teamwork`. The host runs the bundled engine either way. Nothing is
built, nothing is daemonised, nothing is sent to a service of ours.

## Requirements

| Requirement | Value |
|---|---|
| Agent host | any host that loads a skill directory, or that can run a script and read `AGENTS.md` |
| Engine runtime | CPython 3.9 - 3.13, standard library only, no third-party dependencies |
| Platforms | Linux, macOS, Windows |

## Four channels, one engine

Every channel below ships the engine in `src/teamwork/` from the same tagged
revision - `src/teamwork/version.py` is the one version string - so they differ in
what your agent can load from them, not in what they do.

| Channel | Get it with | What you receive | Pick it when |
|---|---|---|---|
| **Skill clone** (the product) | the `git clone` in [Install the skill](#install-the-skill) | `SKILL.md`, the role charters, `references/`, `templates/` and the engine, as plain tracked files | Your agent host loads a skill directory |
| **npm package** | `npm install @nidvue/teamwork`, or your host's own package command | the same skill tree under `skills/teamwork/`, the prompts that ship beside it, and the project notices | Your host resolves skills from the npm registry |
| **GitHub-release wheel** | [the release asset](#install-from-the-github-release-wheel) | the Python package: the `teamwork` console script and `python -m teamwork` | You want `teamwork` on your PATH |
| **Source** | `git clone` then `python -m pip install .` | everything, editable | You are working on the engine |

None of them is a fork and none carries a second copy of the code. What a release
publishes on each face, and how to read the version it currently serves, is in
[Releases](../releases.md).

## Install the skill

```console
$ mkdir -p .agents/skills
$ git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
$ rm -rf .agents/skills/teamwork/.git
```

Dropping the nested `.git` matters: a plain clone inside a repository is recorded
as a gitlink (a submodule without `.gitmodules`), so a fresh clone of your project
would contain an empty directory. The skill must be committed as plain files. A
real submodule is a valid alternative:
`git submodule add https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork`.

That is the whole install: `SKILL.md`, the 15 role charters, `references/`,
`templates/`, the engine and the docs arrive in one directory.

A skill is a directory. The only host-specific question is which directory that
host scans, and the portable conventions are:

| Scope | Path | Use it when |
|---|---|---|
| Project | `.agents/skills/teamwork/` | Commit it so every teammate, session and worktree gets the same protocol |
| User | `~/.agents/skills/teamwork/` | The team should be available in every project |

If your host names its own skills directory, clone there instead; nothing else
changes. A host with no skill loader uses the same protocol through `AGENTS.md`
(`teamwork agents-md`). Where a host maps skills to slash commands, the request
is `/teamwork <prompt>`; everywhere else, naming the skill in the request loads
it:

```text
> use the teamwork skill: <prompt>
```

Re-scan or reload skills after adding the directory. The skill is advertised at
startup and loaded on demand. The optional mapping of host operations (spawn,
message, schedule) is in
[references/Adapters.md](https://github.com/Nidvue/Teamwork/blob/main/references/Adapters.md).

!!! note "Updating the skill: follow the remote, not a checklist"
    The host reads the **copy** in its skills directory, so a `git pull` in a
    checkout somewhere else changes nothing the agent sees. One command does both
    halves - fast-forward a source checkout from the remote, then mirror it into
    the installed directory:

    ```console
    $ teamwork refresh                 # fetch origin/main, then mirror into the host's skills directory
    $ teamwork refresh --dest ~/.agents/skills/teamwork
    $ teamwork refresh --check          # drift check: writes nothing, exits 1 when stale
    $ teamwork refresh --dry-run        # what it would copy, deletes and writes nothing
    ```

    It refuses to clobber a dirty checkout (it mirrors the checkout as it stands
    instead and says so), deletes files the source no longer ships (a renamed
    engine module must not shadow the new one), and never touches a file outside
    the bundle trees, so an operator note in the skills directory survives. With no
    checkout in use it keeps a tool-managed mirror beside the skills directory,
    created once with `--repo <url>` and updated from then on. The destination
    is resolved from the host's skills directory - `--dest` names one directly
    and `--host` selects a host's default - and the mirror sits beside it:
    `~/.pi/agent/skills/teamwork` mirrors through
    `~/.pi/agent/.teamwork-source`, and `--host agents` uses
    `~/.agents/.teamwork-source`:

    ```console
    $ teamwork refresh --mirror --repo https://github.com/Nidvue/Teamwork.git
    ```

    After a refresh, **reload the skill** (restart the host session, or re-scan
    skills) so the new ``SKILL.md`` is read - the command prints that reminder
    whenever it wrote something. Pin a tag when you want a fixed protocol revision
    instead of `main` - name it with `git tag -l --sort=-v:refname | head -1`
    rather than copying a literal, because a version printed on a page goes stale
    the day it is tagged: the checkout is then moved onto that tag's commit
    *detached* and the refresh prints `pinned to tag <tag>`. It is a read-only
    mirror of that revision - re-run with `--branch main` to follow the branch
    again, or name another tag to move the pin.

## Optional: install the engine on PATH

The skill always works from its own directory. Install the same engine as a
package only when you want to drive the team yourself from a terminal, or when
your host cannot run a bundled script.

The distribution name is `teamwork-agents` (the name `teamwork` is taken on
PyPI); the import name is `teamwork` and the console script is `teamwork`.

!!! warning "The package index is not live yet"
    The distribution is **not published to PyPI**:
    `https://pypi.org/pypi/teamwork-agents/json` returns not-found. Every index
    command in this section fails for now. They are recorded here so the channel
    is described, and `scripts/check_release_consistency.py` rule R8 reads the
    marker below - an unmarked index command would be a claim that does not
    resolve. Install from the GitHub-release wheel or from source instead.

### Install from the GitHub release wheel

Each tag publishes a wheel and an sdist with checksums and SBOMs. The commands
below resolve the newest **release** from the tag list instead of printing a
version here, because a released wheel can be older than the checkout - a version
is bumped before it is tagged, so read both rather than assuming they agree:

```console
$ tag="$(git tag -l --sort=-v:refname | head -1)"
$ python3 scripts/teamwork.py --version
$ python -m pip install "https://github.com/Nidvue/Teamwork/releases/download/$tag/teamwork_agents-${tag#v}-py3-none-any.whl"
# or the sdist, when your environment builds from source
$ python -m pip install "https://github.com/Nidvue/Teamwork/releases/download/$tag/teamwork_agents-${tag#v}.tar.gz"
```

If you need the tree's exact engine instead of the released one, install from the
checkout: `python -m pip install .`. The release assets themselves, and how to
verify them, are listed in [Releases](../releases.md).

### Install the skill bundle from npm

The same skill tree is published to the npm registry as `@nidvue/teamwork`, for a
host that resolves skills from packages rather than from a directory on disk. The
bundle carries `skills/teamwork/` (the clone's own tree), the prompts that ship
beside it and the project notices:

```console
$ npm view @nidvue/teamwork version      # the version the registry serves
$ npm install @nidvue/teamwork           # or your host's own package command
```

The registry entry and the newest tag can disagree - the registry learns about a
version only when the release publishes it - so read the version from that
command rather than from this page. This is not the Python package: `npm install`
puts the bundle in the project's `node_modules/`, where a host that resolves npm
packages finds `skills/` and `prompts/`, while `pip` puts the `teamwork` command
on your PATH.

### Index commands (unavailable until PyPI publishing is enabled)

<!-- release-consistency: channel-unavailable -->
```console
$ python -m pip install teamwork-agents      # unavailable: not on PyPI yet
```

Verify (once the channel is live):

```console
$ teamwork --version
teamwork <version>
```

The number printed is `__version__` in the installed `teamwork/version.py`, so
read it from the command rather than from a copy of this page.

### Install with pipx (isolated, on PATH)

[pipx](https://pipx.pypa.io/) installs the CLI into its own environment and puts
`teamwork` on your PATH. **Unavailable until the package is on PyPI:**

<!-- release-consistency: channel-unavailable -->
```console
$ pipx install teamwork-agents
$ teamwork --version
```

### Run without installing (uvx)

[uv](https://docs.astral.sh/uv/) can run the console script from an ephemeral
environment. **Unavailable until the package is on PyPI:**

<!-- release-consistency: channel-unavailable -->
```console
$ uvx --from teamwork-agents teamwork --version
```

### Install from source

```console
$ git clone https://github.com/Nidvue/Teamwork.git
$ cd Teamwork
$ python -m pip install .
```

For development, install the package in editable mode with the test and docs
extras (see [CONTRIBUTING.md](https://github.com/Nidvue/Teamwork/blob/main/CONTRIBUTING.md)):

```console
$ python -m pip install -e ".[dev]"
```

You can also run the engine straight from a checkout, or from the cloned skill
directory, without installing anything:

```console
$ python3 scripts/teamwork.py --version
teamwork <version>
```

## Platform notes

=== "Linux"

    Use `python3` if `python` is not on PATH. No system packages are needed.

    <!-- release-consistency: channel-unavailable -->
    ```console
    $ python3 -m pip install teamwork-agents   # unavailable: not on PyPI yet
    ```

=== "macOS"

    Use the python.org installer or Homebrew Python. If `pip` refuses with an
    "externally managed environment" error, use `pipx` or a virtual environment.

    <!-- release-consistency: channel-unavailable -->
    ```console
    $ python3 -m venv .venv && . .venv/bin/activate
    $ python -m pip install teamwork-agents   # unavailable: not on PyPI yet
    ```

=== "Windows"

    Use the Python launcher or PowerShell. Quote the extras when installing from
    source.

    <!-- release-consistency: channel-unavailable -->
    ```powershell
    PS> py -m pip install teamwork-agents   # unavailable: not on PyPI yet
    PS> py -m pip install -e ".[dev]"
    ```

## Verify the installation

Check the skill first: reload the host and confirm the skill is listed. Then
run the engine's offline smoke check - no network, no workspace needed:

```console
$ python3 .agents/skills/teamwork/scripts/teamwork.py selftest
  PASS  bundled skill assets   ok
  PASS  core helpers           ok
  PASS  workspace init         ok
  PASS  task queue round-trip  ok
  PASS  stop-condition gate    ok

teamwork selftest: 5/5 checks passed
  version:   <version>
  python:    3.12.13 (posix)
  skill:     /path/to/Teamwork
```

With the package installed, `teamwork selftest` runs the identical check. Exit
code `0` means the install is sound. If the skill assets are missing, the
directory is incomplete; re-clone it.

## Uninstall

```console
$ rm -rf .agents/skills/teamwork               # the skill (project)
$ rm -rf ~/.agents/skills/teamwork              # the skill (user)
$ python -m pip uninstall teamwork-agents        # the optional engine (pip)
$ pipx uninstall teamwork-agents                 # the optional engine (pipx)
```

Next: [Quickstart](quickstart.md).
