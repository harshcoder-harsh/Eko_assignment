"""Deterministic analytics computations shared by the Claw agents.

Every number that ends up in front of the user (or the LLM) is computed here
with pandas / numpy / scikit-learn — never hallucinated by the model.
"""
import numpy as np
import pandas as pd

from analytics.utils import (
    json_safe,
    numeric_columns,
    datetime_columns,
    categorical_columns,
    round_num,
    pct_change,
)


# --------------------------------------------------------------------------- #
# Column-role inference
# --------------------------------------------------------------------------- #
def infer_metric_columns(df: pd.DataFrame):
    """Heuristically pick the numeric columns that look like business metrics.

    Drops obvious ID / index columns (mostly-unique integers, names containing
    'id').
    """
    metrics = []
    for c in numeric_columns(df):
        lname = c.lower()
        if lname in ("id", "index") or lname.endswith("_id") or lname.endswith(" id") or lname == "unnamed: 0":
            continue
        # A near-unique INTEGER column is probably an identifier/row number.
        # Continuous floats (e.g. Revenue) are naturally near-unique, so we
        # only drop integer-typed columns on the cardinality heuristic.
        is_int = pd.api.types.is_integer_dtype(df[c])
        nunique = df[c].nunique(dropna=True)
        if is_int and df.shape[0] > 20 and nunique >= df.shape[0] * 0.95:
            continue
        metrics.append(c)
    return metrics or numeric_columns(df)


def primary_datetime_column(df: pd.DataFrame):
    dts = datetime_columns(df)
    if not dts:
        return None
    # Prefer the datetime column with the widest coverage.
    return max(dts, key=lambda c: df[c].notna().sum())


def _resample_metrics(tdf, dt_col, metrics, period, agg="sum"):
    """Resample to `period` and trim leading/trailing PARTIAL buckets.

    A partial bucket (e.g. a half-finished current week) otherwise produces a
    sharp false drop in trend / period-over-period calculations.
    """
    g = tdf.set_index(dt_col).resample(period)
    counts = g.size()
    if agg == "mean":
        data = g[metrics].mean()
    else:
        data = g[metrics].sum(min_count=1)
    data = data.dropna(how="all")
    counts = counts.reindex(data.index).fillna(0)

    if len(data) >= 3:
        # Trim trailing partial bucket.
        median_tail = counts.iloc[:-1].median()
        if median_tail > 0 and counts.iloc[-1] < 0.5 * median_tail:
            data = data.iloc[:-1]
            counts = counts.iloc[:-1]
    if len(data) >= 3:
        # Trim leading partial bucket.
        median_head = counts.iloc[1:].median()
        if median_head > 0 and counts.iloc[0] < 0.5 * median_head:
            data = data.iloc[1:]
    return data


def _choose_period(span_days: float) -> str:
    if span_days <= 2:
        return "h"      # hourly
    if span_days <= 60:
        return "D"      # daily
    if span_days <= 730:
        return "W"      # weekly
    return "ME"         # month-end


# --------------------------------------------------------------------------- #
# 1. KPIs / descriptive stats
# --------------------------------------------------------------------------- #
def compute_kpis(df: pd.DataFrame):
    metrics = infer_metric_columns(df)
    kpis = []
    for c in metrics:
        s = df[c].dropna()
        if s.empty:
            continue
        kpis.append({
            "name": c,
            "total": round_num(s.sum()),
            "average": round_num(s.mean()),
            "median": round_num(s.median()),
            "min": round_num(s.min()),
            "max": round_num(s.max()),
            "std": round_num(s.std()),
            "count": int(s.shape[0]),
        })

    # Categorical breakdowns (top category per low-cardinality column).
    breakdowns = []
    for c in categorical_columns(df):
        vc = df[c].value_counts(dropna=True).head(6)
        if vc.empty:
            continue
        breakdowns.append({
            "column": c,
            "distinct": int(df[c].nunique(dropna=True)),
            "top": [{"value": str(k), "count": int(v), "pct": round_num(v / df.shape[0] * 100, 1)} for k, v in vc.items()],
        })

    return json_safe({
        "row_count": int(df.shape[0]),
        "metric_count": len(kpis),
        "kpis": kpis,
        "breakdowns": breakdowns,
    })


# --------------------------------------------------------------------------- #
# 2. Trends (time series + correlations)
# --------------------------------------------------------------------------- #
def compute_trends(df: pd.DataFrame):
    metrics = infer_metric_columns(df)
    dt_col = primary_datetime_column(df)
    result = {"has_time_series": False, "series": [], "correlations": []}

    if dt_col and metrics:
        tdf = df[[dt_col] + metrics].dropna(subset=[dt_col]).copy()
        tdf = tdf.sort_values(dt_col)
        if not tdf.empty:
            span_days = (tdf[dt_col].max() - tdf[dt_col].min()).days or 1
            period = _choose_period(span_days)
            grouped = _resample_metrics(tdf, dt_col, metrics, period, agg="sum")

            result["has_time_series"] = True
            result["time_column"] = dt_col
            result["period"] = {"h": "hourly", "D": "daily", "W": "weekly", "ME": "monthly"}.get(period, period)

            for m in metrics:
                if m not in grouped.columns:
                    continue
                series = grouped[m].dropna()
                if series.shape[0] < 2:
                    continue
                points = [{"t": str(idx.date() if hasattr(idx, "date") else idx), "v": round_num(val)}
                          for idx, val in series.items()]
                # Fit a line; use its endpoints for both direction and % change so
                # the two never contradict each other.
                x = np.arange(series.shape[0])
                y = series.values.astype(float)
                slope, intercept = np.polyfit(x, y, 1)
                slope = float(slope)
                fit_first = float(intercept)
                fit_last = float(slope * (len(y) - 1) + intercept)
                trend_change = pct_change(fit_first, fit_last)
                # Direction from the total fitted change so it never contradicts
                # the reported change_pct.
                if trend_change is None:
                    direction = "flat"
                elif trend_change > 5:
                    direction = "increasing"
                elif trend_change < -5:
                    direction = "decreasing"
                else:
                    direction = "flat"
                result["series"].append({
                    "metric": m,
                    "direction": direction,
                    "change_pct": trend_change,
                    "first": round_num(float(series.iloc[0])),
                    "last": round_num(float(series.iloc[-1])),
                    "peak": round_num(series.max()),
                    "trough": round_num(series.min()),
                    "points": points[-60:],  # cap payload
                })

    # Correlations between metrics (regardless of time).
    if len(metrics) >= 2:
        corr = df[metrics].corr(numeric_only=True)
        seen = set()
        pairs = []
        for i, a in enumerate(metrics):
            for b in metrics[i + 1:]:
                try:
                    val = corr.loc[a, b]
                except (KeyError, ValueError):
                    continue
                if pd.isna(val):
                    continue
                if abs(val) >= 0.5:
                    pairs.append({"a": a, "b": b, "r": round_num(val)})
        pairs.sort(key=lambda p: abs(p["r"]), reverse=True)
        result["correlations"] = pairs[:8]

    return json_safe(result)


# --------------------------------------------------------------------------- #
# 3. Anomaly detection (z-score + IQR)
# --------------------------------------------------------------------------- #
def detect_anomalies(df: pd.DataFrame, z_thresh: float = 3.0, max_per_col: int = 20):
    metrics = infer_metric_columns(df)
    dt_col = primary_datetime_column(df)
    anomalies = []
    columns_summary = []

    for c in metrics:
        s = df[c].dropna()
        if s.shape[0] < 8:
            continue
        mean, std = float(s.mean()), float(s.std())
        q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
        iqr = q3 - q1
        lower_iqr, upper_iqr = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        col_anoms = []
        for idx, val in s.items():
            v = float(val)
            z = (v - mean) / std if std > 0 else 0.0
            is_z = abs(z) >= z_thresh
            is_iqr = iqr > 0 and (v < lower_iqr or v > upper_iqr)
            if is_z or is_iqr:
                row = {
                    "column": c,
                    "row_index": int(idx),
                    "value": round_num(v),
                    "z_score": round_num(z),
                    "direction": "high" if v > mean else "low",
                    "methods": [m for m, flag in (("z-score", is_z), ("IQR", is_iqr)) if flag],
                }
                if dt_col and idx in df.index and pd.notna(df.at[idx, dt_col]):
                    row["when"] = str(df.at[idx, dt_col])
                col_anoms.append(row)

        col_anoms.sort(key=lambda r: abs(r["z_score"] or 0), reverse=True)
        columns_summary.append({
            "column": c,
            "anomaly_count": len(col_anoms),
            "normal_range": [round_num(lower_iqr), round_num(upper_iqr)],
            "mean": round_num(mean),
        })
        anomalies.extend(col_anoms[:max_per_col])

    anomalies.sort(key=lambda r: abs(r["z_score"] or 0), reverse=True)
    return json_safe({
        "total_anomalies": sum(c["anomaly_count"] for c in columns_summary),
        "columns": columns_summary,
        "anomalies": anomalies[:100],
    })


# --------------------------------------------------------------------------- #
# 4. Customer / entity segmentation (KMeans)
# --------------------------------------------------------------------------- #
def segment_entities(df: pd.DataFrame, max_k: int = 5):
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    metrics = infer_metric_columns(df)
    feat_cols = [c for c in metrics if df[c].notna().sum() >= max(10, df.shape[0] * 0.5)]
    if len(feat_cols) < 2:
        return json_safe({
            "ok": False,
            "reason": "Need at least 2 well-populated numeric columns to segment.",
            "feature_columns": feat_cols,
        })

    X = df[feat_cols].copy()
    X = X.fillna(X.median(numeric_only=True))
    if X.shape[0] < 10:
        return json_safe({"ok": False, "reason": "Need at least 10 rows to segment.", "feature_columns": feat_cols})

    # Winsorize each feature to its 1st–99th percentile before scaling so that a
    # handful of extreme outliers can't each claim their own cluster (which
    # otherwise produces degenerate 1-member segments).
    Xc = X.copy()
    for c in feat_cols:
        lo, hi = Xc[c].quantile(0.01), Xc[c].quantile(0.99)
        if hi > lo:
            Xc[c] = Xc[c].clip(lo, hi)

    Xs = StandardScaler().fit_transform(Xc)

    # Pick k by silhouette score over a small range.
    best_k, best_score, best_labels = 2, -1.0, None
    upper = min(max_k, X.shape[0] - 1)
    for k in range(2, max(3, upper + 1)):
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(Xs)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(Xs, labels)
        except Exception:
            continue
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels

    if best_labels is None:
        return json_safe({"ok": False, "reason": "Clustering did not converge on this data.", "feature_columns": feat_cols})

    df_seg = X.copy()
    df_seg["__segment__"] = best_labels

    overall_means = {c: float(X[c].mean()) for c in feat_cols}
    segments = []
    for seg_id in sorted(set(best_labels)):
        members = df_seg[df_seg["__segment__"] == seg_id]
        profile = {}
        highlights = []
        for c in feat_cols:
            seg_mean = float(members[c].mean())
            profile[c] = round_num(seg_mean)
            ov = overall_means[c] or 1.0
            delta = (seg_mean - ov) / abs(ov) * 100 if ov else 0
            if abs(delta) >= 20:
                highlights.append({"feature": c, "vs_avg_pct": round_num(delta), "direction": "above" if delta > 0 else "below"})
        highlights.sort(key=lambda h: abs(h["vs_avg_pct"] or 0), reverse=True)
        segments.append({
            "segment": int(seg_id),
            "size": int(members.shape[0]),
            "size_pct": round_num(members.shape[0] / df.shape[0] * 100, 1),
            "profile": profile,
            "highlights": highlights[:4],
            "label": _auto_label_segment(highlights),
        })

    segments.sort(key=lambda s: s["size"], reverse=True)
    return json_safe({
        "ok": True,
        "k": best_k,
        "silhouette": round_num(best_score, 3),
        "feature_columns": feat_cols,
        "segments": segments,
    })


def _auto_label_segment(highlights):
    if not highlights:
        return "Balanced / average profile"
    top = highlights[0]
    feat = top["feature"]
    dirn = "high" if top["direction"] == "above" else "low"
    return f"{dirn.capitalize()} {feat}"


# --------------------------------------------------------------------------- #
# 5. KPI monitoring (period-over-period change)
# --------------------------------------------------------------------------- #
def monitor_kpis(df: pd.DataFrame):
    metrics = infer_metric_columns(df)
    dt_col = primary_datetime_column(df)
    changes = []

    if dt_col and metrics:
        tdf = df[[dt_col] + metrics].dropna(subset=[dt_col]).sort_values(dt_col)
        if not tdf.empty:
            span_days = (tdf[dt_col].max() - tdf[dt_col].min()).days or 1
            period = _choose_period(span_days)
            grouped = _resample_metrics(tdf, dt_col, metrics, period, agg="sum")
            label = {"h": "hour", "D": "day", "W": "week", "ME": "month"}.get(period, period)
            if grouped.shape[0] >= 2:
                current = grouped.iloc[-1]
                previous = grouped.iloc[-2]
                for m in metrics:
                    if m not in grouped.columns:
                        continue
                    cur, prev = current.get(m), previous.get(m)
                    if pd.isna(cur) or pd.isna(prev):
                        continue
                    change = pct_change(prev, cur)
                    changes.append({
                        "metric": m,
                        "current": round_num(cur),
                        "previous": round_num(prev),
                        "change_pct": change,
                        "period": label,
                        "status": _change_status(change),
                    })
            return json_safe({
                "mode": "time-based",
                "period": label,
                "changes": sorted(changes, key=lambda c: abs(c["change_pct"] or 0), reverse=True),
            })

    # Fallback: compare the first half vs the second half of the rows.
    if metrics and df.shape[0] >= 4:
        mid = df.shape[0] // 2
        for m in metrics:
            first = df[m].iloc[:mid].mean()
            second = df[m].iloc[mid:].mean()
            if pd.isna(first) or pd.isna(second):
                continue
            change = pct_change(first, second)
            changes.append({
                "metric": m,
                "current": round_num(second),
                "previous": round_num(first),
                "change_pct": change,
                "period": "second vs first half",
                "status": _change_status(change),
            })
    return json_safe({
        "mode": "split-based",
        "period": "second half vs first half (no date column found)",
        "changes": sorted(changes, key=lambda c: abs(c["change_pct"] or 0), reverse=True),
    })


def _change_status(change):
    if change is None:
        return "stable"
    if change >= 15:
        return "up_strong"
    if change >= 3:
        return "up"
    if change <= -15:
        return "down_strong"
    if change <= -3:
        return "down"
    return "stable"
