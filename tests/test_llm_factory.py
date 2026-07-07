"""Unit tests for create_llm_client() provider routing — no real API calls."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

from tradingagents.llm_clients.factory import create_llm_client

# All providers the factory must handle.
# conftest.py sets every API key env var to "placeholder" so _assert_api_key passes.
_OPENAI_COMPATIBLE_CASES = [
    ("openai", "gpt-4o"),
    ("xai", "grok-3"),
    ("deepseek", "deepseek-chat"),
    ("qwen", "qwen-plus"),
    ("glm", "glm-4-flash"),
    ("minimax", "MiniMax-Text-01"),
    ("openrouter", "openai/gpt-4o"),
    ("ollama", "llama3.2"),
]


@pytest.mark.parametrize("provider,model", _OPENAI_COMPATIBLE_CASES)
def test_openai_compatible_providers_return_client(provider, model):
    """All OpenAI-compatible providers must instantiate without error."""
    with patch("tradingagents.llm_clients.openai_client.ChatOpenAI"):
        client = create_llm_client(provider, model)
    assert client is not None


def test_anthropic_provider_returns_client():
    with patch("tradingagents.llm_clients.anthropic_client.ChatAnthropic"):
        client = create_llm_client("anthropic", "claude-haiku-4-5-20251001")
    assert client is not None


def test_google_provider_returns_client():
    with patch("tradingagents.llm_clients.google_client.ChatGoogleGenerativeAI"):
        client = create_llm_client("google", "gemini-2.0-flash")
    assert client is not None


def test_azure_provider_returns_client():
    with patch("tradingagents.llm_clients.azure_client.AzureChatOpenAI"):
        client = create_llm_client("azure", "gpt-4o")
    assert client is not None


def test_unsupported_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_client("not-a-real-provider", "some-model")


def test_provider_lookup_is_case_insensitive():
    """Provider string should be lowercased before dispatch."""
    with patch("tradingagents.llm_clients.anthropic_client.ChatAnthropic"):
        client = create_llm_client("Anthropic", "claude-haiku-4-5-20251001")
    assert client is not None


def test_missing_api_key_raises_value_error(monkeypatch):
    """_assert_api_key must raise before the client is constructed."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_llm_client("openai", "gpt-4o")
