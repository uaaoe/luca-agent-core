"""
SentinelGraph Sandboxed Tool Definitions.
ALL tools in this module operate within a strict simulated sandbox for demo purposes.
NO real external accounts, cloud infrastructures, or banking APIs are connected.
"""
import uuid
from datetime import datetime, timezone
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# 1. Read-Only Diagnostic Tool (Risk: SAFE)
# ---------------------------------------------------------------------------
@tool
def query_cluster_telemetry(component: str = "all") -> str:
    """
    Query real-time infrastructure telemetry (CPU, memory, network latency, active pods).
    SAFE read-only diagnostic tool.
    """
    assert component and isinstance(component, str), "Assertion failed: component must be a string"
    
    comp = component.lower().strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    
    telemetry = {
        "cluster_id": "bcn-edge-mesh-01",
        "timestamp": timestamp,
        "environment": "SANDBOX-SIMULATION",
        "cpu_utilization_pct": 42.4,
        "memory_used_gb": 19.8,
        "memory_total_gb": 32.0,
        "active_microservices": 24,
        "average_latency_ms": 8.6,
        "status": "HEALTHY",
        "audit_mode": "ENFORCED"
    }

    if comp == "cpu":
        return f"[SANDBOX TELEMETRY] Cluster CPU: {telemetry['cpu_utilization_pct']}% (Healthy, 8 cores active)."
    elif comp == "memory":
        return f"[SANDBOX TELEMETRY] Cluster Memory: {telemetry['memory_used_gb']}GB / {telemetry['memory_total_gb']}GB used."
    elif comp == "network":
        return f"[SANDBOX TELEMETRY] Network: Avg latency {telemetry['average_latency_ms']}ms, 0 packet loss."
    else:
        return (
            f"[SANDBOX TELEMETRY @ {timestamp}]\n"
            f"• Cluster: {telemetry['cluster_id']} ({telemetry['status']})\n"
            f"• CPU: {telemetry['cpu_utilization_pct']}% | RAM: {telemetry['memory_used_gb']}/{telemetry['memory_total_gb']} GB\n"
            f"• Latency: {telemetry['average_latency_ms']}ms | Active Pods: {telemetry['active_microservices']}\n"
            f"• Policy Audit: Active"
        )


# ---------------------------------------------------------------------------
# 2. Service Scaling Adjustment (Risk: GUARDED)
# ---------------------------------------------------------------------------
@tool
def adjust_service_scaling(service_name: str, replicas: int) -> str:
    """
    Adjust the replica count of a microservice in the cluster.
    GUARDED operational tool.
    """
    assert service_name and isinstance(service_name, str), "Assertion failed: service_name must be non-empty"
    assert isinstance(replicas, int) and 1 <= replicas <= 20, "Assertion failed: replicas must be between 1 and 20"

    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    return (
        f"[SIMULATED ACTION - DEMO ONLY]\n"
        f"✓ Service '{service_name}' successfully scaled to {replicas} replicas at {timestamp}.\n"
        f"✓ Traffic distribution rebalanced. No service downtime detected."
    )


# ---------------------------------------------------------------------------
# 3. Emergency Disbursement Simulator (Risk: CRITICAL)
# ---------------------------------------------------------------------------
@tool
def simulate_emergency_disbursement(recipient: str, amount: float, currency: str = "EUR", rationale: str = "") -> str:
    """
    Simulate an emergency financial resource allocation or contractor disbursement.
    CRITICAL tool: Strict simulation sandbox only. No real money or banking API is touched.
    """
    assert recipient and isinstance(recipient, str), "Assertion failed: recipient must be non-empty"
    assert amount > 0, "Assertion failed: amount must be positive"
    
    sim_tx_id = f"SIM-TX-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    
    return (
        f"==========================================================\n"
        f"🛡️ [SIMULATED SANDBOX LEDGER - DEMO ONLY - NO REAL FUNDS]\n"
        f"==========================================================\n"
        f"• Status: EXECUTED (Human Operator Authorized)\n"
        f"• Transaction Reference: {sim_tx_id}\n"
        f"• Amount Allocated: {amount:,.2f} {currency.upper()}\n"
        f"• Beneficiary / Contractor: {recipient}\n"
        f"• Justification: {rationale or 'Emergency operational response'}\n"
        f"• Settled At: {timestamp}\n"
        f"• Verification: Cryptographic hash recorded in demo audit ledger."
    )


# ---------------------------------------------------------------------------
# 4. Standard Reusable Utilities (Weather & Calculator)
# ---------------------------------------------------------------------------
@tool
def get_weather_forecast(city: str) -> str:
    """Get the current weather forecast for a given city."""
    assert city and isinstance(city, str), "City must be a non-empty string"
    return f"The weather in {city} is 24°C, pleasant and mostly sunny."

@tool
def calculate_metric(expression: str) -> str:
    """Safely calculate basic mathematical expressions."""
    assert expression and isinstance(expression, str), "Expression must be a non-empty string"
    try:
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {})
        return f"Calculation result: {result}"
    except Exception as exc:
        return f"Calculation error: {str(exc)}"


# Consolidated Tools Registry
tools = [
    query_cluster_telemetry,
    adjust_service_scaling,
    simulate_emergency_disbursement,
    get_weather_forecast,
    calculate_metric,
]
tools_by_name = {t.name: t for t in tools}
