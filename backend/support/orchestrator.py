"""Workflow orchestrator for the Support Escalation Claw."""
from support.classifier import classify_query
from support.sop_retriever import retrieve_sop_context
from support.responder import draft_response
from support.escalation import should_escalate, is_unresolved
from support.ticket_store import create_ticket, ESCALATED, OPEN, RESOLVED
from support import audit
from mem0 import MemoryClient
import os

mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))


def run_support_workflow(query: str, user_email: str = "default_user") -> dict:
    run_id = audit.start_run(user_email, query)
    audit.log_event(run_id, "RECEIVED", {"query": query})

    # Step 1: Classify
    classification = classify_query(query)
    audit.log_event(run_id, "CLASSIFIED", classification)

    # Step 2: Memory retrieve
    memory_context = ""
    try:
        search_result = mem0_client.search(
            query=query,
            filters={"user_id": user_email},
            limit=5
        )
        if isinstance(search_result, dict):
            memories_list = search_result.get('results', [])
        elif isinstance(search_result, list):
            memories_list = search_result
        else:
            memories_list = []

        if memories_list:
            memory_context = "Previous interaction context:\n"
            for mem in memories_list:
                if isinstance(mem, dict):
                    memory_context += f"- {mem.get('memory', str(mem))}\n"
                else:
                    memory_context += f"- {str(mem)}\n"

        audit.log_event(run_id, "MEMORY_RETRIEVED", {
            "memories_found": len(memories_list),
            "context": memory_context
        })
    except Exception as e:
        audit.log_event(run_id, "MEMORY_RETRIEVED", {
            "memories_found": 0,
            "error": str(e)
        })

    # Step 3: SOP retrieval
    retrieval = retrieve_sop_context(query, user_email)
    audit.log_event(run_id, "SOP_RETRIEVED", {
        "scoped_to_sop": retrieval["scoped_to_sop"],
        "num_sources": len(retrieval["sources"]),
        "source_names": [s["name"] for s in retrieval["sources"]],
    })

    # Step 4: Draft response
    draft = draft_response(
        query=query,
        issue_type=classification["issue_type"],
        severity=classification["severity"],
        context_block=retrieval["context_block"],
        memory_context=memory_context,
    )
    audit.log_event(run_id, "DRAFTED", {"draft_response": draft})

    # Step 5: Escalation
    escalate, escalation_reason = should_escalate(
        classification["severity"], draft
    )
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
        audit.log_event(run_id, "TICKETED", {
            "ticket_id": ticket["ticket_id"],
            "status": status
        })
        final_state = "ESCALATED" if escalate else "TICKETED"
        if escalate:
            audit.log_event(run_id, "ESCALATED", {
                "reason": escalation_reason
            })

    audit.finish_run(run_id, final_state)

    # Step 6: Save memory
    try:
        mem0_client.add(
            messages=[
                {"role": "user", "content": query},
                {"role": "assistant", "content": draft}
            ],
            user_id=user_email,
            metadata={
                "issue_type": classification["issue_type"],
                "severity": classification["severity"],
                "state": final_state,
                "ticket_id": ticket["ticket_id"] if ticket else None,
                "run_id": run_id
            }
        )
    except Exception:
        pass

    return {
        "run_id": run_id,
        "state": final_state,
        "classification": classification,
        "draft_response": draft,
        "sources": retrieval["sources"],
        "scoped_to_sop": retrieval["scoped_to_sop"],
        "ticket": ticket,
        "memory_context": memory_context,
    }
