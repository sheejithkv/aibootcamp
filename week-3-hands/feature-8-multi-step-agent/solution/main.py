"""
Feature 8: Multi-Step Agent — solution

The agent now PLANS before it acts. For complex requests that require multiple
steps, the assistant first decomposes the task into 2–5 concrete steps, then
executes each step in sequence using the Feature 7 agent loop, and finally
synthesizes a final answer from all results.

This implements the Plan-and-Execute design pattern — the first of two major
agent architectures taught in Week 3 (the other being the ReAct loop, which
executes and reasons simultaneously rather than planning upfront).

New endpoints vs Feature 7:
  POST /api/agent/plan              — create a task, kick off planning + execution
  GET  /api/agent/status/{task_id} — poll task progress (used by the UI)
  GET  /api/mcp/servers            — placeholder (Feature 9 fills this in)

All Feature 1-7 endpoints remain unchanged.

Run with:
    uvicorn main:app --reload --port 8000

YOUR DOMAIN CUSTOMIZATION:
  Requests that benefit from multi-step planning: anything that involves
  gathering information from multiple sources, then producing a report or
  recommendation. E.g.: "Compare our Q1 and Q2 sales reports and summarise
  the key differences" → Step 1: search Q1, Step 2: search Q2, Step 3: compare.
"""
import json
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from shared.agent import run_agent
from shared.document_store import (
    delete_document,
    get_chunks,
    get_document,
    list_documents,
    save_chunk,
    save_document,
    update_document,
)
from shared.ingestion import CHUNKING_STRATEGIES, extract_pages, extract_text
from shared.llm_client import call_llm
from shared.models import (
    AgentTask,
    Chunk,
    Document,
    Message,
    SmartChatResponse,
    StructuredResponse,
)
from shared.planner import execute_plan, make_plan
from shared.provider_check import check_provider_config
from shared.retrieval_memory import (
    build_knowledge_digest,
    get_current_digest,
    get_recent_retrievals,
    log_retrieval,
)
from shared.router import classify_query
from shared.session_store import add_message, create_session, get_session, list_sessions
from shared.task_store import create_task, get_task
from shared.tenant_context import get_tenant_id
from shared.vector_store import (
    add_chunks,
    delete_document_chunks,
    get_stats as vector_get_stats,
    search as vector_search,
)

CONTEXT_WINDOW_SIZE = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_provider_config()
    yield


app = FastAPI(
    title="My AI BlockSeBlock Assistant",
    description="Domain-Specific AI Assistant — AI Engineering Bootcamp, BlockseBlock",
    version="8.0.0",
    lifespan=lifespan,
)


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
    """Body for POST /api/agent/plan."""
    message: str


# ---------------------------------------------------------------------------
# Feature 1: Plain chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant for [YOUR_DOMAIN]. "
                "Answer clearly and concisely. "
                "If you don't know something, say so honestly rather than guessing."
            ),
        },
        {"role": "user", "content": request.message},
    ]
    result = await call_llm(messages)
    return ChatResponse(response=result.content or "")


# ---------------------------------------------------------------------------
# Feature 2: Structured chat
# ---------------------------------------------------------------------------

_STRUCTURED_SYSTEM_PROMPT = """You are a helpful AI assistant for [YOUR_DOMAIN].

For every user message, respond ONLY with a JSON object (no markdown, no extra text)
with exactly these four fields:

{
  "intent": "<one of: general_question | domain_question | action_request | unclear>",
  "answer": "<your response to the user, written in plain English>",
  "confidence": <a number between 0.0 and 1.0 representing how sure you are>,
  "sources_needed": <true if domain documents would improve this answer, false otherwise>
}

Respond ONLY with the JSON object. No preamble, no explanation, no markdown fences."""


def _parse_structured(raw_text: str) -> StructuredResponse:
    try:
        return StructuredResponse(**json.loads(raw_text))
    except Exception:
        return StructuredResponse(
            intent="unclear",
            answer=raw_text or "The assistant returned an unexpected response.",
            confidence=0.0,
            sources_needed=False,
        )


@app.post("/api/chat/structured", response_model=StructuredResponse)
async def chat_structured(request: ChatRequest) -> StructuredResponse:
    messages = [
        {"role": "system", "content": _STRUCTURED_SYSTEM_PROMPT},
        {"role": "user", "content": request.message},
    ]
    result = await call_llm(messages, temperature=0.3, response_format={"type": "json_object"})
    return _parse_structured(result.content or "")


# ---------------------------------------------------------------------------
# Feature 3: Session management
# ---------------------------------------------------------------------------

@app.post("/api/sessions")
async def new_session(tenant_id: str = Depends(get_tenant_id)) -> dict:
    session_id = create_session(tenant_id=tenant_id)
    return {"session_id": session_id}


@app.get("/api/sessions", response_model=list[SessionSummary])
async def sessions_list() -> list[SessionSummary]:
    summaries = []
    for s in list_sessions():
        first_user_msg = next((m.content for m in s.messages if m.role == "user"), "")
        title = (first_user_msg[:60] + "…") if len(first_user_msg) > 60 else (first_user_msg or "New conversation")
        summaries.append(SessionSummary(
            id=s.id,
            created_at=s.created_at.isoformat(),
            message_count=len(s.messages),
            title=title,
        ))
    return summaries


@app.post("/api/sessions/{session_id}/chat", response_model=StructuredResponse)
async def session_chat(
    session_id: str,
    request: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> StructuredResponse:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    messages: list[dict] = [{"role": "system", "content": _STRUCTURED_SYSTEM_PROMPT}]
    history = session.messages[-CONTEXT_WINDOW_SIZE:]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    add_message(session_id, "user", request.message)
    result = await call_llm(messages, temperature=0.3, response_format={"type": "json_object"})
    structured = _parse_structured(result.content or "")
    add_message(session_id, "assistant", structured.answer)
    return structured


@app.get("/api/sessions/{session_id}/history", response_model=list[Message])
async def session_history(
    session_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> list[Message]:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session.messages


# ---------------------------------------------------------------------------
# Feature 4: Document ingestion
# ---------------------------------------------------------------------------

@app.post("/api/documents/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    strategy: str = Form("sentence"),
    tenant_id: str = Depends(get_tenant_id),
) -> Document:
    if strategy not in CHUNKING_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{strategy}'. Choose: {', '.join(CHUNKING_STRATEGIES)}.",
        )
    filename = file.filename or "unknown"
    doc = save_document(filename, tenant_id=tenant_id)
    try:
        file_bytes = await file.read()
        text = extract_text(file_bytes, filename)
        pages = extract_pages(file_bytes, filename)
        chunk_dicts = CHUNKING_STRATEGIES[strategy](text, pages)
        for cd in chunk_dicts:
            save_chunk(Chunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                text=cd["text"],
                chunk_index=cd["chunk_index"],
                metadata={"filename": filename, "chunk_index": cd["chunk_index"],
                           "page_number": cd.get("page_number"), "strategy": strategy},
            ))
        chunk_texts = [cd["text"] for cd in chunk_dicts]
        chunk_metas = [{"filename": filename, "chunk_index": cd["chunk_index"], "strategy": strategy} for cd in chunk_dicts]
        add_chunks(doc.id, chunk_texts, chunk_metas, tenant_id=tenant_id)
        update_document(doc.id, status="ready", chunk_count=len(chunk_dicts), chunking_strategy=strategy)
    except Exception as exc:
        update_document(doc.id, status="error", chunk_count=0, chunking_strategy=strategy)
        raise HTTPException(status_code=422, detail=str(exc))
    return get_document(doc.id, tenant_id=tenant_id)  # type: ignore[return-value]


@app.get("/api/documents", response_model=list[Document])
async def documents_list(tenant_id: str = Depends(get_tenant_id)) -> list[Document]:
    return list_documents(tenant_id=tenant_id)


@app.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str, tenant_id: str = Depends(get_tenant_id)) -> dict:
    if get_document(doc_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    delete_document_chunks(doc_id)
    delete_document(doc_id, tenant_id=tenant_id)
    return {"deleted": doc_id}


@app.get("/api/documents/{doc_id}/chunks", response_model=list[Chunk])
async def document_chunks(doc_id: str, tenant_id: str = Depends(get_tenant_id)) -> list[Chunk]:
    if get_document(doc_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return get_chunks(doc_id)


# ---------------------------------------------------------------------------
# Feature 5: Semantic search
# ---------------------------------------------------------------------------

@app.post("/api/search")
async def search_documents(req: SearchRequest, tenant_id: str = Depends(get_tenant_id)) -> list[dict]:
    filters = {"document_id": req.document_id} if req.document_id else None
    return vector_search(req.query, top_k=req.top_k, filters=filters, tenant_id=tenant_id)


@app.get("/api/search/stats")
async def search_stats() -> dict:
    return vector_get_stats()


# ---------------------------------------------------------------------------
# Feature 6: Smart Router
# ---------------------------------------------------------------------------

_SMART_SYSTEM_PROMPT = """You are a helpful AI assistant for [YOUR_DOMAIN].
Answer clearly and concisely in plain English."""

_SMART_RAG_SYSTEM_PROMPT = """You are a helpful AI assistant for [YOUR_DOMAIN].
You have been given relevant excerpts from documents to help answer the user's question.
Use the provided context to give an accurate, grounded answer."""

_SMART_HYBRID_SYSTEM_PROMPT = """You are a helpful AI assistant for [YOUR_DOMAIN].
Some potentially relevant document excerpts have been retrieved. Use them if helpful; ignore them if not."""


def _build_context_block(chunks: list[dict]) -> str:
    lines = ["--- RETRIEVED CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[{i}] From: {chunk.get('filename', 'unknown')} (chunk {chunk.get('chunk_index', 0)})")
        lines.append(chunk.get("text", ""))
    lines.append("--- END CONTEXT ---")
    return "\n".join(lines)


@app.post("/api/sessions/{session_id}/chat/smart", response_model=SmartChatResponse)
async def smart_chat(
    session_id: str,
    request: SmartChatRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> SmartChatResponse:
    from shared.config import settings

    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    classification = await classify_query(request.message)
    needs_retrieval = classification["needs_retrieval"]
    confidence = classification["confidence"]
    query_type = classification["query_type"]

    chunks_used: list[dict] = []
    source: str
    retrieval_method: str = "none"

    high_confidence = confidence > 0.6

    if high_confidence and needs_retrieval:
        if query_type == "professional_document" and settings.enable_pageindex:
            chunks_used = vector_search(request.message, top_k=5, tenant_id=tenant_id)
            source = "pageindex"
            retrieval_method = "pageindex"
        else:
            chunks_used = vector_search(request.message, top_k=5, tenant_id=tenant_id)
            source = "rag"
            retrieval_method = "vector"
        system_prompt = _SMART_RAG_SYSTEM_PROMPT
    elif high_confidence and not needs_retrieval:
        source = "llm"
        retrieval_method = "none"
        system_prompt = _SMART_SYSTEM_PROMPT
    else:
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
        log_retrieval(session_id=session_id, tenant_id=tenant_id, query=request.message,
                      chunk_ids=chunk_ids, retrieval_method=retrieval_method)

    return SmartChatResponse(
        answer=answer, source=source, chunks_used=chunks_used,  # type: ignore[arg-type]
        confidence=confidence, retrieval_method=retrieval_method,
    )


@app.get("/api/tenant/info")
async def tenant_info(tenant_id: str = Depends(get_tenant_id)) -> dict:
    from shared.config import settings
    docs = list_documents(tenant_id=tenant_id)
    return {"tenant_id": tenant_id, "multi_tenant_enabled": settings.enable_multi_tenant,
            "document_count": len(docs)}


@app.get("/api/retrieval-memory/recent")
async def retrieval_memory_recent(limit: int = 20, tenant_id: str = Depends(get_tenant_id)) -> list[dict]:
    entries = get_recent_retrievals(tenant_id=tenant_id, limit=limit)
    return [{"session_id": e.session_id, "query": e.query, "chunks_retrieved": e.chunks_retrieved,
             "timestamp": e.timestamp.isoformat(), "retrieval_method": e.retrieval_method} for e in entries]


@app.post("/api/retrieval-memory/rebuild")
async def retrieval_memory_rebuild(tenant_id: str = Depends(get_tenant_id)) -> dict:
    digest = await build_knowledge_digest(tenant_id=tenant_id)
    if digest is None:
        return {"message": "No retrieval history found for this tenant."}
    return {"summary": digest.summary, "topics_covered": digest.topics_covered,
            "source_session_count": digest.source_session_count, "last_updated": digest.last_updated.isoformat()}


@app.get("/api/retrieval-memory/digest")
async def retrieval_memory_digest(tenant_id: str = Depends(get_tenant_id)) -> dict:
    digest = get_current_digest(tenant_id=tenant_id)
    if digest is None:
        return {"message": "No digest built yet. Call POST /api/retrieval-memory/rebuild first."}
    return {"summary": digest.summary, "topics_covered": digest.topics_covered,
            "source_session_count": digest.source_session_count, "last_updated": digest.last_updated.isoformat()}


# ---------------------------------------------------------------------------
# Feature 7: Single-turn agent
# ---------------------------------------------------------------------------

@app.post("/api/sessions/{session_id}/agent/run")
async def agent_run(
    session_id: str,
    request: AgentRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    session = get_session(session_id, tenant_id=tenant_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return await run_agent(
        message=request.message,
        session_id=session_id,
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# Feature 8: Multi-step agent (Plan-and-Execute)
# ---------------------------------------------------------------------------

@app.post("/api/agent/plan")
async def agent_plan(
    request: PlanRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """
    Start a multi-step agent task.

    1. Creates a new session (each task gets its own conversation context).
    2. Calls make_plan() to decompose the request into 2-5 steps.
    3. Kicks off execute_plan() as a background task.
    4. Returns the task_id immediately — the client polls /api/agent/status/{task_id}.
    """
    session_id = create_session(tenant_id=tenant_id)
    task = create_task(message=request.message, session_id=session_id, tenant_id=tenant_id)

    # Generate the plan synchronously so we can store it on the task immediately.
    plan = await make_plan(request.message)
    from shared.task_store import update_task
    update_task(task.id, plan=plan)

    # Execute the plan in the background — the client polls for progress.
    background_tasks.add_task(execute_plan, task.id)

    return {"task_id": task.id, "session_id": session_id, "plan": plan}


@app.get("/api/agent/status/{task_id}")
async def agent_status(task_id: str) -> dict:
    """
    Return the current state of a multi-step agent task.

    The UI polls this endpoint every ~1.5 seconds while status is 'planning'
    or 'executing', then renders the result when status transitions to 'done'
    or 'error'.
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task.model_dump()


# ---------------------------------------------------------------------------
# Health + provider info
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/provider-info")
async def provider_info():
    from shared.config import settings
    voice_name = settings.effective_voice_provider().lower().strip()
    llm_name = settings.llm_provider.lower().strip()
    model_map = {
        "openai": settings.openai_model, "anthropic": settings.anthropic_model,
        "cohere": settings.cohere_model, "ollama": settings.ollama_model,
        "groq": settings.groq_model, "azure": settings.azure_openai_deployment_name,
        "bedrock": settings.bedrock_model_id, "vertex": settings.vertex_model,
        "custom": settings.custom_model,
    }
    return {
        "llm_provider": llm_name,
        "llm_model": model_map.get(llm_name, "unknown"),
        "voice_provider": voice_name if voice_name != llm_name else None,
        "voice_model": model_map.get(voice_name) if voice_name != llm_name else None,
    }


_ui_path = Path(__file__).resolve().parents[3] / "ui"
if _ui_path.exists():
    app.mount("/", StaticFiles(directory=str(_ui_path), html=True), name="ui")
