"""LLM abstraction layer.

Supports both local (Ollama) and API (Groq/Together) providers.
"""

from src.llm.base_llm import BaseLLM
from src.llm.local_llm import LocalLLM
from src.llm.api_llm import ApiLLM

__all__ = ["BaseLLM", "LocalLLM", "ApiLLM"]
