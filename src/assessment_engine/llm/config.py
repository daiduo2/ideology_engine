"""LLM configuration for multiple providers."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal


class LLMConfig(BaseModel):
    """Configuration for LLM provider.

    Supports Anthropic and OpenAI-compatible APIs.

    Examples:
        # Anthropic (default)
        config = LLMConfig(
            provider="anthropic",
            api_key="sk-ant-...",
            model="claude-opus-4-6"
        )

        # Anthropic with custom base URL (proxy)
        config = LLMConfig(
            provider="anthropic",
            api_key="sk-ant-...",
            model="claude-opus-4-6",
            base_url="https://my-proxy.example.com/v1"
        )

        # OpenAI
        config = LLMConfig(
            provider="openai",
            api_key="sk-...",
            model="gpt-4o"
        )

        # OpenAI-compatible (e.g., Azure, Gemini, local models)
        config = LLMConfig(
            provider="openai",
            api_key="...",
            model="gpt-4",
            base_url="https://my-api.openai.azure.com/openai/deployments/gpt4"
        )
    """

    provider: Literal["anthropic", "openai"] = Field(
        default="anthropic",
        description="LLM provider: 'anthropic' or 'openai'"
    )

    api_key: Optional[str] = Field(
        default=None,
        description="API key. If not provided, will use environment variable"
    )

    model: str = Field(
        default="claude-opus-4-6",
        description="Model name to use"
    )

    base_url: Optional[str] = Field(
        default=None,
        description="Custom base URL for API (for proxies or custom endpoints)"
    )

    temperature: float = Field(
        default=0.3,
        ge=0,
        le=2,
        description="Default temperature for generation"
    )

    max_tokens: int = Field(
        default=4096,
        ge=1,
        description="Maximum tokens to generate"
    )

    timeout: Optional[float] = Field(
        default=60.0,
        description="Request timeout in seconds"
    )

    model_config = ConfigDict(frozen=True)

    def get_api_key(self) -> str:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key

        env_vars = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        import os
        env_var = env_vars.get(self.provider)
        if env_var:
            key = os.environ.get(env_var)
            if key:
                return key

        raise ValueError(
            f"API key not provided and {env_vars.get(self.provider)} not set"
        )
