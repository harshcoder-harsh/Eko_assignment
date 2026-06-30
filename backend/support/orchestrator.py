"""Workflow orchestrator for the Support Escalation Claw.

This is the agent's core loop. It owns a bounded workflow with explicit
states, rather than just answering a question:

    RECEIVED -> CLASSIFIED -> SOP_RETRIEVED -> DRAFTED -> (RESOLVED | TICKETED -> ESCALATED?)

Every transition is written to the audit trail (support/audit.py) so the
full decision history of a run can be inspected later.
"""
from support.classifier import classify_query
from support.sop_retriever import retrieve_sop_context
from support.responder import draft_response
from support.escalation import should_escalate, is_unresolved
from support.ticket_store import create_ticket, ESCALATED, OPEN, RESOLVED
from support import audit

STATES = [
    "RECEIVED",
    "CLASSIFIED",
    "SOP_RETRIEVED",
    "DRAFTED",
    "RESOLVED",
    "TICKETED",
    "ESCALATED",
]


def run_support_workflow(query: str, user_email: str = "default_user") -> dict:
    """Run the full support workflow for one query and return a structured result."""
    run_id = audit.start_run(user_email, query)
    audit.log_event(run_id, "RECEIVED", {"query": query})

    # Step 1: Classify
    classification = classify_query(query)
    audit.log_event(run_id, "CLASSIFIED", classification)

    # Step 2: Retrieve SOP context
    retrieval = retrieve_sop_context(query, user_email)
    audit.log_event(run_id, "SOP_RETRIEVED", {
        "scoped_to_sop": retrieval["scoped_to_sop"],
        "num_sources": len(retrieval["sources"]),
        "source_names": [s["name"] for s in retrieval["sources"]],
    })

    # Step 3: Draft grounded response
    draft = draft_response(
        query=query,
        issue_type=classification["issue_type"],
        severity=classification["severity"],
        context_block=retrieval["context_block"],
    )
    audit.log_event(run_id, "DRAFTED", {"draft_response": draft})

    # Step 4: Decide escalation (deterministic guardrail, not LLM-decided)
    escalate, escalation_reason = should_escalate(classification["severity"], draft)
    unresolved = is_unresolved(draft)

    ticket = None
    final_state = "RESOLVED"

    if escalate or unresolved:
        status = ESCALATED if escalate else OPEN
        ticket = create_ticket(
            user_email=user_email,
            query=query,
            issue_type=classification["issue_type"],
            severity=classification["severity"],
            draft_response=draft,
            status=status,
            escalation_reason=escalation_reason,
        )
        audit.log_event(run_id, "TICKETED", {"ticket_id": ticket["ticket_id"], "status": status})
        final_state = "ESCALATED" if escalate else "TICKETED"
        if escalate:
            audit.log_event(run_id, "ESCALATED", {"reason": escalation_reason})

    audit.finish_run(run_id, final_state)

    return {
        "run_id": run_id,
        "state": final_state,
        "classification": classification,
        "draft_response": draft,
        "sources": retrieval["sources"],
        "scoped_to_sop": retrieval["scoped_to_sop"],
        "ticket": ticket,
    }
