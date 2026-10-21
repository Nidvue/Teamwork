"""The child environment every harness that spawns git must use.

Two requirements pull in opposite directions, and a child environment that
satisfies only one of them is a defect:

* **The platform's own variables must survive.** On Windows the interpreter
  initialises its hash seed from the OS RNG, which needs ``SystemRoot``,
  ``TEMP`` and ``TMP``. A hand-built environment that keeps only ``PATH`` and
  ``HOME`` drops them, and the child dies before it runs a single command:
  ``Fatal Python error: _Py_HashRandomization_Init: failed to get random
  numbers to initialize Python``.
* **The caller's git configuration must not.** ``GIT_CONFIG_GLOBAL``,
  ``GIT_CONFIG_SYSTEM``, ``XDG_CONFIG_HOME`` and ``HOME``-derived config files
  decide where hooks are written (``core.hooksPath``), what a fresh branch is
  called (``init.defaultBranch``) and whether a commit is signed
  (``commit.gpgsign``). A test that inherits them measures the developer's
  machine instead of the contract.

So the rule is: **start from ``os.environ`` and re-assert the hermeticity on
top of it.** The base keeps the platform's variables; the pins above them take
the caller's git configuration back out. This is the shape the refresh harness
already used (``GIT_ENV`` in ``tests/unit/test_skill_refresh.py``) and the
shape every site now uses.

``GIT_CONFIG_SYSTEM`` and ``XDG_CONFIG_HOME`` are *removed* rather than
overwritten: git reads the system config and ``$XDG_CONFIG_HOME/git/config``
in addition to the global one, and pointing them at a real file would put the
caller's configuration back in.

The environment is a configuration source of its own, and the pins do not
cover it. ``GIT_CONFIG`` is git's ``--file`` pointer, ``GIT_CONFIG_COUNT``
with its numbered ``GIT_CONFIG_KEY_<n>`` / ``GIT_CONFIG_VALUE_<n>`` pairs
injects configuration straight into the child, and ``GIT_TEMPLATE_DIR``
installs the caller's hooks into every fresh repository. Git reads the
injected configuration *above* the global file, so a ``/dev/null`` global
leaves an injected ``commit.gpgsign`` in force - all of them are removed.

The variables that point git at a *repository* (``GIT_DIR``, ``GIT_WORK_TREE``
and friends) are removed for the same reason: a child that inherits them acts
on the caller's repository instead of the throwaway tree the test made.
"""

from __future__ import annotations

import os

#: The variables that decide which git configuration a child reads. They are
#: removed from the inherited environment, then re-asserted where a site wants
#: a specific value.
#:
#: ``GIT_CONFIG`` is git's ``--file`` pointer (a whole config file), and
#: ``GIT_CONFIG_COUNT``/``GIT_CONFIG_PARAMETERS`` inject configuration straight
#: into the child's git. The pins below do NOT neutralise any of them: git
#: reads the environment-injected configuration with a higher precedence than
#: the global file, so ``GIT_CONFIG_NOSYSTEM=1`` and a ``/dev/null`` global
#: leave an injected ``commit.gpgsign`` in force.
GIT_CONFIG_VARS = (
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "XDG_CONFIG_HOME",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
)

#: The prefixes of the numbered environment-injected configuration pairs
#: (``GIT_CONFIG_KEY_<n>`` / ``GIT_CONFIG_VALUE_<n>``). They are numbered, so
#: they cannot be listed one by one: git pairs them with ``GIT_CONFIG_COUNT``,
#: and an unmatched pair makes the child die with "missing config key".
GIT_CONFIG_PAIR_PREFIXES = (
    "GIT_CONFIG_KEY_",
    "GIT_CONFIG_VALUE_",
)

#: The variables that point git at a repository. A developer shell can carry
#: them (``git -C`` sets GIT_DIR, a script can export it), and a child that
#: inherits them acts on that repository instead of the throwaway tree the test
#: made - which is not a hermetic failure but a wrong-repository failure.
GIT_REPO_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
)

#: The pins that make a child's git configuration hermetic: no system config,
#: no global config, and no credential prompt that could block a run.
HERMETIC_GIT = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}

#: The variables that make git read a caller's *template* directory, whose
#: ``hooks/`` are installed into every fresh repository. It is the environment
#: twin of ``init.templateDir``, so it belongs with the configuration.
GIT_TEMPLATE_VAR = "GIT_TEMPLATE_DIR"


def child_env(base: dict | None = None, **overrides: str) -> dict:
    """A child environment: the platform's variables, but not the caller's git config.

    ``base`` defaults to ``os.environ``. The result keeps every platform
    variable (so a Windows child can initialise its RNG) and re-asserts the
    hermetic git pins on top, so none of the caller's git configuration can
    reach the child - not the global, system or XDG files, not the
    environment-injected pairs (``GIT_CONFIG_COUNT`` and friends), and not the
    template directory whose hooks git would install into every fresh repo.
    ``overrides`` are applied last, so a site that wants a different ``HOME``
    or a pinned identity still wins.
    """
    env = dict(os.environ if base is None else base)
    for name in GIT_CONFIG_VARS + GIT_REPO_VARS + (GIT_TEMPLATE_VAR,):
        env.pop(name, None)
    for name in [key for key in env if key.startswith(GIT_CONFIG_PAIR_PREFIXES)]:
        env.pop(name, None)
    env.update(HERMETIC_GIT)
    env.update({key: str(value) for key, value in overrides.items()})
    return env
