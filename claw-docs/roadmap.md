# Next-Version Roadmap

## Near-term
- **Human notification on escalation** — currently escalated tickets just sit
  with `status=escalated`; next step is a Slack/email webhook fired from
  `support/orchestrator.py` when `should_escalate()` returns true.
- **Dedicated SOP upload path** — right now SOP/FAQ detection relies on a
  filename convention against the general Drive sync. A dedicated
  `/support/sop/upload` (or a tagged folder in Drive) would make the
  scoping explicit rather than inferred from filenames.
- **Frontend surface for tickets/audit** — currently only API endpoints
  exist (`/support/tickets`, `/support/audit/...`); a simple dashboard view
  (reusing the existing Next.js frontend) would let a human triage tickets
  without hitting the API directly.

## Medium-term
- **Multi-turn clarification** — if a query is too ambiguous to classify
  confidently, allow the agent to ask one clarifying question before
  drafting, instead of always producing a best-effort answer.
- **Ticket-resolution learning loop** — when a human resolves a ticket, store
  the human's final answer alongside the original query/classification so
  future similar queries can be classified more confidently (would require
  a feedback dataset, not full fine-tuning).
- **Configurable severity thresholds** — `AUTO_ESCALATE_SEVERITIES` is
  currently hardcoded in `escalation.py`; make it configurable per
  deployment (e.g. a `low`-severity-only team might want `medium` to also
  auto-escalate).

## Longer-term
- **Multi-agent handoff** — split classification and drafting into separate
  Claws that can be swapped/upgraded independently (e.g. a dedicated billing
  Claw with billing-system tool access vs. a generic technical Claw).
- **Tool-use for ticket systems** — instead of an internal ticket store,
  integrate with an external ticketing system (Zendesk/Jira/Linear) via MCP,
  so "creating a ticket" means actually creating it in the tool the support
  team already uses.
- **Self-evaluation** — periodically sample resolved tickets and have a
  separate evaluator pass check whether the SOP grounding was actually
  correct, to catch silent SOP-retrieval drift over time.
