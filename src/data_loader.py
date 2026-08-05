"""
Data loader for Olist Brazilian E-Commerce CSV datasets.

Loads all 9 CSVs once, builds indexed lookups, and exposes query
methods consumed by every agent.  Singleton guarantees a single copy
of the data in memory regardless of how many agents are instantiated.

Owner: Member A
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.config import DATA_DIR, CSV_FILES

logger = logging.getLogger(__name__)


class DataLoader:
    """Singleton data loader with indexed lookups for Olist CSVs."""

    _instance: Optional[DataLoader] = None
    _loaded: bool = False

    # ── Singleton ─────────────────────────────────────────────────

    def __new__(cls) -> DataLoader:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (useful in tests)."""
        cls._instance = None
        cls._loaded = False

    # ── Loading ───────────────────────────────────────────────────

    def load(self) -> DataLoader:
        """Load every CSV and build indexes.  Idempotent."""
        if self._loaded:
            return self

        logger.info("Loading Olist datasets from %s …", DATA_DIR)

        # Raw DataFrames
        self.orders: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["orders"]
        )
        self.order_items: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["order_items"]
        )
        self.order_payments: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["order_payments"]
        )
        self.order_reviews: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["order_reviews"]
        )
        self.customers: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["customers"]
        )
        self.products: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["products"]
        )
        self.sellers: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["sellers"]
        )
        self.geolocation: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["geolocation"]
        )
        self.category_translation: pd.DataFrame = pd.read_csv(
            DATA_DIR / CSV_FILES["category_translation"]
        )

        # Indexed views for O(1) lookups
        self._order_idx: pd.DataFrame = self.orders.set_index("order_id")
        self._items_grp = self.order_items.groupby("order_id")
        self._payments_grp = self.order_payments.groupby("order_id")
        self._customer_idx: pd.DataFrame = self.customers.set_index("customer_id")
        self._customer_unique_grp = self.customers.groupby("customer_unique_id")
        self._product_idx: pd.DataFrame = self.products.set_index("product_id")
        self._seller_idx: pd.DataFrame = self.sellers.set_index("seller_id")
        self._cat_trans_idx: pd.DataFrame = self.category_translation.set_index(
            "product_category_name"
        )

        sizes = {k: len(getattr(self, k)) for k in
                 ("orders", "order_items", "order_payments", "customers",
                  "products", "sellers")}
        logger.info("Datasets loaded — row counts: %s", sizes)

        self._loaded = True
        return self

    # ── Order ─────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Optional[pd.Series]:
        """Single order row by ``order_id``, or ``None``."""
        try:
            row = self._order_idx.loc[order_id]
            # If duplicate order_ids exist the index returns a DF; take first.
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
        except KeyError:
            return None

    def get_order_status(self, order_id: str) -> Optional[str]:
        """Shortcut for ``order_status``."""
        order = self.get_order(order_id)
        return str(order["order_status"]) if order is not None else None

    # ── Order Items ───────────────────────────────────────────────

    def get_order_items(self, order_id: str) -> pd.DataFrame:
        """All item rows for *order_id*.  Empty DF when none exist."""
        try:
            return self._items_grp.get_group(order_id).reset_index(drop=True)
        except KeyError:
            return pd.DataFrame()

    # ── Payments ──────────────────────────────────────────────────

    def get_order_payments(self, order_id: str) -> pd.DataFrame:
        """All payment rows for *order_id*.  Empty DF when none exist."""
        try:
            return self._payments_grp.get_group(order_id).reset_index(drop=True)
        except KeyError:
            return pd.DataFrame()

    # ── Customer ──────────────────────────────────────────────────

    def get_customer(self, customer_id: str) -> Optional[pd.Series]:
        """Customer row by ``customer_id``."""
        try:
            row = self._customer_idx.loc[customer_id]
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
        except KeyError:
            return None

    def get_customer_orders(self, customer_unique_id: str) -> pd.DataFrame:
        """All orders placed by the *same person* (via ``customer_unique_id``)."""
        try:
            cust_rows = self._customer_unique_grp.get_group(customer_unique_id)
            cids = cust_rows["customer_id"].tolist()
            return self.orders[self.orders["customer_id"].isin(cids)]
        except KeyError:
            return pd.DataFrame()

    # ── Product ───────────────────────────────────────────────────

    def get_product(self, product_id: str) -> Optional[pd.Series]:
        """Product row by ``product_id``."""
        try:
            row = self._product_idx.loc[product_id]
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
        except KeyError:
            return None

    def get_category_translation(self, category_name: str) -> str:
        """Portuguese → English category name.  Returns original if unknown."""
        if pd.isna(category_name):
            return ""
        try:
            return str(
                self._cat_trans_idx.loc[category_name, "product_category_name_english"]
            )
        except KeyError:
            return str(category_name)

    # ── Seller ────────────────────────────────────────────────────

    def get_seller(self, seller_id: str) -> Optional[pd.Series]:
        """Seller row by ``seller_id``."""
        try:
            row = self._seller_idx.loc[seller_id]
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
        except KeyError:
            return None
