"""AI Observability API — reads traces back out of Langfuse so the frontend
can render an in-app observability dashboard without leaving Highwatch.

All Langfuse access is server-side (the secret key never reaches the browser).
Every endpoint degrades gracefully: if Langfuse is not configured, the routes
return empty payloads with `enabled: false` rather than erroring, so the UI can
show a "connect Langfuse" empty state instead of a crash.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from support import tracing

router = APIRouter(prefix="/observability", tags=["observability"])


# ---------------------------------------------------------------------------
# Helpers — Langfuse's SDK returns Fern/pydantic models with snake_case attrs.
# We normalise everything to plain dicts and read fields defensively, because
# field names have shifted across SDK versions (latency vs. latency_ms, etc.).
# ---------------------------------------------------------------------------
def _to_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    for method in ("model_dump", "dict"):
        fn = getattr(obj, method, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    try:
        return dict(vars(obj))
    except Exception:
        return {}


def _first(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _token_total(usage) -> int:
    """Sum token counts from a usage object of unknown exact shape."""
    u = _to_dict(usage)
    total = _first(u, "total", "total_tokens", "totalTokens")
    if isinstance(total, (int, float)):
        return int(total)
    running = 0
    for k, v in u.items():
        if isinstance(v, (int, float)) and any(
            t in k.lower() for t in ("token", "input", "output", "prompt", "completion")
        ):
            running += int(v)
    return running


def _state_from_output(output) -> str | None:
    o = _to_dict(output) if not isinstance(output, dict) else output
    if isinstance(o, dict):
        return o.get("state")
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/status")
def observability_status():
    """Whether the in-app dashboard has a live Langfuse connection."""
    return {"enabled": tracing.is_enabled()}


@router.get("/traces")
def list_traces(
    limit: int = Query(50, ge=1, le=100),
    hours: int = Query(168, ge=1, le=720),
    name: str | None = None,
):
    """Recent traces (most recent first) with the headline metrics per run."""
    client = tracing.get_client()
    if client is None:
        return {"enabled": False, "traces": []}

    frm = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        resp = client.api.trace.list(
            limit=limit, from_timestamp=frm, order_by="timestamp.desc", name=name
        )
    except Exception as e:
        return {"enabled": True, "error": str(e), "traces": []}

    out = []
    for t in getattr(resp, "data", []) or []:
        d = _to_dict(t)
        out.append({
            "id": _first(d, "id"),
            "name": _first(d, "name"),
            "timestamp": str(_first(d, "timestamp", default="")),
            "latency_s": _first(d, "latency", "latency_ms", default=0),
            "cost": _first(d, "total_cost", "totalCost", "calculated_total_cost", default=0),
            "state": _state_from_output(_first(d, "output")),
            "user_id": _first(d, "user_id", "userId"),
            "tags": _first(d, "tags", default=[]),
        })
    return {"enabled": True, "traces": out}


@router.get("/trace/{trace_id}")
def trace_detail(trace_id: str):
    """Full detail for one run: the span timeline, the model's reasoning
    (draft output), the documents each retriever span pulled, and token/cost.
    """
    client = tracing.get_client()
    if client is None:
        return {"enabled": False}

    try:
        t = _to_dict(client.api.trace.get(trace_id))
    except Exception as e:
        return {"enabled": True, "error": str(e)}

    observations = t.get("observations") or []
    spans = []
    total_tokens = 0
    reasoning = None
    retrieved = []

    # Establish a baseline start so the timeline can be drawn as offsets.
    starts = []
    for o in observations:
        od = _to_dict(o)
        st = _first(od, "start_time", "startTime")
        if st:
            starts.append(str(st))
    base = min(starts) if starts else None

    for o in observations:
        od = _to_dict(o)
        name = _first(od, "name")
        otype = (_first(od, "type", default="") or "").upper()
        st = str(_first(od, "start_time", "startTime", default="") or "")
        et = str(_first(od, "end_time", "endTime", default="") or "")
        latency = _first(od, "latency", "latency_ms", default=None)
        tokens = _token_total(_first(od, "usage", "usage_details", "usageDetails"))
        total_tokens += tokens
        level = _first(od, "level", default="DEFAULT")

        spans.append({
            "name": name,
            "type": otype,
            "start": st,
            "end": et,
            "latency_s": latency,
            "tokens": tokens,
            "model": _first(od, "model"),
            "level": level,
            "cost": _first(od, "calculated_total_cost", "total_cost", "totalCost", default=0),
        })

        out = _first(od, "output")
        if name == "draft_response" and out is not None:
            reasoning = out if isinstance(out, str) else _to_dict(out)
        if otype in ("RETRIEVER",) and out is not None:
            retrieved.append({"span": name, "output": _to_dict(out) if not isinstance(out, str) else out})

    return {
        "enabled": True,
        "id": _first(t, "id"),
        "name": _first(t, "name"),
        "timestamp": str(_first(t, "timestamp", default="")),
        "latency_s": _first(t, "latency", "latency_ms", default=0),
        "cost": _first(t, "total_cost", "totalCost", "calculated_total_cost", default=0),
        "total_tokens": total_tokens,
        "input": _to_dict(_first(t, "input")) if not isinstance(_first(t, "input"), str) else _first(t, "input"),
        "output": _to_dict(_first(t, "output")) if not isinstance(_first(t, "output"), str) else _first(t, "output"),
        "base_time": base,
        "spans": spans,
        "reasoning": reasoning,
        "retrieved_docs": retrieved,
    }


@router.get("/overview")
def overview(hours: int = Query(24, ge=1, le=720)):
    """Aggregate metrics for the dashboard header: volume, latency, tokens,
    cost, errors, model usage, workflow-state breakdown, and a per-hour
    volume series for the traffic chart. Computed from recent traces +
    generation observations.
    """
    client = tracing.get_client()
    if client is None:
        return {"enabled": False}

    frm = datetime.now(timezone.utc) - timedelta(hours=hours)

    # --- traces: volume, latency, cost, error, state breakdown, time series
    try:
        resp = client.api.trace.list(limit=100, from_timestamp=frm, order_by="timestamp.desc")
        traces = [_to_dict(t) for t in (getattr(resp, "data", []) or [])]
    except Exception as e:
        return {"enabled": True, "error": str(e)}

    latencies = []
    total_cost = 0.0
    error_count = 0
    states: dict[str, int] = {}
    buckets: dict[str, int] = {}

    for d in traces:
        lat = _first(d, "latency", "latency_ms")
        if isinstance(lat, (int, float)):
            latencies.append(float(lat))
        c = _first(d, "total_cost", "totalCost", "calculated_total_cost", default=0)
        if isinstance(c, (int, float)):
            total_cost += float(c)

        state = _state_from_output(_first(d, "output"))
        if state:
            states[state] = states.get(state, 0) + 1
        if state and state.upper() in ("ERROR", "FAILED"):
            error_count += 1

        ts = str(_first(d, "timestamp", default=""))
        if len(ts) >= 13:  # YYYY-MM-DDTHH
            hour = ts[:13]
            buckets[hour] = buckets.get(hour, 0) + 1

    latencies.sort()

    def _pct(p):
        if not latencies:
            return 0
        idx = min(len(latencies) - 1, int(round((p / 100) * (len(latencies) - 1))))
        return round(latencies[idx], 3)

    avg_latency = round(sum(latencies) / len(latencies), 3) if latencies else 0

    # --- generations: token totals + per-model usage
    # --- token totals + per-model usage.
    # We read this from each trace's own observations (the same source the
    # trace-detail view uses) rather than observations.get_many, which lags
    # and reports inconsistently on the Hobby tier. Capped at 20 traces so a
    # busy window doesn't fan out into too many detail calls.
    total_tokens = 0
    model_usage: dict[str, dict] = {}
    for d in traces[:20]:
        tid = _first(d, "id")
        if not tid:
            continue
        try:
            full = _to_dict(client.api.trace.get(tid))
        except Exception:
            continue
        for o in (full.get("observations") or []):
            od = _to_dict(o)
            if (_first(od, "type", default="") or "").upper() not in ("GENERATION", "EMBEDDING"):
                continue
            tk = _token_total(_first(od, "usage", "usage_details", "usageDetails"))
            total_tokens += tk
            model = _first(od, "model", default="unknown") or "unknown"
            m = model_usage.setdefault(model, {"calls": 0, "tokens": 0})
            m["calls"] += 1
            m["tokens"] += tk  # token/model breakdown is best-effort

    time_series = [{"hour": h, "count": buckets[h]} for h in sorted(buckets.keys())]

    return {
        "enabled": True,
        "window_hours": hours,
        "total_traces": len(traces),
        "avg_latency_s": avg_latency,
        "p95_latency_s": _pct(95),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "error_count": error_count,
        "error_rate": round(error_count / len(traces), 3) if traces else 0,
        "states": states,
        "model_usage": [{"model": k, **v} for k, v in model_usage.items()],
        "time_series": time_series,
    }