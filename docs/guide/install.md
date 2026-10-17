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
$ git clone https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
```

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

!!! note "Updating the skill"
    `git -C .agents/skills/teamwork pull` (or the path you cloned to) and reload
    the host. Pin a tag (`--branch v1.0.2`) when you want a fixed protocol
    revision.

## Optional: install the engine on PATH

The skill always works from its own directory. Install the same engine as a
package only when you want to drive the team yourself from a terminal, or when
your host cannot run a bundled script.

The distribution name is `teamwork-agents` (the name `teamwork` is taken on
PyPI); the import name is `teamwork` and the console script is `teamwork`.

!!! note "PyPI status"
    PyPI publishing is prepared but not enabled for this release. Until the
    package is published, install from the [GitHub release](https://github.com/Nidvue/Teamwork/releases)
    wheel or from source. The `pip`/`pipx`/`uvx` commands below apply once the
    release is on PyPI.

### Install with pip

```console
$ python -m pip install teamwork-agents
```

Verify:

```console
$ teamwork --version
teamwork 1.0.0
```

### Install with pipx (isolated, on PATH)

[pipx](https://pipx.pypa.io/) installs the CLI into its own environment and puts
`teamwork` on your PATH:

```console
$ pipx install teamwork-agents
$ teamwork --version
```

### Run without installing (uvx)

[uv](https://docs.astral.sh/uv/) can run the console script from an ephemeral
environment:

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
teamwork 1.0.0
```

## Platform notes

=== "Linux"

    Use `python3` if `python` is not on PATH. No system packages are needed.

    ```console
    $ python3 -m pip install teamwork-agents
    ```

=== "macOS"

    Use the python.org installer or Homebrew Python. If `pip` refuses with an
    "externally managed environment" error, use `pipx` or a virtual environment.

    ```console
    $ python3 -m venv .venv && . .venv/bin/activate
    $ python -m pip install teamwork-agents
    ```

=== "Windows"

    Use the Python launcher or PowerShell. Quote the extras when installing from
    source.

    ```powershell
    PS> py -m pip install teamwork-agents
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
  version:   1.0.0
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
