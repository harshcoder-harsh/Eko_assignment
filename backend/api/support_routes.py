"""API routes for the Support Escalation Claw.

Slice 2: every endpoint now requires a valid JWT and is scoped to the caller's
organization. Tickets and audit runs are filtered by org_id, and cross-org
reads of a specific ticket/run return 404 (so you can't probe another org's
IDs). Running the workflow and mutating tickets require an operational role;
viewers are read-only.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from support.orchestrator import run_support_workflow
from support.ticket_store import list_tickets, get_ticket, update_ticket_status, RESOLVED
from support import audit
from auth.security import get_current_user, require_role

router = APIRouter(prefix="/support", tags=["support"])

# Generic message returned to clients on unhandled errors. The real
# exception is logged server-side; str(e) used to be sent to the caller,
# which leaked Mongo URIs, file paths and stack detail.
INTERNAL_ERROR = "An internal error occurred. Please try again."

# Roles allowed to run the agent / mutate tickets. Viewers can only read.
_OPERATOR_ROLES = ("admin", "manager", "support")


class ResolveRequest(BaseModel):
    query: str


@router.post("/resolve")
def resolve_query(req: ResolveRequest, current=Depends(require_role(*_OPERATOR_ROLES))):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    try:
        result = run_support_workflow(
            req.query,
            user_email=current["email"],
            org_id=current["org_id"],
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR)


@router.get("/tickets")
def get_tickets(status: Optional[str] = None, mine_only: bool = False,
                current=Depends(get_current_user)):
    user_email = current["email"] if mine_only else None
    tickets = list_tickets(user_email=user_email, status=status, org_id=current["org_id"])
    for t in tickets:
        t.pop("_id", None)
    return {"tickets": tickets}


@router.get("/ticket/{ticket_id}")
def get_ticket_route(ticket_id: str, current=Depends(get_current_user)):
    ticket = get_ticket(ticket_id)
    # Cross-org access is indistinguishable from "not found".
    if not ticket or ticket.get("org_id") != current["org_id"]:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.pop("_id", None)
    return ticket


@router.post("/ticket/{ticket_id}/resolve")
def resolve_ticket_route(ticket_id: str, current=Depends(require_role(*_OPERATOR_ROLES))):
    ticket = get_ticket(ticket_id)
    if not ticket or ticket.get("org_id") != current["org_id"]:
        raise HTTPException(status_code=404, detail="Ticket not found")
    update_ticket_status(ticket_id, RESOLVED)
    return {"status": "ok", "ticket_id": ticket_id, "new_status": RESOLVED}


@router.get("/audit/{run_id}")
def get_audit_run(run_id: str, current=Depends(get_current_user)):
    run = audit.get_run(run_id) or audit.get_run_by_ticket(run_id)
    if not run or run.get("org_id") != current["org_id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    run.pop("_id", None)
    return run


@router.get("/audit")
def list_audit_runs(mine_only: bool = False, current=Depends(get_current_user)):
    user_email = current["email"] if mine_only else None
    runs = audit.list_runs(user_email=user_email, org_id=current["org_id"])
    for r in runs:
        r.pop("_id", None)
    return {"runs": runs}
