"""Evidence ID builder.

Owner: Member C
"""

from typing import Any, Union
from src.config import LIMITS


def build_order_evidence(order_id: str) -> str:
    return f"order:{order_id}"


def build_item_evidence(order_id: str, order_item_id: Union[int, str]) -> str:
    return f"item:{order_id}:{order_item_id}" if not str(order_item_id).startswith(f"{order_id}:") else f"item:{order_item_id}"


def build_payment_evidence(order_id: str, payment_sequential: Union[int, str]) -> str:
    return f"payment:{order_id}:{payment_sequential}" if not str(payment_sequential).startswith(f"{order_id}:") else f"payment:{payment_sequential}"


def build_seller_evidence(seller_id: str) -> str:
    return f"seller:{seller_id}"


def build_policy_evidence(root_cause_code: str) -> str:
    return f"policy:{root_cause_code}"


def collect_evidence(
    order_id: str,
    item_ids: list[Union[int, str]],
    payment_sequentials: list[Union[int, str]],
    seller_ids: list[str],
    root_cause_codes: list[str],
) -> list[str]:
    """Collect all evidence IDs for a case, respecting limits."""
    evidence = [build_order_evidence(order_id)]

    for item_id in item_ids:
        evidence.append(build_item_evidence(order_id, item_id))

    for seq in payment_sequentials:
        evidence.append(build_payment_evidence(order_id, seq))

    for seller_id in seller_ids:
        evidence.append(build_seller_evidence(seller_id))

    for code in root_cause_codes:
        evidence.append(build_policy_evidence(code))

    return evidence[:LIMITS.get("evidence_ids", 20)]