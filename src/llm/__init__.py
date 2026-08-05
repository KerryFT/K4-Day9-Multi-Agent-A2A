"""
LLM Abstraction Layer.

Provides a unified interface over local (Ollama) and cloud (Groq, Together)
providers.  All use OpenAI-compatible chat-completions endpoints.

Factory
-------
>>> from src.llm import create_llm
>>> llm = create_llm("coordinator")   # reads config automatically
>>> llm.chat("You are helpful.", "Hello")
"""

from src.llm.base_llm import BaseLLM
from src.llm.local_llm import LocalLLM
from src.llm.api_llm import ApiLLM
from src.config import AGENT_MODELS, AGENT_PROVIDERS, LLM_PROVIDERS


def create_llm(agent_name: str) -> BaseLLM:
    """Create the right LLM client for *agent_name* from central config.

    Args:
        agent_name: Key in ``AGENT_MODELS`` (e.g. ``"coordinator"``).

    Returns:
        Configured :class:`BaseLLM` subclass.

    Raises:
        ValueError: Unknown *agent_name*.
    """
    if agent_name not in AGENT_MODELS:
        raise ValueError(
            f"Unknown agent {agent_name!r}. "
            f"Valid names: {sorted(AGENT_MODELS)}"
        )

    model_name = AGENT_MODELS[agent_name]
    provider_key = AGENT_PROVIDERS[agent_name]
    provider_cfg = LLM_PROVIDERS[provider_key]

    cls = LocalLLM if provider_key == "local" else ApiLLM
    return cls(
        model_name=model_name,
        base_url=provider_cfg["base_url"],
        api_key=provider_cfg["api_key"],
    )


__all__ = ["BaseLLM", "LocalLLM", "ApiLLM", "create_llm"]
