"""Persistence for users and organizations.

Backed by the project's existing `db_get_collection` helper, so it uses Mongo
when connected and the JSON fallback otherwise (same as every other feature).
Emails are the natural login key and are stored lowercased so lookups are
case-insensitive without regex.
"""
import uuid
import datetime as dt

from db import db_get_collection
from auth.roles import Role

_users = db_get_collection("users")
_orgs = db_get_collection("organizations")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def get_user_by_email(email: str) -> dict | None:
    return _users.find_one({"email": email.strip().lower()})


def get_user_by_id(user_id: str) -> dict | None:
    return _users.find_one({"user_id": user_id})


def get_org_by_id(org_id: str) -> dict | None:
    return _orgs.find_one({"org_id": org_id})


def create_organization(name: str) -> dict:
    org = {
        "org_id": uuid.uuid4().hex,
        "name": name.strip() or "My Organization",
        "created_at": _now_iso(),
    }
    _orgs.insert_one(org)
    org.pop("_id", None)
    return org


def create_user(*, email: str, password_hash: str, name: str,
                org_id: str, role: str) -> dict:
    user = {
        "user_id": uuid.uuid4().hex,
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "name": name.strip(),
        "org_id": org_id,
        "role": role,
        "created_at": _now_iso(),
    }
    _users.insert_one(user)
    user.pop("_id", None)
    return user


def public_user(user: dict) -> dict:
    """Strip secrets before returning a user over the API."""
    return {
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "org_id": user.get("org_id"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
    }


def register_user_and_org(*, email: str, password_hash: str, name: str,
                          org_name: str) -> dict:
    """Register flow: create the org, then its first user as ADMIN.

    Returns {user, org}. Caller is responsible for the duplicate-email check
    (so it can return a clean 409 before we create the org).
    """
    org = create_organization(org_name)
    user = create_user(
        email=email,
        password_hash=password_hash,
        name=name,
        org_id=org["org_id"],
        role=Role.ADMIN.value,
    )
    return {"user": user, "org": org}