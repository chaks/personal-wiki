# Personal Wiki Chat

A local AI-powered chat assistant that queries a persistent knowledge wiki built from your documents, code, and notes. Everything runs offline via Ollama — no external API keys required.

## Features

- **Document Ingestion**: Convert PDFs, URLs, markdown, and code repositories to markdown via Docling
- **LLM Entity Extraction**: Automatic extraction of entities and concepts using gemma4:e2b
- **Wiki Generation**: Creates structured wiki pages in `wiki/entities/`, `wiki/concepts/`, and `wiki/generated/`
- **Semantic Search**: Qdrant vector index with chunk-level deduplication for intelligent retrieval
- **Local LLM**: Runs entirely offline with Ollama (gemma4:e2b for extraction/chat, nomic-embed-text for embeddings)
- **Change Detection**: SHA256 content-hash tracking skips unchanged sources
- **Source Management**: REST API and web UI for CRUD operations on data sources
- **Wiki Browsing**: Web UI to browse and explore generated wiki pages
- **Chat History**: SQLite-backed persistence for conversation sessions
- **Markdown Rendering**: Rich markdown (headings, bold, tables, code blocks) in chat responses
- **Async Pipeline**: Full async vector store, indexer, and LLM layers with sync wrappers
- **Wiki Maintenance**: LLM-generated markdown with entities, concepts, and cross-links
- **Wiki Lint**: Checks for broken links, duplicates, and stale claims
- **Security**: API key authentication, rate limiting, path validation, prompt injection protection
- **Health Checks**: Centralized service health endpoint (Ollama + Qdrant + App)

## Architecture

![Architecture](https://raw.githubusercontent.com/chaks/personal-wiki/gh-pages/diagrams/architecture.png)

[View interactive diagram with animations →](https://chaks.github.io/personal-wiki/diagrams/architecture.html)

### Wiki Structure

The ingestion pipeline creates three types of pages:

- `wiki/generated/` — Raw document summaries (from Docling)
- `wiki/entities/` — Extracted entities (people, organizations, products, technologies)
- `wiki/concepts/` — Extracted concepts (theories, patterns, methodologies)

### Service Layers

- `src/services/` — Provider abstractions: `LLMProvider`, `EmbeddingProvider`, `VectorStore`, pipeline stages
- `src/ingestion/` — `SourceAdapter` ABC with concrete adapters (`PDFSourceAdapter`, `URLSourceAdapter`, `CodeSourceAdapter`, `MarkdownCopyAdapter`) wired to shared pipeline stages
- `src/routes/` — REST API routes (source management, wiki browsing)
- `src/lint_checks/` — Wiki quality checks (broken links, duplicates, stale claims)
- `src/security/` — Path validation utilities
- `src/factories.py` — Default pipeline stage factory
- `src/catalog.py` — Source catalog
- `src/prompt.py` — Unified `build_rag_prompt()` for RAG prompt construction

### Ingestion Pipeline

Each source adapter implements `first_stage()` to return a type-specific initial stage, then shares the post-processing stages:

```
first_stage() → Extract → Write → Resolve → Index
```

- **PDF/Markdown** → `ConvertStage` (Docling)
- **URLs** → `URLFetchStage` (httpx fetch + Docling HTML conversion)
- **Code repos** → `CodeGenerateStage` (AST docstring extraction + source wrapping)

Pipeline execution is driven by `SourceAdapter.run()` in `src/ingest.py` via `run_source()`, which accepts a `Reporter` for status output (`FileReporter` for CLI, `NullReporter` for tests).

## Quick Start

### Prerequisites

- Python 3.12+
- Ollama installed (`brew install ollama` or see [ollama.ai](https://ollama.ai))
- Qdrant running (`docker run -p 6333:6333 qdrant/qdrant`)

### Setup

```bash
make setup          # Create venv and install dependencies
```

Or manually:

```bash
pip install -r requirements.txt
```

### Models & Services

```bash
make ollama-pull    # Pull required Ollama models
make qdrant-start   # Start Qdrant in Docker
```

### Run the Server

```bash
make run            # Start the FastAPI server
# or
make run-dev        # Start with debug logging
```

Open http://localhost:8000 for the chat UI, http://localhost:8000/manage for source management,
and http://localhost:8000/browse for wiki browsing.

## Usage

### Adding Sources

Edit `config/sources.yaml`:

```yaml
sources:
  - type: pdf
    path: sources/pdfs/my-document.pdf
    tags: [research, ai]

  - type: url
    url: https://example.com/article
    tags: [reference]

  - type: markdown
    path: sources/notes/meeting.md
    tags: [meetings]

  - type: markdown
    path: sources/markdown/essay-on-distributed-systems.md
    full_pipeline: true    # Run LLM extraction (not just copy+index)
    tags: [distributed-systems]

  - type: code
    path: sources/code/my-project
    language: python
    tags: [codebase]
```

The `full_pipeline` flag controls whether markdown files go through the full LLM extraction (entity/concept extraction,
wiki page creation) or are simply copied and indexed.

### Running Ingestion

```bash
make ingest    # Process configured sources
```

This will:

1. Convert PDFs to markdown via Docling, ingest URLs and code repositories
2. Extract entities and concepts using gemma4:e2b (for full_pipeline sources)
3. Create wiki pages in `wiki/entities/` and `wiki/concepts/`
4. Index all pages in Qdrant for semantic search

### Web UI Pages

| Page   | URL                          | Description                       |
|--------|------------------------------|-----------------------------------|
| Chat   | http://localhost:8000/       | Ask questions against your wiki   |
| Manage | http://localhost:8000/manage | Add, edit, enable/disable sources |
| Browse | http://localhost:8000/browse | Browse and explore wiki pages     |

### API Endpoints

| Method   | Endpoint                 | Description                    |
|----------|--------------------------|--------------------------------|
| `GET`    | `/health`                | Service health check           |
| `POST`   | `/chat`                  | Chat with wiki (SSE streaming)     |
| `GET`    | `/api/sources`           | List all sources               |
| `POST`   | `/api/sources`           | Add a new source               |
| `PUT`    | `/api/sources/{id}`      | Update a source                |
| `DELETE` | `/api/sources/{id}`      | Delete a source                |
| `GET`    | `/api/wiki/pages`        | List wiki pages                |
| `GET`    | `/api/wiki/pages/{path}` | Get a wiki page                |

### Wiki Health Check

```bash
make lint-wiki    # Check for broken links, orphans, duplicates, etc.
```

### Directory Structure

```
personal-wiki/
├── sources/              # Raw input documents (immutable)
├── wiki/                 # LLM-maintained markdown
├── state/                # Registry and change-tracking state
├── static/               # Chat UI files
├── src/                  # Python source code
│   ├── services/         # LLMProvider, EmbeddingProvider, VectorStore, pipeline stages
│   ├── ingestion/        # SourceAdapter ABC + concrete adapters
│   ├── routes/           # REST API routes (sources, wiki browsing)
│   ├── lint_checks/      # Wiki quality checks (broken links, duplicates, stale claims)
│   ├── security/         # Path validation utilities
│   ├── factories.py      # Default pipeline stage factory
│   ├── catalog.py        # Source catalog
│   ├── ingest.py         # Ingestion CLI (SourceSpec, Reporter, run_source_async)
│   ├── prompt.py         # Unified RAG prompt builder
│   ├── chat.py           # ChatEngine with wiki retrieval
│   ├── history.py        # SQLite-backed chat history
│   ├── indexer.py        # Qdrant-based semantic indexing
│   ├── registry.py       # Source registry with SHA256 change detection
│   └── server.py         # FastAPI app factory (create_app)
├── config/               # Configuration
├── Makefile              # Development commands
└── tests/                # Test suite
```

## Testing

```bash
make test         # Run tests
make test-cov     # Run tests with coverage
```

## Deployment

For comprehensive deployment instructions covering local development, production, cloud providers (AWS/GCP/Azure),
security, monitoring, and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

**Quick production deploy with Docker Compose:**

```bash
docker compose up --build -d
```

## Makefile Reference

| Command                              | Description                          |
|--------------------------------------|--------------------------------------|
| `make setup`                         | Create venv and install dependencies |
| `make run`                           | Start the server                     |
| `make run-dev`                       | Start with debug logging             |
| `make ingest`                        | Run document ingestion pipeline      |
| `make lint-wiki`                     | Check wiki pages for issues          |
| `make health`                        | Check all service health             |
| `make qdrant-start/stop/status/logs` | Manage Qdrant container              |
| `make qdrant-backup`                 | Create Qdrant snapshot backup        |
| `make qdrant-restore`                | Restore Qdrant from snapshot         |
| `make qdrant-wipe`                   | Destroy Qdrant container and data    |
| `make ollama-pull`                   | Pull required Ollama models          |
| `make test` / `make test-cov`        | Run tests                            |
| `make clean`                         | Remove venv, caches, generated files |

## Acknowledgments

This project is inspired by Andrej
Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — an incremental,
persistent knowledge base where LLMs handle bookkeeping and humans curate.

## License

MIT
