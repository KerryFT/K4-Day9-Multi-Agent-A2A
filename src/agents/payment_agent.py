"""Payment Agent — reconciles payment data with order totals.

Compares sum of payment_value against sum of item prices + freight.

Owner: Member C
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import PAYMENT_TOLERANCE_BRL, DECIMAL_PLACES, LIMITS


class PaymentAgent(BaseAgent):
    """Agent responsible for payment reconciliation."""

    agent_name = "payment"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Reconcile payments against order items + freight.

        Returns:
            dict with 'payment_reconciliation' key containing:
            - item_total_brl, freight_total_brl, expected_total_brl
            - payment_total_brl, difference_brl, reconciled
            - payment_types
        """
        # TODO: Member C implements this
        # 1. Get order_payments -> sum payment_value
        # 2. Get order_items -> sum price, sum freight_value
        # 3. expected_total = sum(price) + sum(freight)
        # 4. difference = payment_total - expected_total
        # 5. reconciled = abs(difference) <= PAYMENT_TOLERANCE_BRL
        # 6. Handle null case: no items -> all nulls
        # 7. Round to DECIMAL_PLACES
        return {
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": None,
                "freight_total_brl": None,
                "expected_total_brl": None,
                "payment_total_brl": None,
                "difference_brl": None,
                "reconciled": None,
                "payment_types": [],
            }
        }
