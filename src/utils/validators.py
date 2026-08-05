"""Validators for output data.

Owner: Member C
"""

import re
from typing import Any

from src.config import LIMITS


VALID_PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}

VALID_SECONDARY_ISSUES = {
    "multi_item_order",
    "multi_seller_order",
    "split_payment",
    "repeat_customer",
    "multiple_categories",
}

VALID_CASE_STATUSES = {"action_required", "no_action"}

VALID_EVIDENCE_PATTERNS = [
    re.compile(r"^order:.+$"),
    re.compile(r"^item:.+:\d+$"),
    re.compile(r"^payment:.+:\d+$"),
    re.compile(r"^seller:.+$"),
    re.compile(r"^policy:.+$"),
]


def validate_evidence_id(evidence_id: str) -> bool:
    """Check if an evidence ID matches a valid pattern."""
    return any(p.match(evidence_id) for p in VALID_EVIDENCE_PATTERNS)


def validate_array_limits(output: dict) -> list[str]:
    """Check all arrays respect their limits. Returns list of errors."""
    errors = []
    entities = output.get("affected_entities", {})
    for key, limit in LIMITS.items():
        # Check in affected_entities
        if key in entities and len(entities[key]) > limit:
            errors.append(f"affected_entities.{key} exceeds limit {limit}")
        # Check in top-level
        if key in output and isinstance(output[key], list) and len(output[key]) > limit:
            errors.append(f"{key} exceeds limit {limit}")
    return errors


def validate_confidence(confidence: float) -> bool:
    """Check confidence is in [0, 1]."""
    return 0 <= confidence <= 1


def validate_case_status(status: str) -> bool:
    """Check case_status is valid."""
    return status in VALID_CASE_STATUSES
