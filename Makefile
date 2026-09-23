PYTHON ?= python3.12
VENV   ?= .venv
BIN    := $(VENV)/bin
PIP    := $(BIN)/pip
PY     := $(BIN)/python
COMPOSE ?= docker compose
BASE_URL ?= http://localhost:8000

.DEFAULT_GOAL := help

.PHONY: help install up down test lint inject investigate eval clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install package + dev dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

up: ## Build and start the Docker Compose stack
	$(COMPOSE) up -d --build

down: ## Stop the Docker Compose stack
	$(COMPOSE) down

test: ## Run the test suite
	$(BIN)/pytest

lint: ## Run ruff lint + format check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

inject: ## Inject a scenario, e.g. make inject SCENARIO=bad_deployment
	@test -n "$(SCENARIO)" || (echo "Usage: make inject SCENARIO=<name>" >&2; exit 1)
	curl -fsS -X POST "$(BASE_URL)/api/v1/scenarios/inject" \
		-H 'Content-Type: application/json' \
		-d '{"scenario": "$(SCENARIO)"}'
	@echo

investigate: ## Trigger an investigation of open incidents
	curl -fsS -X POST "$(BASE_URL)/api/v1/incidents/investigate" \
		-H 'Content-Type: application/json' -d '{}'
	@echo

eval: ## Run the evaluation harness
	$(PY) -m ops_pilot.evals

clean: ## Remove local artifacts and tear down containers/volumes
	rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	-$(COMPOSE) down -v --remove-orphans
