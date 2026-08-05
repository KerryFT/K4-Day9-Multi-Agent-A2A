"""
Local LLM client — Ollama (OpenAI-compatible ``/v1`` endpoint).

Connects to a locally running Ollama server.  Includes retry with
back-off for transient connection failures (e.g. Ollama still loading
a model).

Owner: Member A
"""

from __future__ import annotations

import logging
import time

from openai import OpenAI, APIConnectionError, APIError

from src.llm.base_llm import BaseLLM
from src.config import LLM_MAX_RETRIES, LLM_TIMEOUT

logger = logging.getLogger(__name__)


class LocalLLM(BaseLLM):
    """LLM client for locally-hosted Ollama models (≤ 10 B)."""

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
    ) -> None:
        super().__init__(model_name, base_url, api_key)
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=LLM_TIMEOUT,
        )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Chat completion via Ollama with automatic retry."""
        kwargs: dict = dict(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                logger.debug(
                    "[%s] OK  attempt=%d  chars=%d",
                    self.model_name, attempt, len(content),
                )
                return content

            except APIConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Connection failed (attempt %d/%d). "
                    "Is Ollama running at %s?",
                    self.model_name, attempt, LLM_MAX_RETRIES, self.base_url,
                )
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)

            except APIError as exc:
                logger.error("[%s] API error: %s", self.model_name, exc)
                raise

        # All retries exhausted
        raise ConnectionError(
            f"Could not reach Ollama at {self.base_url} "
            f"after {LLM_MAX_RETRIES} attempts"
        ) from last_exc
