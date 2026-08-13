# Feature 9: MCP Integration

**Week 3 · Hands — Feature 9 of 12 · Week 3 Complete**

Your agent now speaks **MCP** — the Model Context Protocol. Tools no longer need to be hardcoded in `shared/tools.py`. Any MCP-compatible server can expose tools to your agent, and any MCP-compatible client (Claude Desktop, Cursor, Google ADK) can use the servers you build.

This is the "USB for AI tools" moment: one standard connector, every tool works with every client.

---

## New Concepts

| Concept | What it means |
|---|---|
| **MCP (Model Context Protocol)** | An open standard for connecting AI apps to tools and data sources — one protocol, all clients |
| **MCP server** | A process that exposes tools via JSON-RPC (started as a subprocess for stdio transport) |
| **MCP client** | Code that connects to a server, lists its tools, and calls them (what we build) |
| **stdio transport** | The server runs as a subprocess; we communicate via stdin/stdout — simplest, no network needed |
| **SSE transport** | The server is a persistent HTTP service — for remote/shared tool servers |
| **Server registry** | A list of MCP servers your agent knows about; add entries to expand your agent's capabilities |

---

## New Endpoints

```
GET  /api/mcp/servers                 → list connected servers (name, transport, status)
GET  /api/mcp/tools                   → list all tools from all connected servers
POST /api/mcp/execute                 → directly invoke any MCP tool
     Body: { "tool_name": "...", "arguments": {...} }
```

`POST /api/sessions/{id}/agent/run` now uses `run_agent_with_mcp()` which merges local tools + MCP tools into one list. The LLM sees them all and doesn't know which source each tool comes from.

---

## What You Built

```
shared/mcp_demo_server.py    ← MCP server (3 mock tools: weather, news, exchange rate)
shared/domain_mcp_server.py  ← Template for YOUR domain's MCP server
shared/mcp_client.py         ← Client: connect, list tools, call tools
shared/agent.py              ← run_agent_with_mcp() merges local + MCP tools
```

We use a **local MCP server** (not an external service) so:
- Zero external infrastructure — no signup, no API keys
- You can read and modify the server code alongside the client
- The exact same pattern works to connect to any real public MCP server

---

## MCP SDK Ecosystem

| SDK | Language | Use case | Install |
|---|---|---|---|
| `mcp` (official) | Python | Server-side and script integrations | `pip install mcp` |
| `@modelcontextprotocol/sdk` (official) | TypeScript/Node.js | Most public servers (filesystem, GitHub, Postgres) | `npm install @modelcontextprotocol/sdk` |
| Community SDKs | Rust, Go, Java, C# | Language-specific integrations | See MCP docs |

Most popular public MCP servers are written in TypeScript. Our Python client connects to them via stdio without knowing TypeScript — that's the whole point of a standard protocol.

---

## Your Task

1. Open `starter/mcp_client.py`
2. Implement `list_mcp_tools()`:
   - **STEP 1**: Loop through SERVER_REGISTRY, call `_list_tools_from_server()` for each enabled server, cache and return the combined list
3. Implement `call_mcp_tool()`:
   - **STEP 2**: Look up which server owns the tool, find it in the registry, call `_call_tool_on_server()`
4. Run the server: `uvicorn main:app --reload --port 8000`
5. Verify: `GET /api/mcp/tools` returns the demo server's tools (weather, news, exchange rate)
6. Add at least **one real tool** to `shared/domain_mcp_server.py` for your domain (a database query, an API call, or a file read)
7. Set `ENABLE_DOMAIN_MCP_SERVER=true` in `.env` and restart — your tool appears in `/api/mcp/tools`
8. Send an agent request that uses your domain tool — it should appear tagged as `MCP:domain` in the Steps panel

---

## Google ADK + MCP

The same MCP servers you just built work natively with Google ADK:

```python
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Connect ADK to the SAME demo server we built above.
mcp_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["-m", "shared.mcp_demo_server"]
    )
)

agent = Agent(model="gemini-2.0-flash", tools=[mcp_tools])
# ADK + MCP: the agent can now call any tool exposed by our MCP server.
```

**Notice:** ADK's `MCPToolset` uses the SAME Python MCP SDK under the hood. What we built manually in `mcp_client.py` is what ADK's `MCPToolset` does in 4 lines. You now understand what those 4 lines are doing.

---

## Week 3 Complete

You've built the complete "Hands" layer:

| Feature | What you built |
|---|---|
| Feature 7 | Single-turn agent with tool calling (ReAct loop) |
| Feature 8 | Multi-step agent with planning (Plan-and-Execute) |
| Feature 9 | MCP integration — external tools via standard protocol |

**Combined capability:** your agent can plan multi-step tasks, execute each step using local tools OR tools from any MCP server, and synthesize a final answer — all while maintaining conversation history and tenant isolation from the previous week.

**Week 4 preview:** Docker containerization, production deployment, rate limiting, and eval harness. Your agent goes from `localhost:8000` to a real URL.

---

> See `resource/mcp-setup-guide.md` (Resource 9) for connecting to public MCP servers and the full SDK ecosystem guide.
