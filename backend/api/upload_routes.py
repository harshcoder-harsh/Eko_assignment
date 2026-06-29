"""No-auth direct document ingestion for the RAG chat.

Lets a user upload a PDF / DOCX / TXT file directly, or import one from a direct
URL, WITHOUT connecting Google Drive. The file is processed, embedded and added
to the same FAISS index used by the Drive sync flow, so it is immediately
chattable on the dashboard.
"""
import os
import uuid
from datetime import datetime
from urllib.parse import urlparse, unquote

import requests
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from processing.parser import process_single_file
from embedding.embedder import embed_chunks
from search.vector_store import load_faiss_index, add_chunks_to_index, save_faiss_index
from connectors.gdrive import current_user_email, SYNC_DIR
from db import files_collection

router = APIRouter(tags=["documents"])

SUPPORTED_DOC_EXT = {".pdf", ".docx", ".txt"}
MAX_BYTES = 25 * 1024 * 1024  # 25 MB

_EXT_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def _download(url: str) -> bytes:
    try:
        resp = requests.get(url, timeout=30, stream=True, headers={"User-Agent": "Highwatch-RAG/1.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Could not fetch URL: {e}")
    content = b""
    for chunk in resp.iter_content(8192):
        content += chunk
        if len(content) > MAX_BYTES:
            raise ValueError("File too large (max 25 MB).")
    if not content:
        raise ValueError("The URL returned an empty file.")
    return content


def _filename_from_url(url: str) -> str:
    name = unquote(os.path.basename(urlparse(url).path)) or "document"
    return name


def _ingest_document(content: bytes, filename: str, user_email: str, source: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_DOC_EXT:
        raise ValueError(f"Unsupported file type '{ext or 'none'}'. Supported: {', '.join(sorted(SUPPORTED_DOC_EXT))}")

    if not os.path.exists(SYNC_DIR):
        os.makedirs(SYNC_DIR)

    doc_id = uuid.uuid4().hex[:16]
    path = os.path.join(SYNC_DIR, f"{doc_id}{ext}")
    with open(path, "wb") as f:
        f.write(content)

    # Register metadata so it appears in /documents and citations resolve.
    files_collection.update_one(
        {"user_email": user_email, "file_id": doc_id},
        {"$set": {
            "user_email": user_email,
            "file_id": doc_id,
            "name": filename,
            "path": path,
            "mimeType": _EXT_MIME.get(ext, "application/octet-stream"),
            "modifiedTime": datetime.utcnow().isoformat(),
            "source": source,
        }},
        upsert=True,
    )

    # Process -> chunk -> embed -> index (same pipeline as Drive sync).
    chunks = process_single_file({"id": doc_id, "name": filename, "path": path})
    if not chunks:
        files_collection.delete_many({"user_email": user_email, "file_id": doc_id})
        raise ValueError("No readable text could be extracted from this file.")

    embedded = embed_chunks(chunks)
    index = load_faiss_index()
    add_chunks_to_index(index, embedded)
    save_faiss_index(index)

    return {"id": doc_id, "name": filename, "chunks": len(embedded)}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 25 MB).")
        try:
            doc = _ingest_document(content, file.filename, current_user_email(), "upload")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return {"status": "success", "document": doc}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class DocUrlRequest(BaseModel):
    url: str


@router.post("/documents/import-url")
def import_document_url(req: DocUrlRequest):
    try:
        content = _download(req.url)
        filename = _filename_from_url(req.url)
        try:
            doc = _ingest_document(content, filename, current_user_email(), "url")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return {"status": "success", "document": doc}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
