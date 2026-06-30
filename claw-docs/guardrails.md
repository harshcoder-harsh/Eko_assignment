# Guardrails

## 1. Escalation is deterministic, not LLM-decided
`support/escalation.py`'s `should_escalate()` is plain Python logic — fixed
severity thresholds (`critical`, `high` always escalate) — independent of
how the LLM phrased its draft response. This is intentional: an LLM that
happens to sound confident must never be the thing that decides a critical
issue doesn't need a human. The LLM only produces inputs (`severity`,
`draft_response`); a deterministic rule consumes them.

## 2. Grounded-or-refuse drafting
`support/responder.py`'s system prompt explicitly instructs the model to say
"I don't have enough information in our SOPs to resolve this" rather than
invent a policy. `support/escalation.py`'s `is_unresolved()` then checks the
draft for that signal and routes it to a ticket instead of returning a
possibly-fabricated answer to the user as final.

## 3. Scoped retrieval, with transparent fallback
SOP retrieval only pulls from documents matching the SOP/FAQ naming
convention. If none exist yet, it falls back to the full document set so the
workflow doesn't simply break — but the response explicitly reports
`scoped_to_sop: false` so a human reviewing the audit trail knows the
grounding was generic, not authoritative SOP material.

## 4. Validated classification taxonomy
`classify_query()` validates the LLM's `issue_type`/`severity` output
against a fixed enum (`ISSUE_TYPES`, `SEVERITIES`). Any value outside that
set is coerced to a safe default (`general`/`low`) rather than passed
through — this prevents a malformed or adversarial LLM response from
producing an unrecognized state downstream.

## 5. Graceful degradation, never silent failure
Every Groq call (classification, drafting) has a deterministic fallback path
that triggers on missing API key or any exception, so the workflow always
completes and reaches a terminal state — it never crashes mid-run and leaves
a query unaccounted for. The audit trail logs whichever path was taken.

## 6. No silent ticket auto-resolution
Tickets are only ever marked `resolved` via an explicit human action
(`POST /support/ticket/{id}/resolve`). The workflow itself never closes a
ticket it created.

## 7. Full auditability
Every state transition is persisted before the response is returned, not
batched or best-effort. If a run reaches `RESOLVED` without ever escalating
a critical issue, that should be reconstructable purely from
`GET /support/audit/{run_id}` without needing to re-run anything.
