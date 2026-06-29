"""Groq-powered narrative layer for the analytics Claws.

The numbers are always computed deterministically in `engine.py`. The narrator
ONLY turns those pre-computed facts into readable prose / recommendations. It is
explicitly instructed never to invent figures, and it degrades gracefully to a
deterministic fallback summary when Groq is unavailable.
"""
import os
import json

_SYSTEM_PROMPT = """You are 'Claw', an autonomous business-analytics agent.
You are given a JSON object of ALREADY-COMPUTED statistics about a dataset
(KPIs, trends, anomalies, segments, period-over-period changes).

Strict rules:
1. Use ONLY the numbers present in the provided JSON. NEVER invent or estimate figures.
2. Be concise, specific and business-oriented. Quote exact numbers from the JSON.
3. Write in clean markdown: short sections, bold labels, bullet points.
4. Where the task asks for it, give concrete, prioritised recommended actions and call out risks.
5. If the data is insufficient for a conclusion, say so plainly.
Do not include a preamble like 'Here is the summary'. Start directly with the content."""


def _fallback(task: str, facts: dict) -> str:
    """Deterministic markdown when the LLM is unavailable, so the agent still works."""
    lines = [f"### {task} (offline summary)"]
    kpis = facts.get("kpis", {}).get("kpis") if isinstance(facts.get("kpis"), dict) else None
    if kpis:
        lines.append("**Key metrics:**")
        for k in kpis[:6]:
            lines.append(f"- **{k['name']}** — total {k.get('total')}, avg {k.get('average')}, range {k.get('min')}–{k.get('max')}")
    trends = facts.get("trends", {}).get("series") if isinstance(facts.get("trends"), dict) else None
    if trends:
        lines.append("\n**Trends:**")
        for t in trends[:6]:
            lines.append(f"- **{t['metric']}** is {t['direction']} ({t.get('change_pct')}% over the period)")
    changes = facts.get("monitoring", {}).get("changes") if isinstance(facts.get("monitoring"), dict) else None
    if changes:
        lines.append("\n**Period-over-period changes:**")
        for c in changes[:6]:
            lines.append(f"- **{c['metric']}**: {c.get('change_pct')}% ({c.get('previous')} → {c.get('current')})")
    anoms = facts.get("anomalies", {}) if isinstance(facts.get("anomalies"), dict) else {}
    if anoms.get("total_anomalies"):
        lines.append(f"\n**Anomalies:** {anoms['total_anomalies']} unusual data point(s) detected.")
    segs = facts.get("segments", {}).get("segments") if isinstance(facts.get("segments"), dict) else None
    if segs:
        lines.append("\n**Segments:**")
        for s in segs[:6]:
            lines.append(f"- Segment {s['segment']} ({s.get('label')}) — {s['size']} members ({s.get('size_pct')}%)")
    lines.append("\n_LLM narrative unavailable (GROQ_API_KEY not set or rate-limited); showing computed facts only._")
    return "\n".join(lines)


def narrate(task: str, instruction: str, facts: dict, max_tokens: int = 900) -> str:
    """Generate the natural-language insight for a Claw."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _fallback(task, facts)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        facts_json = json.dumps(facts, default=str)[:14000]
        user_msg = f"""TASK: {task}

INSTRUCTION: {instruction}

COMPUTED STATISTICS (JSON):
{facts_json}"""

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content
    except Exception as e:
        msg = str(e).lower()
        if "rate_limit" in msg or "429" in msg:
            return _fallback(task, facts) + "\n\n_(AI narrative skipped — rate limit reached.)_"
        return _fallback(task, facts)
