# Production Readiness Checklist — Alpine Trail Co. AI Assistant

Use this checklist before promoting your assistant from development to production.
Tick each item off as you implement it. Items marked ★ are covered in Feature 11.

---

## Part 1 — Observability ★

- [ ] **Structured logging** — All log lines are JSON (not plain text). Each line includes
      `timestamp`, `level`, `request_id`, `path`, `duration_ms`. Machine-parseable by
      Datadog, Loki, and CloudWatch without custom parsing rules.

- [ ] **Request tracing** — Every request has a unique `X-Request-ID` header echoed
      in the response. Support logs and incident reports can correlate a user's
      complaint with a specific log line.

- [ ] **Latency baseline** — Run the assistant under normal load and record avg latency.
      Use this as the baseline for regression detection on future deployments.
      (Worksheet: see section below.)

- [ ] **Error rate baseline** — Measure error rate under normal load (should be < 1%).
      Alert if it exceeds 5% in any 5-minute window.

- [ ] **Health check** — `GET /api/health` returns 200 with version + provider. Load
      balancers and uptime monitors use this for routing decisions.

- [ ] **Rate limiting** — Chat and agent endpoints are protected. Users hitting the limit
      get a clean 429 response, not a crash. Set `RATE_LIMIT_PER_MINUTE` in `.env`.

---

## Part 2 — Eval Harness ★

- [ ] **Golden test set exists** — `tests/eval_cases_example.json` has at least 10 cases
      covering all intent types: general, domain, action, unclear.

- [ ] **Eval runs in CI** — `POST /api/eval/run` is called in your deployment pipeline.
      Reject a deploy if pass rate drops below the threshold (e.g. 80%).

- [ ] **Content checks are non-trivial** — `expected_answer_contains` checks verify that
      factually correct terms appear (e.g. "waterproof", "Gore-Tex"), not just that the
      endpoint returns 200.

- [ ] **Domain cases require indexed documents** — Upload your product catalogue before
      evaluating domain questions. A domain case that hits "llm" instead of "rag" means
      either the router or the vector index needs tuning.

- [ ] **Eval pass rate tracked over time** — Store `EvalReport.pass_rate` in a time-series
      so you can detect regressions across releases.

---

## Part 3 — Reliability

- [ ] **Provider failover** — If the primary LLM provider is down, is there a fallback?
      Consider `LLM_PROVIDER=groq` as primary, `VOICE_PROVIDER=openai` as secondary.

- [ ] **Timeout on LLM calls** — Wrap `call_llm()` with `asyncio.wait_for(…, timeout=30)`
      for user-facing endpoints. A hung LLM call should fail fast, not block the server.

- [ ] **Vector DB persistence** — `VECTOR_DB_PATH` points to a mounted volume, not `/tmp`.
      Document embeddings survive a container restart.

- [ ] **Session TTL set** — `SESSION_TTL_SECONDS` is configured. In-memory sessions grow
      unbounded otherwise; a 1-hour TTL is a safe default.

- [ ] **MCP servers reachable** — Run `GET /api/mcp/servers` after each deploy and verify
      `"enabled": true`. A failed MCP connection silently falls back to local tools.

---

## Part 4 — Security

- [ ] **API keys in secrets vault** — No API keys in environment variables on the host.
      Use `SECRETS_PROVIDER=infisical` or `SECRETS_PROVIDER=doppler` (see Bonus 0.5.1).

- [ ] **CORS restricted** — If the UI is served from a different origin, allow only known
      origins. Don't use `allow_origins=["*"]` in production.

- [ ] **Rate limiting per user** — Replace `get_remote_address` with a user-ID key function
      if your app has authentication. IP-based limits are easy to bypass with proxies.

- [ ] **Input length limits** — Add a max-length validation on `ChatRequest.message` (e.g.
      4000 chars). Extremely long inputs can inflate LLM costs significantly.

- [ ] **File upload validation** — `POST /api/documents/upload` accepts only `.txt`, `.pdf`,
      `.docx`. Reject other MIME types and check file size before reading bytes.

---

## Part 5 — Costs

- [ ] **Token budget per request** — Set `max_tokens` on every `call_llm()` call to prevent
      runaway completions. The default is provider-specific and often very large.

- [ ] **Embedding model cost** — `text-embedding-3-small` costs ~10× less than
      `text-embedding-3-large` with minimal quality loss for most RAG use cases.
      Benchmark before committing to the larger model.

- [ ] **VLM cost controls** — `detail="low"` reduces vision token usage by ~85% at the cost
      of image resolution. Use `detail="auto"` for product photos, `detail="low"` for
      screenshots where only text is needed.

- [ ] **Monthly cost alert** — Set a budget alert in your cloud provider console. Even a
      small traffic spike can generate a surprise bill overnight.

---

## Latency Worksheet

Fill this in after your first load test (10 concurrent users, 60 seconds):

| Endpoint                        | p50 (ms) | p95 (ms) | p99 (ms) | Error rate |
|----------------------------------|----------|----------|----------|------------|
| POST /api/chat                  |          |          |          |            |
| POST /api/sessions/{id}/chat/smart |       |          |          |            |
| POST /api/voice/chat            |          |          |          |            |
| POST /api/vision/analyze        |          |          |          |            |
| POST /api/sessions/{id}/agent/run |        |          |          |            |

**Typical production targets:**
- Chat: p95 < 3 s (user perceives < 3 s as "instant")
- Voice: p95 < 5 s (STT + LLM + TTS pipeline)
- Agent: p95 < 10 s (tool calls add 1–3 s each)
- Vision: p95 < 8 s (VLM inference time varies widely by provider)

---

## SLM vs Cloud LLM — Cost / Latency Comparison Template

Run the same 10 eval cases on each provider and record:

| Provider       | Avg latency (ms) | Pass rate | Cost per 1K calls | Privacy |
|----------------|-----------------|-----------|-------------------|---------|
| Groq (Llama 3) |                 |           | ~$0.00 (free tier)|public |
| OpenAI gpt-4o-mini |             |           | ~$0.30            |public |
| Anthropic Sonnet |               |           | ~$1.80            |public |
| Ollama llama3.1 (local) |        |           | $0.00             |private|
| Ollama phi3 (local) |            |           | $0.00             |private|

**Decision rule:** If Ollama pass rate ≥ 80% of cloud pass rate, prefer local for:
- high-volume workloads (cost)
- sensitive data (privacy)
- offline deployments (reliability)

Use cloud for: highest accuracy requirements, voice (TTS), vision (highest quality VLM).

---

## Eval Design Guide

**What makes a good eval case?**

1. **Deterministic intent** — The question should classify to the same intent every run.
   "What are your store hours?" → always `domain_question`.
   Avoid ambiguous questions like "tell me more" (context-dependent intent).

2. **Verifiable content** — `expected_answer_contains` should check terms that are always
   correct, not phrasing that varies. "hiking" not "These boots are ideal for hiking."

3. **Coverage across intent types:**
   - ≥ 3 general questions (LLM knowledge, no retrieval)
   - ≥ 4 domain questions (require indexed documents)
   - ≥ 2 action requests (should trigger tool use or graceful handoff)
   - ≥ 1 unclear input (should ask for clarification, not crash)

4. **Regression catches** — Add a new case every time a bug is reported in production.
   The eval set grows with your incident history.

5. **Threshold:** Start at 70% pass rate as the deploy gate. Tighten to 80% once your
   eval set covers all major intent types and your domain documents are indexed.
