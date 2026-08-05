"""Customer Agent — identifies customer and retrieves order history.

Looks up customer_unique_id from the claimed order and finds
all related orders for the same customer.

Owner: Member B
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import LIMITS


class CustomerAgent(BaseAgent):
    """Agent responsible for customer identity and history."""

    agent_name = "customer"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Look up customer info and order history.

        Returns:
            dict with 'customer_context' key containing:
            - customer_unique_id: str | None
            - related_order_ids: list[str]
        """
        order = self.data.get_order(order_id)
        if order is None:
            return {
                "customer_context": {
                    "customer_unique_id": None,
                    "related_order_ids": [],
                }
            }

        customer_id = str(order["customer_id"])
        customer = self.data.get_customer(customer_id)
        if customer is None:
            return {
                "customer_context": {
                    "customer_unique_id": None,
                    "related_order_ids": [],
                }
            }

        customer_unique_id = str(customer["customer_unique_id"])
        cust_orders_df = self.data.get_customer_orders(customer_unique_id)

        related_order_ids: list[str] = []
        if not cust_orders_df.empty:
            all_ids = cust_orders_df["order_id"].tolist()
            seen = set()
            for oid in all_ids:
                oid_str = str(oid)
                if oid_str != order_id and oid_str not in seen:
                    seen.add(oid_str)
                    related_order_ids.append(oid_str)

        limit = LIMITS.get("related_order_ids", 5)
        related_order_ids = related_order_ids[:limit]

        return {
            "customer_context": {
                "customer_unique_id": customer_unique_id,
                "related_order_ids": related_order_ids,
            }
        }
