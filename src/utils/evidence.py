"""Evidence ID builder.

Builds evidence IDs from data in the exact format required:
- order:<order_id>
- item:<order_id>:<order_item_id>
- payment:<order_id>:<payment_sequential>
- seller:<seller_id>
- policy:<root_cause_code>

Owner: Member C
"""

from typing import Optional
from src.config import LIMITS


def build_order_evidence(order_id: str) -> str:
    """Build evidence ID for an order."""
    return f"order:{order_id}"


def build_item_evidence(order_id: str, order_item_id: int) -> str:
    """Build evidence ID for an order item."""
    return f"item:{order_id}:{order_item_id}"


def build_payment_evidence(order_id: str, payment_sequential: int) -> str:
    """Build evidence ID for a payment."""
    return f"payment:{order_id}:{payment_sequential}"


def build_seller_evidence(seller_id: str) -> str:
    """Build evidence ID for a seller."""
    return f"seller:{seller_id}"


def build_policy_evidence(root_cause_code: str) -> str:
    """Build evidence ID for a policy rule."""
    return f"policy:{root_cause_code}"


def collect_evidence(
    order_id: str,
    item_ids: list[int],
    payment_sequentials: list[int],
    seller_ids: list[str],
    root_cause_codes: list[str],
) -> list[str]:
    """Collect all evidence IDs for a case, respecting limits."""
    evidence = []

    # Order evidence
    evidence.append(build_order_evidence(order_id))

    # Item evidence
    for item_id in item_ids:
        evidence.append(build_item_evidence(order_id, item_id))

    # Payment evidence
    for seq in payment_sequentials:
        evidence.append(build_payment_evidence(order_id, seq))

    # Seller evidence
    for seller_id in seller_ids:
        evidence.append(build_seller_evidence(seller_id))

    # Policy evidence
    for code in root_cause_codes:
        evidence.append(build_policy_evidence(code))

    # Enforce limit
    return evidence[:LIMITS["evidence_ids"]]
