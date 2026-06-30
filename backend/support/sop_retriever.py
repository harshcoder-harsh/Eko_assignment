"""SOP / FAQ retrieval for the Support Escalation Claw.

Reuses the existing FAISS index (synced from Google Drive via connectors/gdrive.py)
rather than building a second vector store. Documents are treated as SOPs/FAQs
based on a naming convention: any synced file whose name contains "sop" or "faq"
(case-insensitive) is considered SOP material. If no such files exist yet, the
retriever transparently falls back to the full document set so the workflow
still works end to end during early testing — but it flags this in the
returned context so the caller and audit trail know grounding was generic.
"""
from search.vector_store import search_faiss, get_document_metadata
from db import files_collection


def _sop_doc_ids(user_email: str) -> set:
    """Return the file_ids of synced docs whose name looks like an SOP/FAQ doc."""
    sop_ids = set()
    try:
        cursor = files_collection.find({"user_email": user_email})
    except Exception:
        cursor = files_collection.find()
    for doc in cursor:
        name = (doc.get("name") or "").lower()
        if "sop" in name or "faq" in name or "policy" in name or "runbook" in name:
            fid = doc.get("file_id") or doc.get("id")
            if fid:
                sop_ids.add(fid)
    return sop_ids


def retrieve_sop_context(query: str, user_email: str, k: int = 6) -> dict:
    """Retrieve the most relevant SOP/FAQ chunks for a classified query.

    Returns:
        {
          "context_block": str,        # formatted text block for the LLM prompt
          "sources": list[dict],       # [{doc_id, name, chunk_text}]
          "scoped_to_sop": bool,       # True if filtered to SOP-tagged docs
        }
    """
    sop_ids = _sop_doc_ids(user_email)

    all_chunks = search_faiss(query, k=max(k * 4, 20), filters=None)

    if sop_ids:
        chunks = []
        for chunk in all_chunks:
            doc_id = chunk["doc_id"]
            base_doc_id = doc_id.split("_chunk_")[0] if "_chunk_" in doc_id else doc_id
            if base_doc_id in sop_ids:
                chunks.append(chunk)
            if len(chunks) >= k:
                break
        scoped = True
        if not chunks:
            # No SOP-tagged chunks matched this query; fall back to general retrieval
            chunks = all_chunks[:k]
            scoped = False
    else:
        chunks = all_chunks[:k]
        scoped = False

    context_parts = []
    sources = []
    for chunk in chunks:
        doc_id = chunk["doc_id"]
        text = chunk["text"]
        metadata = get_document_metadata(doc_id)
        doc_name = metadata.get("name", "Unknown Document") if metadata else "Unknown Document"
        context_parts.append(f"SOP Document: {doc_name}\nContent:\n{text}")
        if not any(s["doc_id"] == doc_id for s in sources):
            sources.append({"doc_id": doc_id, "name": doc_name, "chunk_text": text})

    return {
        "context_block": "\n\n---\n\n".join(context_parts),
        "sources": sources,
        "scoped_to_sop": scoped,
    }
