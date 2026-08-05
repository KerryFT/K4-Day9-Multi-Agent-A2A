"""
Abstract base class for LLM clients.

Defines the contract that :class:`LocalLLM` and :class:`ApiLLM` implement.
Both expose an OpenAI-compatible ``chat()`` method.

Owner: Member A
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Minimal interface every LLM backend must satisfy."""

    def __init__(self, model_name: str, base_url: str, api_key: str) -> None:
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key

    # ── Core API ──────────────────────────────────────────────────

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat-completion request and return the response text.

        Args:
            system_prompt: System-level instruction.
            user_message:  User message / query.
            temperature:   Sampling temperature (0 → deterministic).
            max_tokens:    Max tokens in the response.
            json_mode:     Request structured JSON output.

        Returns:
            The assistant's reply as a plain string.
        """
        ...

    # ── Utilities ─────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Return ``True`` if the provider is reachable."""
        try:
            resp = self.chat("Reply OK.", "ping", max_tokens=5)
            return bool(resp.strip())
        except Exception as exc:
            logger.warning("Health-check failed for %s: %s", self.model_name, exc)
            return False

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(model={self.model_name!r})"
