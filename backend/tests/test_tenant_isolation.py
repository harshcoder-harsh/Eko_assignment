
import faiss
import numpy as np


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
