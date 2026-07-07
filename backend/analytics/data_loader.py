"""Dataset ingestion, cleaning and profiling for the analytics agents.

Datasets (CSV / Excel) are persisted to disk under DATASETS_DIR and their
metadata is tracked in MongoDB (collection `datasets`, with the same
JSON-file fallback used everywhere else in this app).
"""
import os
import io
import uuid
import datetime

import numpy as np
import pandas as pd

from analytics.utils import (
    json_safe,
    numeric_columns,
    datetime_columns,
    categorical_columns,
    round_num,
)

DATASETS_DIR = "analytics_data"

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".tsv"}


def _ensure_dir():
    if not os.path.exists(DATASETS_DIR):
        os.makedirs(DATASETS_DIR)


def _datasets_collection():
    # Imported lazily so this module can be used in scripts/tests without a DB.
    from db import db_get_collection
    return db_get_collection("datasets")


def read_dataframe(path: str) -> pd.DataFrame:
    """Read a CSV/TSV/Excel file from disk into a DataFrame."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    # Default to CSV. Try utf-8 then fall back to latin-1 for messy exports.
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def read_dataframe_from_bytes(content: bytes, filename: str) -> pd.DataFrame:
    ext = os.path.splitext(filename)[1].lower()
    bio = io.BytesIO(content)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(bio)
    if ext == ".tsv":
        return pd.read_csv(bio, sep="\t")
    try:
        return pd.read_csv(bio)
    except UnicodeDecodeError:
        bio.seek(0)
        return pd.read_csv(bio, encoding="latin-1")


def clean_dataframe(df: pd.DataFrame):
    """Clean a raw DataFrame and return (clean_df, list_of_actions).

    Cleaning is deterministic and reported back so the Data Analyst Claw can
    explain exactly what it did to the raw data.
    """
    actions = []
    original_shape = df.shape

    # 1. Normalise column names (strip whitespace, collapse spaces).
    new_cols = []
    renamed = 0
    for c in df.columns:
        nc = str(c).strip()
        nc = " ".join(nc.split())
        if nc != str(c):
            renamed += 1
        new_cols.append(nc if nc else f"column_{len(new_cols)}")
    df.columns = new_cols
    if renamed:
        actions.append(f"Normalised {renamed} column name(s) (trimmed whitespace).")

    # 2. Drop fully-empty rows and columns.
    before_cols = df.shape[1]
    df = df.dropna(axis=1, how="all")
    dropped_cols = before_cols - df.shape[1]
    if dropped_cols:
        actions.append(f"Dropped {dropped_cols} completely empty column(s).")

    before_rows = df.shape[0]
    df = df.dropna(axis=0, how="all")
    dropped_rows = before_rows - df.shape[0]
    if dropped_rows:
        actions.append(f"Dropped {dropped_rows} completely empty row(s).")

    # 3. Remove exact duplicate rows.
    before_rows = df.shape[0]
    df = df.drop_duplicates()
    dup_rows = before_rows - df.shape[0]
    if dup_rows:
        actions.append(f"Removed {dup_rows} duplicate row(s).")

    # 4. Strip whitespace on object/string columns.
    obj_cols = df.select_dtypes(include="object").columns
    for c in obj_cols:
        try:
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"": np.nan, "nan": np.nan, "None": np.nan, "null": np.nan})
        except Exception:
            pass

    # 5. Attempt numeric coercion for object cols that are mostly numbers
    #    (handles currency/thousand-separator strings like "$1,200").
    coerced_numeric = []
    for c in df.select_dtypes(include="object").columns:
        sample = df[c].dropna().astype(str).str.replace(r"[,$%\s]", "", regex=True)
        coerced = pd.to_numeric(sample, errors="coerce")
        non_null = sample.shape[0]
        if non_null > 0 and coerced.notna().mean() >= 0.9:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(r"[,$%\s]", "", regex=True),
                errors="coerce",
            )
            coerced_numeric.append(c)
    if coerced_numeric:
        actions.append(f"Converted {len(coerced_numeric)} text column(s) to numeric: {', '.join(coerced_numeric[:5])}.")

    # 6. Attempt datetime parsing for object columns that look like dates.
    coerced_dates = []
    for c in df.select_dtypes(include="object").columns:
        lname = c.lower()
        looks_like_date = any(k in lname for k in ("date", "time", "day", "month", "year", "timestamp"))
        sample = df[c].dropna().head(50)
        if sample.empty:
            continue
        try:
            parsed = pd.to_datetime(sample, errors="coerce")
        except Exception:
            continue
        if parsed.notna().mean() >= (0.7 if looks_like_date else 0.95):
            df[c] = pd.to_datetime(df[c], errors="coerce")
            coerced_dates.append(c)
    if coerced_dates:
        actions.append(f"Parsed {len(coerced_dates)} column(s) as dates: {', '.join(coerced_dates[:5])}.")

    # 7. Fill remaining numeric NaNs report (we do NOT impute silently; just note).
    total_missing = int(df.isna().sum().sum())
    if total_missing:
        actions.append(f"{total_missing} missing value(s) remain across the dataset (left as-is for transparency).")

    if not actions:
        actions.append("Data was already clean — no transformations needed.")

    summary = {
        "original_rows": int(original_shape[0]),
        "original_cols": int(original_shape[1]),
        "clean_rows": int(df.shape[0]),
        "clean_cols": int(df.shape[1]),
        "actions": actions,
    }
    return df.reset_index(drop=True), summary


def profile_dataframe(df: pd.DataFrame, preview_rows: int = 8):
    """Build a structured profile of the dataset for the UI and the LLM."""
    num_cols = numeric_columns(df)
    dt_cols = datetime_columns(df)
    cat_cols = categorical_columns(df)

    columns = []
    for c in df.columns:
        s = df[c]
        col = {
            "name": c,
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "missing_pct": round_num(s.isna().mean() * 100, 1),
            "unique": int(s.nunique(dropna=True)),
        }
        if c in num_cols:
            col["kind"] = "numeric"
            desc = s.describe()
            col["min"] = round_num(desc.get("min"))
            col["max"] = round_num(desc.get("max"))
            col["mean"] = round_num(desc.get("mean"))
            col["median"] = round_num(s.median())
            col["std"] = round_num(desc.get("std"))
        elif c in dt_cols:
            col["kind"] = "datetime"
            col["min"] = str(s.min()) if s.notna().any() else None
            col["max"] = str(s.max()) if s.notna().any() else None
        else:
            col["kind"] = "categorical" if c in cat_cols else "text"
            top = s.value_counts(dropna=True).head(5)
            col["top_values"] = [{"value": str(k), "count": int(v)} for k, v in top.items()]
        columns.append(col)

    preview = df.head(preview_rows).copy()
    # Stringify datetimes for clean JSON.
    for c in dt_cols:
        preview[c] = preview[c].astype(str)
    preview_records = json_safe(preview.where(pd.notna(preview), None).to_dict(orient="records"))

    return {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "numeric_columns": num_cols,
        "datetime_columns": dt_cols,
        "categorical_columns": cat_cols,
        "columns": columns,
        "preview": preview_records,
    }


def save_dataset(content: bytes, filename: str, user_email: str, source: str = "upload", org_id: str = None):
    """Persist an uploaded dataset, clean it, store cleaned copy + metadata.

    Returns the dataset metadata dict (including profile).
    """
    _ensure_dir()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    dataset_id = uuid.uuid4().hex[:16]

    # Read raw -> clean -> persist a parquet/csv of the cleaned frame for fast reload.
    raw_df = read_dataframe_from_bytes(content, filename)
    if raw_df.empty:
        raise ValueError("The uploaded file contains no rows.")

    clean_df, clean_summary = clean_dataframe(raw_df)

    clean_path = os.path.join(DATASETS_DIR, f"{dataset_id}.parquet")
    stored_as = "parquet"
    try:
        clean_df.to_parquet(clean_path, index=False)
    except Exception:
        # pyarrow may be unavailable; fall back to CSV.
        clean_path = os.path.join(DATASETS_DIR, f"{dataset_id}.csv")
        stored_as = "csv"
        clean_df.to_csv(clean_path, index=False)

    profile = profile_dataframe(clean_df)

    meta = {
        "dataset_id": dataset_id,
        "user_email": user_email,
        "org_id": org_id,
        "name": filename,
        "path": clean_path,
        "stored_as": stored_as,
        "source": source,
        "rows": int(clean_df.shape[0]),
        "cols": int(clean_df.shape[1]),
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
        "clean_summary": clean_summary,
    }

    coll = _datasets_collection()
    coll.update_one(
        {"dataset_id": dataset_id},
        {"$set": meta},
        upsert=True,
    )

    result = dict(meta)
    result["profile"] = profile
    return json_safe(result)


def load_dataset(dataset_id: str, org_id: str = None):
    """Load (metadata, DataFrame) for a stored dataset, scoped to the org."""
    coll = _datasets_collection()
    meta = coll.find_one({"dataset_id": dataset_id})
    if not meta:
        raise ValueError("Dataset not found.")
    # Cross-org access is indistinguishable from "not found".
    if org_id is not None and meta.get("org_id") != org_id:
        raise ValueError("Dataset not found.")
    path = meta.get("path")
    if not path or not os.path.exists(path):
        raise ValueError("Dataset file is missing on the server. Please re-upload.")

    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        df = read_dataframe(path)
    # Re-coerce datetimes that may have been flattened by CSV round-trip.
    for c in df.columns:
        if df[c].dtype == object and any(k in c.lower() for k in ("date", "time")):
            try:
                parsed = pd.to_datetime(df[c], errors="coerce")
                if parsed.notna().mean() >= 0.7:
                    df[c] = parsed
            except Exception:
                pass
    return meta, df


def list_datasets(org_id: str):
    coll = _datasets_collection()
    docs = list(coll.find({"org_id": org_id}))
    out = []
    for d in docs:
        out.append({
            "dataset_id": d.get("dataset_id"),
            "name": d.get("name"),
            "rows": d.get("rows"),
            "cols": d.get("cols"),
            "source": d.get("source"),
            "uploaded_at": d.get("uploaded_at"),
        })
    out.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    return out


def delete_dataset(dataset_id: str, org_id: str):
    coll = _datasets_collection()
    meta = coll.find_one({"dataset_id": dataset_id})
    if not meta or (org_id is not None and meta.get("org_id") != org_id):
        return False
    path = meta.get("path")
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    coll.delete_many({"dataset_id": dataset_id})
    return True
