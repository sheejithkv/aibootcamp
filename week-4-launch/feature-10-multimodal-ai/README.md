# Feature 10: Multimodal AI

**Week 4 · Launch — Feature 10 of 12**

Up until now, everything has been text in → text out. But real-world AI assistants communicate through multiple channels — voice, images, documents as images, screenshots. These different channels are called **modalities**.

This feature adds two new modalities to your assistant:

| Part | What it does |
|------|-------------|
| **Part A — Voice** | Record a question → transcribe → LLM → speak the answer (STT → LLM → TTS) |
| **Part B — Vision** | Upload an image → VLM analyzes it → returns a text answer |
| **Part C — Modality Router** | One unified endpoint detects text/voice/vision and routes to the correct pipeline |

---

## New Concepts

| Concept | What it means |
|---------|---------------|
| **Modality** | A channel of communication: text, voice, or image. "Multimodal" means the system handles more than one. |
| **STT (Speech-to-Text)** | Converts audio recordings to text. Uses Whisper-class models (OpenAI Whisper, Groq Whisper). |
| **TTS (Text-to-Speech)** | Converts text to spoken audio. Returns MP3 bytes the browser can play. |
| **VLM (Vision Language Model)** | A language model that also accepts images as input. Same chat interface, but the "user" message can include an image. |
| **SLM (Small Language Model)** | A compact model that runs locally. For vision, Ollama offers free local VLMs (LLaVA, Phi-3 Vision). |
| **Base64 encoding** | How binary data (audio/image bytes) travels over JSON APIs: raw bytes → base64 string → back to bytes. |
| **Modality routing** | Detecting the type of input (text/voice/vision) and routing to the correct pipeline — the Feature 6 Anti-RAG pattern, extended. |
| **detail parameter** | Controls VLM resolution: "auto" (default), "high" (fine text in documents), "low" (fast overview). |

---

## The Voice Pipeline (Part A)

```
           Browser
     ┌──────────────────┐
     │ MediaRecorder    │  ← user speaks
     │ (WebM/WAV/MP3)   │
     └────────┬─────────┘
              │ audio bytes
              ▼
     POST /api/voice/chat      Stage 2: STT (transcribe_audio)
              │ transcript text
              ▼
     Smart Router (Feature 6)  Stage 3: LLM (smart_chat)
              │ text answer
              ▼
     synthesize_speech()       Stage 4: TTS
              │ MP3 bytes → base64
              ▼
     Browser plays audio + shows transcript
```

**Finding your latency bottleneck:** Log a timestamp before and after each stage. For most domains, Stage 3 (LLM) is the biggest bottleneck. Using Groq for STT + chat reduces Stage 2 and 3 significantly — Groq's LPU hardware is 10-20x faster than GPU inference.

---

## Vision Models: Cloud + Local Options (Part B)

VLMs accept images alongside text. You can run them in the cloud or locally for free.

| Provider | Model | How to use | Cost |
|----------|-------|------------|------|
| OpenAI | `gpt-4o` | `VLM_PROVIDER=openai` | Paid, very accurate |
| OpenAI | `gpt-4o-mini` | `VLM_PROVIDER=openai, VLM_MODEL=gpt-4o-mini` | Cheaper, still good |
| Anthropic | `claude-sonnet-4-6` | `VLM_PROVIDER=anthropic` | Paid |
| **Ollama** | **LLaVA 7B** | `VLM_PROVIDER=ollama, VLM_MODEL=llava` | **Free, local** |
| **Ollama** | **Phi-3 Vision** | `VLM_PROVIDER=ollama, VLM_MODEL=phi3:vision` | **Free, fast on 8GB RAM** |
| **Ollama** | **LLaVA-Phi 3B** | `VLM_PROVIDER=ollama, VLM_MODEL=llava-phi3` | **Fastest local VLM** |

> **If you're running on Ollama:** You can use a local VLM like LLaVA or Phi-3 Vision for Part B with zero API cost. Pull the model with `ollama pull llava`, then set `VLM_PROVIDER=ollama` and `VLM_MODEL=llava` in `.env`.

### Setting up your vision model

```bash
# Option 1: Ollama (free, local, private)
ollama pull llava          # general purpose, 7B params
ollama pull phi3:vision    # great for documents and charts, lighter
ollama pull llava-phi3     # fastest, 3B params, runs on 8GB RAM

# .env settings for Ollama vision:
VLM_PROVIDER=ollama
VLM_MODEL=llava   # or phi3:vision, llava-phi3

# Option 2: OpenAI (cloud, most accurate)
# .env settings:
VLM_PROVIDER=openai
VLM_MODEL=gpt-4o           # or gpt-4o-mini for lower cost
```

---

## Connection to Feature 6 (Anti-RAG)

Feature 6's Smart Router classifies text queries before deciding whether to retrieve:
```
text query → classify(needs_retrieval?) → LLM / RAG / hybrid
```

Feature 10's Modality Router extends the same pattern to input types:
```
request → detect_modality(audio? image? text?) → voice / vision / text pipeline
```

**Same concept, different dimension.** The Anti-RAG insight — "decide before you act, don't blindly process everything" — applies equally to modality detection. This connection is why `detect_modality()` lives in `shared/router.py` alongside Feature 6's `classify_query()`.

---

## New Endpoints

```
POST /api/voice/transcribe   audio file → {"text": "..."}
POST /api/voice/chat         audio file + session_id → {transcript, answer, audio_base64}
POST /api/vision/analyze     image file + prompt → {answer, model_used}
POST /api/vision/chat        image file + prompt + session_id → {answer, model_used}
POST /api/chat/multimodal    unified: text/audio/image + session_id → MultimodalChatResponse
```

---

## New `.env` Variables

```env
# FEATURE 10 — Multimodal AI

# Voice provider (STT/TTS). Defaults to LLM_PROVIDER if not set.
# Groq: free STT (Whisper). OpenAI: STT + TTS both supported.
# Ollama: NOT supported for voice — set VOICE_PROVIDER=openai or groq.
VOICE_PROVIDER=groq

# Vision provider. Defaults to LLM_PROVIDER if not set.
# Groq: NOT supported for vision — set VLM_PROVIDER=openai or ollama.
VLM_PROVIDER=ollama

# STT model for transcription (Groq/OpenAI).
STT_MODEL=whisper-large-v3

# TTS model for speech synthesis (OpenAI only).
# TTS_MODEL=tts-1

# VLM model for image analysis.
# Cloud: gpt-4o, gpt-4o-mini, claude-sonnet-4-6
# Local (Ollama): llava, phi3:vision, llava-phi3
VLM_MODEL=llava
```

---

## Your Task

### Part A — Voice
1. Implement `POST /api/voice/transcribe`: read audio bytes → `transcribe_audio()` → return text
2. Implement `POST /api/voice/chat`: transcribe → smart chat → `synthesize_speech()` → return `VoiceChatResponse`
3. Test using the 🎤 button in the Chat tab: record a domain question, hear the answer

### Part B — Vision
4. Implement `POST /api/vision/analyze`: read image bytes → `analyze_image()` → return `VisionAnalyzeResponse`
5. Test using the 📷 button in the Chat tab: upload a domain-relevant image (product photo, policy document screenshot, form scan) and ask a question about it
6. Try the `detail` parameter: use `"high"` for documents with fine text, `"low"` for quick object identification

### Part C — Modality Router
7. Fill in the voice and vision branches in `POST /api/chat/multimodal` (the text branch is provided)
8. Test all three modalities through the unified endpoint from Swagger at `/docs`
9. Reflect: compare the multimodal routing pattern to the Anti-RAG pattern from Feature 6

---

## What You Built → Framework Equivalent

| This course | Production framework |
|-------------|---------------------|
| `transcribe_audio()` | OpenAI Whisper / Groq Whisper API client — same provider abstraction pattern as `call_llm()` |
| `synthesize_speech()` | OpenAI TTS / ElevenLabs API client |
| `analyze_image()` + multipart message | LangChain `HumanMessage` with image content blocks (same schema, wrapped by LangChain) |
| `detect_modality()` + routing | Custom routing layer — **no standard framework equivalent yet**. Most production teams still hand-roll this. |

> **Note on modality routing:** Unlike RAG (which has dozens of frameworks) or tool calling (OpenAI/Anthropic native support), modality routing is still an open problem. The approach in this feature — inspect the request, detect the type, delegate to the right pipeline — is how leading AI teams solve it today.

---

## Coming in Feature 11

Feature 11 adds **observability and eval harness**:
- Structured JSON logging with request IDs
- Rate limiting (slowapi)
- `GET /api/metrics` — request counts, latency, error rates
- `POST /api/eval/run` — automated quality testing for your AI
- **Connection to Feature 10:** run the eval harness after swapping providers (e.g. cloud LLM → local SLM) to measure quality change

See **Resource 10** (`resource/multimodal-guide.md`) for the voice latency worksheet, SLM VLM comparison table, and domain use-case guide.
