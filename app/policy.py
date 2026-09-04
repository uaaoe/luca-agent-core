"""
SentinelGraph Policy Engine: Deterministic Guardrails & Risk Classification.
Enforces programmatic security boundaries and contracts before tool execution.
"""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    SAFE = "SAFE"            # Read-only queries, telemetry, calculations
    GUARDED = "GUARDED"      # Reversible config adjustments, minor parameter changes
    CRITICAL = "CRITICAL"    # Financial allocations, resource deletion, privilege changes

class PolicyStatus(str, Enum):
    PASSED = "PASSED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"

class PolicyCheckResult(BaseModel):
    status: PolicyStatus
    risk_level: RiskLevel
    requires_approval: bool
    reason: str
    tool_name: str
    sanitized_args: Dict[str, Any] = Field(default_factory=dict)
    simulation_banner: str = "[SIMULATED DEMO SANDBOX - NO REAL ASSETS OR INFRASTRUCTURE MODIFIED]"

class PolicyEngine:
    """Evaluates agent tool invocations against deterministic programmatic rules."""

    MAX_SIMULATED_DISBURSEMENT_CAP = 500_000.0  # Caps simulation at 500k EUR
    MAX_SERVICE_REPLICAS = 20

    @classmethod
    def evaluate(cls, tool_name: str, args: Dict[str, Any]) -> PolicyCheckResult:
        """
        Main policy gateway. Inspects tool calls and returns deterministic
        verdicts: PASSED (auto-execute), FLAGGED (requires HITL approval), or BLOCKED.
        """
        sanitized = dict(args)

        # 1. Telemetry Query (Read-only -> SAFE)
        if tool_name == "query_cluster_telemetry":
            component = str(sanitized.get("component", "all")).lower()
            valid_components = {"all", "cpu", "memory", "network", "pods", "security"}
            if component not in valid_components:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                    reason=f"Unknown component '{component}'. Allowed: {', '.join(sorted(valid_components))}.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )
            return PolicyCheckResult(
                status=PolicyStatus.PASSED,
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
                reason="Read-only diagnostic query verified.",
                tool_name=tool_name,
                sanitized_args=sanitized,
            )

        # 2. Weather or Math (Read-only -> SAFE)
        if tool_name in ("get_weather_forecast", "calculate_metric"):
            return PolicyCheckResult(
                status=PolicyStatus.PASSED,
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
                reason="Stateless utility call verified.",
                tool_name=tool_name,
                sanitized_args=sanitized,
            )

        # 3. Service Scaling (Operational Adjustment -> GUARDED)
        if tool_name == "adjust_service_scaling":
            service_name = str(sanitized.get("service_name", "")).strip()
            replicas = sanitized.get("replicas")

            if not service_name:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.GUARDED,
                    requires_approval=False,
                    reason="service_name cannot be empty.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            try:
                replicas = int(replicas)
                sanitized["replicas"] = replicas
            except (ValueError, TypeError):
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.GUARDED,
                    requires_approval=False,
                    reason=f"Invalid replicas value '{replicas}'. Must be an integer.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if replicas < 1 or replicas > cls.MAX_SERVICE_REPLICAS:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.GUARDED,
                    requires_approval=False,
                    reason=f"Replicas ({replicas}) out of permissible bounds (1-{cls.MAX_SERVICE_REPLICAS}).",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if replicas > 10:
                # High-resource threshold triggers human approval
                return PolicyCheckResult(
                    status=PolicyStatus.FLAGGED,
                    risk_level=RiskLevel.GUARDED,
                    requires_approval=True,
                    reason=f"Scaling service '{service_name}' to {replicas} pods exceeds high-capacity threshold (>10).",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            return PolicyCheckResult(
                status=PolicyStatus.PASSED,
                risk_level=RiskLevel.GUARDED,
                requires_approval=False,
                reason=f"Permissible scaling adjustment ({replicas} replicas).",
                tool_name=tool_name,
                sanitized_args=sanitized,
            )

        # 4. Emergency Financial Allocation (Financial / Sandbox -> CRITICAL)
        if tool_name == "simulate_emergency_disbursement":
            recipient = str(sanitized.get("recipient", "")).strip()
            currency = str(sanitized.get("currency", "EUR")).upper().strip()
            rationale = str(sanitized.get("rationale", "")).strip()

            try:
                amount = float(sanitized.get("amount", 0.0))
                sanitized["amount"] = amount
            except (ValueError, TypeError):
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=False,
                    reason="Invalid amount format. Must be numeric.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if amount <= 0:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=False,
                    reason="Disbursement amount must be strictly positive.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if amount > cls.MAX_SIMULATED_DISBURSEMENT_CAP:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=False,
                    reason=f"Requested {amount:,.2f} {currency} exceeds maximum sandbox policy cap ({cls.MAX_SIMULATED_DISBURSEMENT_CAP:,.2f} {currency}).",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if currency not in ("EUR", "USD", "GBP"):
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=False,
                    reason=f"Currency '{currency}' not permitted in sandbox.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            if not recipient or len(recipient) < 3:
                return PolicyCheckResult(
                    status=PolicyStatus.BLOCKED,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=False,
                    reason="Recipient entity name is incomplete or missing.",
                    tool_name=tool_name,
                    sanitized_args=sanitized,
                )

            # High-stakes financial action: MANDATORY Human-in-the-Loop Interrupt
            return PolicyCheckResult(
                status=PolicyStatus.FLAGGED,
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                reason=f"Critical action: Simulated transfer of {amount:,.2f} {currency} to '{recipient}'. Operator authorization required.",
                tool_name=tool_name,
                sanitized_args=sanitized,
            )

        # Unrecognized tool -> Default to strict review
        return PolicyCheckResult(
            status=PolicyStatus.FLAGGED,
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            reason=f"Unregistered tool '{tool_name}'. Policy requires explicit operator clearance.",
            tool_name=tool_name,
            sanitized_args=sanitized,
        )
