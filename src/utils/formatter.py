"""Output formatter — converts internal dicts to submission JSON.

Owner: Member C
"""

import json
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR, LIMITS


def format_output(case_output: dict) -> dict:
    """Ensure output dict matches the exact submission schema."""
    formatted = {
        "case_id": case_output.get("case_id", ""),
        "case_assessment": {
            "primary_issue": case_output.get("case_assessment", {}).get("primary_issue", ""),
            "secondary_issues": case_output.get("case_assessment", {}).get("secondary_issues", []),
            "case_status": case_output.get("case_assessment", {}).get("case_status", "no_action"),
            "confidence": float(case_output.get("case_assessment", {}).get("confidence", 0.95)),
        },
        "affected_entities": {
            "order_ids": case_output.get("affected_entities", {}).get("order_ids", [])[:LIMITS.get("order_ids", 5)],
            "item_ids": case_output.get("affected_entities", {}).get("item_ids", [])[:LIMITS.get("item_ids", 5)],
            "seller_ids": case_output.get("affected_entities", {}).get("seller_ids", [])[:LIMITS.get("seller_ids", 3)],
            "payment_ids": case_output.get("affected_entities", {}).get("payment_ids", [])[:LIMITS.get("payment_ids", 5)],
        },
        "customer_context": {
            "customer_unique_id": case_output.get("customer_context", {}).get("customer_unique_id", ""),
            "related_order_ids": case_output.get("customer_context", {}).get("related_order_ids", [])[:LIMITS.get("related_order_ids", 5)],
        },
        "product_context": {
            "product_ids": case_output.get("product_context", {}).get("product_ids", [])[:LIMITS.get("product_ids", 5)],
            "category_names": case_output.get("product_context", {}).get("category_names", [])[:LIMITS.get("category_names", 5)],
        },
        "delivery_analysis": {
            "delivered_at": case_output.get("delivery_analysis", {}).get("delivered_at"),
            "estimated_delivery_at": case_output.get("delivery_analysis", {}).get("estimated_delivery_at"),
            "carrier_handoff_at": case_output.get("delivery_analysis", {}).get("carrier_handoff_at"),
            "delivery_variance_hours": case_output.get("delivery_analysis", {}).get("delivery_variance_hours"),
            "seller_handoff_analysis": case_output.get("delivery_analysis", {}).get("seller_handoff_analysis", []),
            "late_handoff_seller_ids": case_output.get("delivery_analysis", {}).get("late_handoff_seller_ids", []),
        },
        "payment_reconciliation": {
            "currency": case_output.get("payment_reconciliation", {}).get("currency", "BRL"),
            "item_total_brl": case_output.get("payment_reconciliation", {}).get("item_total_brl"),
            "freight_total_brl": case_output.get("payment_reconciliation", {}).get("freight_total_brl"),
            "expected_total_brl": case_output.get("payment_reconciliation", {}).get("expected_total_brl"),
            "payment_total_brl": case_output.get("payment_reconciliation", {}).get("payment_total_brl"),
            "difference_brl": case_output.get("payment_reconciliation", {}).get("difference_brl"),
            "reconciled": case_output.get("payment_reconciliation", {}).get("reconciled"),
            "payment_types": case_output.get("payment_reconciliation", {}).get("payment_types", []),
        },
        "root_cause_analysis": {
            "ranked_causes": case_output.get("root_cause_analysis", {}).get("ranked_causes", [])[:LIMITS.get("ranked_causes", 3)],
            "responsible_parties": case_output.get("root_cause_analysis", {}).get("responsible_parties", [])[:LIMITS.get("responsible_parties", 3)],
        },
        "evidence_ids": case_output.get("evidence_ids", [])[:LIMITS.get("evidence_ids", 20)],
        "financial_resolution": {
            "currency": case_output.get("financial_resolution", {}).get("currency", "BRL"),
            "recommended_refund_brl": round(float(case_output.get("financial_resolution", {}).get("recommended_refund_brl", 0.0)), 2),
        },
        "resolution_actions": case_output.get("resolution_actions", [])[:LIMITS.get("resolution_actions", 5)],
    }
    return formatted


def save_output(case_id: str, case_output: dict) -> Path:
    """Save a case output to the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    formatted = format_output(case_output)
    output_path = OUTPUT_DIR / f"{case_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=2, ensure_ascii=False)
    return output_path


def save_all_outputs(outputs: dict[str, dict]) -> list[Path]:
    """Save all case outputs."""
    paths = []
    for case_id, output in sorted(outputs.items()):
        paths.append(save_output(case_id, output))
    return paths