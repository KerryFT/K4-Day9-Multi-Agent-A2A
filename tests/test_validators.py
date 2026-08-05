"""Tests for validators.

Owner: Member B
"""

import pytest
from src.utils.validators import (
    validate_evidence_id,
    validate_confidence,
    validate_case_status,
)


class TestValidators:
    """Test suite for validators."""

    def test_valid_order_evidence(self):
        assert validate_evidence_id("order:abc123") is True

    def test_valid_item_evidence(self):
        assert validate_evidence_id("item:abc123:1") is True

    def test_valid_payment_evidence(self):
        assert validate_evidence_id("payment:abc123:1") is True

    def test_valid_seller_evidence(self):
        assert validate_evidence_id("seller:seller123") is True

    def test_valid_policy_evidence(self):
        assert validate_evidence_id("policy:SELLER_HANDOFF_AFTER_LIMIT") is True

    def test_invalid_evidence(self):
        assert validate_evidence_id("invalid:format") is False
        assert validate_evidence_id("random_string") is False

    def test_valid_confidence(self):
        assert validate_confidence(0.0) is True
        assert validate_confidence(0.5) is True
        assert validate_confidence(1.0) is True

    def test_invalid_confidence(self):
        assert validate_confidence(-0.1) is False
        assert validate_confidence(1.1) is False

    def test_valid_case_status(self):
        assert validate_case_status("action_required") is True
        assert validate_case_status("no_action") is True

    def test_invalid_case_status(self):
        assert validate_case_status("invalid") is False
