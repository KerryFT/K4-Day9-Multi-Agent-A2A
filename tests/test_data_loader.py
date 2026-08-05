"""Tests for DataLoader.

Owner: Member B
"""

import pytest
from src.data_loader import DataLoader


class TestDataLoader:
    """Test suite for DataLoader."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load data once for all tests."""
        self.loader = DataLoader().load()

    def test_orders_loaded(self):
        """Check orders DataFrame is loaded and non-empty."""
        assert len(self.loader.orders) > 0
        assert "order_id" in self.loader.orders.columns

    def test_get_order_returns_series(self):
        """Check get_order returns a pandas Series."""
        first_order_id = self.loader.orders.iloc[0]["order_id"]
        order = self.loader.get_order(first_order_id)
        assert order is not None
        assert order["order_id"] == first_order_id

    def test_get_order_not_found(self):
        """Check get_order returns None for invalid ID."""
        assert self.loader.get_order("nonexistent_id") is None

    def test_get_order_items(self):
        """Check get_order_items returns DataFrame."""
        first_order_id = self.loader.order_items.iloc[0]["order_id"]
        items = self.loader.get_order_items(first_order_id)
        assert len(items) > 0

    def test_get_order_payments(self):
        """Check get_order_payments returns DataFrame."""
        first_order_id = self.loader.order_payments.iloc[0]["order_id"]
        payments = self.loader.get_order_payments(first_order_id)
        assert len(payments) > 0
