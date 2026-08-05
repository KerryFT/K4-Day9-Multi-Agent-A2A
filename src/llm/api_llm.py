"""
Cloud API LLM client — Groq · Together AI · OpenRouter.

All three providers expose OpenAI-compatible ``/v1/chat/completions``.
Includes retry with exponential back-off for rate-limit (429) and
transient connection errors.

Owner: Member A
"""

from __future__ import annotations

import logging
import time

from openai import OpenAI, APIConnectionError, APIError, RateLimitError

from src.llm.base_llm import BaseLLM
from src.config import LLM_MAX_RETRIES, LLM_TIMEOUT

logger = logging.getLogger(__name__)


class ApiLLM(BaseLLM):
    """LLM client for cloud API providers (OpenAI-compatible)."""

    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
    ) -> None:
        super().__init__(model_name, base_url, api_key)
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy-initialise the OpenAI client on first use."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    f"No API key for {self.model_name}. "
                    f"Set the key in .env and reload."
                )
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=LLM_TIMEOUT,
            )
        return self._client

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Chat completion via cloud API with rate-limit retry."""
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

            except RateLimitError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "[%s] Rate-limited (attempt %d/%d). Backing off %ds …",
                    self.model_name, attempt, LLM_MAX_RETRIES, wait,
                )
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(wait)

            except APIConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Connection failed (attempt %d/%d)",
                    self.model_name, attempt, LLM_MAX_RETRIES,
                )
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)

            except APIError as exc:
                logger.error("[%s] API error: %s", self.model_name, exc)
                raise

        # All retries exhausted
        raise ConnectionError(
            f"Cloud API request to {self.base_url} failed "
            f"after {LLM_MAX_RETRIES} attempts"
        ) from last_exc
