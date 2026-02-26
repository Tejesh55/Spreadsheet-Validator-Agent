"""
Tool: Update rows in validated_errors.jsonl using row_hash.
"""

import os
import json
from typing import List, Dict


RUN_DIR = "runs/current"
ERROR_PATH = os.path.join(RUN_DIR, "validated_errors.jsonl")


def update_data(user_updates: List[Dict]) -> Dict[str, str]:
    """
    Updates the errors file, based on user's suggestions on fixes
    
    user_updates format:
    [
        {
            "row_hash": "...",
            "updates": { "fx_rate": 1.08 }
        }
    ]
    """

    if not os.path.exists(ERROR_PATH):
        return {"message": "No error file found to update."}

    # Load existing errors
    rows = []
    with open(ERROR_PATH, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line.strip()))

    # Build quick lookup
    update_map = {
        item["row_hash"]: item["updates"]
        for item in user_updates
    }

    updated_count = 0

    for row in rows:
        rh = row.get("row_hash")
        if rh in update_map:
            for key, value in update_map[rh].items():
                row[key] = value
            updated_count += 1

    # Rewrite file
    with open(ERROR_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    return {
        "updated_rows": updated_count,
        "message": f"{updated_count} rows updated successfully."
    }