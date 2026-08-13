"""
Feature 1: Hello AI — starter

Your job: implement the /api/chat endpoint so it calls the LLM and returns
a reply. Everything else (app setup, health check, UI serving) is already done
for you — the server will boot and /docs will work before you write a single line.

Run this with:
    uvicorn main:app --reload --port 8000

Steps:
  1. Look for the TODO comments below — there are two.
  2. Fill in the ChatRequest model (Step 1).
  3. Implement the chat() function body (Step 2).
  4. Test your changes at http://localhost:8000/docs.
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from shared.llm_client import call_llm
from shared.provider_check import check_provider_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks before the server begins accepting requests."""
    await check_provider_config()
    yield


app = FastAPI(
    title="My AI Assistant",
    description="Domain-Specific AI Assistant — AI Engineering Bootcamp, BlockseBlock",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    """The body expected by POST /api/chat."""


    message: str


class ChatResponse(BaseModel):
    """The body returned by POST /api/chat."""

    response: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant for enterprise Kubernetes and "
                "OpenShift platform engineering, SRE, and production incident troubleshooting. "
                "Answer clearly and concisely. "
                "If you don't know something, say so honestly rather than guessing."
            ),
        },
        {
            "role": "system",
            "content": "Always end your reply with a relevant follow-up question.",
        },
        {
            "role": "user",
            "content": request.message,
        },
    ]

    result = await call_llm(
        messages,
        temperature=0.2,
        max_tokens=50,
    )

    return ChatResponse(response=result.content or "")
#    result = await call_llm(messages)
#    return ChatResponse(response=result.content or "")


@app.get("/api/health")
async def health():
    """Quick liveness check — returns 200 OK if the server is running."""
    return {"status": "ok"}


@app.get("/api/provider-info")
async def provider_info():
    """Return which LLM and voice provider are currently active (no API keys)."""
    from shared.config import settings

    voice_name = settings.effective_voice_provider().lower().strip()
    llm_name = settings.llm_provider.lower().strip()

    model_map = {
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "cohere": settings.cohere_model,
        "ollama": settings.ollama_model,
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
