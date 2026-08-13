# Feature 11 — Production Design

**Week 4 of the AI Engineering Bootcamp (BlockseBlock)**

You've built an AI assistant that works. This feature is about making it work *reliably* —
adding the observability and quality infrastructure that production AI teams depend on.

---

## What You'll Build

### Part A — Observability

**The problem:** Your assistant is running. Is it fast? Is it failing? You can't tell.

**What you add:**

| Component | What it does | Framework equivalent |
|-----------|-------------|---------------------|
| `JSONFormatter` | Turns every log line into a searchable JSON object | structlog, python-json-logger |
| `RequestIDMiddleware` | Assigns a UUID to every request; echoes it as `X-Request-ID` | OpenTelemetry trace context |
| `TimingMiddleware` | Records wall-clock latency + error flag for every `/api/*` call | Prometheus middleware |
| `shared/metrics.py` | In-memory counter/accumulator for requests, latency, errors | Prometheus in-process registry |
| `GET /api/metrics` | Live snapshot: total_requests, avg_latency_ms, error_rate | Prometheus `/metrics` scrape |
| `GET /api/health` | Enriched: version + provider + metrics snapshot | ECS health check / k8s liveness probe |
| Rate limiting | `@limiter.limit("60/minute")` on chat + agent endpoints | nginx rate limiting / AWS WAF |

**Why request IDs matter:**
When a user reports "the assistant gave a wrong answer at 3:42 PM," you search your
logs for `request_id: "abc123"` and see the exact LLM input, output, latency, and routing
decision for that specific request. Without IDs, you're guessing.

### Part B — Eval Harness

**The problem:** LLM outputs are non-deterministic. You can't unit-test them with `assert`.

**What you add:**

```
tests/eval_cases_example.json   ← 10 golden test cases (Alpine Trail Co.)
shared/eval_harness.py          ← EvalCase, EvalResult, EvalReport + run_eval()
POST /api/eval/run              ← runs all cases, scores each one, returns report
GET /api/eval/last              ← retrieve most recent report
```

**How a case is scored:**

```
EvalCase:
  question: "What is down fill power?"
  expected_intent: "general_question"   ← classify_query() must return this
  expected_source: "llm"                ← routing decision must be this
  expected_answer_contains: ["warmth"]  ← LLM answer must contain this word

Checks run per case:
  ✓ intent_check   — actual_intent == expected_intent
  ✓ source_check   — actual_source == expected_source (skipped if null)
  ✓ content_check  — each phrase in expected_answer_contains found in answer

Case passes: all active checks pass (zero failures)
```

**Framework equivalent:** This is a minimal LangSmith / RAGAS eval. Production AI teams
run this on every deploy via CI — if pass rate drops below 80%, the deploy is rejected.

---

## New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/metrics` | Live request metrics snapshot |
| `POST` | `/api/eval/run` | Run 10 golden cases; save report |
| `GET`  | `/api/eval/last` | Fetch most recent eval report |
| `GET`  | `/api/health` | Enriched health check (version + metrics) |

All Feature 1–10 endpoints remain unchanged.

---

## Rate Limiting

Rate limiting is added to the highest-traffic endpoints:

```python
@app.post("/api/chat")
@limiter.limit("60/minute")          # per IP address
async def chat(http_request: Request, request: ChatRequest):
    ...
```

When a client hits the limit, they receive a `429 Too Many Requests` response with a
`Retry-After` header. The limit is 60/minute for chat (matches a typical free-tier quota)
and 30/minute for the agent (agent calls are heavier — tool calls cost extra tokens).

Install slowapi: `pip install slowapi`

---

## UI Updates (Admin Tab)

The Admin tab gains two new sections:

**Metrics Dashboard** — auto-refreshes every 5 seconds:
- Total Requests | Avg Latency | Error Rate | Last Eval Pass Rate

**Eval Harness** — click "Run Eval" to run all 10 cases:
- Pass/fail bar (green/amber/red based on pass rate)
- Per-case table: question, actual intent, actual source, PASS/FAIL + failure details

---

## Connection to Earlier Features

| Earlier feature | How F11 extends it |
|-----------------|-------------------|
| F6 Smart Router | Eval harness reuses classify_query + vector_search — same routing logic tested |
| F6 Rate limiting | Protects the same `/api/chat` and agent endpoints Smart Mode routes through |
| F9 MCP Integration | `GET /api/metrics` would be a natural MCP tool for an ops agent to call |
| F10 Voice/Vision | TimingMiddleware measures STT + TTS latency — the bottleneck you need to find |

---

## Running

```bash
# Install the new dependency
pip install slowapi

# Start the server
cd week-4-launch/feature-11-production-design/solution
uvicorn main:app --reload --port 8000

# Check it's working
curl http://localhost:8000/api/health
curl http://localhost:8000/api/metrics

# Run the eval
curl -X POST http://localhost:8000/api/eval/run
```

---

## Files Added / Changed

```
shared/
  logging_config.py   ← NEW: JSONFormatter + setup_logging()
  middleware.py        ← NEW: RequestIDMiddleware + TimingMiddleware
  metrics.py           ← NEW: in-memory metrics store
  eval_harness.py      ← NEW: EvalCase / EvalResult / EvalReport / run_eval()

week-4-launch/feature-11-production-design/
  solution/main.py               ← F10 carry-forward + F11 additions
  starter/main.py                ← TODOs 1-4
  tests/eval_cases_example.json  ← 10 Alpine Trail Co. eval cases
  resource/production-checklist.md ← 20-item checklist + eval worksheet

ui/
  index.html  ← Admin panel: metrics dashboard + eval harness sections
  app.js       ← loadMetrics(), renderMetrics(), runEval(), renderEvalReport()
  style.css    ← metric cards, pass/fail bar, eval case table

requirements.txt  ← added slowapi
```
