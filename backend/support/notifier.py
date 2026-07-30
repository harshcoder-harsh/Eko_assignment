"""Slack notification for escalated tickets.

Fire-and-forget by design: a failed notification must never fail the
escalation itself, and must never block the response to the user.
"""
import os
import threading

import requests


def notify_escalation(ticket_id: str, query: str, issue_type: str,
                      severity: str, reason: str, org_id: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return  # not configured; stay silent like the other optional integrations

    payload = {
        "text": f":rotating_light: Ticket escalated — {severity} / {issue_type}",
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": f"Escalated: {issue_type} ({severity})"}},
            {"type": "section",
             "text": {"type": "mrkdwn", "text": f"*Query*\n{query[:500]}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Ticket*\n`{ticket_id}`"},
                {"type": "mrkdwn", "text": f"*Reason*\n{reason}"},
            ]},
        ],
    }

    def _send():
        try:
            requests.post(webhook, json=payload, timeout=5)
        except Exception as e:
            print(f"Slack notification failed for ticket {ticket_id}: {e}")

    threading.Thread(target=_send, daemon=True).start()