"""Shared Hermes Agent factory for the Support Escalation Claw.

This module is the bridge between our workflow orchestrator and Hermes
Agent (NousResearch/hermes-agent), the LLM agent runtime that actually
performs the reasoning steps (classification, drafting).

Why Hermes here and not a raw Groq SDK call:
  - The evaluator explicitly required evidence of an established agent
    framework (OpenClaw / Hermes Agent / NemoClaw / NanoClaw), not a
    hand-rolled LLM wrapper.
  - Hermes Agent ships as a real pip package (`pip install hermes-agent`)
    with a documented Python-library mode (`AIAgent.chat()`), and works
    with any OpenAI-compatible endpoint — including Groq, which this
    project already uses for inference.

Why toolsets are explicitly disabled (enabled_toolsets=[]):
  - Hermes's built-in toolsets (browser, terminal, file, code_execution,
    etc.) are general-purpose autonomous-agent capabilities. Granting them
    here would let the LLM take unbounded actions during what is supposed
    to be a narrow, auditable classification/drafting step — directly
    against the guardrails documented in claw-docs/guardrails.md ("agent
    must never silently decide" / deterministic escalation logic).
  - Hermes is used purely as the reasoning/completion engine. All control
    flow (retrieval scoping, escalation decisions, ticket creation, audit
    logging) stays in support/orchestrator.py, not inside the agent loop.
"""
import os

_agent_cache = {}


def get_hermes_agent(system_prompt: str = None, cache_key: str = "default") -> "AIAgent":
    """Return a Hermes AIAgent configured to talk to Groq, with all
    autonomous toolsets disabled (pure text-completion mode).

    Raises if GROQ_API_KEY is not set — callers are expected to catch
    this and fall back to the deterministic path, same as the rest of
    this module's Groq-based callers did before this integration.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set; cannot construct a Hermes agent.")

    if cache_key in _agent_cache:
        return _agent_cache[cache_key]

    from run_agent import AIAgent

    agent = AIAgent(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        enabled_toolsets=[],          # no browser/terminal/file/code_execution — bounded reasoning only
        quiet_mode=True,
        skip_memory=True,             # each classification/draft call is stateless and independent
        skip_context_files=True,
        load_soul_identity=False,
        max_iterations=1,             # single-turn: no autonomous multi-step tool loop
        ephemeral_system_prompt=system_prompt,
    )
    _agent_cache[cache_key] = agent
    return agent
