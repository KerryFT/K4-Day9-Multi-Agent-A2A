"""Abstract base class for all agents.

Every agent inherits from BaseAgent and implements process().
This ensures a consistent interface for the coordinator.

Owner: Member A
"""

from abc import ABC, abstractmethod
from typing import Any

from src.data_loader import DataLoader
from src.llm.base_llm import BaseLLM


class BaseAgent(ABC):
    """Base class for all domain agents."""

    agent_name: str = "base"

    def __init__(self, data_loader: DataLoader, llm: BaseLLM | None = None):
        """
        Args:
            data_loader: Shared DataLoader instance with cached CSVs.
            llm: Optional LLM client. Some agents may be purely deterministic.
        """
        self.data = data_loader
        self.llm = llm

    @abstractmethod
    def process(self, order_id: str, **kwargs) -> dict[str, Any]:
        """Process a case and return structured results.

        Args:
            order_id: The claimed_order_id from the input case.
            **kwargs: Additional context from other agents.

        Returns:
            dict with agent-specific results.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_name={self.agent_name}>"
