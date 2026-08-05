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
            - customer_unique_id: str
            - related_order_ids: list[str]
        """
        # TODO: Member B implements this
        # 1. Get order -> customer_id
        # 2. Get customer -> customer_unique_id
        # 3. Find all orders with same customer_unique_id
        # 4. Exclude claimed_order_id from related_order_ids
        # 5. Respect LIMITS["related_order_ids"]
        return {
            "customer_context": {
                "customer_unique_id": None,
                "related_order_ids": [],
            }
        }
