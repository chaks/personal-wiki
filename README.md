# Personal Wiki Chat

A local AI-powered chat assistant that queries a persistent knowledge wiki.

## Features

- **Document Ingestion**: Convert PDFs, URLs, markdown, and code to markdown via Docling
- **LLM Entity Extraction**: Automatic extraction of entities and concepts using gemma4:e2b
- **Wiki Generation**: Creates structured wiki pages in `wiki/entities/` and `wiki/concepts/`
- **Semantic Search**: Qdrant vector index for intelligent query retrieval
- **Local LLM**: Runs entirely offline with Ollama (gemma4:e2b for extraction, nomic-embed-text for embeddings)
- **Change Detection**: Content-hash based tracking skips unchanged sources
- **Wiki Maintenance**: LLM-generated markdown with entities, concepts, and links
- **Health Checks**: Wiki linter detects orphan pages and other issues

## Architecture

```
sources/ → Docling → wiki/ → Qdrant → Chat UI
              ↓          ↑
          gemma4:e2b    Ollama (embeddings + generation)
          extraction
```

### Wiki Structure

The ingestion pipeline creates three types of pages:
- `wiki/generated/` - Raw document summaries (from Docling)
- `wiki/entities/` - Extracted entities (people, organizations, products, technologies)
- `wiki/concepts/` - Extracted concepts (theories, patterns, methodologies)

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama installed (`brew install ollama` or see [ollama.ai](https://ollama.ai))
- Qdrant running (`docker run -p 6333:6333 qdrant/qdrant`)

### Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Pull Ollama models:**

```bash
ollama pull gemma4:e2b      # For entity/concept extraction
ollama pull nomic-embed-text  # For semantic embeddings
```

3. **Start Qdrant:**

```bash
docker run -p 6333:6333 qdrant/qdrant
```

4. **Run the server:**

```bash
python -m src --host 0.0.0.0 --port 8000
```

5. **Open chat UI:** http://localhost:8000

## Logging

Logs are written to `logs/personal-wiki.log` (rotating, 10MB max) and stdout.

**Enable debug logs:**

```bash
python -m src --log-level DEBUG
```

Valid log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

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
```

### Running Ingestion

Process configured sources and extract entities/concepts:

```bash
python -m src.ingest
```

This will:
1. Convert PDFs to markdown via Docling
2. Extract entities and concepts using gemma4:e2b
3. Create wiki pages in `wiki/entities/` and `wiki/concepts/`
4. Index all pages in Qdrant for semantic search

### Wiki Health Check

Run the wiki linter to find orphan pages and other issues:

```bash
python -m src --lint
```

### Directory Structure

```
personal-wiki/
├── sources/          # Raw input documents (immutable)
├── wiki/             # LLM-maintained markdown
├── state/            # Registry and state
├── static/           # Chat UI files
├── src/              # Python source code
└── config/           # Configuration
```

## API

- `GET /health` - Health check
- `POST /chat` - Chat endpoint (SSE streaming)
- `GET /` - Serve chat UI

## Deployment

For comprehensive deployment instructions covering local development, production, cloud providers (AWS/GCP/Azure), security, monitoring, and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

**Quick production deploy with Docker Compose:**

```bash
docker compose up --build -d
```

## Testing

```bash
pytest tests/ -v
```

## Acknowledgments

This project is inspired by Andrej Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — an incremental, persistent knowledge base where LLMs handle bookkeeping and humans curate.

## License

MIT
