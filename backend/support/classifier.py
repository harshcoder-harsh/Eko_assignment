"""Issue classification for the Support Escalation Claw.

Takes a raw user query and classifies it into:
  - issue_type: billing | technical | access | bug | feature_request | general
  - severity:   low | medium | high | critical

Uses Groq for the classification call (strict JSON output) and falls back to a
deterministic keyword-based classifier if Groq is unavailable or returns
something unparseable. The fallback ensures the workflow never breaks even
when the LLM call fails, mirroring how analytics/narrator.py degrades.
"""
import os
import json
import re

ISSUE_TYPES = ["billing", "technical", "access", "bug", "feature_request", "general"]
SEVERITIES = ["low", "medium", "high", "critical"]

_SYSTEM_PROMPT = """You are a support-ticket classifier. Given a user's support query,
classify it into exactly one issue_type and one severity.

issue_type must be one of: billing, technical, access, bug, feature_request, general
severity must be one of: low, medium, high, critical

Severity guidance:
- critical: production down, data loss, security breach, payment failure blocking business
- high: major feature broken, no workaround, affecting multiple users
- medium: feature degraded, workaround exists, affecting one user
- low: cosmetic issue, question, minor inconvenience

Respond with ONLY a JSON object, no markdown, no preamble:
{"issue_type": "...", "severity": "...", "reasoning": "one short sentence"}"""

_CRITICAL_KEYWORDS = ["down", "outage", "data loss", "breach", "hacked", "can't login", "cannot login", "production"]
_HIGH_KEYWORDS = ["broken", "not working", "error", "failed", "urgent", "blocked"]
_BILLING_KEYWORDS = ["billing", "invoice", "charge", "refund", "payment", "subscription"]
_ACCESS_KEYWORDS = ["access", "permission", "login", "password", "locked out", "2fa"]
_BUG_KEYWORDS = ["bug", "crash", "exception", "stack trace"]
_FEATURE_KEYWORDS = ["feature request", "would be nice", "can you add", "suggestion"]


def _fallback_classify(query: str) -> dict:
    """Deterministic keyword-based classification used when Groq is unavailable."""
    q = query.lower()

    if any(k in q for k in _CRITICAL_KEYWORDS):
        severity = "critical"
    elif any(k in q for k in _HIGH_KEYWORDS):
        severity = "high"
    else:
        severity = "low"

    if any(k in q for k in _BILLING_KEYWORDS):
        issue_type = "billing"
    elif any(k in q for k in _ACCESS_KEYWORDS):
        issue_type = "access"
    elif any(k in q for k in _BUG_KEYWORDS):
        issue_type = "bug"
        if severity == "low":
            severity = "medium"
    elif any(k in q for k in _FEATURE_KEYWORDS):
        issue_type = "feature_request"
    elif any(k in q for k in _HIGH_KEYWORDS):
        issue_type = "technical"
        if severity == "low":
            severity = "medium"
    else:
        issue_type = "general"

    return {
        "issue_type": issue_type,
        "severity": severity,
        "reasoning": "Keyword-based fallback classification (LLM unavailable).",
    }


def classify_query(query: str) -> dict:
    """Classify a support query. Always returns a dict with issue_type, severity, reasoning."""
    try:
        from support.hermes_runtime import get_hermes_agent

        agent = get_hermes_agent(system_prompt=_SYSTEM_PROMPT, cache_key="classifier")
        raw = agent.chat(f"Query: {query}").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)

        issue_type = parsed.get("issue_type", "general")
        severity = parsed.get("severity", "low")

        if issue_type not in ISSUE_TYPES:
            issue_type = "general"
        if severity not in SEVERITIES:
            severity = "low"

        return {
            "issue_type": issue_type,
            "severity": severity,
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception:
        return _fallback_classify(query)
