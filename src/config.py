"""
Centralized configuration for the Multi-Agent Dispute Resolution System.

All model names are HARDCODED here (required by assignment rules — NOT in .env).
API keys are loaded from .env via python-dotenv.

Owner: Member A
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOGGING_DIR = ROOT_DIR / "logging"

# ─── CSV File Mapping ─────────────────────────────────────────────────
CSV_FILES: dict[str, str] = {
    "orders":               "olist_orders_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "order_payments":       "olist_order_payments_dataset.csv",
    "order_reviews":        "olist_order_reviews_dataset.csv",
    "customers":            "olist_customers_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "geolocation":          "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# ─── Model Configuration (HARDCODED — assignment requirement) ─────────
# Constraint: every model ≤ 10 B parameters
AGENT_MODELS: dict[str, str] = {
    "coordinator":   "qwen2.5:7b",           # 7B  local
    "customer":      "llama-3.1-8b-instant",  # 8B  api (Groq)
    "order_product": "qwen2.5:7b",           # 7B  local
    "payment":       "qwen2.5:7b",           # 7B  local
    "delivery":      "qwen2.5:7b",           # 7B  local
    "policy":        "gemma2-9b-it",          # 9B  api (Together)
    "verifier":      "qwen2.5:7b",           # 7B  local
}

# ─── LLM Provider Settings ───────────────────────────────────────────
LLM_PROVIDERS: dict[str, dict[str, str]] = {
    "local": {
        "base_url": "http://localhost:11434/v1",
        "api_key":  "ollama",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key":  os.getenv("GROQ_API_KEY", ""),
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key":  os.getenv("TOGETHER_API_KEY", ""),
    },
}

AGENT_PROVIDERS: dict[str, str] = {
    "coordinator":   "local",
    "customer":      "groq",
    "order_product": "local",
    "payment":       "local",
    "delivery":      "local",
    "policy":        "together",
    "verifier":      "local",
}

# ─── Business Rules — EC_POLICY_V2 ───────────────────────────────────
PAYMENT_TOLERANCE_BRL: float = 0.10
DECIMAL_PLACES: int = 2

# Primary issues — evaluated top-to-bottom; first match wins
PRIMARY_ISSUES: list[str] = [
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
]

# Secondary issues — appended in this order when condition is met
SECONDARY_ISSUES: list[str] = [
    "multi_item_order",      # ≥ 2 item rows
    "multi_seller_order",    # ≥ 2 distinct sellers
    "split_payment",         # ≥ 2 payment rows
    "repeat_customer",       # same customer_unique_id has another order
    "multiple_categories",   # ≥ 2 distinct categories
]

# Root-cause code per primary issue
ROOT_CAUSE_CODES: dict[str, str] = {
    "canceled_order_paid":     "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid":  "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller":    "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment":     "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim":  "DELIVERY_WITHIN_ESTIMATE",
}

# Responsible party: (party_type, party_id)  —  None means no party
# For "late_delivery_seller", party_id is filled dynamically per seller
RESPONSIBLE_PARTIES: dict[str, tuple[str, str] | None] = {
    "canceled_order_paid":     ("platform", "OLIST_PLATFORM"),
    "unavailable_order_paid":  ("platform", "OLIST_PLATFORM"),
    "late_delivery_seller":    ("seller", "__DYNAMIC__"),
    "late_delivery_logistics": ("logistics_provider", "LOGISTICS_PROVIDER"),
    "valid_split_payment":     None,
    "unsupported_late_claim":  None,
}

# Primary action per primary issue
PRIMARY_ACTIONS: dict[str, str] = {
    "canceled_order_paid":     "issue_full_refund",
    "unavailable_order_paid":  "issue_full_refund",
    "late_delivery_seller":    "refund_freight",
    "late_delivery_logistics": "refund_freight",
    "valid_split_payment":     "explain_valid_split_payment",
    "unsupported_late_claim":  "reject_late_refund",
}

# Supplementary actions — appended in this order after primary action
SUPPLEMENTARY_ACTIONS: list[str] = [
    "review_seller_handoff",
    "review_carrier_delay",
    "verify_refund_completion",
    "coordinate_multi_seller_case",
    "verify_payment_allocation",
]

# Issues that require refund → case_status = "action_required"
ACTION_REQUIRED_ISSUES: set[str] = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
}

# ─── Output Limits (README §6) ───────────────────────────────────────
LIMITS: dict[str, int] = {
    "order_ids":           5,
    "item_ids":            5,
    "seller_ids":          3,
    "payment_ids":         5,
    "related_order_ids":   5,
    "product_ids":         5,
    "category_names":      5,
    "ranked_causes":       3,
    "responsible_parties":  3,
    "evidence_ids":        20,
    "resolution_actions":  5,
}

# ─── LLM Parameters ──────────────────────────────────────────────────
LLM_TEMPERATURE: float = 0.1
LLM_MAX_TOKENS: int = 2048
LLM_TIMEOUT: int = 30
LLM_MAX_RETRIES: int = 2

# ─── Timestamp Format ────────────────────────────────────────────────
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"
