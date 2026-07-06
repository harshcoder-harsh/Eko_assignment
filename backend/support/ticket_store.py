"""Support ticket persistence.

Tickets are created when the agent cannot fully resolve a query from SOP
context, or when severity requires escalation. Uses the same Mongo/JSON
fallback pattern as the rest of the app (db.db_get_collection), so this works
identically whether MongoDB is configured or not.
"""
import uuid
from datetime import datetime

from db import db_get_collection

tickets_collection = db_get_collection("tickets")

OPEN = "open"
ESCALATED = "escalated"
RESOLVED = "resolved"

VALID_STATUSES = [OPEN, ESCALATED, RESOLVED]


def create_ticket(user_email: str, query: str, issue_type: str, severity: str,
                   draft_response: str, status: str = OPEN, escalation_reason: str = None,
                   org_id: str = None) -> dict:
    ticket = {
        "ticket_id": str(uuid.uuid4()),
        "org_id": org_id,
        "user_email": user_email,
        "query": query,
        "issue_type": issue_type,
        "severity": severity,
        "draft_response": draft_response,
        "status": status,
        "escalation_reason": escalation_reason,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    tickets_collection.insert_one(ticket)
    ticket.pop("_id", None)
    return ticket


def list_tickets(user_email: str = None, status: str = None, org_id: str = None) -> list:
    query = {}
    if org_id:
        query["org_id"] = org_id
    if user_email:
        query["user_email"] = user_email
    if status:
        query["status"] = status
    cursor = tickets_collection.find(query) if query else tickets_collection.find()
    return list(cursor)


def get_ticket(ticket_id: str) -> dict:
    return tickets_collection.find_one({"ticket_id": ticket_id})


def update_ticket_status(ticket_id: str, status: str) -> bool:
    if status not in VALID_STATUSES:
        return False
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow().isoformat()}},
    )
    return True
