"""API routes for the Support Escalation Claw.

Endpoints:
  POST /support/resolve         - run the full workflow on a query
  GET  /support/tickets         - list tickets (optionally filter by status)
  GET  /support/ticket/{id}     - get a single ticket
  POST /support/ticket/{id}/resolve - mark a ticket resolved
  GET  /support/audit/{run_id}  - inspect the full audit trail of a workflow run
  GET  /support/audit           - list recent workflow runs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from support.orchestrator import run_support_workflow
from support.ticket_store import list_tickets, get_ticket, update_ticket_status, RESOLVED
from support import audit

router = APIRouter(prefix="/support", tags=["support"])


def _current_user_email() -> str:
    try:
        from connectors.gdrive import get_drive_service
        service = get_drive_service()
        about = service.about().get(fields="user").execute()
        return about['user']['emailAddress']
    except Exception:
        return "default_user"


class ResolveRequest(BaseModel):
    query: str


@router.post("/resolve")
def resolve_query(req: ResolveRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    user_email = _current_user_email()
    try:
        result = run_support_workflow(req.query, user_email)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets")
def get_tickets(status: Optional[str] = None, mine_only: bool = True):
    user_email = _current_user_email() if mine_only else None
    tickets = list_tickets(user_email=user_email, status=status)
    for t in tickets:
        t.pop("_id", None)
    return {"tickets": tickets}


@router.get("/ticket/{ticket_id}")
def get_ticket_route(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.pop("_id", None)
    return ticket


@router.post("/ticket/{ticket_id}/resolve")
def resolve_ticket_route(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    update_ticket_status(ticket_id, RESOLVED)
    return {"status": "ok", "ticket_id": ticket_id, "new_status": RESOLVED}


@router.get("/audit/{run_id}")
def get_audit_run(run_id: str):
    run = audit.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.pop("_id", None)
    return run


@router.get("/audit")
def list_audit_runs(mine_only: bool = True):
    user_email = _current_user_email() if mine_only else None
    runs = audit.list_runs(user_email=user_email)
    for r in runs:
        r.pop("_id", None)
    return {"runs": runs}
