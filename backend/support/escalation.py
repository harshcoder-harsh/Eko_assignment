"""Escalation logic for the Support Escalation Claw.

Bounded, deterministic rules (not LLM-decided) so escalation is auditable and
predictable — this is the core "guardrail" of the agent: it must never let an
LLM silently decide to NOT escalate a critical issue.
"""

# Severity that always escalates regardless of how good the drafted answer looks.
AUTO_ESCALATE_SEVERITIES = {"critical", "high"}

# Phrases in the drafted response that indicate the model could not ground an
# answer in SOP context — treated as "unresolved" and routed to a ticket.
UNRESOLVED_SIGNALS = [
    "cannot find that information",
    "couldn't find any relevant information",
    "i don't have enough information",
    "i'm not able to determine",
    "do not have access",
]


def should_escalate(severity: str, draft_response: str) -> tuple:
    """Return (should_escalate: bool, reason: str | None)."""
    if severity in AUTO_ESCALATE_SEVERITIES:
        return True, f"Severity '{severity}' requires mandatory human escalation."

    lowered = (draft_response or "").lower()
    for signal in UNRESOLVED_SIGNALS:
        if signal in lowered:
            return True, "Drafted response indicates the issue could not be grounded in SOP context."

    return False, None


def is_unresolved(draft_response: str) -> bool:
    """Whether the drafted response failed to resolve the query (separate from escalation)."""
    lowered = (draft_response or "").lower()
    return any(signal in lowered for signal in UNRESOLVED_SIGNALS)
