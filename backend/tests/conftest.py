import os
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")


@pytest.fixture
def isolated_vector_store(tmp_path, monkeypatch):
    import search.vector_store as vs

    monkeypatch.setattr(vs, "INDEX_FILE", str(tmp_path / "faiss.index"))
    monkeypatch.setattr(vs, "CHUNKS_JSONL_FILE", str(tmp_path / "chunks.jsonl"))
    monkeypatch.setattr(vs, "CHUNKS_JSON_FILE", str(tmp_path / "chunks.json"))
    monkeypatch.chdir(tmp_path)

    for attr in ("_index_cache", "_index_mtime",
                 "_chunks_cache", "_chunks_mtime", "_chunks_path"):
        monkeypatch.setattr(vs, attr, None, raising=False)

    return vs

@pytest.fixture
def stub_embedder(monkeypatch):
    """Replace the SentenceTransformers model with a deterministic hash-based
    encoder so retrieval tests don't need torch or a model download."""
    import numpy as np
    import sys
    import types

    class _StubModel:
        def encode(self, texts, normalize_embeddings=True, **kwargs):
            out = []
            for t in texts:
                rng = np.random.default_rng(abs(hash(t)) % (2**32))
                v = rng.random(384).astype("float32")
                if normalize_embeddings:
                    v = v / np.linalg.norm(v)
                out.append(v)
            return np.array(out, dtype="float32")

    module = types.ModuleType("embedding.embedder")
    module.model = _StubModel()
    monkeypatch.setitem(sys.modules, "embedding.embedder", module)
    return module.model