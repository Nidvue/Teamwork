# Teamwork - development and release tasks.
#
# Run `make help` for the target list. All Python work uses $(PYTHON) so the
# same Makefile works on Linux, macOS and Windows (GNU make + python3/py).

PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip
DIST   ?= dist

.DEFAULT_GOAL := help

.PHONY: help install dev lint format typecheck test test-unit test-integration \
        test-acceptance selftest build verify privacy docs links identity clean \
        release-check ci

help: ## Show this help.
	@printf 'Teamwork - available targets:\n\n'
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@printf '\nPYTHON=%s  PIP=%s  DIST=%s\n' '$(PYTHON)' '$(PIP)' '$(DIST)'

install: ## Install the package (runtime, zero dependencies).
	$(PIP) install .

dev: ## Editable install with the dev extras (pytest, pytest-cov, ruff, mypy, build).
	$(PIP) install -e ".[dev]"

lint: ## Static checks: ruff check + ruff format --check.
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

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

privacy: ## Scan the working tree and full git history for private data.
	$(PYTHON) scripts/privacy_scan.py --tree --history

links: ## Check markdown links, URLs and back-links.
	$(PYTHON) scripts/teamwork.py links

identity: ## Fail when a commit is not authored/committed by the acting role.
	$(PYTHON) scripts/teamwork.py identity --audit

docs: ## Build the documentation site in strict mode.
	$(PYTHON) -m mkdocs build --strict

clean: ## Remove build artefacts and local tool caches (keeps .venv).
	rm -rf $(DIST) build site
	rm -rf src/*.egg-info *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . \( -path ./.venv -o -path ./.git -o -path ./.pi \) -prune -o \
		-type d -name __pycache__ -exec rm -rf {} +
	@printf 'clean: removed build output and caches\n'

release-check: lint test verify privacy docs links identity ## Run the full local release gate.
	@printf 'release-check: all gates passed\n'

ci: release-check ## Alias for the documented one-shot local pipeline.
	@printf 'ci: all gates passed\n'
