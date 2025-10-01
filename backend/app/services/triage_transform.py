import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

REPORT_TITLE = "Safety & Triage Summary"
SAFE_NO_URGENT_MSG = (
    "No immediate life-threatening concerns detected based on provided answers and text. "
    "This is safety triage, not a diagnosis. If your child seems in immediate danger, call 911."
)
URGENT_PRESENT_MSG = (
    "We have flagged the following issues as URGENT and requiring immediate contact with a medical professional."
)


def _sha256_of_obj(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_patient_report(triage_result: Dict[str, Any], source_version: str = "1.0.0") -> Dict[str, Any]:
    """
    Build patient-friendly report JSON from clinician triage result.

    Expected keys in triage_result (per TRIAGE_JSON_SCHEMA_EXAMPLE):
    - urgent_items: List[triage_item]

    Returns JSON with keys per the patient's simplified schema:
    - summary_title, message, urgent_items, meta
    """
    urgent_items: List[Dict[str, Any]] = list(triage_result.get("urgent_items", []) or [])

    # Only include URGENT items and only the required fields
    urgent_items_filtered: List[Dict[str, Any]] = []
    for item in urgent_items:
        severity = item.get("severity")
        if severity == "URGENT (HIGH)":
            urgent_items_filtered.append(
                {
                    "severity": severity,
                    "category": item.get("category"),
                    "evidence": item.get("evidence"),
                    "why_it_matters": item.get("why_it_matters"),
                    "next_step": item.get("next_step"),
                }
            )

    has_urgent = len(urgent_items_filtered) > 0
    message = URGENT_PRESENT_MSG if has_urgent else SAFE_NO_URGENT_MSG

    report = {
        "summary_title": REPORT_TITLE,
        "message": message,
        "urgent_items": urgent_items_filtered,
        "meta": {
            "source_version": source_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "linked_input_hash": _sha256_of_obj(triage_result),
        },
    }
    return report
