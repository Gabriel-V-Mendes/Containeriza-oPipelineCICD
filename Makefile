# Atalhos do dia a dia. Rode `make` para ver a lista.
.DEFAULT_GOAL := help
SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
IMAGE ?= devops-api:local

.PHONY: help up down logs ps venv lint fmt test smoke scan secrets nonroot protect-main

help: ## Lista os comandos
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Sobe API + Postgres (um comando) e espera ficarem saudáveis
	docker compose up -d --build --wait

down: ## Derruba tudo (mantém o volume do banco)
	docker compose down

logs: ## Acompanha os logs
	docker compose logs -f

ps: ## Status dos containers (inclui health)
	docker compose ps

$(PY): requirements-dev.txt
	python3 -m venv $(VENV)
	$(PY) -m pip install -q -r requirements-dev.txt
	@touch $(PY)

venv: $(PY) ## Cria o virtualenv local com as dependências de dev

lint: $(PY) ## Ruff + hadolint
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
	docker run --rm -i hadolint/hadolint:v2.15.1 < Dockerfile

fmt: $(PY) ## Formata o código
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

test: $(PY) ## Testes (SQLite em memória; defina DATABASE_URL para usar Postgres)
	$(VENV)/bin/pytest --cov

smoke: ## Testa a API rodando (após `make up`)
	curl -fsS http://127.0.0.1:8000/health && echo
	curl -fsS http://127.0.0.1:8000/health/ready && echo

nonroot: ## Prova que a imagem roda sem root
	@echo "USER: $$(docker image inspect -f '{{.Config.User}}' $(IMAGE))  UID: $$(docker run --rm --entrypoint id $(IMAGE) -u)"

scan: ## Trivy na imagem local (mesmo critério do CI)
	trivy image --scanners vuln --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 $(IMAGE)

secrets: ## Gitleaks em todo o histórico + arquivos não commitados
	gitleaks git . --redact --verbose
	gitleaks dir . --redact --verbose

protect-main: ## Aplica branch protection na main (exige gh autenticado)
	./scripts/protect-main.sh
