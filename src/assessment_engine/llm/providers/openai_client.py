"""OpenAI-compatible LLM client implementation."""

import json
from typing import Any

from assessment_engine.llm.base import BaseLLMClient
from assessment_engine.llm.config import LLMConfig


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs.

    Supports:
    - OpenAI official API
    - Azure OpenAI
    - Gemini (via OpenAI compatibility)
    - Local models (llama.cpp, vLLM, etc.)
    - Third-party proxies
    """

    def __init__(self, config: LLMConfig = None):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI client requires 'openai' package. Install with: pip install openai"
            ) from e

        if config is None:
            config = LLMConfig(provider="openai", model="gpt-4o")

        self.config = config

        # Build client kwargs
        client_kwargs = {
            "api_key": config.get_api_key(),
        }

        # Add base URL if provided
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = OpenAI(**client_kwargs)

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Make a structured call to OpenAI API and parse JSON response."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        content = self._extract_json_from_response(content)

        return json.loads(content)
