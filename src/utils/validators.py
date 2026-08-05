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
    
    # Check in affected_entities
    for key in ["order_ids", "item_ids", "seller_ids", "payment_ids"]:
        if key in entities and key in LIMITS:
            if len(entities[key]) > LIMITS[key]:
                errors.append(f"affected_entities.{key} exceeds limit {LIMITS[key]}")

    # Check in customer_context & product_context
    cust_ctx = output.get("customer_context", {})
    if "related_order_ids" in cust_ctx and len(cust_ctx["related_order_ids"]) > LIMITS.get("related_order_ids", 5):
        errors.append(f"customer_context.related_order_ids exceeds limit {LIMITS['related_order_ids']}")

    prod_ctx = output.get("product_context", {})
    if "product_ids" in prod_ctx and len(prod_ctx["product_ids"]) > LIMITS.get("product_ids", 5):
        errors.append(f"product_context.product_ids exceeds limit {LIMITS['product_ids']}")
    if "category_names" in prod_ctx and len(prod_ctx["category_names"]) > LIMITS.get("category_names", 5):
        errors.append(f"product_context.category_names exceeds limit {LIMITS['category_names']}")

    # Check in root_cause_analysis
    rca = output.get("root_cause_analysis", {})
    if "ranked_causes" in rca and len(rca["ranked_causes"]) > LIMITS.get("ranked_causes", 3):
        errors.append(f"root_cause_analysis.ranked_causes exceeds limit {LIMITS['ranked_causes']}")
    if "responsible_parties" in rca and len(rca["responsible_parties"]) > LIMITS.get("responsible_parties", 3):
        errors.append(f"root_cause_analysis.responsible_parties exceeds limit {LIMITS['responsible_parties']}")

    # Check top-level lists
    if "evidence_ids" in output and len(output["evidence_ids"]) > LIMITS.get("evidence_ids", 20):
        errors.append(f"evidence_ids exceeds limit {LIMITS['evidence_ids']}")
    if "resolution_actions" in output and len(output["resolution_actions"]) > LIMITS.get("resolution_actions", 5):
        errors.append(f"resolution_actions exceeds limit {LIMITS['resolution_actions']}")

    return errors


def validate_confidence(confidence: float) -> bool:
    """Check confidence is in [0, 1]."""
    return isinstance(confidence, (int, float)) and 0 <= confidence <= 1


def validate_case_status(status: str) -> bool:
    """Check case_status is valid."""
    return status in VALID_CASE_STATUSES


def validate_full_output(output: dict) -> tuple[bool, list[str]]:
    """Validate full output dictionary against all business and schema rules."""
    errors = []

    # 1. Primary & Secondary issue validation
    assessment = output.get("case_assessment", {})
    primary = assessment.get("primary_issue")
    if primary not in VALID_PRIMARY_ISSUES:
        errors.append(f"Invalid primary_issue: {primary}")

    secondaries = assessment.get("secondary_issues", [])
    for sec in secondaries:
        if sec not in VALID_SECONDARY_ISSUES:
            errors.append(f"Invalid secondary_issue: {sec}")

    # 2. Case status validation
    status = assessment.get("case_status")
    if not validate_case_status(status):
        errors.append(f"Invalid case_status: {status}")

    # 3. Confidence score validation
    conf = assessment.get("confidence", -1)
    if not validate_confidence(conf):
        errors.append(f"Invalid confidence score: {conf}")

    # 4. Evidence IDs validation
    evidence_ids = output.get("evidence_ids", [])
    for ev_id in evidence_ids:
        if not validate_evidence_id(ev_id):
            errors.append(f"Invalid evidence_id format: {ev_id}")

    # 5. Array limits validation
    errors.extend(validate_array_limits(output))

    return len(errors) == 0, errors