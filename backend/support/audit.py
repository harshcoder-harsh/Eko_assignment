"""Audit trail for the Support Escalation Claw.

Every workflow run gets a run_id. Each step of the workflow (classification,
SOP retrieval, drafting, ticket creation, escalation decision) appends an
event to this run's log. This is what lets the agent's behavior be inspected
after the fact — required for "own a workflow" rather than "answer a
question".
"""
import uuid
from datetime import datetime

from db import db_get_collection

audit_collection = db_get_collection("audit_log")


def start_run(user_email: str, query: str) -> str:
    run_id = str(uuid.uuid4())
    audit_collection.insert_one({
        "run_id": run_id,
        "user_email": user_email,
        "query": query,
        "events": [],
        "state": "started",
        "started_at": datetime.utcnow().isoformat(),
    })
    return run_id


def log_event(run_id: str, step: str, detail: dict):
    """Append a step event to the run's audit log."""
    record = audit_collection.find_one({"run_id": run_id})
    if not record:
        return
    events = record.get("events", [])
    events.append({
        "step": step,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat(),
    })
    audit_collection.update_one({"run_id": run_id}, {"$set": {"events": events}})


def finish_run(run_id: str, final_state: str):
    audit_collection.update_one(
        {"run_id": run_id},
        {"$set": {"state": final_state, "finished_at": datetime.utcnow().isoformat()}},
    )


def get_run(run_id: str) -> dict:
    return audit_collection.find_one({"run_id": run_id})


def list_runs(user_email: str = None) -> list:
    query = {"user_email": user_email} if user_email else None
    cursor = audit_collection.find(query) if query else audit_collection.find()
    return list(cursor)
