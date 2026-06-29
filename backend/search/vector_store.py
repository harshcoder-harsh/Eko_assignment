import faiss
import numpy as np
import json
import os
from db import files_collection

INDEX_FILE = "synced_docs/faiss.index"
CHUNKS_JSONL_FILE = "synced_docs/chunks.jsonl"
CHUNKS_JSON_FILE = "synced_docs/chunks.json"
DIMENSION = 384 # Dimension for 'all-MiniLM-L6-v2'

_index_cache = None
_index_mtime = None
_chunks_cache = None
_chunks_mtime = None
_chunks_path = None

def load_faiss_index():
    global _index_cache, _index_mtime
    if os.path.exists(INDEX_FILE):
        mtime = os.path.getmtime(INDEX_FILE)
        if _index_cache is not None and _index_mtime == mtime:
            return _index_cache
        _index_cache = faiss.read_index(INDEX_FILE)
        _index_mtime = mtime
        return _index_cache
    # Using IndexFlatIP for Cosine Similarity (requires normalized embeddings)
    _index_cache = faiss.IndexFlatIP(DIMENSION)
    _index_mtime = None
    return _index_cache

def load_chunks():
    global _chunks_cache, _chunks_mtime, _chunks_path
    path = None
    if os.path.exists(CHUNKS_JSONL_FILE):
        path = CHUNKS_JSONL_FILE
    elif os.path.exists(CHUNKS_JSON_FILE):
        path = CHUNKS_JSON_FILE

    if not path:
        _chunks_cache = []
        _chunks_mtime = None
        _chunks_path = None
        return []

    mtime = os.path.getmtime(path)
    if _chunks_cache is not None and _chunks_mtime == mtime and _chunks_path == path:
        return _chunks_cache

    if path.endswith(".jsonl"):
        chunks = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunks.append(json.loads(line))
        _chunks_cache = chunks
    else:
        with open(path, "r") as f:
            _chunks_cache = json.load(f)

    _chunks_mtime = mtime
    _chunks_path = path
    return _chunks_cache

def save_faiss_index(index):
    global _index_cache, _index_mtime
    if not os.path.exists("synced_docs"):
        os.makedirs("synced_docs")
    faiss.write_index(index, INDEX_FILE)
    _index_cache = index
    try:
        _index_mtime = os.path.getmtime(INDEX_FILE)
    except Exception:
        _index_mtime = None

def save_chunks(chunks):
    global _chunks_cache, _chunks_mtime, _chunks_path
    if not os.path.exists("synced_docs"):
        os.makedirs("synced_docs")
    with open(CHUNKS_JSONL_FILE, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
    _chunks_cache = chunks
    _chunks_path = CHUNKS_JSONL_FILE
    try:
        _chunks_mtime = os.path.getmtime(CHUNKS_JSONL_FILE)
    except Exception:
        _chunks_mtime = None

def append_chunks(chunks):
    global _chunks_cache, _chunks_mtime, _chunks_path
    if not chunks:
        return
    if not os.path.exists("synced_docs"):
        os.makedirs("synced_docs")
    if _chunks_cache is None or _chunks_path != CHUNKS_JSONL_FILE:
        _chunks_cache = []
        _chunks_mtime = None
        _chunks_path = CHUNKS_JSONL_FILE
    with open(CHUNKS_JSONL_FILE, "a") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
    _chunks_cache.extend(chunks)
    _chunks_path = CHUNKS_JSONL_FILE
    try:
        _chunks_mtime = os.path.getmtime(CHUNKS_JSONL_FILE)
    except Exception:
        _chunks_mtime = None

def add_chunks_to_index(index, new_chunks):
    if not new_chunks:
        return
    embeddings = np.array([chunk['embedding'] for chunk in new_chunks]).astype('float32')
    if len(embeddings) > 0:
        index.add(embeddings)

    for chunk in new_chunks:
        if 'embedding' in chunk:
            del chunk['embedding']

    append_chunks(new_chunks)

def add_to_faiss(new_chunks):
    index = load_faiss_index()
    add_chunks_to_index(index, new_chunks)
    save_faiss_index(index)

def search_faiss(query, k=5, filters=None):
    from embedding.embedder import model
    index = load_faiss_index()
    chunks = load_chunks()

    if index.ntotal == 0 or len(chunks) == 0:
        return []

    if filters and isinstance(filters, dict) and filters.get("doc_id"):
        wanted = filters["doc_id"]
        doc_chunks = []
        for chunk in chunks:
            base_doc_id = chunk["doc_id"].split('_chunk_')[0] if '_chunk_' in chunk["doc_id"] else chunk["doc_id"]
            if base_doc_id == wanted:
                doc_chunks.append(chunk)

        if not doc_chunks:
            return []

        if len(doc_chunks) <= k:
            return doc_chunks

        step = max(1, len(doc_chunks) // k)
        sampled = doc_chunks[::step][:k]
        if len(sampled) < k:
            sampled.extend(doc_chunks[-(k - len(sampled)):])
        return sampled[:k]

    if filters and isinstance(filters, dict) and filters.get("doc_id"):
        search_k = min(index.ntotal, max(k * 100, 1000))
    elif filters:
        search_k = min(index.ntotal, max(k * 25, 250))
    else:
        search_k = min(k, index.ntotal)

    query_embedding = model.encode([query], normalize_embeddings=True).astype('float32')
    distances, indices = index.search(query_embedding, search_k)

    results = []
    for i in indices[0]:
        if i < len(chunks) and i != -1:
            chunk = chunks[i]
            if filters:
                if isinstance(filters, dict) and filters.get("doc_id"):
                    base_doc_id = chunk["doc_id"].split('_chunk_')[0] if '_chunk_' in chunk["doc_id"] else chunk["doc_id"]
                    if base_doc_id != filters["doc_id"]:
                        continue
                else:
                    doc_id = chunk["doc_id"]
                    metadata = get_document_metadata(doc_id)
                    if metadata:
                        match = True
                        for key, val in filters.items():
                            if key == "name":
                                m = metadata.get(key)
                                if (m or "").strip().lower() != (val or "").strip().lower():
                                    match = False
                                    break
                            elif metadata.get(key) != val:
                                match = False
                                break
                        if not match:
                            continue
            results.append(chunk)
            if len(results) >= k:
                break

    return results

def get_document_metadata(doc_id):
    # Strip the _chunk_X suffix to get the real doc_id
    base_doc_id = doc_id.split('_chunk_')[0] if '_chunk_' in doc_id else doc_id
    
    # Instead of looking for a local metadata.json, we fetch from MongoDB
    # Try both 'file_id' and 'id' depending on how it was saved
    doc = files_collection.find_one({"file_id": base_doc_id})
    if not doc:
        doc = files_collection.find_one({"id": base_doc_id})
    if doc:
        return {
            "name": doc.get("name"),
            "mimeType": doc.get("mimeType"),
            "modifiedTime": doc.get("modifiedTime")
        }
    return None
