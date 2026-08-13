# Deployment Runbook — Feature 12: Ship It

Step-by-step commands for deploying your AI assistant to production.
Keep this file. You'll reference it every time you deploy.

---

## 1. Local Docker (verify before deploying)

Always confirm your image builds and runs locally before pushing to a cloud platform.

```bash
cd week-4-launch/feature-12-ship-it/

# Build and start
docker compose up --build

# Verify it's running
curl http://localhost:8000/api/health

# Tail logs
docker compose logs -f app

# Stop (data preserved in named volumes)
docker compose down
```

**Expected health response:**
```json
{"status": "ok", "version": "12.0.0", "provider": "groq", "metrics": {...}}
```

If health returns an error, check the logs: `docker compose logs app`.

---

## 2. Cloud Platform Landscape

| Platform | Best for | Free tier | Docker required | Database storage |
|---|---|---|---|---|
| **Railway** | Fastest to deploy, great DX | $5 credit | Yes | Volumes supported |
| **Render** | Simple, auto-deploy from git | 750 hrs/mo | Yes | Persistent disks |
| **AWS App Runner** | AWS ecosystem, auto-scaling | No | Yes (ECR) | EFS mount |
| **GCP Cloud Run** | Serverless scaling to zero | Always-free tier | Yes (Artifact Registry) | GCS FUSE / Filestore |
| **Azure Container Apps** | Azure ecosystem | No | Yes (ACR) | Azure File Share |

**Recommendation for first deployment:** Railway or Render — git push to deploy, no cloud account required beyond a free signup.

---

## 3. Platform Steps

### Railway (fastest)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create a new project from the repo root
railway init

# Set environment variables (from your .env file)
railway variables set LLM_PROVIDER=groq
railway variables set GROQ_API_KEY=your_key_here
railway variables set GROQ_MODEL=llama-3.3-70b-versatile
railway variables set VECTOR_DB_PATH=/data/chroma

# Deploy
railway up

# Open in browser
railway open
```

Add a Volume in the Railway dashboard: mount path `/data`, size 1 GB.

---

### Render

1. Push your repo to GitHub.
2. Go to render.com → New → Web Service → Connect your GitHub repo.
3. Set:
   - **Root directory:** `week-4-launch/feature-12-ship-it`
   - **Environment:** Docker
   - **Dockerfile path:** `Dockerfile`
   - **Docker context:** `../..` (repo root)
4. Add environment variables in the Render dashboard (same as your `.env`).
5. Add a **Persistent Disk**: mount path `/data`, size 1 GB.
6. Click **Create Web Service** — Render builds and deploys automatically.

Auto-deploy is on by default: every push to `main` triggers a new deployment.

---

### AWS App Runner

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag for ECR (run from repo root)
docker build \
  -f week-4-launch/feature-12-ship-it/Dockerfile \
  -t ai-assistant:latest .

docker tag ai-assistant:latest \
  <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-assistant:latest

# Push to ECR
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-assistant:latest
```

Then in the AWS Console:
1. App Runner → Create service → Container registry → ECR
2. Select your image URI
3. Port: 8000
4. Add environment variables
5. For persistent storage, mount an EFS access point at `/data`

---

### GCP Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Build and push to Artifact Registry (run from repo root)
gcloud builds submit \
  --tag gcr.io/your-project-id/ai-assistant:latest \
  --config week-4-launch/feature-12-ship-it/cloudbuild.yaml .

# Deploy
gcloud run deploy ai-assistant \
  --image gcr.io/your-project-id/ai-assistant:latest \
  --platform managed \
  --region us-central1 \
  --port 8000 \
  --set-env-vars LLM_PROVIDER=groq,GROQ_MODEL=llama-3.3-70b-versatile \
  --set-secrets GROQ_API_KEY=groq-api-key:latest \
  --allow-unauthenticated
```

For persistent storage, use a Filestore NFS mount or Cloud Storage FUSE.

---

### Azure Container Apps

```bash
# Login
az login
az acr login --name your-registry-name

# Build and push (run from repo root)
docker build \
  -f week-4-launch/feature-12-ship-it/Dockerfile \
  -t your-registry-name.azurecr.io/ai-assistant:latest .

docker push your-registry-name.azurecr.io/ai-assistant:latest

# Deploy
az containerapp create \
  --name ai-assistant \
  --resource-group your-rg \
  --image your-registry-name.azurecr.io/ai-assistant:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars LLM_PROVIDER=groq GROQ_MODEL=llama-3.3-70b-versatile \
  --secrets groq-api-key=secretref:your-key-vault-secret
```

Add an Azure File Share volume for persistent storage.

---

## 4. Environment Variables in Production

**Never commit secrets to git.** In production, inject them via:

| Platform | Method |
|---|---|
| Railway | Dashboard → Variables |
| Render | Dashboard → Environment → Add Environment Variable |
| AWS App Runner | Service configuration → Environment variables + Secrets Manager |
| GCP Cloud Run | `--set-secrets` flag + Secret Manager |
| Azure Container Apps | `--secrets` flag + Key Vault reference |

**Required variables:**

```bash
LLM_PROVIDER=groq                      # or openai, anthropic, ollama, etc.
GROQ_API_KEY=gsk_...                   # your provider API key
GROQ_MODEL=llama-3.3-70b-versatile    # model name for your provider
VECTOR_DB_PATH=/data/chroma            # must point to your persistent volume mount
```

**Optional variables:**
```bash
VOICE_PROVIDER=openai                  # if using a different provider for voice
VLM_PROVIDER=openai                    # if using a different provider for vision
ENABLE_MULTI_TENANT=false
ENABLE_LONG_TERM_CONTEXT=false
```

---

## 5. Rollback

If a deployment breaks production:

**Railway:**
```bash
railway rollback
```

**Render:**
In the Render dashboard → Deploys → click the previous deploy → Rollback to this deploy.

**Docker (local or self-hosted):**
```bash
# Tag your known-good image before deploying
docker tag ai-assistant:latest ai-assistant:stable

# If the new deploy breaks, roll back
docker tag ai-assistant:stable ai-assistant:latest
docker compose up -d
```

**General principle:** always tag images with a version or git SHA, not just `latest`.

```bash
# Better tagging
git_sha=$(git rev-parse --short HEAD)
docker tag ai-assistant:latest ai-assistant:$git_sha
```

---

## 6. Final Launch Checklist

Run through this before calling a deployment "live":

```
Infrastructure
  [ ] docker compose up --build runs without errors locally
  [ ] GET /api/health returns {"status": "ok"} in the deployed environment
  [ ] Named volumes are mounted — restart the container and verify uploaded docs persist
  [ ] .env is NOT committed to git (check: git log --all -- .env)

Secrets
  [ ] API key is set as an environment secret, not hardcoded
  [ ] .dockerignore excludes .env (the image contains no secrets)

CI/CD
  [ ] GitHub Actions eval.yml is in .github/workflows/ and pushed to main
  [ ] Smoke tests pass in GitHub Actions (check the Actions tab)
  [ ] GROQ_API_KEY secret added to GitHub repo (for eval gate)

Quality
  [ ] POST /api/eval/run returns pass_rate >= 0.70
  [ ] At least 3 domain documents are uploaded and indexed
  [ ] Run a manual end-to-end test: upload doc → chat → check source = "rag"

Monitoring
  [ ] GET /api/metrics is accessible and showing live request counts
  [ ] Container health check is green in the platform dashboard
  [ ] Log output is JSON-formatted (check platform log viewer)
```

Ship it.
