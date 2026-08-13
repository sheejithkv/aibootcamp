# Feature 7: First Agent

**Week 3 · Phase: Hands**

---

## Week 3 Begins — You're Giving Your Assistant Hands

Features 1 through 6 built a capable assistant: it can talk, remember, read your documents, and decide which retrieval path to take. But there is a sharp limit on what it can do — it can only *answer*. No matter how well it understands a request, it cannot actually do anything in the world. Feature 7 crosses that line. You will give the LLM a set of tools — Python functions it can choose to call — and build the loop that runs those calls and feeds the results back. The moment you do this, "assistant" becomes "agent": something that can observe a situation, select an action, execute it, and incorporate the result into its next thought. This is the capability that makes AI systems useful in production, and it starts here.

---

## The Agent Loop

Every agent — from the simplest tool-calling demo to the most sophisticated autonomous system — runs some version of this loop:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   User message                                                              │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────┐                                  │
│   │  LLM  (Call 1 — with tool schemas) │                                  │
│   └─────────────────────────────────────┘                                  │
│       │                                                                     │
│       ├── Option A: model returns plain text ──────────────────────────┐   │
│       │                                                                 │   │
│       └── Option B: model returns tool_calls [ ]                       │   │
│               │                                                         │   │
│               ▼                                                         │   │
│        For each tool call:                                              │   │
│          look up function in TOOLS_REGISTRY                             │   │
│          execute with the arguments the model chose                     │   │
│          collect the result dict                                        │   │
│               │                                                         │   │
│               ▼                                                         │   │
│        Append tool results to the message history                       │   │
│               │                                                         │   │
│               ▼                                                         │   │
│   ┌─────────────────────────────────────┐                              │   │
│   │  LLM  (Call 2 — with tool results) │                              │   │
│   └─────────────────────────────────────┘                              │   │
│               │                                                         │   │
│               ▼                                                         │   │
│        Final answer in natural language  ◄──────────────────────────────┘  │
│               │                                                             │
│               ▼                                                             │
│       Return to user: { result, steps, tools_used }                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

This is the two-call pattern. It is the foundation of everything in Week 3. Keep this diagram in mind as you read the code — every line in `run_agent()` maps to one of these boxes.

---

## New Concepts

### AI Agent

An AI agent is not a model — it is a loop. The model is one participant. The agent is the overall system: the loop that calls the model, receives its decisions, executes whatever it decided to do, and feeds the results back for the next decision. A model alone can only predict the next token. An agent can take an action, observe what happened, and decide what to do next. Feature 7 is the minimum viable version of this loop: one round of tool calls, two LLM calls, one final answer.

### Tool / Function Calling

Function calling is the mechanism by which the LLM outputs a structured action request instead of plain text. When you pass tool schemas to the model, it can decide to respond with a `tool_calls` list rather than a text response. Each entry specifies which function to call and what arguments to pass — as structured JSON, not prose. Your code then calls the actual Python function and returns the result.

The key shift: the LLM is no longer just a text generator. It is a reasoning engine that decides *what action to take next*. The execution still happens in your Python code — the LLM just tells you what to run.

### Tool Schema

A tool schema is the description you give the LLM so it knows what a tool does, when to use it, and what arguments to provide. It is a JSON object following the OpenAI function-calling format:

```python
CHECK_AVAILABILITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_availability",
        "description": "Check whether a time slot is available for booking. "
                       "Call this when the user asks if a date or time is free.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM 24-hour format"},
            },
            "required": ["date", "time"],
        },
    },
}
```

**Why descriptions matter:** The LLM uses the `description` field — both at the function level and for each parameter — to decide when and how to call a tool. It does not inspect your Python code. A vague description means the model cannot tell when to use the tool, so it either never calls it or calls it in the wrong situations. Good descriptions are the single most important factor in agent reliability. See Resource 7 for a full guide.

### Two-Call Pattern

The agent makes two calls to the LLM per turn:

**Call 1** — the decision call. The model receives the user's message plus the list of available tool schemas. It responds with either plain text (no tool needed) or a list of `tool_calls` (tools to invoke, with arguments it chose).

**Call 2** — the synthesis call. After your code executes the tools and collects their results, those results are appended to the conversation as `tool` role messages. The model is called again with this enriched history. Now it can see what the tools returned and write a final natural-language answer.

The second call is necessary because the model's first response is a decision, not an answer. Without Call 2, the user would see raw JSON from the tool — not a coherent response. Call 2 is where the agent synthesizes what it learned from the tools into something the user can actually read.

---

## New Endpoint

```
POST /api/agent/run
```

**Request:**
```json
{
  "session_id": "abc-123",
  "message": "Do you have anything available this Friday at 3pm?"
}
```

**Response:**
```json
{
  "result": "Yes, Friday at 3:00 PM is available. Would you like me to book it?",
  "steps": [
    {
      "tool": "check_availability",
      "args": {"date": "2026-07-03", "time": "15:00"},
      "result": {"available": true, "slot": "2026-07-03T15:00"}
    }
  ],
  "tools_used": ["check_availability"]
}
```

The `steps` array is the audit trail: every tool the agent called, the exact arguments it chose, and what the tool returned. This is not just for debugging — it is the transparency layer that lets you verify the agent is behaving correctly. In production, you log this. In the UI, you can display it as a "how I got this answer" panel.

---

## Your Task

### Step 1: Implement the two-call loop in `starter/agent.py`

Open `starter/agent.py`. The skeleton is there with TODO comments guiding each step:

- [ ] Build the initial message list (system prompt + session history + user message)
- [ ] Call 1: pass `tools=[schema for schema in TOOLS_REGISTRY.values()]` to `call_llm()`
- [ ] Check `result.tool_calls` — if empty, return the plain text response immediately
- [ ] For each tool call: look up the function in `TOOLS_REGISTRY`, call it with `**args`, collect the result
- [ ] Append the assistant's tool-call message and the tool result messages to the history
- [ ] Call 2: call the LLM again with the enriched history (no tools needed this time)
- [ ] Return the final result plus the steps list

Test it works end-to-end before moving to Step 2. Use the Swagger UI at `http://localhost:8000/docs` to send a message that should trigger a tool.

### Step 2: Replace the example tools with tools for your domain

Open `shared/tools.py`. The three example tools (`check_availability`, `create_ticket`, `lookup_info`) are placeholders for Alpine Trail Co. Replace them with tools appropriate for *your* domain.

Before writing code, use the worksheet in `resource/tool-design-worksheet.md` (Resource 7) to plan your tools. Sketch the function signature, the description, the parameters, and a sample return value before you touch the code. It is much faster than designing tools in a REPL.

- [ ] Rename or replace all three example tools
- [ ] Update the `TOOLS_REGISTRY` dict to map each function name to its callable and schema
- [ ] Update the system prompt in `starter/agent.py` to describe what your tools do

### Step 3: Test each tool with messages that should trigger it

For each tool you built:

- [ ] Write a sample user message that should trigger it (e.g. "Is there a slot open on Tuesday?")
- [ ] Send it to `/api/agent/run` and verify the `steps` array shows the right tool was called
- [ ] Check that the arguments the model chose make sense
- [ ] Send a message that should NOT trigger any tool — confirm `steps` is empty and the model answered directly

This is the core reliability test for a tool-calling agent. If a tool is never called, the description is too vague. If it is called when it should not be, the description is too broad.

### Step 4: Add a fourth tool (stretch goal)

- [ ] Design a fourth tool that handles a common user request your three tools do not cover
- [ ] Add its function, schema, and entry in `TOOLS_REGISTRY`
- [ ] Test that the model correctly calls it (and the other three) based on context
- [ ] Try sending a message that could plausibly trigger two different tools — observe which one the model picks and whether it ever calls both in sequence

---

## Framework Bridge — Now You've Built It, Here's How the Industry Packages It

You just implemented an agent loop from scratch. Every major AI framework has a version of what you built. Here is how your code maps to the two most common ones.

### Google ADK

Google ADK (Agent Development Kit) is an open-source Python framework from Google for building multi-agent systems, released alongside Gemini 2.0. It provides declarative agent construction, built-in session management, and native multi-agent orchestration.

**What your code maps to in ADK:**

| What you built | Google ADK equivalent |
|---|---|
| `shared/tools.py` TOOL_SCHEMA dict | `@tool` decorated function (schema inferred from docstring + type hints) |
| `shared/agent.py` TOOLS_REGISTRY | `Agent(tools=[check_availability, create_ticket, lookup_info])` |
| The two-LLM-call loop in `run_agent()` | Handled internally by the ADK runner — you never write it |
| `shared/session_store.py` sessions | ADK's built-in `InMemorySessionService` or `DatabaseSessionService` |

This is what our `run_agent()` does under the hood. ADK packages it. Now you know what ADK is actually doing when you use it — and what to do when it doesn't behave the way you expect.

```python
# from google.adk.agents import Agent
# from google.adk.tools import tool
#
# @tool
# def check_availability(date: str, time: str) -> dict:
#     """Check appointment availability for a given date and time."""
#     return {"available": True}
#
# agent = Agent(model="gemini-2.0-flash", tools=[check_availability])
# # The loop, memory, and tool execution happen inside ADK
```

The `@tool` decorator reads the function's docstring and type hints to generate the schema automatically — the same schema you wrote by hand in `TOOL_SCHEMA`. Hand-rolling the schema first (as you did) makes it obvious what ADK is inferring, which is critical when the schema is wrong and the model is not calling the tool as expected.

### LangChain Agents

LangChain takes a different approach: it builds agents from composable chains and wraps them in an `AgentExecutor`.

**What your code maps to in LangChain:**

| What you built | LangChain equivalent |
|---|---|
| `shared/tools.py` + TOOL_SCHEMA | `@tool` decorated functions (LangChain infers schema from docstring) |
| `run_agent()` loop | `AgentExecutor.invoke({"input": message})` |
| TOOLS_REGISTRY | `create_openai_tools_agent(llm, tools, prompt)` |
| `steps` return value | `AgentExecutor(return_intermediate_steps=True)` |

Both ADK and LangChain reduce the loop to a single call. The tradeoff: you lose visibility into what is happening inside. When an agent misbehaves, you need to know whether the tool schema is wrong, the model chose the wrong tool, or the result parsing failed. Having written the loop yourself, you will find bugs in both frameworks faster than someone who started there.

---

## Going Further — The Frontier

### DeepAgent: When the Tool Registry Itself Becomes the Bottleneck

Feature 7 uses a static registry: you register three (or four) tools, and the agent picks from them. This works well when the tool space is small, stable, and known in advance. Most production agents today work this way.

DeepAgent ([github.com/RUC-NLPIR/DeepAgent](https://github.com/RUC-NLPIR/DeepAgent), WWW 2026 Oral paper from Renmin University of China and Xiaohongshu) addresses what happens when neither of those conditions holds.

**Two key departures from what you built:**

**1. Dynamic tool discovery.** Instead of a pre-registered set of tools, DeepAgent can search for tools from a pool of over 16,000 RapidAPIs during reasoning. "Find the right tool" is itself an action type — the agent searches the tool space as part of solving the problem, rather than selecting from a fixed menu. This matters when the task is unpredictable and no single team could anticipate which tools will be needed.

**2. Unified reasoning stream.** Feature 8 (which you build next) separates planning from execution. DeepAgent merges them: a single coherent text stream interleaves four action types — internal thought, tool search, tool call, and memory fold. Memory folding is the mechanism that compresses history into three layers (episodic memory, working memory, and tool memory) so the agent does not exhaust its context window on long tasks.

**Where you are vs where DeepAgent is:**

| Capability | Feature 7 (what you built) | DeepAgent |
|---|---|---|
| Tool selection | Static TOOLS_REGISTRY | Dynamic discovery from 16,000+ APIs |
| Reasoning structure | Plan (Call 1) → execute → synthesize (Call 2) | Unified reasoning stream with four interleaved action types |
| Memory | Session history (Feature 3) + agent steps | Brain-inspired memory folding: episodic + working + tool memory |
| Multi-step tasks | Single tool-call round | Iterative loop with context compression |

DeepAgent is the horizon, not the starting point. The static registry you built is the right choice for most production applications today — it is predictable, debuggable, and fast. Understanding DeepAgent tells you what problems arise *after* the registry works and what the field is building next.

---

## How to Run

```bash
cd week-3-hands/feature-7-first-agent/starter
uvicorn main:app --reload --port 8000
```

Features 1–6 work immediately. The `/api/agent/run` endpoint returns a 501 until you implement the two-call loop in `starter/agent.py`.

Open `http://localhost:8000` — the Agent tab appears in the navigation. Use the Swagger docs at `http://localhost:8000/docs` to test tool calls directly before wiring up the UI.

---

## Key Files

| File | Status | What it does |
|---|---|---|
| `starter/agent.py` | **Your work** | The two-call loop: implement `run_agent()` |
| `shared/tools.py` | **Your work** | Tool functions + TOOL_SCHEMA dicts — replace with your domain's tools |
| `starter/main.py` | Provided | FastAPI app with the `/api/agent/run` endpoint wired up |
| `shared/llm_client.py` | Unchanged | `call_llm()` — now used with `tools=` parameter |
| `shared/session_store.py` | Unchanged | Session history — the agent reads it to maintain conversation context |
| `shared/providers/base.py` | Unchanged | `LLMResponse.tool_calls` — the normalized list your loop reads |
| `solution/agent.py` | Reference | Complete implementation — open only after attempting your own |
| `solution/tools.py` | Reference | Complete Alpine Trail Co. tool set |
| `resource/tool-design-worksheet.md` | Resource | Resource 7: anatomy of a tool + design worksheet for your domain |
