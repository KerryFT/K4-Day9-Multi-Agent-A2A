"""Order & Product Agent — retrieves order details, items, sellers, products.

Joins order_items with products and sellers to build
affected_entities and product_context.

Owner: Member B
"""

from typing import Any

import pandas as pd

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
        items_df = self.data.get_order_items(order_id)

        item_ids: list[str] = []
        seller_ids: list[str] = []
        product_ids: list[str] = []
        category_names: list[str] = []

        if not items_df.empty:
            # 1. Build item_ids: "order_id:order_item_id"
            for _, row in items_df.iterrows():
                item_id_str = f"{order_id}:{row['order_item_id']}"
                if item_id_str not in item_ids:
                    item_ids.append(item_id_str)

            # 2. Unique seller_ids
            for s_id in items_df["seller_id"].dropna().unique():
                s_id_str = str(s_id)
                if s_id_str not in seller_ids:
                    seller_ids.append(s_id_str)

            # 3. Unique product_ids & category_names
            for p_id in items_df["product_id"].dropna().unique():
                p_id_str = str(p_id)
                if p_id_str not in product_ids:
                    product_ids.append(p_id_str)

                prod_row = self.data.get_product(p_id_str)
                if prod_row is not None:
                    cat_pt = prod_row.get("product_category_name")
                    if pd.notna(cat_pt) and str(cat_pt).strip():
                        cat_en = self.data.get_category_translation(str(cat_pt))
                        if cat_en and cat_en not in category_names:
                            category_names.append(cat_en)

        # Apply limits
        order_ids = [order_id][:LIMITS.get("order_ids", 5)]
        item_ids = item_ids[:LIMITS.get("item_ids", 5)]
        seller_ids = seller_ids[:LIMITS.get("seller_ids", 3)]
        product_ids = product_ids[:LIMITS.get("product_ids", 5)]
        category_names = category_names[:LIMITS.get("category_names", 5)]

        return {
            "affected_entities": {
                "order_ids": order_ids,
                "item_ids": item_ids,
                "seller_ids": seller_ids,
                "payment_ids": [],
            },
            "product_context": {
                "product_ids": product_ids,
                "category_names": category_names,
            },
        }
