"""Mapping Slack identities to FlowClaw users.

WHY THIS EXISTS
---------------
A Slack interactive payload tells you a Slack user id (`U01ABCDE`) and a team id.
FlowClaw's authorisation model keys on `user_id`, `role` and `org_id`. Without a
deliberate mapping between the two, any action taken from Slack either:

  * runs unauthenticated (channel membership silently becomes a permission), or
  * gets attributed to nobody, blinding the audit trail at exactly the moment a
    human intervened.

THE FLOW
--------
1. In Slack, the user asks to link. We mint a one-time code and return it
   *ephemerally* — only that Slack user can see it. Possession of the code
   therefore proves control of the Slack account.
2. In FlowClaw, while authenticated, the user submits the code. The Bearer token
   proves control of the FlowClaw account.
3. Only with both halves present do we create the binding.

WHAT WE DELIBERATELY DO NOT DO
------------------------------
Auto-matching on email (via Slack's `users.info`) is tempting and wrong: it makes
"controls the Slack account" equivalent to "controls the FlowClaw account", so
FlowClaw's auth boundary silently becomes the Slack workspace admin's problem.
The linking step must be an explicit act by someone holding both credentials.
"""
import datetime as dt
import secrets

from db import db_get_collection

_links = db_get_collection("slack_links")
_codes = db_get_collection("slack_link_codes")

CODE_TTL_SECONDS = 10 * 60
_MAX_ACTIVE_CODES_PER_USER = 3


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.isoformat()


def create_link_code(slack_team_id: str, slack_user_id: str) -> str:
    """Mint a short-lived single-use code for a Slack user.

    Rate-limited per Slack user so a spammed slash command cannot flood the
    collection or widen the guessing window.
    """
    if not slack_team_id or not slack_user_id:
        raise ValueError("slack_team_id and slack_user_id are required")

    now = _now()
    # Drop this user's expired codes, then cap the number of live ones.
    _codes.delete_many({
        "slack_user_id": slack_user_id,
        "expires_at": {"$lt": _iso(now)},
    })
    active = _codes.count_documents({"slack_user_id": slack_user_id})
    if active >= _MAX_ACTIVE_CODES_PER_USER:
        raise ValueError("Too many pending link codes. Try again in a few minutes.")

    # 16 bytes url-safe: not guessable within the 10 minute window.
    code = secrets.token_urlsafe(16)
    _codes.insert_one({
        "code": code,
        "slack_team_id": slack_team_id,
        "slack_user_id": slack_user_id,
        "created_at": _iso(now),
        "expires_at": _iso(now + dt.timedelta(seconds=CODE_TTL_SECONDS)),
    })
    return code


def redeem_link_code(code: str, *, user_id: str, org_id: str, email: str) -> dict:
    """Bind a Slack identity to a FlowClaw user. Called from an AUTHENTICATED route.

    Raises ValueError on an unknown, expired or already-used code.
    """
    if not code:
        raise ValueError("A link code is required.")

    entry = _codes.find_one({"code": code.strip()})
    if not entry:
        raise ValueError("That link code is not valid.")

    # Single use: consume it before doing anything else, so a race cannot
    # redeem the same code twice.
    _codes.delete_one({"code": entry["code"]})

    if entry.get("expires_at", "") < _iso(_now()):
        raise ValueError("That link code has expired. Request a new one in Slack.")

    link = {
        "slack_team_id": entry["slack_team_id"],
        "slack_user_id": entry["slack_user_id"],
        "user_id": user_id,
        "org_id": org_id,
        "email": email,
        "linked_at": _iso(_now()),
    }
    # One FlowClaw account per Slack identity per workspace. Re-linking replaces.
    _links.update_one(
        {"slack_team_id": link["slack_team_id"],
         "slack_user_id": link["slack_user_id"]},
        {"$set": link},
        upsert=True,
    )
    return link


def get_link(slack_team_id: str, slack_user_id: str) -> dict | None:
    if not slack_team_id or not slack_user_id:
        return None
    return _links.find_one({
        "slack_team_id": slack_team_id,
        "slack_user_id": slack_user_id,
    })


def unlink(slack_team_id: str, slack_user_id: str) -> bool:
    result = _links.delete_one({
        "slack_team_id": slack_team_id,
        "slack_user_id": slack_user_id,
    })
    return getattr(result, "deleted_count", 0) > 0