"""
Abstract base class for all domain agents.

Provides:
- Consistent ``process()`` interface for the coordinator
- Pandas-safe utility methods (NaN → None, timestamp formatting, hour delta)
- Optional LLM helper with built-in error handling
- Per-agent logging

Every agent (customer, order_product, payment, delivery, policy, verifier)
inherits from this class.

Owner: Member A
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from src.config import DECIMAL_PLACES
from src.data_loader import DataLoader
from src.llm.base_llm import BaseLLM


class BaseAgent(ABC):
    """Base class every domain agent must inherit."""

    agent_name: str = "base"

    def __init__(self, data_loader: DataLoader, llm: BaseLLM | None = None) -> None:
        """
        Args:
            data_loader: Singleton :class:`DataLoader` with all CSVs cached.
            llm:         Optional LLM client.  Agents may be purely
                         deterministic (no LLM needed).
        """
        self.data = data_loader
        self.llm = llm
        self.log = logging.getLogger(f"agent.{self.agent_name}")

    # ═══════════════════════════════════════════════════════════════
    #  Core Interface
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    def process(self, order_id: str, **kwargs: Any) -> dict[str, Any]:
        """Run the agent's analysis on *order_id*.

        Args:
            order_id: ``claimed_order_id`` from the input case.
            **kwargs:  Extra context forwarded by the coordinator
                       (e.g. other agents' results for the policy agent).

        Returns:
            Flat dict with agent-specific result keys.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    #  LLM Helper
    # ═══════════════════════════════════════════════════════════════

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        *,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Call the LLM with automatic error handling.

        Returns:
            Response text, or ``""`` if no LLM is configured or the
            call fails.
        """
        if self.llm is None:
            self.log.debug("No LLM configured — skipping call")
            return ""
        try:
            return self.llm.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except Exception as exc:
            self.log.error("LLM call failed: %s", exc)
            return ""

    # ═══════════════════════════════════════════════════════════════
    #  Pandas-safe Conversion Utilities
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        """``str(value)`` — returns ``None`` for NaN / NaT."""
        if pd.isna(value):
            return None
        return str(value).strip()

    @staticmethod
    def _safe_float(value: Any, decimals: int = DECIMAL_PLACES) -> Optional[float]:
        """``round(float(value), decimals)`` — returns ``None`` for NaN."""
        if pd.isna(value):
            return None
        return round(float(value), decimals)

    @staticmethod
    def _format_ts(value: Any) -> Optional[str]:
        """Keep CSV timestamp as ``'YYYY-MM-DD HH:MM:SS'``, or ``None``."""
        if pd.isna(value):
            return None
        s = str(value).strip()
        # Truncate sub-second precision if present
        return s[:19] if len(s) > 19 else s

    @staticmethod
    def _hours_between(later: Any, earlier: Any) -> Optional[float]:
        """``(later − earlier)`` in decimal hours, rounded.

        Returns ``None`` when either operand is NaN / NaT.
        """
        if pd.isna(later) or pd.isna(earlier):
            return None
        delta = pd.Timestamp(later) - pd.Timestamp(earlier)
        return round(delta.total_seconds() / 3600, DECIMAL_PLACES)

    # ═══════════════════════════════════════════════════════════════
    #  Repr
    # ═══════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
