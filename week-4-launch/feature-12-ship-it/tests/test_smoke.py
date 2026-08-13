"""
Smoke tests for Feature 12: Ship It

Structural checks that run in CI without a real LLM call:
  - The app module imports without error
  - GET /api/health returns 200 with expected fields
  - GET / serves the static UI (200 or redirect)
  - GET /api/metrics returns a valid metrics shape

These tests use FastAPI's TestClient which runs the app in-process.
They don't start a real server and don't make real LLM calls.

The GROQ_API_KEY env var is set in CI so the app can import; the tests
themselves don't hit the LLM — they only check structural correctness.
"""
import sys
from pathlib import Path

import pytest

# Add repo root so shared/ is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

# Import the solution app.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "solution"))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


def test_health_has_required_fields(client):
    resp = client.get("/api/health")
    body = resp.json()
    assert body.get("status") == "ok"
    assert "version" in body
    assert "provider" in body


def test_ui_served(client):
    resp = client.get("/")
    # Static file mount returns 200 for index.html.
    assert resp.status_code in (200, 301, 302), (
        f"Expected 200/redirect, got {resp.status_code}"
    )


def test_metrics_endpoint(client):
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_requests" in body
    assert "avg_latency_ms" in body
    assert "error_rate" in body


def test_provider_info_endpoint(client):
    resp = client.get("/api/provider-info")
    assert resp.status_code == 200
    body = resp.json()
    assert "llm_provider" in body
    assert "llm_model" in body
