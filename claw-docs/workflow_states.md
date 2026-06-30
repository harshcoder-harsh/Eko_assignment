# Workflow States

The orchestrator (`support/orchestrator.py`) drives every query through a
fixed state sequence. States are written to the audit trail as they happen,
not reconstructed afterward.

```
RECEIVED
   |
   v
CLASSIFIED        (issue_type + severity assigned)
   |
   v
SOP_RETRIEVED     (SOP/FAQ context pulled, scoped or unscoped)
   |
   v
DRAFTED           (grounded response generated)
   |
   v
 [escalation check: severity is critical/high, OR draft is unresolved?]
   |
   +-- no  --> RESOLVED          (terminal — no ticket created)
   |
   +-- yes (unresolved, not severe) --> TICKETED   (terminal — ticket status=open)
   |
   +-- yes (severe) --> TICKETED --> ESCALATED     (terminal — ticket status=escalated)
```

## State definitions

| State | Meaning | Terminal? |
|---|---|---|
| `RECEIVED` | Query accepted, audit run started | no |
| `CLASSIFIED` | issue_type + severity assigned | no |
| `SOP_RETRIEVED` | SOP context fetched (scoped or fallback) | no |
| `DRAFTED` | Grounded response drafted | no |
| `RESOLVED` | Draft is grounded and severity is low/medium — no human needed | **yes** |
| `TICKETED` | Draft unresolved (couldn't ground in SOPs) but not high-severity — queued for human review | **yes** |
| `ESCALATED` | Severity critical/high — ticket created with status `escalated`, mandatory human handoff | **yes** |

## Ticket status vs. workflow state

Workflow state (`RESOLVED`/`TICKETED`/`ESCALATED`) is the *outcome of one
run*. Ticket status (`open`/`escalated`/`resolved`) is the *current state of
a ticket*, which can change later via `POST /support/ticket/{id}/resolve`
once a human has handled it. These are deliberately separate concerns: the
workflow result is immutable history; the ticket is a living record.
