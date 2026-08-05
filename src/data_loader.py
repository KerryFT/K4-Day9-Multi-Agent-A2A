"""Data loader for Olist CSV datasets.

Loads and caches all 9 CSV files. Provides lookup methods
for querying by order_id, customer_id, etc.

Owner: Member A
"""

import pandas as pd
from pathlib import Path
from typing import Optional

from src.config import DATA_DIR


class DataLoader:
    """Singleton-like data loader that caches all CSV DataFrames."""

    _instance: Optional["DataLoader"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self) -> "DataLoader":
        """Load all CSV files into memory."""
        if self._loaded:
            return self

        self.orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
        self.order_items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
        self.order_payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
        self.order_reviews = pd.read_csv(DATA_DIR / "olist_order_reviews_dataset.csv")
        self.customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
        self.products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
        self.sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
        self.geolocation = pd.read_csv(DATA_DIR / "olist_geolocation_dataset.csv")
        self.category_translation = pd.read_csv(
            DATA_DIR / "product_category_name_translation.csv"
        )

        self._loaded = True
        return self

    def get_order(self, order_id: str) -> Optional[pd.Series]:
        """Get order row by order_id."""
        rows = self.orders[self.orders["order_id"] == order_id]
        return rows.iloc[0] if len(rows) > 0 else None

    def get_order_items(self, order_id: str) -> pd.DataFrame:
        """Get all item rows for an order."""
        return self.order_items[self.order_items["order_id"] == order_id]

    def get_order_payments(self, order_id: str) -> pd.DataFrame:
        """Get all payment rows for an order."""
        return self.order_payments[self.order_payments["order_id"] == order_id]

    def get_customer(self, customer_id: str) -> Optional[pd.Series]:
        """Get customer row by customer_id."""
        rows = self.customers[self.customers["customer_id"] == customer_id]
        return rows.iloc[0] if len(rows) > 0 else None

    def get_customer_orders(self, customer_unique_id: str) -> pd.DataFrame:
        """Get all orders for a customer_unique_id."""
        customer_ids = self.customers[
            self.customers["customer_unique_id"] == customer_unique_id
        ]["customer_id"].tolist()
        return self.orders[self.orders["customer_id"].isin(customer_ids)]

    def get_product(self, product_id: str) -> Optional[pd.Series]:
        """Get product row by product_id."""
        rows = self.products[self.products["product_id"] == product_id]
        return rows.iloc[0] if len(rows) > 0 else None

    def get_seller(self, seller_id: str) -> Optional[pd.Series]:
        """Get seller row by seller_id."""
        rows = self.sellers[self.sellers["seller_id"] == seller_id]
        return rows.iloc[0] if len(rows) > 0 else None

    def get_category_translation(self, category_name: str) -> Optional[str]:
        """Get English translation for a category name."""
        rows = self.category_translation[
            self.category_translation["product_category_name"] == category_name
        ]
        if len(rows) > 0:
            return rows.iloc[0]["product_category_name_english"]
        return category_name  # Return original if no translation
