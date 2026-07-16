"""Workflow orchestrator for the Support Escalation Claw."""
from support.classifier import classify_query
from support.sop_retriever import retrieve_sop_context
from support.responder import draft_response
from support.escalation import should_escalate, is_unresolved
from support.ticket_store import create_ticket, ESCALATED, OPEN, RESOLVED
from support import audit
from support import tracing
import os

_mem0_client = None
_mem0_initialised = False


def _get_mem0():
    """Lazily build the mem0 client. Returns None if MEM0_API_KEY is unset or
    construction fails, so import never breaks and memory degrades to a no-op."""
    global _mem0_client, _mem0_initialised
    if _mem0_initialised:
        return _mem0_client
    _mem0_initialised = True
    if not os.getenv("MEM0_API_KEY"):
        return None
    try:
        from mem0 import MemoryClient
        _mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
    except Exception:
        _mem0_client = None
    return _mem0_client


def run_support_workflow(query: str, user_email: str = "default_user", org_id: str = None) -> dict:
    run_id = audit.start_run(user_email, query, org_id=org_id)
    audit.log_event(run_id, "RECEIVED", {"query": query})

    # The whole run is one Langfuse trace (root observation). Each workflow
    # step below opens a child span that nests under it automatically. When
    # Langfuse is not configured, `tracing.observation` yields a no-op and
    # the workflow behaves exactly as before.
    with tracing.observation(
        "run_support_workflow",
        as_type="agent",
        input={"query": query},
        metadata={"run_id": run_id, "user_email": user_email, "org_id": org_id},
        user_id=user_email,
        tags=[f"org:{org_id}"] if org_id else [],
    ) as root:
        # Step 1: Classify
        with tracing.observation("classify", input={"query": query}) as span:
            classification = classify_query(query)
            span.update(output=classification)
        audit.log_event(run_id, "CLASSIFIED", classification)

        # Step 2: Memory retrieve
        memory_context = ""
        with tracing.observation(
            "memory_retrieve", as_type="retriever", input={"query": query}
        ) as span:
            try:
                client = _get_mem0()
                search_result = client.search(
                    query=query,
                    filters={"user_id": user_email},
                    limit=5
                ) if client else []
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
                # Chronological transcript recall from the org+user-scoped audit log.
                try:
                    recent = audit.list_runs(user_email=user_email, org_id=org_id)
                    recent = sorted(recent, key=lambda r: r.get("started_at") or "", reverse=True)
                    prior = [r.get("query") for r in recent if r.get("run_id") != run_id][:5]
                    if prior:
                        memory_context += "\nRecent queries (most recent first):\n"
                        for q in prior:
                            memory_context += f"- {q}\n"
                except Exception:
                    pass
                audit.log_event(run_id, "MEMORY_RETRIEVED", {
                    "memories_found": len(memories_list),
                    "context": memory_context
                })
                span.update(output={
                    "memories_found": len(memories_list),
                    "context": memory_context,
                })
            except Exception as e:
                audit.log_event(run_id, "MEMORY_RETRIEVED", {
                    "memories_found": 0,
                    "error": str(e)
                })
                span.update(
                    output={"memories_found": 0, "error": str(e)},
                    level="WARNING",
                    status_message=str(e),
                )

        # Step 3: SOP retrieval
        with tracing.observation(
            "sop_retrieve", as_type="retriever", input={"query": query}
        ) as span:
            retrieval = retrieve_sop_context(query, user_email)
            audit.log_event(run_id, "SOP_RETRIEVED", {
                "scoped_to_sop": retrieval["scoped_to_sop"],
                "num_sources": len(retrieval["sources"]),
                "source_names": [s["name"] for s in retrieval["sources"]],
            })
            span.update(output={
                "scoped_to_sop": retrieval["scoped_to_sop"],
                "num_sources": len(retrieval["sources"]),
                "source_names": [s["name"] for s in retrieval["sources"]],
            })

        # Step 4: Draft response
        _model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        with tracing.observation(
            "draft_response",
            as_type="generation",
            input={
                "query": query,
                "issue_type": classification["issue_type"],
                "severity": classification["severity"],
                "has_memory_context": bool(memory_context),
            },
            metadata={"model": _model, "token_source": "estimated"},
        ) as span:
            draft = draft_response(
                query=query,
                issue_type=classification["issue_type"],
                severity=classification["severity"],
                context_block=retrieval["context_block"],
                memory_context=memory_context,
            )
            audit.log_event(run_id, "DRAFTED", {"draft_response": draft})

            # Hermes' agent.chat() returns only text, so we estimate tokens
            # (~4 chars/token) for the observability dashboard. Marked
            # "estimated" in metadata so it's not mistaken for real usage.
            _prompt_text = f"{query}\n{classification['issue_type']}\n{classification['severity']}\n{retrieval['context_block']}\n{memory_context}"
            _in_tokens = max(1, len(_prompt_text) // 4)
            _out_tokens = max(1, len(draft or "") // 4)
            span.update(
                output=draft,
                model=_model,
                usage_details={
                    "input": _in_tokens,
                    "output": _out_tokens,
                    "total": _in_tokens + _out_tokens,
                },
            )

        # Step 5: Escalation
        with tracing.observation(
            "escalation_decision",
            input={"severity": classification["severity"]},
        ) as span:
            escalate, escalation_reason = should_escalate(
                classification["severity"], draft
            )
            unresolved = is_unresolved(draft)
            span.update(output={
                "escalate": escalate,
                "unresolved": unresolved,
                "reason": escalation_reason,
            })

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
                org_id=org_id,
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
        with tracing.observation("memory_save") as span:
            try:
                client = _get_mem0()
                if client:
                    client.add(
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
                span.update(output={"saved": True})
            except Exception as e:
                span.update(
                    output={"saved": False, "error": str(e)},
                    level="WARNING",
                    status_message=str(e),
                )

        result = {
            "run_id": run_id,
            "state": final_state,
            "classification": classification,
            "draft_response": draft,
            "sources": retrieval["sources"],
            "scoped_to_sop": retrieval["scoped_to_sop"],
            "ticket": ticket,
            "memory_context": memory_context,
        }
        root.update(output={
            "state": final_state,
            "issue_type": classification["issue_type"],
            "severity": classification["severity"],
            "ticket_id": ticket["ticket_id"] if ticket else None,
        })

    # Flush outside the span so the trace is exported promptly for this
    # short-lived request. No-op when tracing is disabled.
    tracing.flush()

    return result