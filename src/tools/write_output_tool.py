"""
Tool: Build success.xlsx and errors.xlsx from stored validated files.
Reads from disk (deterministic), builds Excel in memory, returns base64.
"""

import os
import json
import base64
import pandas as pd
from io import BytesIO
from typing import Dict, List


# ---- Deterministic Paths ----

RUN_DIR = "runs/current"
SUCCESS_PATH = os.path.join(RUN_DIR, "validated_success.jsonl")
ERROR_PATH = os.path.join(RUN_DIR, "validated_errors.jsonl")


def _read_jsonl(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line.strip()))
    return rows


def write_output() -> Dict[str, str]:
    """
    Reads validated_success.jsonl and validated_errors.jsonl,
    builds Excel files in memory, returns base64-encoded content.
    """

    success_rows = _read_jsonl(SUCCESS_PATH)
    error_rows = _read_jsonl(ERROR_PATH)

    base_cols = [
        "employee_id", "dept", "amount", "currency", "spend_date",
        "vendor", "fx_rate", "amount_usd",
        "cost_center", "approval_required"
    ]

    success_df = pd.DataFrame(success_rows)
    error_df = pd.DataFrame(error_rows)

    # Ensure required columns exist
    for col in base_cols:
        if col not in success_df.columns:
            success_df[col] = None
        if col not in error_df.columns:
            error_df[col] = None

    if "error_reason" not in error_df.columns:
        error_df["error_reason"] = None

    success_df = success_df[base_cols]
    error_df = error_df[base_cols + ["error_reason"]]

    # ---- Build Excel in memory ----

    buf_success = BytesIO()
    buf_errors = BytesIO()

    success_df.to_excel(buf_success, index=False, engine="openpyxl")
    error_df.to_excel(buf_errors, index=False, engine="openpyxl")

    buf_success.seek(0)
    buf_errors.seek(0)

    return {
        "success_b64": base64.b64encode(buf_success.read()).decode("ascii"),
        "errors_b64": base64.b64encode(buf_errors.read()).decode("ascii"),
    }