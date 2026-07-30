"""Role definitions for multi-tenant RBAC.

Registration assigns roles (the first user of an org becomes ADMIN) and routes
enforce them via `auth.security.require_role`. Tokens carry a role from day one.

Roles are ordered by privilege so a simple `>=` check can express "this route
needs at least Manager". VIEWER is the floor, ADMIN the ceiling.

NOTE: SUPPORT and ANALYST deliberately share rank 1 — they are siblings, not a
hierarchy — so `role_at_least` cannot distinguish them. Routes that need to
separate the two must use an explicit role tuple with `require_role`, which is
what the support endpoints do.
"""
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"        # full control: org settings, members, billing, everything
    MANAGER = "manager"    # manage agents, documents, view all analytics
    ANALYST = "analyst"    # run analytics claws, read documents
    SUPPORT = "support"    # run the support escalation claw, manage tickets
    VIEWER = "viewer"      # read-only across the org


# Higher number = more privilege. Used later for "at least role X" checks.
ROLE_RANK = {
    Role.VIEWER: 0,
    Role.SUPPORT: 1,
    Role.ANALYST: 1,   # support and analyst are siblings, not a hierarchy
    Role.MANAGER: 2,
    Role.ADMIN: 3,
}


def role_at_least(user_role: str, required: Role) -> bool:
    """True if user_role is at least as privileged as `required`."""
    try:
        return ROLE_RANK.get(Role(user_role), -1) >= ROLE_RANK[required]
    except ValueError:
        return False