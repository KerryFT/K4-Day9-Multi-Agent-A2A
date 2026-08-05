"""Configuration for the multi-agent system.

Model names are hardcoded here (required by assignment rules - NOT in .env).
API keys are loaded from .env file.

Owner: Member A
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Paths
# ============================================================
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOGGING_DIR = ROOT_DIR / "logging"

# ============================================================
# Model Configuration (MUST be hardcoded, NOT in .env)
# All models <= 10B parameters
# ============================================================
AGENT_MODELS = {
    "coordinator": "qwen2.5:7b",
    "customer": "llama-3.1-8b-instant",
    "order_product": "qwen2.5:7b",
    "payment": "qwen2.5:7b",
    "delivery": "qwen2.5:7b",
    "policy": "gemma2-9b-it",
    "verifier": "qwen2.5:7b",
}

# ============================================================
# LLM Provider Settings
# ============================================================
LLM_PROVIDERS = {
    "local": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",  # Ollama doesn't need real key
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY", ""),
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key": os.getenv("TOGETHER_API_KEY", ""),
    },
}

# Map agent -> provider
AGENT_PROVIDERS = {
    "coordinator": "local",
    "customer": "groq",
    "order_product": "local",
    "payment": "local",
    "delivery": "local",
    "policy": "together",
    "verifier": "local",
}

# ============================================================
# Business Rules Thresholds
# ============================================================
PAYMENT_TOLERANCE_BRL = 0.10
DECIMAL_PLACES = 2
CONFIDENCE_DEFAULT = 0.92

# ============================================================
# Output Limits (from README)
# ============================================================
LIMITS = {
    "order_ids": 5,
    "item_ids": 5,
    "seller_ids": 3,
    "payment_ids": 5,
    "related_order_ids": 5,
    "product_ids": 5,
    "category_names": 5,
    "ranked_causes": 3,
    "responsible_parties": 3,
    "evidence_ids": 20,
    "resolution_actions": 5,
}

# ============================================================
# LLM Parameters
# ============================================================
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 2048
