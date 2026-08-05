"""Policy Agent — applies EC_POLICY_V2 business rules.

Determines primary_issue, secondary_issues, root cause,
responsible parties, refund amount, and resolution actions.

Owner: Member C
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import DECIMAL_PLACES, LIMITS
from src.utils.evidence import collect_evidence


class PolicyAgent(BaseAgent):
    """Agent responsible for policy evaluation and case resolution."""

    agent_name = "policy"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Apply EC_POLICY_V2 rules based on all collected context."""
        customer_ctx = kwargs.get("customer", {}).get("customer_context", {}) if isinstance(kwargs.get("customer"), dict) else {}
        order_prod_ctx = kwargs.get("order_product", {}) if isinstance(kwargs.get("order_product"), dict) else {}
        payment_ctx = kwargs.get("payment", {}).get("payment_reconciliation", {}) if isinstance(kwargs.get("payment"), dict) else {}
        delivery_ctx = kwargs.get("delivery", {}).get("delivery_analysis", {}) if isinstance(kwargs.get("delivery"), dict) else {}

        order_status = kwargs.get("order_status") or order_prod_ctx.get("order_status", "")
        pmt_total = payment_ctx.get("payment_total_brl") or 0.0
        freight_total = payment_ctx.get("freight_total_brl") or 0.0
        del_var = delivery_ctx.get("delivery_variance_hours")
        late_sellers = delivery_ctx.get("late_handoff_seller_ids", [])
        reconciled = payment_ctx.get("reconciled")

        raw_pmts_count = kwargs.get("raw_pmts_count", len(kwargs.get("affected_entities", {}).get("payment_ids", [])))
        raw_items_count = kwargs.get("raw_items_count", len(kwargs.get("affected_entities", {}).get("item_ids", [])))
        raw_sellers_count = kwargs.get("raw_sellers_count", len(kwargs.get("affected_entities", {}).get("seller_ids", [])))
        related_orders = customer_ctx.get("related_order_ids", [])
        categories = order_prod_ctx.get("product_context", {}).get("category_names", [])

        primary_issue = ""
        responsible_parties = []
        recommended_refund = 0.0
        action_main = ""
        root_cause = ""

        # Priority 1: canceled_order_paid
        if order_status == "canceled" and pmt_total > 0:
            primary_issue = "canceled_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund = pmt_total
            action_main = "issue_full_refund"
            root_cause = "ORDER_CANCELED_AFTER_PAYMENT"

        # Priority 2: unavailable_order_paid
        elif order_status == "unavailable" and pmt_total > 0:
            primary_issue = "unavailable_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund = pmt_total
            action_main = "issue_full_refund"
            root_cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"

        # Priority 3: late_delivery_seller
        elif del_var is not None and del_var > 0 and len(late_sellers) > 0:
            primary_issue = "late_delivery_seller"
            responsible_parties = [{"party_type": "seller", "party_id": s_id} for s_id in late_sellers[:LIMITS.get("responsible_parties", 3)]]
            recommended_refund = freight_total
            action_main = "refund_freight"
            root_cause = "SELLER_HANDOFF_AFTER_LIMIT"

        # Priority 4: late_delivery_logistics
        elif del_var is not None and del_var > 0 and len(late_sellers) == 0:
            primary_issue = "late_delivery_logistics"
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund = freight_total
            action_main = "refund_freight"
            root_cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"

        # Priority 5: valid_split_payment
        elif raw_pmts_count >= 2 and reconciled is True:
            primary_issue = "valid_split_payment"
            responsible_parties = []
            recommended_refund = 0.0
            action_main = "explain_valid_split_payment"
            root_cause = "MULTIPLE_PAYMENTS_RECONCILED"

        # Priority 6: unsupported_late_claim
        else:
            primary_issue = "unsupported_late_claim"
            responsible_parties = []
            recommended_refund = 0.0
            action_main = "reject_late_refund"
            root_cause = "DELIVERY_WITHIN_ESTIMATE"

        # Secondary issues in strict order:
        secondary_issues = []
        if raw_items_count >= 2:
            secondary_issues.append("multi_item_order")
        if raw_sellers_count >= 2:
            secondary_issues.append("multi_seller_order")
        if raw_pmts_count >= 2:
            secondary_issues.append("split_payment")
        if len(related_orders) > 0:
            secondary_issues.append("repeat_customer")
        if len(categories) >= 2:
            secondary_issues.append("multiple_categories")

        # Additional actions sequence:
        actions = [action_main]
        if root_cause == "SELLER_HANDOFF_AFTER_LIMIT":
            actions.append("review_seller_handoff")
        elif root_cause == "CARRIER_DELIVERED_AFTER_ESTIMATE":
            actions.append("review_carrier_delay")

        if recommended_refund > 0:
            actions.append("verify_refund_completion")
        if raw_sellers_count >= 2:
            actions.append("coordinate_multi_seller_case")
        if raw_pmts_count >= 2 and primary_issue != "valid_split_payment":
            actions.append("verify_payment_allocation")

        # Evidence construction
        item_seqs = kwargs.get("item_sequentials", list(range(1, raw_items_count + 1)))
        payment_seqs = kwargs.get("payment_sequentials", list(range(1, raw_pmts_count + 1)))
        seller_ids = [p["party_id"] for p in responsible_parties if p.get("party_type") == "seller"]

        evidence_ids = collect_evidence(
            order_id=order_id,
            item_ids=item_seqs,
            payment_sequentials=payment_seqs,
            seller_ids=seller_ids,
            root_cause_codes=[root_cause] if root_cause else [],
        )

        return {
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": "action_required" if recommended_refund > 0 else "no_action",
                "confidence": 0.95,
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": root_cause, "rank": 1}],
                "responsible_parties": responsible_parties[:LIMITS.get("responsible_parties", 3)],
            },
            "evidence_ids": evidence_ids[:LIMITS.get("evidence_ids", 20)],
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": round(recommended_refund, DECIMAL_PLACES),
            },
            "resolution_actions": actions[:LIMITS.get("resolution_actions", 5)],
        }