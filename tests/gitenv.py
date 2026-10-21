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

The variables that point git at a *repository* (``GIT_DIR``, ``GIT_WORK_TREE``
and friends) are removed for the same reason: a child that inherits them acts
on the caller's repository instead of the throwaway tree the test made.
"""

from __future__ import annotations

import os

#: The variables that decide which git configuration a child reads. They are
#: removed from the inherited environment, then re-asserted where a site wants
#: a specific value.
GIT_CONFIG_VARS = (
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "XDG_CONFIG_HOME",
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


def child_env(base: dict | None = None, **overrides: str) -> dict:
    """A child environment: the platform's variables, but not the caller's git config.

    ``base`` defaults to ``os.environ``. The result keeps every platform
    variable (so a Windows child can initialise its RNG) and re-asserts the
    hermetic git pins on top, so the caller's ``GIT_CONFIG_GLOBAL``,
    ``GIT_CONFIG_SYSTEM`` and ``XDG_CONFIG_HOME`` cannot reach the child.
    ``overrides`` are applied last, so a site that wants a different ``HOME``
    or a pinned identity still wins.
    """
    env = dict(os.environ if base is None else base)
    for name in GIT_CONFIG_VARS + GIT_REPO_VARS:
        env.pop(name, None)
    env.update(HERMETIC_GIT)
    env.update({key: str(value) for key, value in overrides.items()})
    return env
