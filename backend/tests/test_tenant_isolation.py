
import faiss
import numpy as np
import pytest


def _random_normalized(n, dim=384):
    v = np.random.rand(n, dim).astype("float32")
    faiss.normalize_L2(v)
    return v


def _seed(vs, chunks):
    index = faiss.IndexFlatIP(vs.DIMENSION)
    index.add(_random_normalized(len(chunks)))
    vs.save_faiss_index(index)
    vs.save_chunks(chunks)


def test_remove_org_keeps_other_orgs(isolated_vector_store):
    vs = isolated_vector_store
    chunks = [
        {"doc_id": "d1", "text": "a", "org_id": "orgA"},
        {"doc_id": "d2", "text": "b", "org_id": "orgA"},
        {"doc_id": "d3", "text": "c", "org_id": "orgB"},
        {"doc_id": "d4", "text": "d", "org_id": "orgA"},
        {"doc_id": "d5", "text": "e", "org_id": "orgB"},
    ]
    _seed(vs, chunks)
    removed = vs.remove_org_from_index("orgA")
    assert removed == 3
    remaining = vs.load_chunks()
    assert len(remaining) == 2
    assert {c["org_id"] for c in remaining} == {"orgB"}
    assert vs.load_faiss_index().ntotal == 2


def test_remove_org_not_present_is_noop(isolated_vector_store):
    vs = isolated_vector_store
    chunks = [
        {"doc_id": "d1", "text": "a", "org_id": "orgB"},
        {"doc_id": "d2", "text": "b", "org_id": "orgB"},
    ]
    _seed(vs, chunks)
    removed = vs.remove_org_from_index("orgA-does-not-exist")
    assert removed == 0
    assert vs.load_faiss_index().ntotal == 2
    assert len(vs.load_chunks()) == 2


def test_remove_org_on_empty_store(isolated_vector_store):
    vs = isolated_vector_store
    assert vs.remove_org_from_index("orgA") == 0


# --- retrieval scoping -------------------------------------------------------
# The tests above only cover DELETION (remove_org_from_index). The leak that
# shipped was on the READ path: search_faiss defaulted org_id=None, which
# disabled the tenant filter entirely, and the Support Claw's SOP retriever
# called it without org_id. These two tests cover that path.

def test_search_is_scoped_to_org(isolated_vector_store, stub_embedder):
    vs = isolated_vector_store
    chunks = [
        {"doc_id": "a1", "text": "orgA internal refund policy", "org_id": "orgA"},
        {"doc_id": "a2", "text": "orgA escalation runbook", "org_id": "orgA"},
        {"doc_id": "b1", "text": "orgB refund policy", "org_id": "orgB"},
    ]
    _seed(vs, chunks)

    results = vs.search_faiss("refund policy", k=10, org_id="orgB")
    assert results, "org B should still get its own chunks back"
    assert all(c["org_id"] == "orgB" for c in results)
    assert not any(c["doc_id"].startswith("a") for c in results)


def test_unscoped_search_is_rejected(isolated_vector_store, stub_embedder):
    vs = isolated_vector_store
    _seed(vs, [{"doc_id": "a1", "text": "orgA secret", "org_id": "orgA"}])

    with pytest.raises(ValueError):
        vs.search_faiss("secret", k=5)
    with pytest.raises(ValueError):
        vs.search_faiss("secret", k=5, org_id=None)


def test_chunks_without_org_id_are_never_returned(isolated_vector_store, stub_embedder):
    """Legacy chunks ingested before org support must not leak to any tenant."""
    vs = isolated_vector_store
    _seed(vs, [
        {"doc_id": "legacy", "text": "pre-multitenancy document"},
        {"doc_id": "b1", "text": "orgB document", "org_id": "orgB"},
    ])
    results = vs.search_faiss("document", k=10, org_id="orgB")
    assert all(c.get("org_id") == "orgB" for c in results)
