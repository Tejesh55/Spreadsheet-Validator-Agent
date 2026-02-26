"""
Tool: Ingest file, normalize data types, and persist to disk.
"""

import os
import uuid
import json
import pandas as pd
from typing import Dict, List, Any, Optional

REQUIRED_COLUMNS = [
    "employee_id",
    "dept",
    "amount",
    "currency",
    "spend_date",
    "vendor"
]


def _safe_json(value: Any):
    """Convert pandas/numpy types to JSON-safe values."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    return value


def _default_uploaded_file_path() -> Optional[str]:
    uploads_dir = "uploads"
    for ext in (".csv", ".xlsx"):
        candidate = os.path.join(uploads_dir, f"current_upload{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def ingest_file() -> Dict[str, Any]:
    """
    Reads uploaded file, normalizes schema, stores processed data on disk.

    Returns:
        {
            "normalized_path": str,
            "row_count": int,
            "prompts": List[str]
        }
    """

    errors: List[str] = []

    file_path = _default_uploaded_file_path()
    if not file_path:
        return {
            "run_id": None,
            "normalized_path": None,
            "row_count": 0,
            "prompts": ["No uploaded file found in uploads folder."]
        }

    try:
        # ---------- Read file ----------
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            return {
                "run_id": None,
                "normalized_path": None,
                "row_count": 0,
                "prompts": ["Unsupported file type. Only .csv and .xlsx allowed."]
            }

        # ---------- Validate schema ----------
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return {
                "run_id": None,
                "normalized_path": None,
                "row_count": 0,
                "prompts": [f"Missing required columns: {missing_cols}"]
            }

        # ---------- Normalize types ----------
        df["employee_id"] = df["employee_id"].astype(str)
        df["dept"] = df["dept"].astype(str)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["currency"] = df["currency"].astype(str)
        df["spend_date"] = pd.to_datetime(df["spend_date"], errors="coerce")
        df["vendor"] = df["vendor"].astype(str)

        df = df.drop(
            columns=["amount_usd", "cost_center", "approval_required", "error_reason"],
            errors="ignore"
        )

        # ---------- Create run directory ----------
        run_dir = os.path.join("runs", "current")
        os.makedirs(run_dir, exist_ok=True)

        normalized_path = os.path.join(run_dir, "normalized.jsonl")

        # ---------- Write JSONL (stream-friendly) ----------
        row_count = 0
        with open(normalized_path, "w", encoding="utf-8") as f:
            for _, row in df.iterrows():
                clean_row = {col: _safe_json(row[col]) for col in df.columns}
                f.write(json.dumps(clean_row) + "\n")
                row_count += 1

        return {
            "normalized_path": normalized_path,
            "row_count": row_count,
            "prompts": errors
        }

    except Exception as e:
        return {
            "normalized_path": None,
            "row_count": 0,
            "prompts": [f"File read error: {str(e)}"]
        }