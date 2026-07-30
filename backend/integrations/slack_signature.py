"""Slack request signature verification.

Every request Slack sends is signed with the app's Signing Secret. Verifying it
answers exactly one question: *did this request come from Slack?*

It does NOT answer "is this person allowed to do this?" — that is the job of
`slack_links` + the same `require_role` / org checks the HTTP routes use. Keeping
those two questions separate is the whole point of this module.

Reference: https://api.slack.com/authentication/verifying-requests-from-slack
"""
import hashlib
import hmac
import os
import time

# Slack recommends rejecting anything older than 5 minutes to bound replay.
MAX_SKEW_SECONDS = 60 * 5

_VERSION = "v0"


class SlackSignatureError(Exception):
    """Raised when a request cannot be attributed to Slack."""


def _signing_secret() -> str:
    secret = os.getenv("SLACK_SIGNING_SECRET")
    if not secret:
        # Fail closed. An unset secret must never mean "skip verification".
        raise SlackSignatureError(
            "SLACK_SIGNING_SECRET is not set; refusing to accept Slack requests."
        )
    return secret


def verify_slack_request(body: bytes, timestamp: str | None, signature: str | None,
                         *, now: float | None = None) -> None:
    """Raise SlackSignatureError unless `body` was signed by Slack.

    `timestamp` is the X-Slack-Request-Timestamp header, `signature` the
    X-Slack-Signature header. `now` is injectable for tests.
    """
    if not timestamp or not signature:
        raise SlackSignatureError("Missing Slack signature headers.")

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        raise SlackSignatureError("Malformed Slack timestamp.")

    current = time.time() if now is None else now
    if abs(current - ts) > MAX_SKEW_SECONDS:
        # Replay protection: an attacker who captures a valid request cannot
        # reuse it indefinitely.
        raise SlackSignatureError("Slack timestamp outside acceptable window.")

    basestring = f"{_VERSION}:{timestamp}:".encode() + body
    expected = _VERSION + "=" + hmac.new(
        _signing_secret().encode(), basestring, hashlib.sha256
    ).hexdigest()

    # Constant-time comparison: a byte-by-byte compare leaks the correct
    # signature through timing.
    if not hmac.compare_digest(expected, signature):
        raise SlackSignatureError("Slack signature mismatch.")
