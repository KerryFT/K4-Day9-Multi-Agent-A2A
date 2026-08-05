"""Local LLM client using Ollama (OpenAI-compatible API).

Owner: Member A
"""

from openai import OpenAI
from src.llm.base_llm import BaseLLM


class LocalLLM(BaseLLM):
    """LLM client for local Ollama models."""

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434/v1", api_key: str = "ollama"):
        super().__init__(model_name, base_url, api_key)
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send chat completion to local Ollama."""
        kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
