# Resource 9: MCP Setup Guide

**AI Engineering Bootcamp · BlockseBlock · Week 3, Feature 9**

---

## Section 1: What MCP Is

MCP (Model Context Protocol) is an open standard for connecting AI applications to tools, data sources, and services. Before MCP, every AI app had to build its own custom integration for every tool — a Slack integration, a database integration, a filesystem integration, each one different. MCP provides a shared "plug" that any compatible tool can use to connect to any compatible AI application.

**The USB analogy:** Before USB, every peripheral had its own proprietary connector. USB created one standard that works for keyboards, mice, cameras, and phones. MCP is USB for AI tools.

### The MCP Vocabulary

| Term | What it means |
|---|---|
| **Server** | A process that exposes tools (and optionally resources/prompts) via the MCP protocol |
| **Client** | Code in your AI app that connects to servers and uses their tools |
| **Tool** | A function the LLM can call — takes arguments, returns a result |
| **Resource** | A data source the model can read (files, database rows, API responses) |
| **Prompt** | A reusable prompt template exposed by the server |
| **Transport** | How client and server communicate — stdio (subprocess), SSE (HTTP), or streamable HTTP |

### Why Standardization Matters

Once you build a tool as an MCP server, it works with:
- Our hand-rolled `mcp_client.py` (what we built in this feature)
- Claude Desktop
- Cursor
- Google ADK's `MCPToolset`
- LangChain MCP adapters
- Any other MCP-compatible client

You build once; every compatible client uses it. No per-integration code.

---

## Section 2: The MCP SDK Ecosystem

| SDK | Language | Best for | Install |
|---|---|---|---|
| `mcp` (official Python) | Python 3.10+ | Server-side integrations, scripts, FastAPI apps | `pip install mcp` |
| `@modelcontextprotocol/sdk` (official TS) | TypeScript / Node.js | Most public MCP servers are written in TS | `npm install @modelcontextprotocol/sdk` |
| `mcp-rs` | Rust | High-performance, embedded systems | crates.io/crates/mcp-core |
| `go-mcp` | Go | Cloud-native microservices | github.com/metoro-io/mcp-golang |
| `mcp4j` | Java | JVM/Spring integrations | github.com/AI-Assisted-Coding/mcp4j |
| `mcpdotnet` | C# | .NET / Azure integrations | github.com/mlnethub/mcpdotnet |

**Key note:** Most popular public MCP servers (filesystem, Git, GitHub, Postgres, Slack) are written in TypeScript. Our Python client can connect to them via stdio transport without you needing to know TypeScript — the protocol is language-agnostic.

---

## Section 3: Running the Demo + Domain Server

### Start the demo server directly (for testing)

```bash
# From the repo root:
python -m shared.mcp_demo_server
# This starts the stdio server — it listens on stdin and responds on stdout.
# Press Ctrl-C to stop.
```

### Connect via the API (normal flow)

```bash
# Start the Feature 9 app
uvicorn week-3-hands/feature-9-mcp-integration/solution/main:app --reload --port 8000

# List all MCP tools
curl http://localhost:8000/api/mcp/tools

# Call a tool directly (for testing)
curl -X POST http://localhost:8000/api/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "get_weather", "arguments": {"location": "London"}}'
```

### Enable your domain server

```bash
# In .env:
ENABLE_DOMAIN_MCP_SERVER=true

# Restart the server — your domain tools now appear in /api/mcp/tools
```

---

## Section 4: Connecting to Public MCP Servers

These are well-maintained public MCP servers you can add to `SERVER_REGISTRY` in `shared/mcp_client.py`.

Each server is run as a subprocess — add one entry to `SERVER_REGISTRY` per server you want to connect.

### Filesystem server (TypeScript/Node.js)

```python
# In SERVER_REGISTRY:
{
    "name": "filesystem",
    "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
    "enabled": True,
    "transport": "stdio",
    "description": "Read/write local files — useful for agents that work with local data",
}
# Prerequisites: Node.js installed (brew install node / apt install nodejs)
# Tools: read_file, write_file, list_directory, create_directory, move_file, search_files
```

### GitHub server

```python
{
    "name": "github",
    "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
    "enabled": True,
    "transport": "stdio",
    "description": "Access GitHub repos, issues, PRs",
}
# Requires: GITHUB_PERSONAL_ACCESS_TOKEN in .env
# Tools: create_or_update_file, search_repositories, get_file_contents, create_issue, etc.
```

### Brave Search

```python
{
    "name": "brave-search",
    "command": ["npx", "-y", "@modelcontextprotocol/server-brave-search"],
    "enabled": True,
    "transport": "stdio",
    "description": "Web search via Brave Search API",
}
# Requires: BRAVE_API_KEY in .env (free tier available at brave.com/search/api/)
# Tools: brave_web_search, brave_local_search
```

### Postgres

```python
{
    "name": "postgres",
    "command": ["npx", "-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/dbname"],
    "enabled": True,
    "transport": "stdio",
    "description": "Query a Postgres database via natural language",
}
# Tools: query (read-only SQL queries, schema inspection)
```

### Slack

```python
{
    "name": "slack",
    "command": ["npx", "-y", "@modelcontextprotocol/server-slack"],
    "enabled": True,
    "transport": "stdio",
    "description": "Post messages, list channels, read threads from Slack",
}
# Requires: SLACK_BOT_TOKEN and SLACK_TEAM_ID in .env
# Tools: slack_post_message, slack_list_channels, slack_get_channel_history, etc.
```

Your agent can have all of these tools simultaneously — each is just another entry in the server registry. The LLM sees all tools from all servers in one unified list and picks the right one for each task.

---

## Section 5: Google ADK + MCP

Google ADK natively supports MCP via `MCPToolset`. The SAME MCP servers you built in this feature work with ADK — no changes to the server code.

```python
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Connect ADK to our demo server.
demo_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["-m", "shared.mcp_demo_server"],
    )
)

# Connect ADK to your domain server too.
domain_tools = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["-m", "shared.domain_mcp_server"],
    )
)

# Build an ADK agent with both tool sets.
agent = Agent(
    model="gemini-2.0-flash",
    tools=[demo_tools, domain_tools],
    instruction="You are a helpful assistant for [YOUR_DOMAIN]. Use your tools when the user's request needs real data.",
)

# Run it.
from google.adk.runners import Runner
runner = Runner(agent=agent, session_service=..., artifact_service=...)
# response = runner.run_async(...)
```

**Step by step:**
1. `MCPToolset(StdioServerParameters(...))` — ADK starts our server as a subprocess (same as our `stdio_client()`)
2. `session.initialize()` — ADK performs the MCP handshake (same as our `session.initialize()`)
3. `session.list_tools()` — ADK discovers available tools (same as our `_list_tools_from_server()`)
4. When the LLM calls a tool, ADK routes it to `session.call_tool()` (same as our `_call_tool_on_server()`)

**The key insight:** ADK's `MCPToolset` does what our `mcp_client.py` does, in 4 lines. The Python MCP SDK is under the hood in both. You now understand what those 4 lines are actually doing — and when ADK's built-in handling isn't enough (custom retry logic, multi-server merging, source tagging), you know how to go beneath it.

---

## Connecting a Remote MCP Server (SSE Transport)

Everything above uses stdio — the server runs as a local subprocess. If you want to connect to a remote MCP server (a company-hosted tool server), you switch to SSE transport:

```python
# Instead of:
from mcp.client.stdio import stdio_client
async with stdio_client(StdioServerParameters(command=..., args=...)) as (read, write):
    ...

# Use:
from mcp.client.sse import sse_client
async with sse_client("https://your-mcp-server.example.com/sse") as (read, write):
    ...
```

The `connect_to_server()` function signature stays the same — only the transport changes. This is the MCP design: clients and servers are transport-agnostic.
