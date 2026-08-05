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
        # 1. Get payment and item records via data_loader/kwargs or internal data reference
        order_payments = kwargs.get("order_payments")
        order_items = kwargs.get("order_items")

        if order_payments is None and hasattr(self, "data") and self.data is not None:
            order_payments = self.data.get_order_payments(order_id)
        if order_items is None and hasattr(self, "data") and self.data is not None:
            order_items = self.data.get_order_items(order_id)

        # Payment rows handling
        pmts = order_payments if order_payments is not None else []
        payment_types = list(set([p["payment_type"] for p in pmts if "payment_type" in p])) if pmts else []
        payment_total = sum(float(p.get("payment_value", 0.0)) for p in pmts) if pmts else 0.0
        payment_total_brl = round(payment_total, DECIMAL_PLACES)

        # 2. Get order_items -> sum price, sum freight_value
        items = order_items if order_items is not None else []
        
        # 6. Handle null case: no items -> all nulls
        if not items:
            return {
                "payment_reconciliation": {
                    "currency": "BRL",
                    "item_total_brl": None,
                    "freight_total_brl": None,
                    "expected_total_brl": None,
                    "payment_total_brl": payment_total_brl,
                    "difference_brl": None,
                    "reconciled": None,
                    "payment_types": payment_types,
                }
            }

        item_total = sum(float(it.get("price", 0.0)) for it in items)
        freight_total = sum(float(it.get("freight_value", 0.0)) for it in items)

        # 3. Calculate expected_total
        expected_total = item_total + freight_total

        # 4. Calculate difference
        difference = payment_total - expected_total

        # 5. Check reconciliation
        reconciled = abs(difference) <= PAYMENT_TOLERANCE_BRL

        # 7. Round to DECIMAL_PLACES
        return {
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": round(item_total, DECIMAL_PLACES),
                "freight_total_brl": round(freight_total, DECIMAL_PLACES),
                "expected_total_brl": round(expected_total, DECIMAL_PLACES),
                "payment_total_brl": payment_total_brl,
                "difference_brl": round(difference, DECIMAL_PLACES),
                "reconciled": reconciled,
                "payment_types": payment_types,
            }
        }