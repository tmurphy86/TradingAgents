import os
from typing import Optional

from .api_key_env import get_api_key_env
from .base_client import BaseLLMClient

# Providers that use the OpenAI-compatible chat completions API
_OPENAI_COMPATIBLE = (
    "openai",
    "xai",
    "deepseek",
    "qwen",
    "qwen-cn",
    "glm",
    "glm-cn",
    "minimax",
    "minimax-cn",
    "ollama",
    "openrouter",
)


def _assert_api_key(provider: str) -> None:
    """Raise a clear ValueError if the required API key env var is not set."""
    env_var = get_api_key_env(provider)
    if env_var and not os.environ.get(env_var):
        raise ValueError(
            f"{env_var} is not set. "
            f"Add it to your .env file or environment before using the '{provider}' provider."
        )


def create_llm_client(
    provider: str,
    model: str,
    base_url: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Provider modules are imported lazily so that simply importing this
    factory (e.g. during test collection) does not pull in heavy LLM SDKs
    or fail when their API keys are absent.

    Args:
        provider: LLM provider name
        model: Model name/identifier
        base_url: Optional base URL for API endpoint
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured BaseLLMClient instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_lower = provider.lower()
    _assert_api_key(provider_lower)

    if provider_lower in _OPENAI_COMPATIBLE:
        from .openai_client import OpenAIClient

        return OpenAIClient(model, base_url, provider=provider_lower, **kwargs)

    if provider_lower == "anthropic":
        from .anthropic_client import AnthropicClient

        return AnthropicClient(model, base_url, **kwargs)

    if provider_lower == "google":
        from .google_client import GoogleClient

        return GoogleClient(model, base_url, **kwargs)

    if provider_lower == "azure":
        from .azure_client import AzureOpenAIClient

        return AzureOpenAIClient(model, base_url, **kwargs)

    raise ValueError(
        f"Unsupported LLM provider: {provider!r}. Supported providers: openai, anthropic, google, azure, xai, deepseek, qwen, glm, minimax, openrouter, ollama"
    )
