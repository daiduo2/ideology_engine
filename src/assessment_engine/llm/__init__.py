"""LLM client module with multi-provider support.

This module provides a unified interface for multiple LLM providers:
- Anthropic (Claude models)
- OpenAI-compatible APIs (OpenAI, Azure, Gemini, local models)

Example:
    from assessment_engine.llm import create_llm_client, LLMConfig

    # Anthropic with custom base URL
    config = LLMConfig(
        provider="anthropic",
        api_key="sk-ant-...",
        base_url="https://my-proxy.example.com/v1"
    )
    client = create_llm_client(config)

    # OpenAI-compatible API
    config = LLMConfig(
        provider="openai",
        api_key="sk-...",
        model="gpt-4o",
        base_url="https://api.openai.com/v1"
    )
    client = create_llm_client(config)
"""
from .client import LLMClient
from .config import LLMConfig
from .factory import create_llm_client
from .base import BaseLLMClient

__all__ = [
    "LLMClient",
    "LLMConfig",
    "create_llm_client",
    "BaseLLMClient",
]
