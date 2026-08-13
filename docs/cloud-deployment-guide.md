# Cloud Deployment Guide

Once your app runs in Docker locally (`docker compose up --build`), you can deploy it to any platform that supports containers. This guide covers the four most common options for AI applications in 2025.

The choice comes down to one question: **how much infrastructure do you want to manage?**

---

## Platform Comparison

| Platform | Setup time | Cost at low traffic | Scales to zero | Persistent volumes | Best for |
|---|---|---|---|---|---|
| **Railway** | 5 min | ~$0–5/mo | No (always-on) | Yes | Fastest path to production |
| **Render** | 10 min | $0 (free tier) | No | Yes | Auto-deploy from git, simple pricing |
| **AWS App Runner** | 30 min | ~$5–15/mo | No | Via EFS | Teams already in AWS |
| **GCP Cloud Run** | 20 min | ~$0 (free tier) | Yes | Via Filestore | Cost-sensitive, serverless scaling |
| **Azure Container Apps** | 30 min | ~$0–5/mo | Yes | Via File Share | Teams in Azure |

---

## Railway — Fastest to Production

Railway connects to your GitHub repo and deploys on every push. No Dockerfile knowledge required (it auto-detects), but using yours is better.

**When to choose Railway:**
- You want to be live in under 10 minutes
- You're a solo developer or small team
- You don't have a cloud provider preference yet

**What to know:**
- Persistent volumes are supported — add a 1 GB volume mounted at `/data`
- Environment variables set in the dashboard are injected at runtime (your `.env` never touches the image)
- Free $5 credit monthly; a small AI assistant runs well within that

See `resource/deployment-runbook.md` → Railway section for exact commands.

---

## Render — Simple Git-Push Deploys

Render is Railway's closest competitor. It has a generous free tier (750 hours/month for web services) and auto-deploys from GitHub without any CLI setup.

**When to choose Render:**
- You want zero-cost hosting for a personal or demo project
- You prefer a dashboard-first workflow over CLI
- You want auto-deploy on every `git push main` without configuration

**What to know:**
- Free tier web services spin down after 15 minutes of inactivity — first request after sleep takes ~30 seconds. Use a paid plan ($7/mo) to keep it always-on.
- Persistent Disk add-on required for the vector DB; mount at `/data`
- Set environment variables in the Render dashboard, not in `.env`

See `resource/deployment-runbook.md` → Render section for exact steps.

---

## AWS App Runner — AWS Ecosystem

App Runner is AWS's managed container service: push a container image to ECR, point App Runner at it, and AWS handles load balancing, TLS, and scaling. No EC2, no ECS task definitions, no ALB.

**When to choose App Runner:**
- Your company is already on AWS
- You need to connect to AWS services (RDS, S3, Secrets Manager)
- You want auto-scaling without managing Kubernetes

**What to know:**
- Requires an AWS account and some familiarity with IAM roles
- Persistent storage via EFS (Elastic File System) — mount at `/data`
- Secrets via AWS Secrets Manager — App Runner can inject them as env vars
- Cost: roughly $0.064/vCPU-hour + $0.007/GB-hour; a 0.25 vCPU / 0.5 GB instance is ~$5/mo

See `resource/deployment-runbook.md` → AWS App Runner section for exact commands.

---

## GCP Cloud Run — Serverless Scaling

Cloud Run runs your container only when requests come in and scales to zero between requests. You pay per request, not per hour — which means $0 at zero traffic.

**When to choose Cloud Run:**
- Your traffic is bursty (demo, classroom, low-volume production)
- You want to pay nothing during idle periods
- You're comfortable with Google Cloud

**What to know:**
- Cold start adds ~1–3 seconds to the first request after a period of no traffic. Use `--min-instances=1` to keep one instance warm if latency matters.
- Persistent storage via Filestore (NFS mount) or Cloud Storage FUSE. Both require additional setup.
- Always-free tier: 2 million requests/month, 360,000 GB-seconds of memory — plenty for a demo.
- Secrets via Secret Manager, injected with `--set-secrets`

See `resource/deployment-runbook.md` → GCP Cloud Run section for exact commands.

---

## Choosing a Platform

**Ship today, iterate later:** Start with Railway or Render. You can migrate to AWS/GCP/Azure later by pushing the same Docker image to their registries.

**Already have a cloud account:** Use the platform you know. The Dockerfile and `docker-compose.yml` you built are portable — they work on all five platforms above without modification.

**Cost-sensitive demo/classroom:** GCP Cloud Run's always-free tier can host a low-traffic AI assistant at literally $0/month.

**Production with compliance requirements:** AWS or Azure — they have the most mature compliance certifications (SOC 2, ISO 27001, HIPAA).

---

## What All Platforms Share

Regardless of platform, these principles apply:

1. **Never bake secrets into the image.** Your `.dockerignore` excludes `.env`. Inject secrets at runtime via the platform's secret management.

2. **Use a non-root user.** Your Dockerfile already does this (`USER appuser`). Most platforms enforce this; some will refuse to run root containers.

3. **Named volumes for state.** The vector DB (`/data/chroma`) and uploads (`/data/uploads`) must be on a persistent volume. Containers are ephemeral — anything written to the container filesystem is gone on restart.

4. **Health checks.** Your `docker-compose.yml` includes a healthcheck on `GET /api/health`. Most platforms use this to decide whether to send traffic to a container. Keep it fast (< 1 second).

5. **Structured logs.** Your app writes JSON logs (Feature 11). All five platforms above can ingest these into their log aggregation systems (CloudWatch, Google Cloud Logging, Azure Monitor) for searching and alerting.
