"""Tenant isolation for the AI Observability API.

The bug these tests pin down: the observability endpoints used to read the
*entire* Langfuse project for any authenticated caller, so logging in with a
different account still showed the previous account's traces. The fix stamps
every trace with an ``org:<org_id>`` tag at write time and filters every read
by the caller's org tag, with cross-org trace IDs returning 404 (same
convention as tickets/audit).

Langfuse itself is faked here: we assert (a) the org filter is actually passed
to the Langfuse list API, and (b) the detail endpoint refuses traces that
don't carry the caller's org tag.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import observability_routes
from auth.security import get_current_user
from support import tracing


# --- fake Langfuse client -----------------------------------------------------
class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeTraceApi:
    def __init__(self, traces):
        self._traces = traces
        self.list_calls = []  # kwargs of every list() call, for assertions

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        tags = kwargs.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        data = [
            t for t in self._traces
            if all(tag in (t.get("tags") or []) for tag in tags)
        ]
        user_id = kwargs.get("user_id")
        if user_id:
            data = [t for t in data if t.get("user_id") == user_id]
        return _FakeResp(data)

    def get(self, trace_id):
        for t in self._traces:
            if t["id"] == trace_id:
                return t
        raise Exception("trace not found in fake langfuse")


class _FakeApi:
    def __init__(self, traces):
        self.trace = _FakeTraceApi(traces)


class _FakeLangfuse:
    def __init__(self, traces):
        self.api = _FakeApi(traces)


_TRACES = [
    {
        "id": "tr-a1", "name": "run_support_workflow", "timestamp": "2026-07-15T10:00:00Z",
        "latency": 2.1, "total_cost": 0.003, "user_id": "alice@orga.com",
        "tags": ["org:orgA"], "output": {"state": "RESOLVED"}, "observations": [],
    },
    {
        "id": "tr-a2", "name": "run_support_workflow", "timestamp": "2026-07-15T11:00:00Z",
        "latency": 3.4, "total_cost": 0.004, "user_id": "adam@orga.com",
        "tags": ["org:orgA"], "output": {"state": "ESCALATED"}, "observations": [],
    },
    {
        "id": "tr-b1", "name": "run_support_workflow", "timestamp": "2026-07-15T12:00:00Z",
        "latency": 1.2, "total_cost": 0.002, "user_id": "bob@orgb.com",
        "tags": ["org:orgB"], "output": {"state": "RESOLVED"}, "observations": [],
    },
    {  # legacy trace written before the fix: no org tag → visible to no one
        "id": "tr-legacy", "name": "run_support_workflow", "timestamp": "2026-07-14T09:00:00Z",
        "latency": 5.0, "total_cost": 0.01, "user_id": None,
        "tags": [], "output": {"state": "RESOLVED"}, "observations": [],
    },
]


def _user(org_id, email):
    return {"user_id": f"u-{email}", "email": email, "org_id": org_id, "role": "admin"}


@pytest.fixture
def client_for(monkeypatch):
    """Factory: an authenticated TestClient for a given org, backed by the
    fake Langfuse project above. Returns (http_client, fake_langfuse)."""
    def _make(org_id, email):
        fake = _FakeLangfuse([dict(t) for t in _TRACES])
        monkeypatch.setattr(tracing, "get_client", lambda: fake)

        app = FastAPI()
        app.include_router(observability_routes.router)
        app.dependency_overrides[get_current_user] = lambda: _user(org_id, email)
        return TestClient(app), fake
    return _make


# --- /observability/traces ----------------------------------------------------
def test_traces_only_returns_callers_org(client_for):
    http, fake = client_for("orgA", "alice@orga.com")
    r = http.get("/observability/traces")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()["traces"]}
    assert ids == {"tr-a1", "tr-a2"}
    # The org filter must be pushed down to Langfuse, not applied client-side.
    assert fake.api.trace.list_calls[0]["tags"] == ["org:orgA"]


def test_traces_other_org_sees_only_its_own(client_for):
    http, _ = client_for("orgB", "bob@orgb.com")
    ids = {t["id"] for t in http.get("/observability/traces").json()["traces"]}
    assert ids == {"tr-b1"}


def test_traces_mine_only_narrows_to_caller(client_for):
    http, _ = client_for("orgA", "alice@orga.com")
    r = http.get("/observability/traces", params={"mine_only": True})
    ids = {t["id"] for t in r.json()["traces"]}
    assert ids == {"tr-a1"}


def test_legacy_untagged_traces_leak_to_no_one(client_for):
    for org, email in (("orgA", "alice@orga.com"), ("orgB", "bob@orgb.com")):
        http, _ = client_for(org, email)
        ids = {t["id"] for t in http.get("/observability/traces").json()["traces"]}
        assert "tr-legacy" not in ids


# --- /observability/trace/{id} -------------------------------------------------
def test_trace_detail_own_org_ok(client_for):
    http, _ = client_for("orgA", "alice@orga.com")
    r = http.get("/observability/trace/tr-a1")
    assert r.status_code == 200
    assert r.json()["id"] == "tr-a1"


def test_trace_detail_cross_org_is_404(client_for):
    http, _ = client_for("orgA", "alice@orga.com")
    r = http.get("/observability/trace/tr-b1")
    assert r.status_code == 404
    # Indistinguishable from a nonexistent ID — no probing across orgs.
    assert r.json()["detail"] == "Trace not found"


def test_trace_detail_legacy_untagged_is_404(client_for):
    http, _ = client_for("orgA", "alice@orga.com")
    assert http.get("/observability/trace/tr-legacy").status_code == 404


# --- /observability/overview ----------------------------------------------------
def test_overview_aggregates_only_callers_org(client_for):
    http, fake = client_for("orgB", "bob@orgb.com")
    r = http.get("/observability/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_traces"] == 1  # only tr-b1, not orgA's two runs
    assert fake.api.trace.list_calls[0]["tags"] == ["org:orgB"]


# --- write-side stamping ---------------------------------------------------------
def test_noop_span_supports_update_trace():
    """When tracing is disabled the orchestrator's root.update_trace(...) must
    stay a harmless no-op."""
    span = tracing._NoopSpan()
    assert span.update_trace(user_id="a@b.com", tags=["org:orgA"]) is span