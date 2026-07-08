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