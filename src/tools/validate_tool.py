"""
Tool: Validate data against deterministic rules.
Reads from default normalized file path.
Validation logic unchanged.
"""

import os
import json
import re
import hashlib
from typing import Dict, List
from datetime import datetime


# ---- Constants ----

RUN_DIR = "runs/current"
NORMALIZED_PATH = os.path.join(RUN_DIR, "normalized.jsonl")
SUCCESS_PATH = os.path.join(RUN_DIR, "validated_success.jsonl")
ERROR_PATH = os.path.join(RUN_DIR, "validated_errors.jsonl")

VALID_DEPTS = ["FIN", "HR", "ENG", "OPS"]
VALID_CURRENCIES = ["USD", "EUR", "GBP", "INR"]
EMPLOYEE_ID_REGEX = re.compile(r"^[A-Z0-9]{4,12}$")


def hash_row(row: Dict) -> str:
    canonical = json.dumps(row, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_data(
    as_of: str,
    cost_center_map: Dict[str, str],
    usd_rounding: str,
    mode: str
) -> dict:
    """
    Validates the data and generates human-in-the-loop prompts for missing/invalid mandatory fields.

    Args:
        as_of (str): As-of date for spend_date rule
        cost_center_map (Dict[str,str]): dept -> cost_center mapping
        usd_rounding (str): rounding amount_usd
        mode (str): 'new' if processing new file or 'reprocess' if processing errors file. Dont ask user, provide based on your reasoning
    """

    mode = mode.lower()

    if mode == "new":
        input_path = NORMALIZED_PATH
    elif mode == "reprocess":
        input_path = ERROR_PATH
    else:
        return {
            "message": "Invalid mode. Use 'new' or 'reprocess'."
        }

    if not os.path.exists(input_path):
        return {
            "validated_success_path": None,
            "validated_error_path": None,
            "total_rows": 0,
            "valid_rows": 0,
            "error_rows": 0,
            "display_errors": [],
            "message": "Normalized file not found. Please run ingest first."
        }

    as_of_date = datetime.strptime(as_of, "%Y-%m-%d")

    total_rows = 0
    valid_rows = 0
    error_rows = 0
    display_errors: List[Dict] = []
    seen_keys = {}

    rows_to_process = []
    with open(input_path, "r", encoding="utf-8") as infile:
        for line in infile:
            rows_to_process.append(json.loads(line.strip()))

    success_mode = "a" if mode == "reprocess" else "w"

    with open(SUCCESS_PATH, success_mode, encoding="utf-8") as success_file, \
         open(ERROR_PATH, "w", encoding="utf-8") as error_file:

        for idx, row in enumerate(rows_to_process):
            total_rows += 1

            # ---- VALIDATION LOGIC (UNCHANGED) ----

            row["error_reason"] = ""
            row.setdefault("fx_rate", None)
            row.setdefault("amount_usd", None)
            row.setdefault("cost_center", None)
            row.setdefault("approval_required", None)
            row["row_hash"] = hash_row(row)

            key = (row.get("employee_id"), row.get("spend_date"))
            if key in seen_keys:
                row["error_reason"] += "Duplicate employee_id and spend_date; "
            else:
                seen_keys[key] = idx

            emp_id = row.get("employee_id")
            if not emp_id or not EMPLOYEE_ID_REGEX.match(str(emp_id)):
                row["error_reason"] += "employee_id missing/invalid; "

            dept = row.get("dept")
            if not dept or dept not in VALID_DEPTS:
                row["error_reason"] += "dept missing/invalid; "

            amt = row.get("amount")
            if amt is None or not (0 < float(amt) <= 100000):
                row["error_reason"] += "amount missing/invalid; "

            currency = row.get("currency")
            if not currency or currency not in VALID_CURRENCIES:
                row["error_reason"] += "currency missing/invalid; "

            spend_date_str = row.get("spend_date")
            try:
                spend_date = datetime.strptime(spend_date_str, "%Y-%m-%d")
                if spend_date > as_of_date:
                    row["error_reason"] += f"spend_date after as_of ({as_of}); "
            except Exception:
                row["error_reason"] += "spend_date invalid; "

            vendor = row.get("vendor")
            if not vendor or str(vendor).strip() == "":
                row["error_reason"] += "vendor missing; "

            if currency != "USD":
                try:
                    fx_val = float(row.get("fx_rate"))
                    if not (0.1 <= fx_val <= 500):
                        raise ValueError()
                except Exception:
                    row["error_reason"] += "fx_rate missing/invalid; "
                    fx_val = None
            else:
                fx_val = 1.0
                row["fx_rate"] = 1.0

            if dept in cost_center_map:
                row["cost_center"] = cost_center_map[dept]
            else:
                row["error_reason"] += "cost_center missing; "

            if dept == "FIN" and amt and float(amt) > 50000:
                row["approval_required"] = "YES"
            else:
                row["approval_required"] = "NO"

            if amt is not None and fx_val is not None:
                raw_usd = float(amt) * fx_val
                if usd_rounding == "cents":
                    row["amount_usd"] = round(raw_usd, 2)
                elif usd_rounding == "whole":
                    row["amount_usd"] = round(raw_usd)
                else:
                    row["amount_usd"] = raw_usd

            # ---- END ORIGINAL LOGIC ----

            if row["error_reason"]:
                error_rows += 1
                error_file.write(json.dumps(row) + "\n")

                if error_rows <= 20:
                    display_errors.append(row)
            else:
                valid_rows += 1
                success_file.write(json.dumps(row) + "\n")

    return {
        "validated_success_path": SUCCESS_PATH,
        "validated_error_path": ERROR_PATH,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "error_rows": error_rows,
        "display_errors": display_errors if error_rows <= 20 else [],
        "message": (
            f"{error_rows} errors found. Showing below."
            if error_rows <= 20
            else f"{error_rows} errors found. Stored in file."
        )
    }