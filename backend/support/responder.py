"""Grounded response drafting for the Support Escalation Claw.

Same pattern as analytics/narrator.py and api/routes.py's /ask endpoint:
Groq-backed with a deterministic fallback so the workflow never hard-fails
just because the LLM call failed.
"""
import os

_SYSTEM_PROMPT = """You are a support agent drafting a response to a customer query.
You are given SOP/FAQ context retrieved from the company's knowledge base.

Rules:
1. Answer ONLY using the provided SOP context. Do not invent policies or steps.
2. If the SOP context does not contain the answer, say plainly:
   "I don't have enough information in our SOPs to resolve this." Do not guess.
3. Be concise, professional, and actionable.
4. If steps are involved, use a numbered list."""


def draft_response(query: str, issue_type: str, severity: str, context_block: str, memory_context: str = "") -> str:
    if not context_block.strip() and not memory_context.strip():
        return "I don't have enough information in our SOPs to resolve this."

    try:
        from support.hermes_runtime import get_hermes_agent

        agent = get_hermes_agent(system_prompt=_SYSTEM_PROMPT, cache_key="responder")

        user_msg = f"""Issue type: {issue_type}
Severity: {severity}

{f"User History:{memory_context}" if memory_context else ""}

SOP Context:
{context_block}

Customer query:
{query}"""

        return agent.chat(user_msg)
    except Exception as e:
        if not os.getenv("GROQ_API_KEY"):
            return (
                f"[Offline draft] Based on the retrieved SOP context for this {issue_type} "
                f"issue (severity: {severity}), here is the relevant material:\n\n{context_block[:800]}"
            )
        return f"I don't have enough information in our SOPs to resolve this. (Draft generation error: {e})"
