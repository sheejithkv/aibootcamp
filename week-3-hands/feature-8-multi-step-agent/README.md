# Feature 8: Multi-Step Agent

**Week 3 · Hands — Feature 8 of 12**

Your agent can now **plan**. Instead of reacting to one message at a time, it decomposes a complex request into 2–5 concrete steps, executes each step in sequence, and synthesizes a final answer from all results.

This is the **Plan-and-Execute** agent design pattern — one of the two major agent architectures alongside ReAct (Reasoning + Acting).

---

## New Concepts

| Concept | What it means |
|---|---|
| **Task decomposition** | Breaking a complex goal into smaller, independently-executable sub-tasks |
| **Plan-and-Execute** | Agent pattern: first commit to a plan, then execute each step — no improvising mid-task |
| **Async execution** | The plan runs in a FastAPI `BackgroundTask` so the endpoint returns instantly |
| **Polling** | The UI calls `GET /api/agent/status/{task_id}` every 1.5 s to read live progress |
| **State machine** | The task moves through: `planning → executing → done / error` |

---

## What You Built vs What Frameworks Call It

| What you built | LangGraph equivalent |
|---|---|
| `make_plan()` LLM call | `StateGraph` node: `"plan"` |
| `execute_plan()` step loop | `StateGraph` node: `"execute"` with a self-loop edge |
| `task_store.update_task()` | LangGraph's built-in `State` object |
| `BackgroundTasks` polling | LangGraph's streaming execution model |

**LangGraph adds what our linear loop doesn't have: conditional edges.** If a step fails, LangGraph can route to a `"retry"` node or a `"human_review"` node. Our loop just sets `status="error"`. See Resource 8 for the full code sketch.

---

## New Endpoints

```
POST /api/agent/plan
Body: { "message": "your complex request" }
Returns: { "task_id": "...", "session_id": "...", "plan": ["Step 1", "Step 2", ...] }

GET /api/agent/status/{task_id}
Returns: AgentTask (id, status, message, plan, steps_completed, result, error)
```

The UI polls `GET /api/agent/status/{task_id}` every 1.5 seconds and renders:
- The plan as a numbered checklist
- Each step as pending → in-progress → done (with result revealed as it completes)
- A final result summary card when `status="done"`
- An error box when `status="error"`

---

## Your Task

1. Open `starter/planner.py`
2. Implement `make_plan()`:
   - **STEP 1**: Call `call_llm()` with `_PLANNER_SYSTEM_PROMPT` and `response_format={"type": "json_object"}`
   - **STEP 2**: Parse the JSON response into a `list[str]` of step instructions
3. Implement `execute_plan()`:
   - **STEP 3**: Loop through `task.plan`, call `run_agent()` for each step, update the task after each one
   - **STEP 4**: Call `call_llm()` once more with `_SYNTHESIZER_SYSTEM_PROMPT` to produce the final answer
4. Run the server: `uvicorn main:app --reload --port 8000`
5. In the Agent tab, switch to **Multi-Step** mode and submit a request that clearly requires 2–3 of your domain's tools in sequence

---

## Test Messages

These will trigger multi-step plans:

```
"Check if Friday at 3 PM is available, then create a support ticket about my account
 login issue, and tell me your business hours"

"What's the availability for next Monday AND Tuesday at 2 PM?"

"Create two tickets: one for my billing question and one for my delivery delay"
```

---

## Framework Bridge

### LangGraph — Conditional Branches and Loops

Our `execute_plan()` runs steps linearly and stops on error. LangGraph models the same flow as a graph with conditional edges — if step 2 fails, the agent can route to a "retry" node or a "human_review" node:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    message: str
    plan: list[str]
    results: list[dict]
    step_index: int

def plan_node(state: AgentState) -> AgentState:
    ...  # calls make_plan()

def execute_node(state: AgentState) -> AgentState:
    ...  # runs one step via run_agent()

def should_continue(state: AgentState) -> str:
    return "execute" if state["step_index"] < len(state["plan"]) else END

graph = StateGraph(AgentState)
graph.add_node("plan", plan_node)
graph.add_node("execute", execute_node)
graph.add_edge("plan", "execute")
graph.add_conditional_edges("execute", should_continue)
graph.set_entry_point("plan")
# Our execute_plan() = compiling and running this graph
```

**Notice what LangGraph adds:** conditional edges. If a step fails, you route to `"retry"` or `"human_review"` instead of just setting `status="error"`. This is what production agent systems need — and now you understand exactly why LangGraph is designed the way it is.

### LangChain Equivalents — The Full Picture

You've now built everything LangChain provides. Here's the complete mapping:

| Feature | What you built | LangChain equivalent |
|---|---|---|
| Feature 1 | `call_llm()` | `LLMChain` / LCEL chain |
| Feature 2 | `_STRUCTURED_SYSTEM_PROMPT` | `ChatPromptTemplate` |
| Feature 2 | `StructuredResponse` | `.with_structured_output()` |
| Feature 3 | `session_store.py` | `ConversationBufferMemory` |
| Feature 3 | sliding window `[-20:]` | `ConversationBufferWindowMemory` |
| Feature 4 | `ingestion.py` | Document loaders + text splitters |
| Feature 5 | `vector_store.py` | `VectorStore` + `Retriever` |
| Feature 6 | Smart Router | `ConversationalRetrievalChain` |
| Feature 7 | `run_agent()` | `AgentExecutor` |
| Feature 8 | `execute_plan()` loop | `StateGraph` (LangGraph) |

You built all of these from scratch. When something breaks inside LangChain or LangGraph, you'll know exactly where to look — because you understand what they're doing under the hood.

---

## Coming Next

**Feature 9: MCP Integration** — connect your agent to external services using the Model Context Protocol. The same `TOOLS_REGISTRY` pattern you built in Feature 7, but now tools can live on any server anywhere, and any MCP-compatible client (Claude Desktop, Cursor, ADK) can use them.

> See `resource/agent-flow-design-template.md` (Resource 8) for a worksheet on designing your own multi-step agent flow.
