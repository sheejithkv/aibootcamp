"""
OpenShift / Kubernetes SRE tools for Feature 7: First Agent.

These tools use deterministic mock data so the agent can demonstrate
tool selection and execution without requiring access to a real cluster,
monitoring platform, or incident-management system.
"""

import uuid


# =============================================================================
# Tool 1: Cluster health
# =============================================================================

_CLUSTER_HEALTH = {
    "prod-ocp": {
        "status": "degraded",
        "ready_nodes": 6,
        "total_nodes": 7,
        "issue": "worker-3 is NotReady",
    },
    "dev-ocp": {
        "status": "healthy",
        "ready_nodes": 4,
        "total_nodes": 4,
        "issue": "none",
    },
    "qa-ocp": {
        "status": "healthy",
        "ready_nodes": 5,
        "total_nodes": 5,
        "issue": "none",
    },
}


def check_cluster_health(
    cluster: str,
    namespace: str = "all",
) -> dict:
    """
    Check the current health of an OpenShift or Kubernetes cluster.

    Args:
        cluster: Cluster name, for example "prod-ocp".
        namespace: Namespace to focus on, or "all".

    Returns:
        A flat dictionary describing cluster health.
    """
    key = cluster.lower().strip()

    result = _CLUSTER_HEALTH.get(
        key,
        {
            "status": "unknown",
            "ready_nodes": 0,
            "total_nodes": 0,
            "issue": "cluster is not present in the mock inventory",
        },
    )

    return {
        "cluster": cluster,
        "namespace": namespace,
        "status": result["status"],
        "ready_nodes": result["ready_nodes"],
        "total_nodes": result["total_nodes"],
        "issue": result["issue"],
    }


CHECK_CLUSTER_HEALTH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_cluster_health",
        "description": (
            "Check the health and node readiness of an OpenShift or Kubernetes cluster. "
            "Call this when the user asks whether a cluster is healthy, degraded, "
            "available, has NotReady nodes, or asks for current cluster status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cluster": {
                    "type": "string",
                    "description": (
                        "The cluster name to inspect, for example "
                        "'prod-ocp', 'dev-ocp', or 'qa-ocp'."
                    ),
                },
                "namespace": {
                    "type": "string",
                    "description": (
                        "Optional namespace to focus on. "
                        "Use 'all' when no namespace is specified."
                    ),
                },
            },
            "required": ["cluster"],
        },
    },
}


# =============================================================================
# Tool 2: Runbook lookup
# =============================================================================

_RUNBOOKS = {
    "etcd": {
        "runbook_id": "RB-ETCD-001",
        "summary": "Investigate etcd health, endpoint latency, database size, and member status.",
        "first_action": "Check etcd operator and member health before taking corrective action.",
    },
    "disk pressure": {
        "runbook_id": "RB-NODE-002",
        "summary": "Investigate node filesystem usage, image filesystem usage, and eviction signals.",
        "first_action": "Identify the filesystem causing DiskPressure and confirm current usage.",
    },
    "crashloop": {
        "runbook_id": "RB-POD-003",
        "summary": "Investigate pod restart history, previous container logs, events, and probes.",
        "first_action": "Inspect pod events and previous container logs to identify the first failure.",
    },
    "certificate": {
        "runbook_id": "RB-CERT-004",
        "summary": "Investigate certificate expiry, issuer status, and certificate consumers.",
        "first_action": "Identify the expiring certificate and verify its issuer and renewal path.",
    },
}


def lookup_runbook(alert: str) -> dict:
    """
    Look up an SRE runbook for an OpenShift or Kubernetes alert or symptom.

    Args:
        alert: Alert, symptom, or issue such as "etcd", "DiskPressure",
               "CrashLoopBackOff", or "certificate expiry".

    Returns:
        A flat dictionary containing runbook information.
    """
    normalized = alert.lower().strip()

    aliases = {
        "diskpressure": "disk pressure",
        "disk_pressure": "disk pressure",
        "crashloopbackoff": "crashloop",
        "crash loop": "crashloop",
        "cert": "certificate",
        "certificate expiry": "certificate",
        "certificate expiration": "certificate",
    }

    normalized = aliases.get(normalized, normalized)

    match = None

    for key, value in _RUNBOOKS.items():
        if key in normalized or normalized in key:
            match = value
            break

    if match is None:
        return {
            "found": False,
            "alert": alert,
            "runbook_id": "none",
            "summary": "No matching runbook was found.",
            "first_action": "Collect cluster events, logs, metrics, and affected-resource status.",
        }

    return {
        "found": True,
        "alert": alert,
        "runbook_id": match["runbook_id"],
        "summary": match["summary"],
        "first_action": match["first_action"],
    }


LOOKUP_RUNBOOK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_runbook",
        "description": (
            "Look up an OpenShift or Kubernetes SRE troubleshooting runbook. "
            "Call this when the user asks how to investigate, troubleshoot, or respond "
            "to an alert or symptom such as etcd problems, DiskPressure, "
            "CrashLoopBackOff, or certificate expiry."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alert": {
                    "type": "string",
                    "description": (
                        "The alert, symptom, or issue to investigate, for example "
                        "'DiskPressure', 'CrashLoopBackOff', 'etcd', or 'certificate expiry'."
                    ),
                },
            },
            "required": ["alert"],
        },
    },
}


# =============================================================================
# Tool 3: Incident creation
# =============================================================================

def create_incident(
    cluster: str,
    summary: str,
    severity: str = "medium",
) -> dict:
    """
    Create a mock SRE incident for a cluster issue.

    Args:
        cluster: Affected cluster name.
        summary: Short description of the problem.
        severity: low, medium, high, or critical.

    Returns:
        A flat dictionary describing the created incident.
    """
    valid_severities = {
        "low",
        "medium",
        "high",
        "critical",
    }

    severity = severity.lower().strip()

    if severity not in valid_severities:
        severity = "medium"

    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    return {
        "incident_id": incident_id,
        "cluster": cluster,
        "summary": summary,
        "severity": severity,
        "status": "open",
        "assignment_group": "platform-sre",
    }


CREATE_INCIDENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_incident",
        "description": (
            "Create an SRE incident for an OpenShift or Kubernetes cluster problem. "
            "Call this only when the user explicitly asks to create, open, raise, "
            "or log an incident or ticket for a cluster issue."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cluster": {
                    "type": "string",
                    "description": "The affected cluster name.",
                },
                "summary": {
                    "type": "string",
                    "description": "A concise summary of the cluster problem.",
                },
                "severity": {
                    "type": "string",
                    "enum": [
                        "low",
                        "medium",
                        "high",
                        "critical",
                    ],
                    "description": (
                        "Incident severity. Use critical for complete production outages, "
                        "high for major degradation, medium for normal operational issues, "
                        "and low for minor issues."
                    ),
                },
            },
            "required": [
                "cluster",
                "summary",
            ],
        },
    },
}
