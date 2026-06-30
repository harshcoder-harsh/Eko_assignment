# Exception Handling

| Failure point | Behavior | Where handled |
|---|---|---|
| `GROQ_API_KEY` not set | Classification falls back to keyword matcher; drafting falls back to a raw context excerpt | `classifier.py::_fallback_classify`, `responder.py` |
| Groq API call raises (rate limit, timeout, network) | Caught broadly, falls back to deterministic path; classifier never propagates the exception | `classifier.py::classify_query` try/except |
| Groq returns malformed/non-JSON output | `json.loads` failure caught, falls back to keyword classifier | `classifier.py::classify_query` |
| Groq returns an `issue_type`/`severity` outside the known enum | Coerced to `general`/`low` rather than rejected | `classifier.py::classify_query` |
| No SOP/FAQ-tagged documents synced yet | Retrieval falls back to unscoped search across all synced docs; flagged via `scoped_to_sop: false` | `sop_retriever.py::retrieve_sop_context` |
| No documents synced at all (empty FAISS index) | `search_faiss` returns `[]`; `context_block` is empty; `responder.py` short-circuits to "I don't have enough information" without calling the LLM | `responder.py::draft_response` |
| Empty query submitted to `/support/resolve` | Rejected with `400` before any workflow step runs | `support_routes.py::resolve_query` |
| Unhandled exception anywhere in `run_support_workflow` | Caught at the route layer, logged via `traceback.print_exc()`, returned as `500` with the error detail | `support_routes.py::resolve_query` |
| Ticket or run ID not found on lookup | `404` returned | `support_routes.py` |
| MongoDB unreachable | Same fallback as the rest of the app — `db.db_get_collection` transparently switches to local JSON file storage; no special handling needed in the support module | `db.py` (existing, reused) |
| Drafting step itself raises (e.g. Groq client error mid-call) | Caught inside `draft_response`, returns the "I don't have enough information" message annotated with the error — this is intentionally treated as an *unresolved* draft so it gets ticketed, not silently dropped | `responder.py::draft_response` |

## Design principle
No exception in the classification or drafting steps is allowed to abort the
workflow run. Every failure degrades to a safe, conservative default (lower
confidence classification, "I don't know" response, fallback retrieval) and
is logged to the audit trail — so a degraded run is still visible and
diagnosable, not invisible.
