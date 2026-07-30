"""Regression tests for the Support Claw SOP retrieval path.

`retrieve_sop_context` previously took only (query, user_email) and called
search_faiss without org_id, so one tenant's SOP/policy documents could be
retrieved into another tenant's LLM prompt and returned `sources`. It also had
an `except Exception: files_collection.find()` fallback that enumerated every
document of every tenant on any Mongo error.
"""
import pytest


class _FakeCollection:
    def __init__(self, docs, raise_on_find=False):
        self._docs = docs
        self._raise = raise_on_find
        self.last_query = None

    def find(self, query=None):
        if self._raise:
            raise RuntimeError("mongo unavailable")
        self.last_query = query
        if not query:
            return list(self._docs)
        return [d for d in self._docs
                if all(d.get(k) == v for k, v in query.items())]

    def find_one(self, query=None):
        matches = self.find(query)
        return matches[0] if matches else None


DOCS = [
    {"org_id": "orgA", "file_id": "a-sop", "name": "orgA Refund SOP"},
    {"org_id": "orgB", "file_id": "b-sop", "name": "orgB Refund SOP"},
]


def _install(monkeypatch, collection, chunks):
    import support.sop_retriever as sr

    monkeypatch.setattr(sr, "files_collection", collection)
    monkeypatch.setattr(sr, "search_faiss",
                        lambda query, k=5, filters=None, org_id=None: [
                            c for c in chunks if c.get("org_id") == org_id
                        ])
    monkeypatch.setattr(sr, "get_document_metadata",
                        lambda doc_id, org_id=None: {"name": f"doc-{doc_id}"})
    return sr


def test_sop_doc_ids_are_scoped_to_org(monkeypatch):
    coll = _FakeCollection(DOCS)
    sr = _install(monkeypatch, coll, [])
    assert sr._sop_doc_ids("orgB") == {"b-sop"}
    assert coll.last_query == {"org_id": "orgB"}


def test_sop_doc_ids_requires_org(monkeypatch):
    sr = _install(monkeypatch, _FakeCollection(DOCS), [])
    with pytest.raises(ValueError):
        sr._sop_doc_ids(None)


def test_mongo_failure_does_not_widen_scope(monkeypatch):
    """The old code fell back to an unscoped find() here."""
    sr = _install(monkeypatch, _FakeCollection(DOCS, raise_on_find=True), [])
    with pytest.raises(RuntimeError):
        sr._sop_doc_ids("orgB")


def test_retrieve_sop_context_returns_only_callers_org(monkeypatch):
    chunks = [
        {"doc_id": "a-sop_chunk_0", "text": "orgA: refunds within 7 days", "org_id": "orgA"},
        {"doc_id": "b-sop_chunk_0", "text": "orgB: refunds within 30 days", "org_id": "orgB"},
    ]
    sr = _install(monkeypatch, _FakeCollection(DOCS), chunks)

    result = sr.retrieve_sop_context("refund window", "user@orgb.test", org_id="orgB")

    assert "orgB" in result["context_block"]
    assert "orgA" not in result["context_block"]
    assert all("a-sop" not in s["doc_id"] for s in result["sources"])


def test_retrieve_sop_context_requires_org_id(monkeypatch):
    sr = _install(monkeypatch, _FakeCollection(DOCS), [])
    with pytest.raises(TypeError):
        sr.retrieve_sop_context("refund window", "user@orgb.test")