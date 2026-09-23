# ---------------------------------------------------------------------------
# OpsPilot — task runner
# Requirements: Python 3.12, Docker with Compose v2+, GNU Make.
# All secrets come from the environment (see .env.example); nothing is hardcoded.
# ---------------------------------------------------------------------------

PYTHON   ?= python3.12
VENV     ?= .venv
BIN      := $(VENV)/bin
PY       := $(BIN)/python
PIP      := $(BIN)/pip
RUFF     := $(BIN)/ruff
MYPY     := $(BIN)/mypy
COMPOSE  ?= docker compose
SCENARIO ?= bad_deployment

.DEFAULT_GOAL := help

.PHONY: help install up down test lint inject investigate eval clean

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create the Python 3.12 venv and install runtime + dev dependencies
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	@mkdir -p data
	@echo "Installed. Activate with: source $(VENV)/bin/activate"

up: ## Build and start the stack (api, postgres, redis, prometheus, otel-collector)
	$(COMPOSE) up -d --build

down: ## Stop the stack (volumes are preserved)
	$(COMPOSE) down --remove-orphans

test: ## Run the pytest suite with coverage
	$(PY) -m pytest --cov=opspilot --cov-report=term-missing

lint: ## Static checks: ruff lint, ruff format check, mypy
	$(RUFF) check src tests
	$(RUFF) format --check src tests
	$(MYPY) src

inject: ## Inject a simulated incident (make inject SCENARIO=bad_deployment)
	$(PY) -m opspilot.cli inject --scenario $(SCENARIO)

investigate: ## Run the agent investigation loop against open incidents
	$(PY) -m opspilot.cli investigate

eval: ## Run the evaluation suite
	$(PY) -m opspilot.cli eval

clean: ## Remove caches and build artifacts (keeps .venv and local data)
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov dist build
	find . -path "./$(VENV)" -prune -o -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
