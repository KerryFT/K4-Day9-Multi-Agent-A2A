"""Abstract base class for LLM clients.

Owner: Member A
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLM(ABC):
    """Base interface for all LLM providers."""

    def __init__(self, model_name: str, base_url: str, api_key: str):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request and return the response text."""
        pass

    def health_check(self) -> bool:
        """Check if the LLM provider is accessible."""
        try:
            response = self.chat(
                system_prompt="You are a test.",
                user_message="Reply with OK.",
                max_tokens=10,
            )
            return len(response) > 0
        except Exception:
            return False
