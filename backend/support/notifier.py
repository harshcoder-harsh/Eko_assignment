"""Slack notification for escalated tickets.

Fire-and-forget by design, matching how Groq / Langfuse / mem0 are handled
elsewhere in this codebase:

  * If SLACK_WEBHOOK_URL is unset the notifier is a no-op, so the app runs
    unchanged without Slack configured.
  * Delivery happens on a daemon thread. A Slack outage must never add latency
    to a support run, and must never turn a successfully-escalated ticket into
    a failed request.
  * Failures are logged, not raised.

MULTI-TENANCY NOTE: a single webhook means every org's escalations land in the
same channel, so whoever reads it sees all tenants' customer queries. That is
acceptable for a single-tenant deployment or a demo. For real multi-tenant use,
either resolve the webhook per org_id or send only the ticket id and let staff
open the ticket in-app behind the normal authorisation checks.
"""
import os
import threading

import requests

_TIMEOUT = 5
_QUERY_PREVIEW_CHARS = 500


def _actions_block(ticket_id):
    """Resolve button + deep link.

    The button is only useful once the clicking Slack user has linked their
    FlowClaw account (`/flowclaw link`); until then the handler replies
    ephemerally telling them to. The deep link always works and routes through
    normal web auth, so it stays as the fallback path.
    """
    app_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    elements = [{
        "type": "button",
        "text": {"type": "plain_text", "text": "Open in FlowClaw"},
        "url": f"{app_url}/support?ticket={ticket_id}",
    }]
    if os.getenv("SLACK_INTERACTIVITY_ENABLED", "").lower() == "true":
        elements.insert(0, {
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "Resolve"},
            "action_id": "resolve_ticket",
            "value": ticket_id,
            "confirm": {
                "title": {"type": "plain_text", "text": "Resolve this ticket?"},
                "text": {"type": "mrkdwn", "text": f"Marks `{ticket_id}` resolved."},
                "confirm": {"type": "plain_text", "text": "Resolve"},
                "deny": {"type": "plain_text", "text": "Cancel"},
            },
        })
    return {"type": "actions", "elements": elements}


def _build_payload(ticket_id, query, issue_type, severity, reason, org_id):
    preview = query if len(query) <= _QUERY_PREVIEW_CHARS else query[:_QUERY_PREVIEW_CHARS] + "…"
    return {
        # Fallback text for notifications and unsupported clients.
        "text": f"Ticket escalated — {severity} / {issue_type} (#{ticket_id})",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Escalated: {issue_type} ({severity})"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Customer query*\n{preview}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticket*\n`{ticket_id}`"},
                    {"type": "mrkdwn", "text": f"*Org*\n`{org_id}`"},
                    {"type": "mrkdwn", "text": f"*Reason*\n{reason or 'not specified'}"},
                ],
            },
            _actions_block(ticket_id),
        ],
    }


def notify_escalation(ticket_id, query, issue_type, severity, reason, org_id):
    """Post an escalation to Slack. Never raises, never blocks."""
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return

    payload = _build_payload(ticket_id, query, issue_type, severity, reason, org_id)

    def _send():
        try:
            resp = requests.post(webhook, json=payload, timeout=_TIMEOUT)
            if resp.status_code >= 400:
                print(f"Slack notification for ticket {ticket_id} "
                      f"returned {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            print(f"Slack notification failed for ticket {ticket_id}: {exc}")

    threading.Thread(target=_send, daemon=True, name=f"slack-{ticket_id}").start