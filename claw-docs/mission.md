# Mission

## What this Claw is

**Support Escalation Claw** is a bounded autonomous agent that owns the
end-to-end resolution of an inbound support query — from raw text to either
a resolved answer or an escalated, audited ticket. It is not a chatbot that
answers questions; it is a workflow that makes decisions, persists state,
and leaves an inspectable trail of what it did and why.

## What "owning the workflow" means here

The agent does not stop at "here's an answer." For every query it:

1. Classifies the issue (type + severity) using a bounded taxonomy.
2. Retrieves grounding context from SOP/FAQ documents specifically (not
   generic document search).
3. Drafts a response constrained to that grounding — it is explicitly
   instructed to say "I don't know" rather than hallucinate a policy.
4. Decides — via deterministic rules, not LLM judgment — whether the issue
   must become a ticket and/or be escalated to a human.
5. Persists the ticket and a full audit trail of every step, decision, and
   tool call made along the way.

## Why this matters

A Q&A system over documents can be fooled into giving a confident-sounding
wrong answer with no consequence. An agent that owns a workflow has to make
a call: resolve, ticket, or escalate — and that call has to be defensible
after the fact. The audit trail (`support/audit.py`) and the deterministic
escalation guardrail (`support/escalation.py`) exist specifically so that
"why did the agent decide X" is always answerable from data, not from
re-running the LLM and hoping for the same answer.

## Non-goals (for this version)

- This Claw does not auto-resolve and close tickets — a human always
  reviews and resolves tickets explicitly (`POST /support/ticket/{id}/resolve`).
- It does not page or notify humans (e.g. Slack/email integration) — see
  `roadmap.md` for that as a next-version item.
- It does not learn from past tickets to improve future classification.
