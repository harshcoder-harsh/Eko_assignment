# Tools

## Agent framework

This Claw uses **Hermes Agent** (`NousResearch/hermes-agent`, MIT-licensed,
installed via `pip install hermes-agent`) as its LLM agent runtime for the
classification and drafting steps. See `support/hermes_runtime.py` for the
integration point.

Hermes is deliberately run with `enabled_toolsets=[]` (all autonomous
toolsets — browser, terminal, file, code_execution, messaging gateways —
disabled) and `max_iterations=1` (single-turn, no autonomous multi-step
loop). This is intentional, not a limitation we ran into: Hermes's full
toolset is built for open-ended personal-assistant use (the kind of agent
that manages your Telegram, browses the web, runs shell commands). Granting
that scope to a classification/drafting step inside a support workflow
would violate the bounded-workflow guardrails this project is built around
(see `guardrails.md`). All control flow — retrieval scoping, the
escalation decision, ticket creation, audit logging — stays in
`support/orchestrator.py`, outside the agent loop, so the workflow remains
deterministic and auditable even though the reasoning steps run on a real
autonomous-agent framework.

The agent's built-in toolsets (`browser`, `terminal`, `file`,
`code_execution`, `web`, `search`, plus 30+ messaging-gateway toolsets like
`hermes-telegram`/`hermes-slack`) remain available in the dependency and
could be selectively enabled for a future version that needs them (see
`roadmap.md`) — for this version they are off by default.

## The agent's other tools

The remaining workflow steps below are not LLM tool calls — they are
explicit Python modules invoked in a fixed order by
`support/orchestrator.py`, which is what keeps the overall workflow bounded
rather than an open-ended agent loop.

## 1. Classifier — `support/classifier.py`
- **Calls:** Hermes Agent (`NousResearch/hermes-agent`, installed via
  `pip install hermes-agent`) as the LLM reasoning runtime, via
  `support/hermes_runtime.py::get_hermes_agent()`. Hermes is pointed at
  Groq's OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`,
  model configurable via `GROQ_MODEL`), with `enabled_toolsets=[]` so the
  agent performs single-turn text reasoning only — no browser, terminal,
  file, or code-execution access.
- **Fallback:** deterministic keyword matcher (`_fallback_classify`) used
  when `GROQ_API_KEY` is unset, Hermes raises, or the response is invalid
  JSON — same resilience contract as before, just with Hermes as the
  primary path instead of a raw Groq SDK call.
- **Output:** `issue_type`, `severity`, `reasoning` — values are validated
  against a fixed enum; anything outside it is coerced to `general` / `low`.

## 2. SOP Retriever — `support/sop_retriever.py`
- **Calls:** the existing FAISS vector store (`search/vector_store.py`,
  unchanged from the base RAG project) — no second vector index is built.
- **Scoping:** filters retrieved chunks to documents matching the SOP/FAQ
  naming convention (see `inputs_outputs.md`). Falls back to unscoped
  retrieval if no SOP-tagged documents are synced yet, and reports this via
  `scoped_to_sop: false` so callers/auditors know grounding was generic.

## 3. Responder — `support/responder.py`
- **Calls:** the same Hermes Agent runtime as the classifier
  (`support/hermes_runtime.py`), system-prompted to answer only from the
  provided SOP context and explicitly refuse to guess. Toolsets remain
  disabled here too — drafting is a pure text-completion task, not an
  autonomous action.
- **Fallback:** if no Groq key is set or Hermes raises, returns a
  deterministic excerpt of the retrieved context (not a hallucinated
  answer) so the workflow can still be tested offline.

## 4. Escalation Guardrail — `support/escalation.py`
- **Not LLM-based by design.** Severity `critical`/`high` always escalates,
  regardless of how confident the drafted response sounds. This is the
  guardrail described in `guardrails.md` — it cannot be talked out of
  escalating by the LLM's own output.

## 5. Ticket Store — `support/ticket_store.py`
- **Calls:** `db.db_get_collection("tickets")` — the same Mongo/local-JSON
  fallback pattern already used by `files_collection` / `chats_collection`
  in the base project, so no new infra is required.

## 6. Audit Logger — `support/audit.py`
- **Calls:** `db.db_get_collection("audit_log")`, same pattern as above.
- Every orchestrator step calls `audit.log_event(...)`, so a full run can be
  replayed/inspected via `GET /support/audit/{run_id}`.

## External services reused (unchanged from base project)
- **Google Drive API** — document sync.
- **Groq API** — LLM calls for classification and drafting.
- **MongoDB (or local JSON fallback)** — persistence.
