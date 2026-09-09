"""
Domain MCP server for Kubernetes/OpenShift SRE operations.

Feature 9 real domain tool:
    get_cluster_nodes

The tool reads the currently configured Kubernetes/OpenShift cluster and
returns actual node readiness, roles, versions, and overall cluster status.
"""

import asyncio
import json
import shutil
import subprocess

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types as mcp_types

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


def _find_cluster_cli() -> list[str]:
    """Return the first available Kubernetes CLI command."""

    if shutil.which("kubectl"):
        return ["kubectl"]

    if shutil.which("oc"):
        return ["oc"]

    if shutil.which("k3s"):
        return ["k3s", "kubectl"]

    raise RuntimeError(
        "No Kubernetes CLI found. Expected kubectl, oc, or k3s."
    )


def _get_cluster_nodes() -> dict:
    """Read actual node state from the current Kubernetes context."""

    cli = _find_cluster_cli()

    proc = subprocess.run(
        [*cli, "get", "nodes", "-o", "json"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if proc.returncode != 0:
        return {
            "error": proc.stderr.strip() or "Cluster query failed",
            "command": " ".join(cli),
        }

    payload = json.loads(proc.stdout)

    nodes = []

    for item in payload.get("items", []):
        metadata = item.get("metadata", {})
        status = item.get("status", {})

        conditions = status.get("conditions", [])
        ready_condition = next(
            (c for c in conditions if c.get("type") == "Ready"),
            None,
        )

        ready = (
            ready_condition is not None
            and ready_condition.get("status") == "True"
        )

        labels = metadata.get("labels", {})

        roles = []

        for key in labels:
            prefix = "node-role.kubernetes.io/"
            if key.startswith(prefix):
                role = key[len(prefix):]
                if role:
                    roles.append(role)

        node_info = status.get("nodeInfo", {})

        nodes.append(
            {
                "name": metadata.get("name"),
                "ready": ready,
                "roles": sorted(roles),
                "kubernetes_version": node_info.get("kubeletVersion"),
                "container_runtime": node_info.get("containerRuntimeVersion"),
                "os": node_info.get("osImage"),
            }
        )

    ready_nodes = sum(1 for node in nodes if node["ready"])
    total_nodes = len(nodes)

    return {
        "source": "live-cluster",
        "cli": " ".join(cli),
        "status": (
            "healthy"
            if total_nodes > 0 and ready_nodes == total_nodes
            else "degraded"
        ),
        "ready_nodes": ready_nodes,
        "total_nodes": total_nodes,
        "nodes": nodes,
    }


if _MCP_AVAILABLE:
    server = Server("kubernetes-sre-domain-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name="get_cluster_nodes",
                description=(
                    "Read the actual Kubernetes or OpenShift cluster currently "
                    "configured on this host. Returns node names, readiness, "
                    "roles, Kubernetes versions, runtime information, and "
                    "overall health. Use this when the user asks about the "
                    "current/local cluster or its node health."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            )
        ]

    @server.call_tool()
    async def call_tool(
        name: str,
        arguments: dict,
    ) -> list[mcp_types.TextContent]:

        if name == "get_cluster_nodes":
            result = _get_cluster_nodes()
        else:
            result = {"error": f"Unknown tool '{name}'"}

        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )
        ]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

else:

    async def main():
        raise RuntimeError(
            "The 'mcp' package is not installed."
        )


if __name__ == "__main__":
    asyncio.run(main())
