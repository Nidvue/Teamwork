# Installation - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [CLI reference](cli.md)

## Requirements

| Requirement | Value |
|---|---|
| Python | CPython 3.9 - 3.13 |
| Runtime dependencies | none (standard library only) |
| Platforms | Linux, macOS, Windows |

The distribution name is `teamwork-agents` (the name `teamwork` is taken on
PyPI); the import name is `teamwork` and the console script is `teamwork`.

!!! note "PyPI status"
    PyPI publishing is prepared but not enabled for this release. Until the
    package is published, install from the [GitHub release](https://github.com/VisionPZ/Nidvue-Teamwork/releases)
    wheel or from source. The `pip`/`pipx`/`uvx` commands below apply once the
    release is on PyPI.

## Install with pip

```console
$ python -m pip install teamwork-agents
```

Verify:

```console
$ teamwork --version
teamwork 1.0.0
```

## Install with pipx (isolated, on PATH)

[pipx](https://pipx.pypa.io/) installs the CLI into its own environment and puts
`teamwork` on your PATH:

```console
$ pipx install teamwork-agents
$ teamwork --version
```

## Run without installing (uvx)

[uv](https://docs.astral.sh/uv/) can run the console script from an ephemeral
environment:

```console
$ uvx --from teamwork-agents teamwork --version
```

## Install from source

```console
$ git clone https://github.com/VisionPZ/Nidvue-Teamwork.git
$ cd Teamwork
$ python -m pip install .
```

For development, install the package in editable mode with the test and docs
extras (see [CONTRIBUTING.md](https://github.com/VisionPZ/Nidvue-Teamwork/blob/main/CONTRIBUTING.md)):

```console
$ python -m pip install -e ".[dev]"
```

You can also run the CLI straight from a checkout without installing anything —
the compatibility shim uses only the standard library:

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

`selftest` runs an offline smoke check — no network, no workspace needed:

```console
$ teamwork selftest
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

Exit code `0` means the install is sound. If the skill assets are missing, the
wheel was built without the bundle; reinstall from a release artifact.

## Uninstall

```console
$ python -m pip uninstall teamwork-agents    # pip
$ pipx uninstall teamwork-agents             # pipx
```

Next: [Quickstart](quickstart.md).
