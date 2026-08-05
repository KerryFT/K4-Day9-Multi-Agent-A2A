"""Verifier Agent — validates output against schema and business rules.

Checks evidence IDs, array limits, null handling, and data consistency.

Owner: Member C
"""

import copy
import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import LIMITS
from src.models import CaseOutput
from src.utils.validators import validate_full_output


class VerifierAgent(BaseAgent):
    """Agent responsible for output validation and correction."""

    agent_name = "verifier"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Validate the draft output and correct if needed."""
        draft = kwargs.get("draft_output", {})
        if not draft:
            return {"valid": False, "errors": ["Empty draft_output provided"], "corrected_output": None}

        errors = []
        corrected = copy.deepcopy(draft)

        # 1. Check required top-level keys
        required_keys = [
            "case_id", "case_assessment", "affected_entities", "customer_context",
            "product_context", "delivery_analysis", "payment_reconciliation",
            "root_cause_analysis", "evidence_ids", "financial_resolution", "resolution_actions"
        ]
        for key in required_keys:
            if key not in corrected:
                errors.append(f"Missing required key: {key}")

        # 2. Validate evidence_id format
        evidence_pattern = re.compile(r"^(order|item|payment|seller|policy):.+$")
        evidences = corrected.get("evidence_ids", [])
        for ev in evidences:
            if not evidence_pattern.match(ev):
                errors.append(f"Invalid evidence_id format: {ev}")

        # 3. Enforce array limits from LIMITS
        if "affected_entities" in corrected:
            ae = corrected["affected_entities"]
            ae["order_ids"] = ae.get("order_ids", [])[:LIMITS.get("order_ids", 5)]
            ae["item_ids"] = ae.get("item_ids", [])[:LIMITS.get("item_ids", 5)]
            ae["seller_ids"] = ae.get("seller_ids", [])[:LIMITS.get("seller_ids", 3)]
            ae["payment_ids"] = ae.get("payment_ids", [])[:LIMITS.get("payment_ids", 5)]

        if "customer_context" in corrected:
            cc = corrected["customer_context"]
            cc["related_order_ids"] = cc.get("related_order_ids", [])[:LIMITS.get("related_order_ids", 5)]

        if "product_context" in corrected:
            pc = corrected["product_context"]
            pc["product_ids"] = pc.get("product_ids", [])[:LIMITS.get("product_ids", 5)]
            pc["category_names"] = pc.get("category_names", [])[:LIMITS.get("category_names", 5)]

        if "root_cause_analysis" in corrected:
            rca = corrected["root_cause_analysis"]
            rca["ranked_causes"] = rca.get("ranked_causes", [])[:LIMITS.get("ranked_causes", 3)]
            rca["responsible_parties"] = rca.get("responsible_parties", [])[:LIMITS.get("responsible_parties", 3)]

        corrected["evidence_ids"] = corrected.get("evidence_ids", [])[:LIMITS.get("evidence_ids", 20)]
        corrected["resolution_actions"] = corrected.get("resolution_actions", [])[:LIMITS.get("resolution_actions", 5)]

        # 4. Check confidence in [0.0, 1.0]
        if "case_assessment" in corrected:
            conf = corrected["case_assessment"].get("confidence", 0.0)
            if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                errors.append(f"Invalid confidence score: {conf}")
                corrected["case_assessment"]["confidence"] = max(0.0, min(1.0, float(conf)))

        # 5. Check case_status validity
        if "case_assessment" in corrected:
            status = corrected["case_assessment"].get("case_status")
            if status not in ["action_required", "no_action"]:
                errors.append(f"Invalid case_status: {status}")

        # 6. Validate timestamp format (basic check)
        if "delivery_analysis" in corrected:
            ts_keys = ["delivered_at", "estimated_delivery_at", "carrier_handoff_at"]
            ts_pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
            for ts_k in ts_keys:
                val = corrected["delivery_analysis"].get(ts_k)
                if val is not None and not ts_pattern.match(str(val)):
                    errors.append(f"Invalid timestamp format in delivery_analysis.{ts_k}: {val}")

        # 7. Check numeric rounding (2 decimal places for floats)
        if "financial_resolution" in corrected:
            refund = corrected["financial_resolution"].get("recommended_refund_brl")
            if isinstance(refund, (int, float)):
                corrected["financial_resolution"]["recommended_refund_brl"] = round(float(refund), 2)

        # 8. Validate evidence against the actual source rows, not regex alone.
        item_rows = self.data.get_order_items(order_id)
        payment_rows = self.data.get_order_payments(order_id)
        item_sequences = (
            item_rows["order_item_id"].tolist()
            if "order_item_id" in item_rows.columns else []
        )
        payment_sequences = (
            payment_rows["payment_sequential"].tolist()
            if "payment_sequential" in payment_rows.columns else []
        )
        valid_item_ids = {
            f"item:{order_id}:{value}" for value in item_sequences
        }
        valid_payment_ids = {
            f"payment:{order_id}:{value}" for value in payment_sequences
        }
        for evidence in corrected.get("evidence_ids", []):
            if evidence.startswith("order:") and evidence != f"order:{order_id}":
                errors.append(f"Order evidence does not match claimed order: {evidence}")
            elif evidence.startswith("item:") and evidence not in valid_item_ids:
                errors.append(f"Item evidence does not exist in CSV: {evidence}")
            elif evidence.startswith("payment:") and evidence not in valid_payment_ids:
                errors.append(f"Payment evidence does not exist in CSV: {evidence}")
            elif evidence.startswith("seller:"):
                seller_id = evidence.removeprefix("seller:")
                if self.data.get_seller(seller_id) is None:
                    errors.append(f"Seller evidence does not exist in CSV: {evidence}")

        # 9. Run the shared business validator and the exact Pydantic schema.
        _, shared_errors = validate_full_output(corrected)
        errors.extend(error for error in shared_errors if error not in errors)
        try:
            CaseOutput.model_validate(corrected)
        except Exception as exc:
            errors.append(f"Pydantic schema validation failed: {exc}")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "corrected_output": corrected if not is_valid else None,
        }
