"""Factory for creating LLM clients based on configuration."""
from assessment_engine.llm.config import LLMConfig
from assessment_engine.llm.base import BaseLLMClient


def create_llm_client(config: LLMConfig = None) -> BaseLLMClient:
    """Create an LLM client based on configuration.

    Args:
        config: LLM configuration. If None, uses default Anthropic config.

    Returns:
        Configured LLM client instance.

    Examples:
        # Default Anthropic client
        client = create_llm_client()

        # Anthropic with custom base URL (proxy)
        config = LLMConfig(
            provider="anthropic",
            api_key="sk-ant-...",
            base_url="https://my-proxy.example.com/v1"
        )
        client = create_llm_client(config)

        # OpenAI official API
        config = LLMConfig(
            provider="openai",
            api_key="sk-...",
            model="gpt-4o"
        )
        client = create_llm_client(config)

        # OpenAI-compatible (Azure, Gemini, local models)
        config = LLMConfig(
            provider="openai",
            api_key="...",
            model="gpt-4",
            base_url="https://my-api.openai.azure.com/openai/deployments/gpt4"
        )
        client = create_llm_client(config)
    """
    if config is None:
        config = LLMConfig()

    if config.provider == "anthropic":
        from assessment_engine.llm.providers.anthropic_client import AnthropicClient
        return AnthropicClient(config)
    elif config.provider == "openai":
        from assessment_engine.llm.providers.openai_client import OpenAIClient
        return OpenAIClient(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
