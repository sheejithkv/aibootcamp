# Feature 12: Ship It

**Week 4 · Final Feature** — Package your AI assistant as a production-ready container and wire up a CI/CD quality gate.

You've built eleven features. This is where you ship them.

---

## What You'll Build

| Artifact | What it does |
|---|---|
| `Dockerfile` | Multi-stage build — installs packages in a builder stage, copies only the venv to the runtime image, runs as a non-root user |
| `docker-compose.yml` | Defines ports, named volumes for the vector DB and uploads, health check, and `env_file` for secret injection |
| `.dockerignore` | Keeps `.env` secrets, `__pycache__`, and `.venv` out of the image build context |
| `.github/workflows/eval.yml` | GitHub Actions CI: smoke tests on every push, eval quality gate when `GROQ_API_KEY` is set |

No new API endpoints. The infrastructure *is* the feature.

---

## New Concepts

### Multi-stage Docker builds

```
Stage 1 (builder): python:3.12-slim
  → pip install -r requirements.txt → /opt/venv

Stage 2 (runtime): python:3.12-slim (fresh)
  → COPY --from=builder /opt/venv /opt/venv
  → COPY app code
  → USER appuser  ← non-root
  → CMD uvicorn
```

The final image has no pip, no gcc, no build cache — only the installed packages and your code. Smaller = faster to pull, smaller attack surface.

### Named Docker volumes

Without named volumes, every `docker compose down` deletes your entire vector database and all uploaded files.

```yaml
volumes:
  - chroma_data:/data/chroma    # Chroma vector DB (document embeddings)
  - uploads_data:/data/uploads  # raw uploaded files
```

Named volumes survive container restarts, updates, and rebuilds. Only `docker compose down -v` removes them.

### Non-root container user

Running as root inside a container means if your app is exploited, the attacker has root access inside the container — they can read environment variables, write to the filesystem, and potentially escape.

```dockerfile
RUN useradd --create-home appuser && chown -R appuser /app /data
USER appuser
```

This is a security best practice required by most production platforms (AWS App Runner, GCP Cloud Run, Azure Container Apps all enforce it).

### GitHub Actions eval quality gate

```yaml
- name: Eval quality gate (pass rate ≥ 70%)
  if: env.GROQ_API_KEY != ''
  run: python week-4-launch/feature-12-ship-it/tests/run_eval_ci.py
```

The `if:` condition means Ollama users get green CI from smoke tests alone. Add a free Groq key as a GitHub secret to unlock the full eval gate.

### What you built → real-world equivalent

| What you built | Real-world equivalent |
|---|---|
| Multi-stage Dockerfile | Standard production Python container pattern |
| `docker-compose.yml` volumes | AWS EFS / GCP Persistent Disk / Azure File Share |
| `.dockerignore` | `.gitignore` equivalent for the container build context |
| GitHub Actions eval gate | CircleCI / GitLab CI eval quality step |
| `USER appuser` | CIS Docker Benchmark — principle of least privilege |
| `VECTOR_DB_PATH` env override | Twelve-Factor App config (env vars over hardcoded paths) |

---

## Your Task

Open `starter/Dockerfile` and fill in the three TODOs:

**TODO 1 — Base image**

```dockerfile
# Replace ??? with the correct image name.
FROM ??? AS builder
# Answer: python:3.12-slim
```

**TODO 2 — Non-root user**

```dockerfile
# Create appuser, give them ownership of /app and /data, then switch.
RUN useradd --create-home appuser && chown -R appuser /app /data
USER appuser
```

**TODO 3 — Start command**

```dockerfile
# Start uvicorn on host 0.0.0.0, port 8000, 1 worker.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

Open `starter/docker-compose.yml` and fill in the three TODOs:

**TODO 1 — Port mapping**

```yaml
ports:
  - "8000:8000"
```

**TODO 2 — Named volumes**

```yaml
volumes:
  - chroma_data:/data/chroma
  - uploads_data:/data/uploads
```

**TODO 3 — Healthcheck**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 20s
```

---

## Run It

```bash
cd week-4-launch/feature-12-ship-it/

# First run — builds the image (takes ~2 min on first run, seconds after)
docker compose up --build

# Subsequent runs — reuses cached image
docker compose up

# Tail logs
docker compose logs -f

# Stop and remove containers (data is preserved in named volumes)
docker compose down

# Nuclear option — also removes all data
docker compose down -v
```

Open **http://localhost:8000** — the same AI assistant, now running in a container.

---

## CI/CD Setup (GitHub Actions)

The workflow at `.github/workflows/eval.yml` runs automatically on every push and pull request to `main`.

**To enable the eval quality gate:**

1. Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret
2. Name: `GROQ_API_KEY`, Value: your Groq key (free at console.groq.com)
3. Push a commit — the eval gate runs automatically

**Without a Groq key:** Smoke tests still run and pass. The eval step is skipped gracefully.

---

## Final Project

**You've shipped a complete AI engineering product.** Here's what you built across 12 features:

```
Week 1 — Brain:      chat → structured output → session memory
Week 2 — Knowledge:  document ingestion → semantic search → smart routing
Week 3 — Hands:      ReAct agent → plan-and-execute → MCP integration
Week 4 — Launch:     voice + vision → observability + evals → containerised CI/CD
```

For cloud deployment options (Railway, Render, AWS App Runner, GCP Cloud Run, Azure Container Apps), see:

- **`resource/deployment-runbook.md`** — step-by-step commands for each platform
- **`docs/cloud-deployment-guide.md`** — platform comparison and decision guide
