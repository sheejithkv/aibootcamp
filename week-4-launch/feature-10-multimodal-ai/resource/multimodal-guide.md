# Resource 10: Multimodal AI Guide

**AI Engineering Bootcamp · BlockseBlock**

---

## Section 1: The Modality Spectrum

Modern AI models exist on a spectrum of supported input/output types:

```
Text-only LLMs
  → LLMs + STT/TTS (voice-capable)
    → VLMs (text + image input)
      → Fully multimodal (text + image + audio)
```

| Model type | Input | Output | Examples |
|------------|-------|--------|---------|
| Text LLM | Text | Text | llama3.1, GPT-4o, Claude Sonnet (text-only) |
| Voice-capable | Text + Audio | Text + Audio | Whisper + GPT-4o + TTS |
| VLM | Text + Image | Text | GPT-4o, Claude 3, LLaVA |
| Fully multimodal | Text + Image + Audio | Text + Audio | GPT-4o (natively multimodal) |

**What this course builds:** By combining STT, a VLM, and TTS, you've assembled a fully multimodal pipeline from composable parts — the same architecture used in production assistants.

---

## Section 2: Local VLMs for Vision (SLM + VLM with Ollama)

You don't need a cloud API for image analysis. These local models run on consumer hardware:

| Model | Pull command | RAM needed | Best for |
|-------|-------------|------------|---------|
| **LLaVA 7B** | `ollama pull llava` | 8GB | General vision Q&A, photos, screenshots |
| **Phi-3 Vision** | `ollama pull phi3:vision` | 6GB | Documents, charts, tables, structured images |
| **LLaVA-Phi 3B** | `ollama pull llava-phi3` | 4GB | Fastest; good for quick identification tasks |
| **BakLLaVA** | `ollama pull bakllava` | 8GB | Strong on instruction following with images |

### Setup steps

```bash
# Step 1: pull your chosen model
ollama pull llava

# Step 2: set in .env
VLM_PROVIDER=ollama
VLM_MODEL=llava

# Step 3: make sure Ollama is running
ollama serve   # in a separate terminal

# Step 4: start the Feature 10 server
cd week-4-launch/feature-10-multimodal-ai/solution
uvicorn main:app --reload --port 8000

# Step 5: test
curl -X POST http://localhost:8000/api/vision/analyze \
  -F "image=@/path/to/your/image.jpg" \
  -F "prompt=What is in this image?"
```

### Privacy benefit of local VLMs

When using `VLM_PROVIDER=ollama`, your images **never leave your machine**. For sensitive domains (medical, legal, financial), local VLMs are the correct choice — not just for cost, but for compliance.

---

## Section 3: Voice Latency Worksheet

The voice pipeline has four stages. Log timestamps between them to identify your bottleneck.

### The four stages

| Stage | Description | Typical latency |
|-------|------------|-----------------|
| 1. Record | Browser MediaRecorder captures audio | Real-time (user-controlled) |
| 2. Transcribe | STT converts audio bytes to text | 0.3–2s depending on provider |
| 3. LLM | Model generates the text answer | 0.5–5s depending on provider + length |
| 4. Synthesize | TTS converts text to audio | 0.5–3s depending on provider |

### Timing exercise

Add `console.time()` calls in `app.js` or print timestamps in `main.py`:

```python
import time

@app.post("/api/voice/chat")
async def voice_chat(audio: UploadFile, session_id: str = Form("")):
    t0 = time.time()
    
    audio_bytes = await audio.read()
    transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")
    t1 = time.time()
    print(f"STT: {(t1-t0)*1000:.0f}ms")
    
    # ... LLM call ...
    t2 = time.time()
    print(f"LLM: {(t2-t1)*1000:.0f}ms")
    
    audio_out = await synthesize_speech(answer)
    t3 = time.time()
    print(f"TTS: {(t3-t2)*1000:.0f}ms")
    print(f"Total: {(t3-t0)*1000:.0f}ms")
```

### Worksheet: fill in your measurements

| Provider config | STT ms | LLM ms | TTS ms | Total ms |
|----------------|--------|--------|--------|---------|
| `LLM_PROVIDER=groq, VOICE_PROVIDER=groq` | | | N/A | |
| `LLM_PROVIDER=groq, VOICE_PROVIDER=openai` | | | | |
| `LLM_PROVIDER=openai` (everything OpenAI) | | | | |
| `LLM_PROVIDER=ollama, VOICE_PROVIDER=groq` | | | N/A | |

**Which stage is your biggest bottleneck?** That's where optimization effort has the most impact.

---

## Section 4: When to Use Which Modality — A Domain Design Guide

Use this guide to decide whether voice, vision, or text serves your domain best.

### Voice (STT + TTS)

**Voice adds value when:**
- Users are doing something with their hands (cooking, working in a lab, driving)
- Users need eyes-free interaction (accessibility, wearables)
- The question is short and conversational: "What's the status of order #1234?"
- The answer is also short and conversational — voice becomes awkward for long technical answers

**Voice is less appropriate when:**
- The answer needs to be read carefully (contracts, precise instructions)
- Users are in a shared space (open-plan office, quiet zone)
- The domain requires typing precise identifiers (product codes, long strings)

**Worksheet: does your domain benefit from voice?**
- [ ] List 3 tasks in your domain where hands-free would help users
- [ ] List 3 tasks where reading is essential — voice wouldn't help
- [ ] Is the target audience in a context where they could use voice? (e.g., workshop vs office)

### Vision (VLM)

**Vision adds value when:**
- Users have a physical artifact they want to ask about (photo, form, screenshot)
- Your domain involves visual inspection: product defects, architectural drawings, lab results
- Documents arrive as scans or photos (not machine-readable text)
- Users want to "show, not describe" — easier to photograph a problem than explain it

**Vision is less appropriate when:**
- Documents are already machine-readable text — extract text instead, cheaper and more accurate
- The image contains text that could be OCR'd first — combine OCR + LLM for better accuracy than VLM alone
- Privacy requires no images to leave the machine — use local VLMs or disable vision

**Worksheet: does your domain benefit from vision?**
- [ ] List 3 types of images users in your domain regularly deal with
- [ ] For each: would a VLM give useful answers, or is text extraction better?
- [ ] What's the sensitivity of these images? Cloud VLM or local VLM?

### Decision guide

```
Does the user have something to SHOW you?
  → YES → Vision (VLM)

Is the user in a hands-free context?
  → YES → Voice (STT + TTS)

Is the answer meant to be read carefully?
  → YES → Text (keep it text)

Everything else?
  → Text (it's faster, cheaper, more accurate for most tasks)
```

---

## Section 5: Provider Quick Reference for Feature 10

```
VOICE (STT):
  groq      → Whisper-large-v3 (fast, free, recommended)
  openai    → Whisper (paid)
  ollama    → NOT SUPPORTED — set VOICE_PROVIDER=groq

VOICE (TTS):
  openai    → tts-1 (paid, natural voices)
  groq      → NOT SUPPORTED — set VOICE_PROVIDER=openai for TTS
  ollama    → NOT SUPPORTED — set VOICE_PROVIDER=openai

VISION (VLM):
  openai    → gpt-4o or gpt-4o-mini (paid, highest accuracy)
  anthropic → claude-sonnet-4-6 (paid, excellent for documents)
  ollama    → llava / phi3:vision / llava-phi3 (FREE, local, private)
  groq      → NOT SUPPORTED — set VLM_PROVIDER=openai or ollama

RECOMMENDED CONFIGS:
  Free everything:   LLM_PROVIDER=groq, VOICE_PROVIDER=groq, VLM_PROVIDER=ollama
  Best quality:      LLM_PROVIDER=openai (covers all three)
  Max privacy:       LLM_PROVIDER=ollama, VOICE_PROVIDER=openai, VLM_PROVIDER=ollama
```
