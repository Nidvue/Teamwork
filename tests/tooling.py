"""One guard for every test that executes a tool the host may not have.

Why this exists: a test that shells out to an external program fails with
``FileNotFoundError [WinError 2] 'make'`` on a machine that does not have it,
while staying green in CI, which does. The contributor learns nothing about the
product from that traceback, and the suite reads as broken instead of telling
them what to install (measured at ``7db810a``: the ``make help`` contract was
red on a host without GNU make - ``T-0003``).

So the rule is: **an absent tool is a skip that names the tool and says why the
test needs it** - never a failure, and never a silent pass. :func:`require_tool`
is the only mechanism; it looks the tool up with :func:`shutil.which` at *call*
time, not at import time, so a test can patch the lookup and prove what the
guard does (``tests/unit/test_tool_guards.py``).

Which tools get a guard, and which do not:

* **Guarded** - tools that only a convenience path needs: ``make`` (the Makefile
  is a wrapper around gates CI runs directly), ``sh``/``bash`` (the git hooks and
  the CI scope classifier are POSIX shell scripts the test executes as fixtures).
  Their absence says nothing about the product.
* **Not guarded** - tools the *product itself* cannot run without: the Python
  interpreter and ``git``. ``teamwork`` commits, branches and audits through git,
  so a host without git cannot run the thing under test; skipping the suite there
  would report a green build for a machine that can never work. The honest signal
  is the loud failure. Revisit this if the product ever gains a git-free mode.
* **Not called at all** - ``npm``/``node``, ``gh``, ``docker``, ``tar`` and
  ``git-lfs``. Those appear in the tests only as names in documentation, as JSON
  metadata read from disk, or behind injected fakes; no test executes them, so
  there is nothing to guard. Adding a guard there would be a claim about a
  dependency the suite does not have.
"""

from __future__ import annotations

import shutil

import pytest

#: tool -> why a test needs it. The sentence is part of the skip message, so the
#: report tells a reader what the tool is for instead of only that it is missing.
TOOL_REASONS = {
    "make": "the Makefile contract executes the committed recipes through it",
    "sh": "the installed git hooks are POSIX shell scripts run with it",
    "bash": "the CI scope classifier is a POSIX shell script run with it",
}

#: The fallback reason for a tool with no entry above: it must still be stated.
GENERIC_REASON = "the test executes it"

#: The tools the suite guards. A tool outside this set is either a prerequisite
#: the product itself cannot run without (the interpreter, ``git``) or is never
#: executed by a test - see the module docstring.
GUARDED_TOOLS = frozenset(TOOL_REASONS)


def missing_tool(name: str) -> bool:
    """True when ``name`` is not on ``PATH``.

    The lookup is a ``shutil.which`` call at *call* time so that a test can
    monkeypatch ``shutil.which`` and measure the guard instead of the host.
    """
    return shutil.which(name) is None


def skip_message(name: str, detail: str | None = None) -> str:
    """The skip text for an absent ``name``: the tool, why it is needed, and detail.

    One builder for both forms of the guard, so a skip always names the tool and
    always states a reason a reader can act on - whoever reports it.
    """
    message = f"required tool {name!r} is not installed: {TOOL_REASONS.get(name, GENERIC_REASON)}"
    return f"{message} ({detail})" if detail else message


def require_tool(name: str, detail: str | None = None) -> None:
    """Skip the calling test when ``name`` is not installed.

    Skips - it does not return - because an absent tool must be visible in the
    report as a skip carrying the tool's name, and a silent ``return`` would be
    the same lie as a failure: a test that did not run, reported as a pass.
    """
    if not missing_tool(name):
        return
    pytest.skip(skip_message(name, detail))
