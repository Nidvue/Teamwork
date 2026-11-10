# Installation - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [CLI reference](cli.md)

Nidvue Teamwork is a **skill for your coding agent**, not a standalone app. You
install it by cloning this repository into the directory your host reads skills
from; the host runs the bundled engine. Nothing is built, nothing is daemonised,
nothing is sent to a service of ours.

## Requirements

| Requirement | Value |
|---|---|
| Agent host | any host that loads a skill directory, or that can run a script and read `AGENTS.md` |
| Engine runtime | CPython 3.9 - 3.13, standard library only, no third-party dependencies |
| Platforms | Linux, macOS, Windows |

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
    whenever it wrote something. Pin a tag (`--branch v1.1.2`) when you want a
    fixed protocol revision instead of `main`: the checkout is then moved onto
    that tag's commit *detached* and the refresh prints `pinned to tag v1.1.2`.
    It is a read-only mirror of that revision - re-run with `--branch main` to
    follow the branch again, or name another tag to move the pin.

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

Each tag publishes a wheel and an sdist with checksums and SBOMs. The URL below
names the newest **release**, which can be older than the checkout - a version is
bumped before it is tagged, so read both rather than assuming they agree:

```console
$ gh release list --limit 1
$ python3 scripts/teamwork.py --version
$ python -m pip install https://github.com/Nidvue/Teamwork/releases/download/v1.1.2/teamwork_agents-1.1.2-py3-none-any.whl
```

If you need the tree's exact engine instead of the released one, install from the
checkout: `python -m pip install .`.

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
