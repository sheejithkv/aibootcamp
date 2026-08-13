"""
Feature 12: Ship It — solution

This is the final feature of the AI Engineering Bootcamp. You've built all twelve
features. Now you package and ship the complete application as a production-ready
container.

What's new in Feature 12 vs Feature 11:
  - Dockerfile:        multi-stage build, Python 3.12-slim, non-root user, healthcheck CMD
  - docker-compose.yml: named volumes for the vector DB and uploads, env_file injection
  - .dockerignore:     keeps secrets and build artifacts out of the image
  - GitHub Actions:    eval.yml runs smoke tests + quality gate on every push to main
  - This file:         identical to Feature 11's solution — no new server logic.
                       Containerisation is infrastructure, not application code.

Your Task (starter/Dockerfile TODOs):
  1. Choose a base image — python:3.12-slim
  2. Copy and activate the virtual environment from the builder stage
  3. Create /data directories and add a non-root user
  4. Write the CMD that starts uvicorn on port 8000

WHAT YOU BUILT → REAL-WORLD EQUIVALENT:
  Dockerfile (multi-stage)    → standard production Python container pattern
  docker-compose.yml volumes  → AWS EFS / GCP Persistent Disk / Azure File Share
  .dockerignore               → .gitignore equivalent for container build context
  GitHub Actions eval gate    → CircleCI / GitLab CI eval quality step
  named volumes               → stateful service data plane
  non-root USER               → principle of least privilege (CIS Docker Benchmark)

Deployment targets covered in resource/deployment-runbook.md:
  Railway, Render, AWS App Runner, GCP Cloud Run, Azure Container Apps

All Feature 1–11 endpoints remain unchanged.

Run locally:
    cd week-4-launch/feature-12-ship-it/
    docker compose up --build

Or without Docker (development):
    uvicorn main:app --reload --port 8000
"""
import base64
import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from shared import metrics
from shared.agent import run_agent_with_mcp
from shared.document_store import (
    delete_document, get_chunks, get_document, list_documents,
    save_chunk, save_document, update_document,
)
from shared.eval_harness import EvalCase, EvalReport, run_eval
from shared.ingestion import CHUNKING_STRATEGIES, extract_pages, extract_text
from shared.llm_client import analyze_image, call_llm, synthesize_speech, transcribe_audio
from shared.logging_config import setup_logging
from shared.mcp_client import (
    SERVER_REGISTRY, call_mcp_tool, get_mcp_tool_schemas, list_mcp_tools,
)
from shared.middleware import RequestIDMiddleware, TimingMiddleware
from shared.models import (
    AgentTask, Chunk, Document, Message, SmartChatResponse, StructuredResponse,
)
from shared.planner import execute_plan, make_plan
from shared.provider_check import check_provider_config
from shared.retrieval_memory import (
    build_knowledge_digest, get_current_digest, get_recent_retrievals, log_retrieval,
)
from shared.router import classify_query, detect_modality
from shared.session_store import add_message, create_session, get_session, list_sessions
from shared.task_store import create_task, get_task, update_task
from shared.tenant_context import get_tenant_id
from shared.vector_store import (
    add_chunks, delete_document_chunks, get_stats as vector_get_stats, search as vector_search,
)

# slowapi is an optional dependency — gracefully degrade if not installed.
# In production, install with: pip install slowapi
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    _limiter: Limiter | None = Limiter(key_func=get_remote_address)
    _RATE_LIMITING = True
except ImportError:
    _limiter = None
    _RATE_LIMITING = False


def _rl(rate: str):
    """Apply @_limiter.limit(rate) if slowapi is installed, else pass through."""
    def deco(func):
        return _limiter.limit(rate)(func) if _limiter else func  # type: ignore[union-attr]
    return deco

_log = logging.getLogger(__name__)

CONTEXT_WINDOW_SIZE = 20
_EVAL_CASES_PATH = Path(__file__).parent.parent / "tests" / "eval_cases_example.json"

# ---------------------------------------------------------------------------
# OpenAPI tag definitions — appear as collapsible sections in /docs
# ---------------------------------------------------------------------------
OPENAPI_TAGS = [
    {
        "name": "F1 · Hello AI",
        "description": "**Week 1 · Feature 1** — Basic text chat. The LLM receives your message and replies.",
    },
    {
        "name": "F2 · Prompt Mastery",
        "description": "**Week 1 · Feature 2** — Structured (JSON-mode) responses with intent, confidence, and answer fields.",
    },
    {
        "name": "F3 · AI Memory",
        "description": "**Week 1 · Feature 3** — Session management and sliding-window conversation history.",
    },
    {
        "name": "F4 · Feed the Brain",
        "description": "**Week 2 · Feature 4** — Document ingestion: upload, chunk, and index files (PDF, DOCX, TXT).",
    },
    {
        "name": "F5 · Find the Answer",
        "description": "**Week 2 · Feature 5** — Semantic search over document chunks using vector embeddings.",
    },
    {
        "name": "F6 · Smart Router",
        "description": "**Week 2 · Feature 6** — Intelligent routing between direct LLM, RAG retrieval, and hybrid modes. Includes tenant isolation (Part B) and retrieval memory (Part C).",
    },
    {
        "name": "F7 · First Agent",
        "description": "**Week 3 · Feature 7** — Tool-calling agent (ReAct pattern). Local tools: check_availability, create_ticket, lookup_info.",
    },
    {
        "name": "F8 · Multi-Step Agent",
        "description": "**Week 3 · Feature 8** — Plan-and-Execute agent. Breaks a request into steps, runs them in the background, poll for status.",
    },
    {
        "name": "F9 · MCP Integration",
        "description": "**Week 3 · Feature 9** — Model Context Protocol. Connect to external tool servers; browse and invoke MCP tools alongside local ones.",
    },
    {
        "name": "F10 · Multimodal AI",
        "description": (
            "**Week 4 · Feature 10** — Voice (STT/TTS) and Vision (VLM). "
            "Part A: record audio → transcribe → LLM → speak the answer. "
            "Part B: upload an image → VLM analyzes it → returns text answer. "
            "Part C: unified modality router detects text/voice/vision and routes automatically."
        ),
    },
    {
        "name": "F11 · Production Design",
        "description": (
            "**Week 4 · Feature 11** — Observability and eval harness. "
            "Part A: structured JSON logging, request tracing (X-Request-ID), latency metrics, rate limiting. "
            "Part B: golden test set + automated quality scoring via POST /api/eval/run."
        ),
    },
    {
        "name": "F12 · Ship It",
        "description": (
            "**Week 4 · Feature 12** — Containerisation and CI/CD. "
            "Dockerfile (multi-stage), docker-compose.yml (named volumes, healthcheck), "
            ".dockerignore, GitHub Actions eval quality gate. "
            "No new API endpoints — the deployment infrastructure IS the feature."
        ),
    },
    {
        "name": "Infrastructure",
        "description": "Health check, active provider info, live metrics — useful for deployment monitoring.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await check_provider_config()
    _log.info("Feature 12 server started", extra={"event": "startup"})
    yield


app = FastAPI(
    title="My AI BlockSeBlock Assistant",
    description=(
        "Domain-Specific AI Assistant — AI Engineering Bootcamp, BlockseBlock\n\n"
        "Endpoints are grouped by **course feature** so you can find exactly what was "
        "added each week. Expand a section to see its endpoints and try them live."
    ),
    version="12.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)

# Middleware — order matters: RequestIDMiddleware is outermost (processes requests first).
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)

# Rate limiting — only if slowapi is installed.
if _RATE_LIMITING and _limiter is not None:
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class SessionSummary(BaseModel):
    id: str
    created_at: str
    message_count: int
    title: str

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: str | None = None

class SmartChatRequest(BaseModel):
    message: str

class AgentRequest(BaseModel):
    message: str

class PlanRequest(BaseModel):
    message: str

class McpExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}

class VoiceChatResponse(BaseModel):
    transcript: str
    answer: str
    audio_base64: str
    audio_mime: str = "audio/mpeg"

class VisionAnalyzeResponse(BaseModel):
    answer: str
    model_used: str

class MultimodalChatResponse(BaseModel):
    modality: str
    answer: str
    source: str | None = None
    chunks_used: list[dict] = []
    confidence: float | None = None
    retrieval_method: str | None = None
    transcript: str | None = None
    audio_base64: str | None = None
    audio_mime: str | None = None
    model_used: str | None = None


# ---------------------------------------------------------------------------
# Features 1–3: Basic chat + sessions (carry-forward)
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse, tags=["F1 · Hello AI"])
@_rl("60/minute")
async def chat(http_request: Request, request: ChatRequest) -> ChatResponse:
    """Basic chat endpoint — rate limited to 60 requests per minute per IP."""
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant for [YOUR_DOMAIN]. Answer clearly and concisely."},
        {"role": "user", "content": request.message},
    ]
    result = await call_llm(messages)
    return ChatResponse(response=result.content or "")


_STRUCTURED_SYSTEM_PROMPT = """You are a helpful AI assistant for [YOUR_DOMAIN].
Respond ONLY with JSON: {"intent": "...", "answer": "...", "confidence": 0.0, "sources_needed": false}"""


def _parse_structured(raw_text: str) -> StructuredResponse:
    try:
        return StructuredResponse(**json.loads(raw_text))
    except Exception:
        return StructuredResponse(intent="unclear", answer=raw_text or "", confidence=0.0, sources_needed=False)


@app.post("/api/chat/structured", response_model=StructuredResponse, tags=["F2 · Prompt Mastery"])
@_rl("60/minute")
async def chat_structured(http_request: Request, request: ChatRequest) -> StructuredResponse:
    """Structured JSON-mode chat — rate limited to 60 requests per minute per IP."""
    result = await call_llm(
        [{"role": "system", "content": _STRUCTURED_SYSTEM_PROMPT}, {"role": "user", "content": request.message}],
        temperature=0.3, response_format={"type": "json_object"},
    )
    return _parse_structured(result.content or "")


@app.post("/api/sessions", tags=["F3 · AI Memory"])
async def new_session(tenant_id: str = Depends(get_tenant_id)) -> dict:
    return {"session_id": create_session(tenant_id=tenant_id)}


@app.get("/api/sessions", response_model=list[SessionSummary], tags=["F3 · AI Memory"])
async def sessions_list() -> list[SessionSummary]:
    summaries = []
    for s in list_sessions():
        first_user_msg = next((m.content for m in s.messages if m.role == "user"), "")
        title = (first_user_msg[:60] + "…") if len(first_user_msg) > 60 else (first_user_msg or "New conversation")
        summaries.append(SessionSummary(id=s.id, created_at=s.created_at.isoformat(), message_count=len(s.messages), title=title))
    return summaries


@app.post("/api/sessions/{session_id}/chat", response_model=StructuredResponse, tags=["F3 · AI Memory"])
async def session_chat(session_id: str, request: ChatRequest, tenant_id: str = Depends(get_tenant_id)) -> StructuredResponse:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    messages: list[dict] = [{"role": "system", "content": _STRUCTURED_SYSTEM_PROMPT}]
    for msg in session.messages[-CONTEXT_WINDOW_SIZE:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    add_message(session_id, "user", request.message)
    result = await call_llm(messages, temperature=0.3, response_format={"type": "json_object"})
    structured = _parse_structured(result.content or "")
    add_message(session_id, "assistant", structured.answer)
    return structured


@app.get("/api/sessions/{session_id}/history", response_model=list[Message], tags=["F3 · AI Memory"])
async def session_history(session_id: str, tenant_id: str = Depends(get_tenant_id)) -> list[Message]:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session.messages


# ---------------------------------------------------------------------------
# Feature 4: Document ingestion
# ---------------------------------------------------------------------------

@app.post("/api/documents/upload", response_model=Document, tags=["F4 · Feed the Brain"])
async def upload_document(file: UploadFile = File(...), strategy: str = Form("sentence"), tenant_id: str = Depends(get_tenant_id)) -> Document:
    if strategy not in CHUNKING_STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Unknown strategy '{strategy}'.")
    filename = file.filename or "unknown"
    doc = save_document(filename, tenant_id=tenant_id)
    try:
        file_bytes = await file.read()
        text = extract_text(file_bytes, filename)
        pages = extract_pages(file_bytes, filename)
        chunk_dicts = CHUNKING_STRATEGIES[strategy](text, pages)
        for cd in chunk_dicts:
            save_chunk(Chunk(id=str(uuid.uuid4()), document_id=doc.id, text=cd["text"], chunk_index=cd["chunk_index"],
                             metadata={"filename": filename, "chunk_index": cd["chunk_index"]}))
        add_chunks(doc.id, [cd["text"] for cd in chunk_dicts],
                   [{"filename": filename, "chunk_index": cd["chunk_index"]} for cd in chunk_dicts], tenant_id=tenant_id)
        update_document(doc.id, status="ready", chunk_count=len(chunk_dicts), chunking_strategy=strategy)
    except Exception as exc:
        update_document(doc.id, status="error", chunk_count=0, chunking_strategy=strategy)
        raise HTTPException(status_code=422, detail=str(exc))
    return get_document(doc.id, tenant_id=tenant_id)  # type: ignore[return-value]


@app.get("/api/documents", response_model=list[Document], tags=["F4 · Feed the Brain"])
async def documents_list(tenant_id: str = Depends(get_tenant_id)) -> list[Document]:
    return list_documents(tenant_id=tenant_id)


@app.delete("/api/documents/{doc_id}", tags=["F4 · Feed the Brain"])
async def remove_document(doc_id: str, tenant_id: str = Depends(get_tenant_id)) -> dict:
    if get_document(doc_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    delete_document_chunks(doc_id)
    delete_document(doc_id, tenant_id=tenant_id)
    return {"deleted": doc_id}


@app.get("/api/documents/{doc_id}/chunks", response_model=list[Chunk], tags=["F4 · Feed the Brain"])
async def document_chunks(doc_id: str, tenant_id: str = Depends(get_tenant_id)) -> list[Chunk]:
    if get_document(doc_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return get_chunks(doc_id)


# ---------------------------------------------------------------------------
# Feature 5: Semantic search
# ---------------------------------------------------------------------------

@app.post("/api/search", tags=["F5 · Find the Answer"])
async def search_documents(req: SearchRequest, tenant_id: str = Depends(get_tenant_id)) -> list[dict]:
    return vector_search(req.query, top_k=req.top_k, filters={"document_id": req.document_id} if req.document_id else None, tenant_id=tenant_id)


@app.get("/api/search/stats", tags=["F5 · Find the Answer"])
async def search_stats() -> dict:
    return vector_get_stats()


# ---------------------------------------------------------------------------
# Feature 6: Smart Router
# ---------------------------------------------------------------------------

_SMART_SYSTEM_PROMPT = "You are a helpful AI assistant for [YOUR_DOMAIN]. Answer clearly and concisely in plain English."
_SMART_RAG_SYSTEM_PROMPT = "You are a helpful AI assistant for [YOUR_DOMAIN]. Use the provided document excerpts to answer accurately."
_SMART_HYBRID_SYSTEM_PROMPT = "You are a helpful AI assistant for [YOUR_DOMAIN]. Some excerpts have been retrieved — use them if helpful."


def _build_context_block(chunks: list[dict]) -> str:
    lines = ["--- RETRIEVED CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[{i}] From: {chunk.get('filename', 'unknown')} (chunk {chunk.get('chunk_index', 0)})")
        lines.append(chunk.get("text", ""))
    lines.append("--- END CONTEXT ---")
    return "\n".join(lines)


@app.post("/api/sessions/{session_id}/chat/smart", response_model=SmartChatResponse, tags=["F6 · Smart Router"])
async def smart_chat(session_id: str, request: SmartChatRequest, tenant_id: str = Depends(get_tenant_id)) -> SmartChatResponse:
    from shared.config import settings
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    classification = await classify_query(request.message)
    chunks_used: list[dict] = []
    source = "llm"
    retrieval_method = "none"
    system_prompt = _SMART_SYSTEM_PROMPT
    high_confidence = classification["confidence"] > 0.6
    if high_confidence and classification["needs_retrieval"]:
        chunks_used = vector_search(request.message, top_k=5, tenant_id=tenant_id)
        source = "rag"
        retrieval_method = "vector"
        system_prompt = _SMART_RAG_SYSTEM_PROMPT
    elif not high_confidence:
        chunks_used = vector_search(request.message, top_k=3, tenant_id=tenant_id)
        source = "hybrid"
        retrieval_method = "vector"
        system_prompt = _SMART_HYBRID_SYSTEM_PROMPT
    if settings.enable_long_term_context:
        digest = get_current_digest(tenant_id)
        if digest and digest.summary:
            system_prompt += f"\n\nContext about this user's history: {digest.summary}"
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if chunks_used:
        messages.append({"role": "system", "content": _build_context_block(chunks_used)})
    for msg in session.messages[-CONTEXT_WINDOW_SIZE:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    result = await call_llm(messages)
    answer = result.content or ""
    add_message(session_id, "user", request.message)
    add_message(session_id, "assistant", answer)
    if chunks_used and settings.enable_long_term_context:
        chunk_ids = [f"{c.get('document_id', '')}_{c.get('chunk_index', 0)}" for c in chunks_used]
        log_retrieval(session_id=session_id, tenant_id=tenant_id, query=request.message, chunk_ids=chunk_ids, retrieval_method=retrieval_method)
    return SmartChatResponse(answer=answer, source=source, chunks_used=chunks_used, confidence=classification["confidence"], retrieval_method=retrieval_method)  # type: ignore[arg-type]


@app.get("/api/tenant/info", tags=["F6 · Smart Router"])
async def tenant_info(tenant_id: str = Depends(get_tenant_id)) -> dict:
    from shared.config import settings
    return {"tenant_id": tenant_id, "multi_tenant_enabled": settings.enable_multi_tenant,
            "document_count": len(list_documents(tenant_id=tenant_id))}


@app.post("/api/retrieval-memory/rebuild", tags=["F6 · Smart Router"])
async def retrieval_memory_rebuild(tenant_id: str = Depends(get_tenant_id)) -> dict:
    digest = await build_knowledge_digest(tenant_id=tenant_id)
    if digest is None:
        return {"message": "No retrieval history found."}
    return {"summary": digest.summary, "topics_covered": digest.topics_covered,
            "source_session_count": digest.source_session_count, "last_updated": digest.last_updated.isoformat()}


@app.get("/api/retrieval-memory/digest", tags=["F6 · Smart Router"])
async def retrieval_memory_digest(tenant_id: str = Depends(get_tenant_id)) -> dict:
    digest = get_current_digest(tenant_id=tenant_id)
    if digest is None:
        return {"message": "No digest built yet."}
    return {"summary": digest.summary, "topics_covered": digest.topics_covered,
            "source_session_count": digest.source_session_count, "last_updated": digest.last_updated.isoformat()}


@app.get("/api/retrieval-memory/recent", tags=["F6 · Smart Router"])
async def retrieval_memory_recent(limit: int = 20, tenant_id: str = Depends(get_tenant_id)) -> list[dict]:
    return [{"session_id": e.session_id, "query": e.query, "timestamp": e.timestamp.isoformat(), "retrieval_method": e.retrieval_method}
            for e in get_recent_retrievals(tenant_id=tenant_id, limit=limit)]


# ---------------------------------------------------------------------------
# Feature 7: Agent (ReAct pattern, MCP-aware)
# ---------------------------------------------------------------------------

@app.post("/api/sessions/{session_id}/agent/run", tags=["F7 · First Agent"])
@_rl("30/minute")
async def agent_run(http_request: Request, session_id: str, request: AgentRequest, tenant_id: str = Depends(get_tenant_id)) -> dict:
    """Agent endpoint — rate limited to 30 requests per minute per IP."""
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return await run_agent_with_mcp(message=request.message, session_id=session_id, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Feature 8: Multi-step agent (Plan-and-Execute)
# ---------------------------------------------------------------------------

@app.post("/api/agent/plan", tags=["F8 · Multi-Step Agent"])
async def agent_plan(request: PlanRequest, background_tasks: BackgroundTasks, tenant_id: str = Depends(get_tenant_id)) -> dict:
    session_id = create_session(tenant_id=tenant_id)
    task = create_task(message=request.message, session_id=session_id, tenant_id=tenant_id)
    plan = await make_plan(request.message)
    update_task(task.id, plan=plan)
    background_tasks.add_task(execute_plan, task.id)
    return {"task_id": task.id, "session_id": session_id, "plan": plan}


@app.get("/api/agent/status/{task_id}", tags=["F8 · Multi-Step Agent"])
async def agent_status(task_id: str) -> dict:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task.model_dump()


# ---------------------------------------------------------------------------
# Feature 9: MCP endpoints
# ---------------------------------------------------------------------------

@app.get("/api/mcp/servers", tags=["F9 · MCP Integration"])
async def mcp_servers() -> list[dict]:
    return [
        {
            "name":        s["name"],
            "transport":   s.get("transport", "stdio"),
            "enabled":     s.get("enabled", False),
            "description": s.get("description", ""),
        }
        for s in SERVER_REGISTRY
    ]


@app.get("/api/mcp/tools", tags=["F9 · MCP Integration"])
async def mcp_tools_list() -> list[dict]:
    try:
        tools = await list_mcp_tools(use_cache=False)
        return tools
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not list MCP tools: {exc}")


@app.post("/api/mcp/execute", tags=["F9 · MCP Integration"])
async def mcp_execute(request: McpExecuteRequest) -> dict:
    try:
        result = await call_mcp_tool(request.tool_name, request.arguments)
        return {"tool_name": request.tool_name, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Feature 10 — Part A: Voice (STT + TTS)
# ---------------------------------------------------------------------------

@app.post("/api/voice/transcribe", tags=["F10 · Multimodal AI"])
async def voice_transcribe(audio: UploadFile = File(...)) -> dict:
    audio_bytes = await audio.read()
    text = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")
    return {"text": text, "filename": audio.filename}


@app.post("/api/voice/chat", response_model=VoiceChatResponse, tags=["F10 · Multimodal AI"])
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str = Form(""),
    tenant_id: str = Depends(get_tenant_id),
) -> VoiceChatResponse:
    audio_bytes = await audio.read()
    transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")

    if session_id:
        session = get_session(session_id, tenant_id=tenant_id)
        if session:
            smart_resp = await smart_chat(session_id, SmartChatRequest(message=transcript), tenant_id)
            answer = smart_resp.answer
        else:
            result = await call_llm([
                {"role": "system", "content": _SMART_SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ])
            answer = result.content or ""
    else:
        result = await call_llm([
            {"role": "system", "content": _SMART_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ])
        answer = result.content or ""

    audio_base64 = ""
    try:
        audio_out = await synthesize_speech(answer)
        audio_base64 = base64.b64encode(audio_out).decode()
    except NotImplementedError:
        pass

    return VoiceChatResponse(transcript=transcript, answer=answer, audio_base64=audio_base64)


# ---------------------------------------------------------------------------
# Feature 10 — Part B: Vision (VLM image understanding)
# ---------------------------------------------------------------------------

@app.post("/api/vision/analyze", response_model=VisionAnalyzeResponse, tags=["F10 · Multimodal AI"])
async def vision_analyze(
    image: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail."),
    detail: str = Form("auto"),
) -> VisionAnalyzeResponse:
    image_bytes = await image.read()
    result = await analyze_image(image_bytes, prompt, detail)
    return VisionAnalyzeResponse(answer=result.content or "", model_used=result.model)


@app.post("/api/vision/chat", response_model=VisionAnalyzeResponse, tags=["F10 · Multimodal AI"])
async def vision_chat(
    image: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail."),
    detail: str = Form("auto"),
    session_id: str = Form(""),
    tenant_id: str = Depends(get_tenant_id),
) -> VisionAnalyzeResponse:
    image_bytes = await image.read()
    result = await analyze_image(image_bytes, prompt, detail)
    answer = result.content or ""

    if session_id:
        session = get_session(session_id, tenant_id=tenant_id)
        if session:
            add_message(session_id, "user", f"[IMAGE] {prompt}")
            add_message(session_id, "assistant", answer)

    return VisionAnalyzeResponse(answer=answer, model_used=result.model)


# ---------------------------------------------------------------------------
# Feature 10 — Part C: Unified modality router
# ---------------------------------------------------------------------------

@app.post("/api/chat/multimodal", response_model=MultimodalChatResponse, tags=["F10 · Multimodal AI"])
async def multimodal_chat(
    session_id: str = Form(...),
    message: str = Form(""),
    audio: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
    prompt: str = Form(""),
    tenant_id: str = Depends(get_tenant_id),
) -> MultimodalChatResponse:
    has_audio = audio is not None and bool(audio.filename)
    has_image = image is not None and bool(image.filename)
    modality = detect_modality(has_audio=has_audio, has_image=has_image)

    if modality == "voice":
        audio_bytes = await audio.read()  # type: ignore[union-attr]
        transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")  # type: ignore[union-attr]
        smart_resp = await smart_chat(session_id, SmartChatRequest(message=transcript), tenant_id)
        audio_base64 = ""
        try:
            audio_out = await synthesize_speech(smart_resp.answer)
            audio_base64 = base64.b64encode(audio_out).decode()
        except NotImplementedError:
            pass
        return MultimodalChatResponse(
            modality="voice",
            answer=smart_resp.answer,
            source=smart_resp.source,
            chunks_used=list(smart_resp.chunks_used),
            confidence=smart_resp.confidence,
            retrieval_method=smart_resp.retrieval_method,
            transcript=transcript,
            audio_base64=audio_base64,
            audio_mime="audio/mpeg",
        )

    if modality == "vision":
        image_bytes = await image.read()  # type: ignore[union-attr]
        text_prompt = prompt or message or "Describe this image in detail."
        result = await analyze_image(image_bytes, text_prompt)
        answer = result.content or ""
        session = get_session(session_id, tenant_id=tenant_id)
        if session:
            add_message(session_id, "user", f"[IMAGE] {text_prompt}")
            add_message(session_id, "assistant", answer)
        return MultimodalChatResponse(modality="vision", answer=answer, model_used=result.model)

    smart_resp = await smart_chat(session_id, SmartChatRequest(message=message), tenant_id)
    return MultimodalChatResponse(
        modality="text",
        answer=smart_resp.answer,
        source=smart_resp.source,
        chunks_used=list(smart_resp.chunks_used),
        confidence=smart_resp.confidence,
        retrieval_method=smart_resp.retrieval_method,
    )


# ---------------------------------------------------------------------------
# Feature 11 — Part A: Observability endpoints
# ---------------------------------------------------------------------------

@app.get("/api/metrics", tags=["F11 · Production Design"])
async def get_metrics() -> dict:
    """
    Live metrics snapshot from the in-memory metrics store.

    Updated by TimingMiddleware on every /api/* request.
    Fields:
      total_requests  — total API calls since server start
      total_errors    — calls that returned 5xx
      avg_latency_ms  — mean response time across all calls
      error_rate      — fraction of calls that errored (0.0–1.0)
      eval_last_run   — the most recent eval report, or null
    """
    return metrics.get_metrics()


# ---------------------------------------------------------------------------
# Feature 11 — Part B: Eval harness endpoints
# ---------------------------------------------------------------------------

@app.post("/api/eval/run", tags=["F11 · Production Design"])
async def eval_run() -> EvalReport:
    """
    Run the golden test set and return a scored report.

    Loads eval_cases_example.json from the tests/ directory alongside this
    solution folder. Runs classify_query + vector_search + call_llm for each
    case — same pipeline as smart_chat, but called directly (no HTTP).

    The report is also stored in-memory so GET /api/eval/last can retrieve it.
    Eval pass rate appears in GET /api/metrics under eval_last_run.

    NOTE: domain_question cases (source: rag) will route to "hybrid" or "llm"
    if no documents are indexed — upload documents first for realistic results.
    """
    if not _EVAL_CASES_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Eval cases file not found at {_EVAL_CASES_PATH}. "
                   "Create tests/eval_cases_example.json relative to this solution folder.",
        )

    raw = json.loads(_EVAL_CASES_PATH.read_text())
    cases = [EvalCase(**c) for c in raw]
    report = await run_eval(cases)
    metrics.set_eval_result(report.model_dump())
    _log.info(
        "Eval run complete",
        extra={"passed": report.passed, "total": report.total, "pass_rate": report.pass_rate},
    )
    return report


@app.get("/api/eval/last", tags=["F11 · Production Design"])
async def eval_last() -> dict:
    """Retrieve the most recent eval report (stored in-memory since last POST /api/eval/run)."""
    data = metrics.get_metrics().get("eval_last_run")
    if data is None:
        raise HTTPException(status_code=404, detail="No eval has been run yet. POST /api/eval/run first.")
    return data


# ---------------------------------------------------------------------------
# Health + provider info
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["Infrastructure"])
async def health() -> dict:
    """
    Health check with live metrics snapshot.

    Returns version, active provider, and a snapshot of request metrics.
    This enriched health check is useful for load balancer health checks and
    uptime monitors that want more than a plain {"status":"ok"}.
    """
    from shared.config import settings
    return {
        "status":   "ok",
        "version":  "12.0.0",
        "provider": settings.llm_provider,
        "metrics":  metrics.get_metrics(),
    }


@app.get("/api/provider-info", tags=["Infrastructure"])
async def provider_info() -> dict:
    from shared.config import settings
    llm_name = settings.llm_provider.lower().strip()
    model_map = {
        "openai": settings.openai_model, "anthropic": settings.anthropic_model,
        "cohere": settings.cohere_model, "ollama": settings.ollama_model,
        "groq": settings.groq_model, "azure": settings.azure_openai_deployment_name,
        "bedrock": settings.bedrock_model_id, "vertex": settings.vertex_model,
    }
    voice_name = settings.effective_voice_provider().lower().strip()
    vlm_name   = settings.effective_vlm_provider().lower().strip()
    return {
        "llm_provider":  llm_name,
        "llm_model":     model_map.get(llm_name, "unknown"),
        "voice_provider": voice_name if voice_name != llm_name else None,
        "voice_model":    model_map.get(voice_name) if voice_name != llm_name else None,
        "vlm_provider":   vlm_name if vlm_name != llm_name else None,
        "vlm_model":      settings.vlm_model if vlm_name != llm_name else None,
        "rate_limiting":  _RATE_LIMITING,
    }


_ui_path = Path(__file__).resolve().parents[3] / "ui"
if _ui_path.exists():
    app.mount("/", StaticFiles(directory=str(_ui_path), html=True), name="ui")
