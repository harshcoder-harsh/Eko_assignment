"""Authorisation tests for Slack-initiated actions.

A verified Slack signature proves only that a request came from Slack. These
tests pin the property that actually matters: a button click is subjected to the
SAME role and tenant checks as POST /support/ticket/{id}/resolve, resolved
through an explicitly linked FlowClaw user.

The org test is the important one. One webhook posts every tenant's escalations
into a single channel, so a Slack user can physically see a button for a ticket
belonging to an org they are not a member of.
"""
import pytest
"""Verify the Slack action enforces the SAME two checks as the HTTP route."""
import os, sys, json, time, hmac, hashlib, types
os.environ["SLACK_SIGNING_SECRET"] = "s3cret"
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod-32b"

# --- in-memory fakes ---
class Coll:
    def __init__(self): self.docs = []
    def find_one(self, q): return next((d for d in self.docs if all(d.get(k)==v for k,v in q.items())), None)
    def insert_one(self, d): self.docs.append(dict(d))
    def count_documents(self, q): return len([d for d in self.docs if all(d.get(k)==v for k,v in q.items())])
    def delete_many(self, q):
        keep=[]; n=0
        for d in self.docs:
            drop=True
            for k,v in q.items():
                if isinstance(v,dict) and "$lt" in v:
                    if not (d.get(k,"") < v["$lt"]): drop=False
                elif d.get(k)!=v: drop=False
            if drop: n+=1
            else: keep.append(d)
        self.docs=keep; return types.SimpleNamespace(deleted_count=n)
    def delete_one(self, q):
        t=self.find_one(q)
        if t: self.docs.remove(t); return types.SimpleNamespace(deleted_count=1)
        return types.SimpleNamespace(deleted_count=0)
    def update_one(self, q, upd, upsert=False):
        t=self.find_one(q)
        if t: t.update(upd.get("$set",{}))
        elif upsert: self.insert_one({**q, **upd.get("$set",{})})

colls = {}
def fake_get_collection(name):
    return colls.setdefault(name, Coll())

import db
db.db_get_collection = fake_get_collection
db.files_collection = Coll(); db.chats_collection = Coll()

import integrations.slack_links as links
links._links = fake_get_collection("slack_links")
links._codes = fake_get_collection("slack_link_codes")

# --- fixtures: two orgs ---
USERS = {
  "u_support_A": {"user_id":"u_support_A","email":"sup@a.test","role":"support","org_id":"orgA"},
  "u_viewer_A":  {"user_id":"u_viewer_A","email":"view@a.test","role":"viewer","org_id":"orgA"},
  "u_admin_B":   {"user_id":"u_admin_B","email":"adm@b.test","role":"admin","org_id":"orgB"},
}
TICKETS = {"tkt_A":{"ticket_id":"tkt_A","org_id":"orgA","status":"escalated"}}

import api.slack_routes as sr
sr.get_user_by_id = lambda uid: USERS.get(uid)
sr.get_ticket = lambda tid: TICKETS.get(tid)
resolved = []


@pytest.fixture(autouse=True)
def _reset():
    resolved.clear()
    yield
sr.update_ticket_status = lambda tid, st: (resolved.append((tid,st)), True)[1]
sr.audit = types.SimpleNamespace(get_run_by_ticket=lambda t: None, log_event=lambda *a, **k: None)

from fastapi import FastAPI
from fastapi.testclient import TestClient
app = FastAPI(); app.include_router(sr.router)
client = TestClient(app)

def click(slack_user, ticket_id, team="T1"):
    payload = json.dumps({"actions":[{"action_id":"resolve_ticket","value":ticket_id}],
                          "user":{"id":slack_user},"team":{"id":team}})
    from urllib.parse import urlencode
    body = urlencode({"payload":payload}).encode()
    ts = str(int(time.time()))
    sig = "v0=" + hmac.new(b"s3cret", f"v0:{ts}:".encode()+body, hashlib.sha256).hexdigest()
    return client.post("/slack/interactivity", content=body,
        headers={"Content-Type":"application/x-www-form-urlencoded",
                 "X-Slack-Request-Timestamp":ts,"X-Slack-Signature":sig})

def link(slack_user, user_id):
    code = links.create_link_code("T1", slack_user)
    u = USERS[user_id]
    links.redeem_link_code(code, user_id=u["user_id"], org_id=u["org_id"], email=u["email"])



def test_unlinked_slack_user_is_rejected():
    r = click("U_UNLINKED_T", "tkt_A")
    assert "isn't linked" in r.json()["text"]
    assert not resolved


def test_insufficient_role_is_rejected():
    link("U_VIEWER_T", "u_viewer_A")
    r = click("U_VIEWER_T", "tkt_A")
    assert "can't resolve" in r.json()["text"]
    assert not resolved


def test_admin_of_other_org_cannot_resolve():
    """Cross-tenant write via the shared channel. Reported as not-found."""
    link("U_ADMIN_B_T", "u_admin_B")
    r = click("U_ADMIN_B_T", "tkt_A")
    assert "not found" in r.json()["text"].lower()
    assert not resolved


def test_operator_of_owning_org_can_resolve():
    link("U_SUPPORT_A_T", "u_support_A")
    r = click("U_SUPPORT_A_T", "tkt_A")
    assert resolved == [("tkt_A", "resolved")]
    assert "sup@a.test" in r.json()["text"]


def test_link_code_is_single_use():
    c = links.create_link_code("T1", "U_ONCE")
    links.redeem_link_code(c, user_id="u_support_A", org_id="orgA", email="sup@a.test")
    with pytest.raises(ValueError):
        links.redeem_link_code(c, user_id="u_admin_B", org_id="orgB", email="adm@b.test")


def test_unknown_link_code_is_rejected():
    with pytest.raises(ValueError):
        links.redeem_link_code("not-a-real-code", user_id="u_admin_B",
                               org_id="orgB", email="x@b.test")


def test_forged_signature_is_rejected():
    from urllib.parse import urlencode
    body = urlencode({"payload": "{}"}).encode()
    ts = str(int(time.time()))
    r = client.post("/slack/interactivity", content=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": "v0=deadbeef",
    })
    assert r.status_code == 401