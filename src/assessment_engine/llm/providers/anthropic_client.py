"""Anthropic LLM client implementation."""
import json
from typing import Dict, Any

from anthropic import Anthropic

from assessment_engine.llm.base import BaseLLMClient
from assessment_engine.llm.config import LLMConfig


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude API with optional custom base URL."""

    def __init__(self, config: LLMConfig = None):
        if config is None:
            config = LLMConfig()

        self.config = config

        # Build client kwargs
        client_kwargs = {
            "api_key": config.get_api_key(),
        }

        # Add base URL if provided (for proxies)
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = Anthropic(**client_kwargs)

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Make a structured call to Claude and parse JSON response."""
        message = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        content = message.content[0].text
        content = self._extract_json_from_response(content)

        return self._safe_json_parse(content)
