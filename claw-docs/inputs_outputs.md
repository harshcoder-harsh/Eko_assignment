# Inputs & Outputs

## Inputs

### 1. SOP / FAQ knowledge base (indirect input)
- **Source:** Google Drive, synced via the existing `connectors/gdrive.py` +
  `POST /sync-drive` pipeline (unchanged from the base RAG project).
- **Identification convention:** any synced file whose name contains `sop`,
  `faq`, `policy`, or `runbook` (case-insensitive) is treated as SOP material
  by `support/sop_retriever.py`. This is a naming convention, not a separate
  upload path, so existing sync infrastructure is reused as-is.
- **Format:** PDF, DOCX, TXT (same parser as the base project —
  `processing/parser.py`).

### 2. User query (direct input)
- **Endpoint:** `POST /support/resolve`
- **Schema:**
  ```json
  { "query": "string, required, non-empty" }
  ```

## Outputs

### 1. Workflow result (synchronous response from `/support/resolve`)
```json
{
  "run_id": "uuid",
  "state": "RESOLVED | TICKETED | ESCALATED",
  "classification": {
    "issue_type": "billing | technical | access | bug | feature_request | general",
    "severity": "low | medium | high | critical",
    "reasoning": "string"
  },
  "draft_response": "string",
  "sources": [
    { "doc_id": "string", "name": "string", "chunk_text": "string" }
  ],
  "scoped_to_sop": true,
  "ticket": { "...": "see ticket schema below, or null if resolved" }
}
```

### 2. Ticket (persisted, `support/ticket_store.py`)
```json
{
  "ticket_id": "uuid",
  "user_email": "string",
  "query": "string",
  "issue_type": "string",
  "severity": "string",
  "draft_response": "string",
  "status": "open | escalated | resolved",
  "escalation_reason": "string | null",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### 3. Audit trail entry (persisted, `support/audit.py`)
```json
{
  "run_id": "uuid",
  "user_email": "string",
  "query": "string",
  "state": "started | RESOLVED | TICKETED | ESCALATED",
  "events": [
    { "step": "RECEIVED | CLASSIFIED | SOP_RETRIEVED | DRAFTED | TICKETED | ESCALATED",
      "detail": { "...": "step-specific data" },
      "timestamp": "ISO timestamp" }
  ],
  "started_at": "ISO timestamp",
  "finished_at": "ISO timestamp"
}
```

## Read endpoints
- `GET /support/tickets?status=open` — list tickets, optionally by status
- `GET /support/ticket/{ticket_id}` — single ticket
- `GET /support/audit/{run_id}` — full audit trail for one workflow run
- `GET /support/audit` — list recent runs for the current user
