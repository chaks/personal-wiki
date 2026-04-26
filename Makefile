PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
PYTHON_VERSION := 3.12

QDRANT_PORT := 6333
OLLAMA_PORT := 11434

TSPIN := $(shell command -v tspin 2>/dev/null)
LOG_VIEWER := $(if $(TSPIN),| $(TSPIN),)

.PHONY: help setup install run run-dev ingest lint-wiki test test-cov clean \
        qdrant-start qdrant-stop qdrant-status qdrant-logs \
        qdrant-backup qdrant-restore qdrant-create-collection qdrant-wipe \
        ollama-pull health

help:  ## List all commands
	@grep -E '^[a-zA-Z_-]+:.*##' Makefile | sort | awk -F'##' '{printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────────

setup:  ## Create venv and install dependencies
	python$(PYTHON_VERSION) -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: setup

# ── App ──────────────────────────────────────────────────────────────────────

run:  ## Start the FastAPI server
	$(PYTHON) -m src --host $(or $(HOST),0.0.0.0) --port $(or $(PORT),8000) --log-level $(or $(LOG_LEVEL),info) 2>&1 $(LOG_VIEWER)

run-dev:  ## Start the server (debug log level)
	$(PYTHON) -m src --host $(or $(HOST),0.0.0.0) --port $(or $(PORT),8000) --log-level DEBUG 2>&1 $(LOG_VIEWER)

ingest:  ## Run the document ingestion pipeline
	$(PYTHON) -m src.ingest 2>&1 $(LOG_VIEWER)

lint-wiki:  ## Check wiki pages for broken links and orphans
	$(PYTHON) -m src --lint

health:  ## Check health of all services
	@curl -sf http://localhost:$(QDRANT_PORT)/healthz && echo "  Qdrant OK" || echo "  Qdrant DOWN"
	@curl -sf http://localhost:$(OLLAMA_PORT) && echo "  Ollama OK" || echo "  Ollama DOWN"
	@curl -sf http://localhost:8000/health && echo "  App OK" || echo "  App DOWN"

# ── Qdrant ───────────────────────────────────────────────────────────────────

qdrant-start:  ## Start Qdrant in Docker
	docker run -d \
		--name qdrant \
		-p $(QDRANT_PORT):6333 \
		-v qdrant_storage:/qdrant/storage \
		qdrant/qdrant:latest

qdrant-stop:  ## Stop Qdrant container
	-docker stop qdrant

qdrant-status:  ## Check Qdrant container status
	@docker ps --filter name=qdrant --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

qdrant-logs:  ## Tail Qdrant logs
	docker logs -f qdrant 2>&1 $(LOG_VIEWER)

qdrant-backup:  ## Create a Qdrant snapshot backup (pass SNAP_DIR=/path/to/backup)
	@docker exec qdrant mkdir -p /qdrant/snapshots
	@docker cp qdrant:/qdrant/snapshots/ $(or $(SNAP_DIR),./backups/qdrant-snapshots)
	@echo "Snapshot saved to $(or $(SNAP_DIR),./backups/qdrant-snapshots)"

qdrant-restore:  ## Restore Qdrant from snapshot (pass SNAP_PATH=/path/to/snapshot)
	@docker cp $(SNAP_PATH) qdrant:/qdrant/snapshots/
	@curl -X POST "http://localhost:$(QDRANT_PORT)/snapshots/restore/$(notdir $(SNAP_PATH))"

qdrant-create-collection:  ## Create the personal_wiki collection in Qdrant
	@curl -sf http://localhost:$(QDRANT_PORT)/collections/personal_wiki > /dev/null 2>&1 \
		&& echo "Collection personal_wiki already exists" \
		|| curl -sX PUT "http://localhost:$(QDRANT_PORT)/collections/personal_wiki" \
			-H 'Content-Type: application/json' \
			-d '{"vectors":{"size":768,"distance":"Cosine"}}' \
		&& echo "Collection created"

qdrant-wipe:  ## Destroy Qdrant container and all stored vectors
	-docker stop qdrant
	-docker rm qdrant
	-docker volume rm qdrant_storage

# ── Ollama ───────────────────────────────────────────────────────────────────

ollama-pull:  ## Pull required Ollama models
	ollama pull gemma4:e2b
	ollama pull nomic-embed-text

# ── Testing ──────────────────────────────────────────────────────────────────

test:  ## Run tests
	$(PYTEST) tests/ -v

test-cov:  ## Run tests with coverage
	$(PYTEST) tests/ -v --cov=src --cov-report=term-missing

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean:  ## Remove venv, caches, and generated files
	rm -rf .venv
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf wiki/ state/ logs/
