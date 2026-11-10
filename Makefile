# Teamwork - development and release tasks.
#
# Run `make help` for the target list. All Python work uses $(PYTHON) so the
# same Makefile works on Linux, macOS and Windows (GNU make + python3/py).

PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip
DIST   ?= dist
HERE   := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.DEFAULT_GOAL := help

.PHONY: help install dev lint format typecheck test test-unit test-integration \
        test-acceptance selftest build verify package sync-skill sync-check privacy \
        docs links identity clean release-consistency release-consistency-online \
        release-check ci ci-fast python-floor

help: ## Show this help.
	@printf 'Teamwork - available targets:\n\n'
	-@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(subst \,/,$(MAKEFILE_LIST)) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@n=$$(grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(subst \,/,$(MAKEFILE_LIST)) | wc -l); \
		if [ "$$n" -eq 0 ]; then \
			echo 'make help: no documented targets found in: $(MAKEFILE_LIST)' >&2; \
			exit 1; \
		fi
	-@printf '\nPYTHON=%s  PIP=%s  DIST=%s\n' '$(PYTHON)' '$(PIP)' '$(DIST)'

install: ## Install the package (runtime, zero dependencies).
	$(PIP) install .

dev: ## Editable install with the dev extras (pytest, pytest-cov, ruff, mypy, build).
	$(PIP) install -e ".[dev]"

lint: ## Static checks: ruff check, ruff format --check, the no-comment rule and the role-mailbox audit.
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) $(HERE)scripts/check_comments.py
	$(PYTHON) $(HERE)scripts/teamwork.py identity --audit --strict-authors

format: ## Auto-format the tree and apply safe lint fixes.
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

typecheck: ## Type-check the runtime with mypy (report-only gate in CI).
	$(PYTHON) -m mypy src/teamwork

test: ## Run the full test suite.
	$(PYTHON) -m pytest -q

test-unit: ## Run the unit tests.
	$(PYTHON) -m pytest tests/unit -q

test-integration: ## Run the integration tests.
	$(PYTHON) -m pytest tests/integration -q

test-acceptance: ## Run the acceptance tests.
	$(PYTHON) -m pytest tests/acceptance -q

selftest: ## Offline smoke test of the CLI straight from the checkout.
	$(PYTHON) scripts/teamwork.py selftest

build: ## Build the sdist and wheel into dist/.
	$(PYTHON) -m build

verify: ## Build, assert the wheel payload and smoke-test it in a throwaway venv.
	$(PYTHON) scripts/verify_release.py

package: ## Assemble the pi package (@nidvue/teamwork) under dist/.
	$(PYTHON) scripts/build_pi_package.py

sync-skill: ## Mirror this checkout into the installed skill directory.
	$(PYTHON) scripts/sync_skill.py

sync-check: ## Fail when the installed skill differs from this checkout (run `make sync-skill` first).
	$(PYTHON) scripts/sync_skill.py --check

privacy: ## Scan the tree, the full git history and the team memory stores for private data.
	$(PYTHON) scripts/privacy_scan.py --tree --history --stores --allow .github/privacy-allow.txt

links: ## Check markdown links, URLs and back-links.
	$(PYTHON) scripts/teamwork.py links

identity: ## Fail when a commit is not authored/committed by the acting role.
	$(PYTHON) scripts/teamwork.py identity --audit --strict-authors

release-consistency: ## Fail when a published fact disagrees with the tree (offline).
	$(PYTHON) scripts/check_release_consistency.py

release-consistency-online: ## Same gate, plus the npm/GitHub/PyPI rules (needs network).
	$(PYTHON) scripts/check_release_consistency.py --online

docs: links ## Build the documentation site in strict mode (link health first, as CI does).
	$(PYTHON) -m mkdocs build --strict

clean: ## Remove build artefacts and local tool caches (keeps .venv).
	rm -rf $(DIST) build site
	rm -rf src/*.egg-info *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . \( -path ./.venv -o -path ./.git -o -path ./.pi \) -prune -o \
		-type d -name __pycache__ -exec rm -rf {} +
	@printf 'clean: removed build output and caches\n'

release-check: lint test selftest sync-check verify release-consistency privacy docs links identity ## Run every local gate CI runs, plus the offline selftest and skill-sync check.
	@printf 'release-check: all gates passed\n'

python-floor: ## Fail when $(PYTHON) is below the supported 3.11 floor.
	@$(PYTHON) -c "import sys; got = '%d.%d' % sys.version_info[:2]; sys.exit('python-floor: ' + sys.executable + ' is Python ' + got + ', but this project requires 3.11 or newer (pyproject requires-python); pass PYTHON=<interpreter> or run make dev') if sys.version_info < (3, 11) else None"

ci-fast: python-floor lint ## The single local gate: lint, link health and the docs contract, in one pass.
	$(PYTHON) $(HERE)scripts/teamwork.py links
	$(PYTHON) -m pytest -q tests/unit/test_docs_contracts.py

ci: release-check ## Alias for the documented one-shot local pipeline.
	@printf 'ci: all gates passed\n'
