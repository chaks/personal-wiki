# Deployment Guide

Comprehensive guide for deploying the Personal Wiki Chat application in local development, production, and cloud environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Environment Variables](#environment-variables)
5. [Cloud Deployment](#cloud-deployment)
6. [Security Considerations](#security-considerations)
7. [Monitoring](#monitoring)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum Version | Purpose |
|---|---|---|
| Python | 3.12+ | Application runtime |
| Docker | Latest | Qdrant container |
| Ollama | Latest | Local LLM (generation + embeddings) |
| Git | Latest | Source control |

Verify prerequisites:

```bash
python --version        # Python 3.12+
docker --version
ollama --version
git --version
```

---

## Local Development

### Step-by-step Setup

1. **Clone the repository**

```bash
git clone <repository-url>
cd personal-wiki
```

2. **Create a virtual environment and install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Pull Ollama models**

```bash
ollama pull gemma4:e2b       # Entity/concept extraction + LLM generation
ollama pull nomic-embed-text  # Semantic embeddings
```

4. **Start Qdrant**

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

5. **Configure your sources**

Edit `config/sources.yaml` to specify documents, URLs, or code repositories to ingest:

```yaml
sources:
  - type: pdf
    path: sources/pdfs/my-document.pdf
    tags: [research]

  - type: url
    url: https://example.com/article
    tags: [reference]

  - type: markdown
    path: sources/notes/meeting.md
    tags: [meetings]

  - type: code
    path: sources/code/my-project
    language: python
    tags: [codebase]
```

6. **Run ingestion**

```bash
python -m src.ingest
```

This converts documents to markdown, extracts entities and concepts, creates wiki pages, and indexes everything in Qdrant.

7. **Start the server**

```bash
python -m src --host 0.0.0.0 --port 8000
```

Or with debug logging:

```bash
python -m src --host 0.0.0.0 --port 8000 --log-level DEBUG
```

8. **Open the chat UI**

Navigate to [http://localhost:8000](http://localhost:8000).

### Optional: Run wiki lint checks

```bash
python -m src --lint
```

---

## Production Deployment

### Docker Compose

A `docker-compose.yml` file orchestrates the full stack: Ollama, Qdrant, and the application.

Create `docker-compose.yml`:

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_storage:/root/.ollama
    restart: unless-stopped

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_BASE_URL=http://ollama:11434
      - WIKI_API_KEYS=${WIKI_API_KEYS}
    volumes:
      - ./wiki:/app/wiki
      - ./state:/app/state
      - ./logs:/app/logs
      - ./sources:/app/sources
      - ./config:/app/config
    depends_on:
      qdrant:
        condition: service_healthy
      ollama:
        condition: service_started
    restart: unless-stopped

volumes:
  qdrant_storage:
  ollama_storage:
```

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p wiki generated entities concepts state logs sources config

EXPOSE 8000

# Pre-pull models are expected to be available via the Ollama service.
# If running Ollama in a separate container, models must be pulled separately.

CMD ["python", "-m", "src", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker compose up --build -d
```

Pull models into the Ollama container after starting:

```bash
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull nomic-embed-text
```

Run ingestion:

```bash
docker compose exec app python -m src.ingest
```

### Production Considerations

- **Reverse proxy**: Place nginx or Traefik in front of the app for TLS termination.
- **Resource limits**: Add `deploy.resources` to `docker-compose.yml` to cap memory/CPU.
- **Persistent volumes**: Ensure `qdrant_storage`, `ollama_storage`, and mounted directories are backed up.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `WIKI_API_KEYS` | *(none)* | Comma-separated API keys for authentication. When set, all requests require the `X-API-Key` header (except `/health`, `/docs`, `/openapi.json`). Generate with: `python -c "from src.auth import generate_api_key; print(generate_api_key())"` |
| `WIKI_DIR` | `./wiki` | Path to wiki content directory |
| `STATE_DIR` | `./state` | Path to state directory |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Cloud Deployment

### AWS

**Option 1: ECS (Fargate)**

```yaml
# docker-compose.yml (use with ECS CLI)
version: "3"
services:
  qdrant:
    image: qdrant/qdrant:latest
    memory_reservation: 512
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

  ollama:
    image: ollama/ollama:latest
    memory_reservation: 2048
    ports:
      - "11434:11434"
    volumes:
      - ollama_storage:/root/.ollama

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - qdrant
      - ollama
```

Deploy with ECS CLI or convert to CloudFormation/Terraform. Use ElastiCache (Redis) if you later need a managed cache layer.

**Option 2: EC2**

Launch a t3.medium (or larger) instance with an Amazon Linux 2 AMI. Install Docker and Docker Compose, copy project files, and run `docker compose up -d`. Use a security group to allow ports 80 and 443 from the internet, and port 22 for SSH only.

**Option 3: App Runner**

Build and push the Docker image to ECR, then create an App Runner service. Note: Ollama requires GPU or significant CPU for reasonable response times; consider running Ollama on a separate EC2 instance or using a cloud LLM API instead.

### GCP

**Cloud Run**

Build and deploy:

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/personal-wiki
gcloud run deploy personal-wiki \
  --image gcr.io/PROJECT_ID/personal-wiki \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2
```

For Ollama, use a separate Cloud Run service with GPU acceleration, or run it on a Compute Engine instance. Point `OLLAMA_BASE_URL` to the Ollama service URL.

**GKE**

For Kubernetes-based deployment, create a `k8s/` directory with Deployments and Services for each component (Qdrant, Ollama, app), plus PersistentVolumeClaims for data.

### Azure

**Container Instances**

```bash
az container create \
  --resource-group myResourceGroup \
  --name personal-wiki \
  --image <acr-login-server>/personal-wiki:latest \
  --dns-name-label personal-wiki \
  --ports 8000 \
  --cpu 2 \
  --memory 4
```

Use Azure Container Registry (ACR) to store images. For Qdrant, use Azure Container Instances with a volume mount to Azure Files. For Ollama, use a VM or AKS node with GPU support.

---

## Security Considerations

### API Key Authentication

Enable authentication by setting `WIKI_API_KEYS`:

```bash
export WIKI_API_KEYS="$(python -c 'from src.auth import generate_api_key; print(generate_api_key())'),$(python -c 'from src.auth import generate_api_key; print(generate_api_key())')"
```

The middleware checks the `X-API-Key` header on all requests except `/health`, `/docs`, and `/openapi.json`. Generate keys with:

```python
from src.auth import generate_api_key
print(generate_api_key())  # 64-character hex string
```

### CORS Configuration

The default CORS policy restricts origins to `localhost:3000` and `localhost:8000`. For production, update `src/server.py` to allow only your domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)
```

### Rate Limiting

Built-in rate limiting is enabled by default at 10 requests per 60 seconds per IP. This is configured in `src/server.py` via `RateLimitMiddleware`. Adjust the values if needed:

```python
app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)
```

The middleware respects `X-Forwarded-For` headers when behind a reverse proxy.

### HTTPS / TLS

Never expose the application directly to the internet. Always use a reverse proxy (nginx, Traefik, or cloud load balancer) for TLS termination:

**nginx example:**

```nginx
server {
    listen 443 ssl http2;
    server_name wiki.example.com;

    ssl_certificate /etc/letsencrypt/live/wiki.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wiki.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;  # Required for SSE streaming
    }
}
```

### Prompt Injection Protection

User messages are sanitized with `html.escape()` before inclusion in LLM prompts. Do not remove this sanitization.

---

## Monitoring

### Health Checks

The `/health` endpoint reports the status of all dependencies:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "ollama": "healthy",
  "qdrant": "healthy",
  "is_healthy": true,
  "ollama_error": null,
  "qdrant_error": null
}
```

Use this endpoint for:

- Load balancer health checks
- Docker `healthcheck` directives
- Kubernetes liveness/readiness probes

### Logging

Logs are written to both `logs/personal-wiki.log` (rotating, 10MB max) and stdout. Configure the level via `--log-level` or the `LOG_LEVEL` environment variable.

Key log messages to monitor:

- `"Starting Personal Wiki Chat server on ..."` - Server startup
- `"Search completed in X.XXXs, found N pages"` - Search performance
- `"Streamed N chunks"` - LLM response sizes
- `"Rate limit exceeded"` - Potential abuse

### Metrics to Track

For production observability, track:

| Metric | Source | Alert Threshold |
|---|---|---|
| Response time (p95) | `/chat` endpoint logs | > 30s |
| Search latency | Search duration logs | > 5s |
| Error rate | Log analysis of ERROR/WARNING | > 1% of requests |
| Qdrant availability | `/health` endpoint | Any unhealthy |
| Ollama availability | `/health` endpoint | Any unhealthy |

Consider integrating Prometheus and Grafana, or a cloud-native monitoring solution (CloudWatch, Stackdriver, Application Insights).

---

## Backup and Recovery

### What to Back Up

| Component | Path / Data | Backup Method |
|---|---|---|
| Qdrant vectors | `/qdrant/storage` (Docker volume) | `qdrant snapshot` API |
| Wiki content | `wiki/` directory | File copy / rsync |
| State (registry, history) | `state/` directory | File copy / rsync |
| Sources | `sources/` directory | File copy / rsync |
| Configuration | `config/` directory | File copy / rsync |
| Ollama models | `/root/.ollama` (Docker volume) | Recreate via `ollama pull` |

### Qdrant Backup

Create a snapshot:

```bash
curl -X POST http://localhost:6333/snapshots/create
```

This returns a snapshot file in the `snapshots/` directory inside the Qdrant container. Copy it out:

```bash
docker cp qdrant:/qdrant/snapshots/ <local-backup-path>/
```

Restore from snapshot:

```bash
docker cp <snapshot-path>/your_snapshot qdrant:/qdrant/snapshots/
curl -X POST "http://localhost:6333/snapshots/restore/your_snapshot"
```

### File-based Backup

For wiki content, state, and configuration:

```bash
# Backup
tar czf wiki-backup-$(date +%Y%m%d).tar.gz wiki/ state/ config/ sources/

# Restore
tar xzf wiki-backup-YYYYMMDD.tar.gz -C /path/to/personal-wiki/
```

Schedule regular backups using cron:

```cron
0 2 * * * cd /path/to/personal-wiki && tar czf /backups/wiki-$(date +\%Y\%m\%d).tar.gz wiki/ state/ config/
```

---

## Troubleshooting

### Ollama

**Problem: "Connection refused" or "Ollama not responding"**

- Ensure Ollama is running: `ollama list`
- Check the base URL. Default is `http://localhost:11434`. If running in Docker Compose, use `http://ollama:11434`.
- Verify the models are pulled: `ollama list` should show `gemma4:e2b` and `nomic-embed-text`.

**Problem: Slow LLM responses**

- Ollama runs on CPU by default. For better performance, ensure GPU support (CUDA or Metal).
- On macOS, Ollama uses Metal automatically.
- On Linux, install CUDA drivers and ensure `CUDA_VISIBLE_DEVICES` is set.
- Consider using a smaller model if latency is critical.

**Problem: OOM errors during extraction**

- The `gemma4:e2b` model requires ~4GB of RAM. Ensure the host or container has sufficient memory.
- In Docker Compose, increase memory limits for the Ollama service.

### Qdrant

**Problem: "Connection refused" on port 6333**

- Ensure Qdrant is running: `docker ps | grep qdrant`
- Check the port: `curl http://localhost:6333/healthz`
- If running in Docker Compose, verify the service name matches `QDRANT_URL` (e.g., `http://qdrant:6333`).

**Problem: Missing collections or empty search results**

- Run ingestion again: `python -m src.ingest`
- Verify collections exist: `curl http://localhost:6333/collections`

**Problem: High memory usage**

- Qdrant loads all vectors into RAM. Large wikis may require more memory.
- Increase the Docker memory limit or adjust Qdrant's `optimizers.memmap_threshold` in its configuration.

### Application

**Problem: Server fails to start**

- Check Python version: `python --version` (requires 3.12+)
- Verify dependencies: `pip install -r requirements.txt`
- Check logs: `cat logs/personal-wiki.log`

**Problem: Slow ingestion**

- Ingestion involves LLM calls for each document. Large PDFs or many sources will take time.
- The change detection mechanism skips unchanged sources. If ingestion is slow on every run, check that content hashes are being recorded in `state/`.
- Consider running ingestion during off-peak hours or on a schedule.

**Problem: API key authentication not working**

- Verify `WIKI_API_KEYS` is set: `echo $WIKI_API_KEYS`
- Use the exact key in the header: `curl -H "X-API-Key: your-key" http://localhost:8000/chat`
- The `/health` endpoint is excluded from auth by design.

**Problem: CORS errors in the browser**

- Ensure the frontend origin is in the `allow_origins` list in `src/server.py`.
- For custom domains, update the CORS configuration before deploying.
