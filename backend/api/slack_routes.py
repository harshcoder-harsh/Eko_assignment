"""Slack endpoints: account linking and interactive actions.

AUTHORISATION CONTRACT
----------------------
`POST /support/ticket/{id}/resolve` enforces two things:

    current = Depends(require_role(*_OPERATOR_ROLES))     # role check
    ticket.org_id == current["org_id"]                    # tenant check

Any action arriving from Slack MUST pass BOTH, resolved through an explicitly
linked FlowClaw user. A verified Slack signature only proves the request came
from Slack — it says nothing about permission. Channel membership is not a role.

The tenant check matters especially here: one webhook posts every org's
escalations into a single channel, so a Slack user whose FlowClaw account lives
in org A can physically see a button for a ticket in org B. Without the org
comparison below, that button would be a cross-tenant write.
"""
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth.security import get_current_user
from auth.store import get_user_by_id
from auth.roles import Role
from integrations.slack_links import (
    create_link_code,
    redeem_link_code,
    get_link,
    unlink,
    CODE_TTL_SECONDS,
)
from integrations.slack_signature import verify_slack_request, SlackSignatureError
from support import audit
from support.ticket_store import get_ticket, update_ticket_status, RESOLVED

router = APIRouter(prefix="/slack", tags=["slack"])

# Mirrors _OPERATOR_ROLES in api/support_routes.py. Imported rather than
# redefined would be better; kept explicit here so the coupling is visible.
_OPERATOR_ROLES = (Role.ADMIN, Role.MANAGER, Role.SUPPORT)


def _ephemeral(text: str) -> dict:
    """Reply visible only to the clicking user."""
    return {"response_type": "ephemeral", "replace_original": False, "text": text}


# --------------------------------------------------------------------------
# Linking: called from FlowClaw, authenticated with a normal Bearer token.
# --------------------------------------------------------------------------

class RedeemRequest(BaseModel):
    code: str


@router.post("/link")
def redeem_link(req: RedeemRequest, current=Depends(get_current_user)):
    """Bind the Slack identity that generated `code` to the calling user.

    The Bearer token proves the FlowClaw side; the code proves the Slack side.
    """
    try:
        link = redeem_link_code(
            req.code,
            user_id=current["user_id"],
            org_id=current["org_id"],
            email=current["email"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "status": "linked",
        "slack_user_id": link["slack_user_id"],
        "email": link["email"],
    }


@router.delete("/link")
def remove_link(slack_user_id: str, slack_team_id: str,
                current=Depends(get_current_user)):
    """Unlink, but only a link that belongs to the caller."""
    existing = get_link(slack_team_id, slack_user_id)
    if not existing or existing.get("user_id") != current["user_id"]:
        raise HTTPException(status_code=404, detail="Link not found")
    unlink(slack_team_id, slack_user_id)
    return {"status": "unlinked"}


# --------------------------------------------------------------------------
# Slack -> FlowClaw. Signature-verified, never session-authenticated.
# --------------------------------------------------------------------------

async def _verified_form(request: Request) -> dict:
    """Read the raw body, verify Slack's signature, return parsed form fields.

    The signature covers the RAW bytes, so the body must be read before any
    parsing and verified before any of it is trusted.
    """
    body = await request.body()
    try:
        verify_slack_request(
            body,
            request.headers.get("X-Slack-Request-Timestamp"),
            request.headers.get("X-Slack-Signature"),
        )
    except SlackSignatureError as exc:
        # 401, not 400: this is an authentication failure.
        raise HTTPException(status_code=401, detail=str(exc))

    from urllib.parse import parse_qs
    return {k: v[0] for k, v in parse_qs(body.decode()).items() if v}


@router.post("/commands")
async def slash_command(request: Request):
    """Handle `/flowclaw link` — issues a one-time code, ephemerally."""
    form = await _verified_form(request)
    text = (form.get("text") or "").strip().lower()
    team_id = form.get("team_id")
    user_id = form.get("user_id")

    if text != "link":
        return _ephemeral("Usage: `/flowclaw link` — connects your Slack account "
                          "to your FlowClaw account.")

    try:
        code = create_link_code(team_id, user_id)
    except ValueError as exc:
        return _ephemeral(str(exc))

    minutes = CODE_TTL_SECONDS // 60
    return _ephemeral(
        f"Your link code is `{code}`.\n"
        f"Sign in to FlowClaw and submit it under Settings → Slack within "
        f"{minutes} minutes. Only you can see this message."
    )


@router.post("/interactivity")
async def interactivity(request: Request):
    """Handle button clicks on escalation messages."""
    form = await _verified_form(request)

    try:
        payload = json.loads(form.get("payload", "{}"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed payload")

    actions = payload.get("actions") or []
    if not actions:
        return _ephemeral("No action received.")

    action_id = actions[0].get("action_id")
    ticket_id = actions[0].get("value")
    slack_user_id = (payload.get("user") or {}).get("id")
    slack_team_id = (payload.get("team") or {}).get("id")

    if action_id != "resolve_ticket":
        return _ephemeral(f"Unsupported action: {action_id}")

    # --- Step 1: which FlowClaw user is this? ---
    link = get_link(slack_team_id, slack_user_id)
    if not link:
        return _ephemeral(
            "Your Slack account isn't linked to FlowClaw yet. "
            "Run `/flowclaw link` to connect it."
        )

    user = get_user_by_id(link["user_id"])
    if not user:
        # Link points at a deleted account: treat as unlinked, don't guess.
        return _ephemeral("Your linked FlowClaw account no longer exists. "
                          "Run `/flowclaw link` again.")

    # --- Step 2: role check, identical to require_role on the HTTP route ---
    if user.get("role") not in [r.value if hasattr(r, "value") else r
                                for r in _OPERATOR_ROLES]:
        return _ephemeral(
            f"Your FlowClaw role ({user.get('role')}) can't resolve tickets. "
            "Requires Admin, Manager or Support."
        )

    # --- Step 3: tenant check, identical to the HTTP route ---
    ticket = get_ticket(ticket_id)
    if not ticket or ticket.get("org_id") != user.get("org_id"):
        # Cross-org is indistinguishable from not-found, same as the HTTP route.
        return _ephemeral("Ticket not found.")

    if ticket.get("status") == RESOLVED:
        return _ephemeral(f"Ticket `{ticket_id}` was already resolved.")

    update_ticket_status(ticket_id, RESOLVED)

    # --- Step 4: attribute the action to a real FlowClaw identity ---
    run = audit.get_run_by_ticket(ticket_id)
    if run:
        audit.log_event(run["run_id"], "RESOLVED_BY_HUMAN", {
            "ticket_id": ticket_id,
            "resolved_by": user.get("email"),
            "via": "slack",
            "slack_user_id": slack_user_id,
        })

    return _ephemeral(f"Resolved `{ticket_id}` as {user.get('email')}.")