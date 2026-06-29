"""The five autonomous analytics agents ('Claws').

Each Claw:
  1. loads the cleaned dataset,
  2. computes deterministic statistics via engine.py,
  3. asks the Groq narrator to turn those facts into an insight summary,
  4. returns a structured payload (facts + markdown insight) for the UI.
"""
from analytics.data_loader import load_dataset
from analytics import engine
from analytics.narrator import narrate
from analytics.utils import json_safe


def _meta(meta, df):
    return {
        "dataset_id": meta.get("dataset_id"),
        "name": meta.get("name"),
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
    }


# --------------------------------------------------------------------------- #
# 1. Data Analyst Claw
# --------------------------------------------------------------------------- #
def data_analyst_claw(dataset_id: str, user_email: str = None):
    meta, df = load_dataset(dataset_id, user_email)
    kpis = engine.compute_kpis(df)
    trends = engine.compute_trends(df)

    facts = {"kpis": kpis, "trends": trends, "clean_summary": meta.get("clean_summary")}
    insight = narrate(
        "Data Analyst",
        "Clean-data recap, the most important KPIs, notable trends and correlations, "
        "and 3-5 key takeaways an analyst should know. End with a short 'Recommended next analyses' list.",
        facts,
        max_tokens=950,
    )
    return json_safe({
        "claw": "data_analyst",
        "title": "Data Analyst Claw",
        "dataset": _meta(meta, df),
        "cleaning": meta.get("clean_summary"),
        "kpis": kpis,
        "trends": trends,
        "insight": insight,
    })


# --------------------------------------------------------------------------- #
# 2. KPI Monitoring Claw
# --------------------------------------------------------------------------- #
def kpi_monitoring_claw(dataset_id: str, user_email: str = None):
    meta, df = load_dataset(dataset_id, user_email)
    monitoring = engine.monitor_kpis(df)
    kpis = engine.compute_kpis(df)

    facts = {"monitoring": monitoring, "kpis": kpis}
    insight = narrate(
        "KPI Monitoring",
        "For each monitored KPI, state the change vs the previous period, judge whether it is good or bad "
        "for the business, suggest the most likely reason, and recommend a concrete follow-up action. "
        "Lead with the metrics that moved the most.",
        facts,
        max_tokens=900,
    )
    return json_safe({
        "claw": "kpi_monitoring",
        "title": "KPI Monitoring Claw",
        "dataset": _meta(meta, df),
        "monitoring": monitoring,
        "insight": insight,
    })


# --------------------------------------------------------------------------- #
# 3. Anomaly Detection Claw
# --------------------------------------------------------------------------- #
def anomaly_detection_claw(dataset_id: str, user_email: str = None):
    meta, df = load_dataset(dataset_id, user_email)
    anomalies = engine.detect_anomalies(df)

    facts = {"anomalies": anomalies}
    insight = narrate(
        "Anomaly Detection",
        "Summarise how many anomalies were found and in which metrics. Describe the most extreme exceptions "
        "(value, how far from normal, when they occurred). Suggest plausible explanations and what to investigate. "
        "If nothing unusual was found, say the data looks healthy.",
        facts,
        max_tokens=850,
    )
    return json_safe({
        "claw": "anomaly_detection",
        "title": "Anomaly Detection Claw",
        "dataset": _meta(meta, df),
        "anomalies": anomalies,
        "insight": insight,
    })


# --------------------------------------------------------------------------- #
# 4. Customer Segmentation Claw
# --------------------------------------------------------------------------- #
def segmentation_claw(dataset_id: str, user_email: str = None):
    meta, df = load_dataset(dataset_id, user_email)
    segments = engine.segment_entities(df)

    facts = {"segments": segments}
    if segments.get("ok"):
        instruction = (
            "Describe each segment in business terms: give it a memorable name, explain who is in it "
            "(using the profile numbers), its size, and how to treat that segment (marketing / retention / pricing). "
            "Finish with which segment is most valuable and why."
        )
    else:
        instruction = "Explain why segmentation could not be performed and what data would be needed to enable it."
    insight = narrate("Customer Segmentation", instruction, facts, max_tokens=950)

    return json_safe({
        "claw": "segmentation",
        "title": "Customer Segmentation Claw",
        "dataset": _meta(meta, df),
        "segments": segments,
        "insight": insight,
    })


# --------------------------------------------------------------------------- #
# 5. Business Performance Claw (orchestrates everything)
# --------------------------------------------------------------------------- #
def business_performance_claw(dataset_id: str, user_email: str = None):
    meta, df = load_dataset(dataset_id, user_email)
    kpis = engine.compute_kpis(df)
    trends = engine.compute_trends(df)
    monitoring = engine.monitor_kpis(df)
    anomalies = engine.detect_anomalies(df)
    segments = engine.segment_entities(df)

    facts = {
        "kpis": kpis,
        "trends": trends,
        "monitoring": monitoring,
        "anomalies": anomalies,
        "segments": segments,
    }
    insight = narrate(
        "Business Performance Report",
        "Write an executive business performance report with these sections, using markdown headings:\n"
        "## Executive Summary (3-4 sentences)\n"
        "## Performance Highlights (best-moving KPIs and trends)\n"
        "## Risks & Concerns (declines, anomalies, concentration risk)\n"
        "## Customer/Segment Insights\n"
        "## Recommended Next Actions (prioritised, concrete bullet list)\n"
        "Quote exact numbers from the JSON throughout.",
        facts,
        max_tokens=1400,
    )
    return json_safe({
        "claw": "business_performance",
        "title": "Business Performance Claw",
        "dataset": _meta(meta, df),
        "kpis": kpis,
        "trends": trends,
        "monitoring": monitoring,
        "anomalies": anomalies,
        "segments": segments,
        "insight": insight,
    })


CLAWS = {
    "data_analyst": data_analyst_claw,
    "kpi_monitoring": kpi_monitoring_claw,
    "anomaly_detection": anomaly_detection_claw,
    "segmentation": segmentation_claw,
    "business_performance": business_performance_claw,
}


def run_claw(claw: str, dataset_id: str, user_email: str = None):
    fn = CLAWS.get(claw)
    if not fn:
        raise ValueError(f"Unknown claw '{claw}'. Available: {', '.join(CLAWS)}")
    return fn(dataset_id, user_email)
