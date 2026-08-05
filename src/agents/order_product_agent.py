"""Order & Product Agent — retrieves order details, items, sellers, products.

Joins order_items with products and sellers to build
affected_entities and product_context.

Owner: Member B
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import LIMITS


class OrderProductAgent(BaseAgent):
    """Agent responsible for order, item, seller, and product data."""

    agent_name = "order_product"

    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Retrieve order items, sellers, products and categories.

        Returns:
            dict with:
            - 'affected_entities': order_ids, item_ids, seller_ids, payment_ids
            - 'product_context': product_ids, category_names
        """
        # TODO: Member B implements this
        # 1. Get order_items for order_id
        # 2. Extract unique seller_ids, product_ids
        # 3. Look up product categories
        # 4. Build item_ids as "order_id:order_item_id"
        # 5. Respect all LIMITS
        return {
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": [],
                "seller_ids": [],
                "payment_ids": [],
            },
            "product_context": {
                "product_ids": [],
                "category_names": [],
            },
        }
