"""Shared helpers for the analytics agents (the 'Claws')."""
import math
import numpy as np
import pandas as pd


def json_safe(obj):
    """Recursively convert numpy/pandas types into plain JSON-serialisable Python.

    FastAPI/pydantic and the JSON encoder choke on numpy scalars, NaN/Inf,
    Timestamps, etc. Every value returned by an analytics agent is funnelled
    through this so the API never 500s on serialisation.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return [json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if pd.isna(obj) if np.isscalar(obj) else False:
        return None
    return obj


def is_datetime_col(series: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(series)


def numeric_columns(df: pd.DataFrame):
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def datetime_columns(df: pd.DataFrame):
    return [c for c in df.columns if is_datetime_col(df[c])]


def categorical_columns(df: pd.DataFrame, max_unique: int = 50):
    cols = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) or is_datetime_col(df[c]):
            continue
        nun = df[c].nunique(dropna=True)
        if 1 <= nun <= max_unique:
            cols.append(c)
    return cols


def round_num(x, ndigits: int = 2):
    try:
        if x is None:
            return None
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, ndigits)
    except (TypeError, ValueError):
        return None


def pct_change(old, new):
    """Percentage change from old -> new, guarding divide-by-zero."""
    try:
        old = float(old)
        new = float(new)
    except (TypeError, ValueError):
        return None
    if old == 0:
        return None if new == 0 else 100.0
    return round((new - old) / abs(old) * 100.0, 2)
