"""Policy Agent — applies EC_POLICY_V2 business rules.

Determines primary_issue, secondary_issues, root cause,
responsible parties, refund amount, and resolution actions.

Owner: Member C
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import PAYMENT_TOLERANCE_BRL, DECIMAL_PLACES, LIMITS


class PolicyAgent(BaseAgent):
    """Agent responsible for policy evaluation and case resolution."""

    agent_name = "policy"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Apply EC_POLICY_V2 rules based on all collected context.

        Expects kwargs from coordinator containing:
        - customer: customer context
        - order_product: order/product context
        - payment: payment reconciliation
        - delivery: delivery analysis

        Returns:
            dict with:
            - case_assessment: primary_issue, secondary_issues, case_status, confidence
            - root_cause_analysis: ranked_causes, responsible_parties
            - evidence_ids: list of evidence strings
            - financial_resolution: recommended_refund_brl
            - resolution_actions: list of action strings
        """
        # TODO: Member C implements this
        # Priority order for primary_issue:
        # 1. canceled_order_paid
        # 2. unavailable_order_paid
        # 3. late_delivery_seller
        # 4. late_delivery_logistics
        # 5. valid_split_payment
        # 6. unsupported_late_claim
        #
        # Secondary issues (in order):
        # 1. multi_item_order (>=2 items)
        # 2. multi_seller_order (>=2 sellers)
        # 3. split_payment (>=2 payment rows)
        # 4. repeat_customer (has related orders)
        # 5. multiple_categories (>=2 categories)
        #
        # Root cause codes:
        # - SELLER_HANDOFF_AFTER_LIMIT
        # - CARRIER_DELIVERED_AFTER_ESTIMATE
        # - ORDER_CANCELED_AFTER_PAYMENT
        # - ORDER_UNAVAILABLE_AFTER_PAYMENT
        # - MULTIPLE_PAYMENTS_RECONCILED
        # - DELIVERY_WITHIN_ESTIMATE
        return {
            "case_assessment": {
                "primary_issue": "",
                "secondary_issues": [],
                "case_status": "no_action",
                "confidence": 0.0,
            },
            "root_cause_analysis": {
                "ranked_causes": [],
                "responsible_parties": [],
            },
            "evidence_ids": [],
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": 0.0,
            },
            "resolution_actions": [],
        }
