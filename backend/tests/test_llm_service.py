"""LLM 服务单元测试"""

import pytest

from app.services.llm_service import LLMConfig, PROVIDER_DEFAULTS, create_provider


class TestLLMConfig:
    def test_default_values(self):
        config = LLMConfig()
        assert config.provider == ""
        assert config.api_key == ""
        assert config.temperature == 0.3
        assert config.max_tokens == 2000

    def test_provider_defaults_keys(self):
        assert "claude" in PROVIDER_DEFAULTS
        assert "openai" in PROVIDER_DEFAULTS
        assert "deepseek" in PROVIDER_DEFAULTS
        assert "kimi" in PROVIDER_DEFAULTS


class TestCreateProvider:
    def test_returns_none_without_api_key(self):
        config = LLMConfig(provider="claude", api_key="")
        assert create_provider(config) is None

    def test_returns_none_without_provider(self):
        config = LLMConfig(provider="", api_key="sk-test-key")
        assert create_provider(config) is None

    def test_creates_claude_provider(self):
        config = LLMConfig(provider="claude", api_key="sk-ant-test")
        provider = create_provider(config)
        assert provider is not None
        assert type(provider).__name__ == "ClaudeProvider"

    def test_creates_openai_provider(self):
        config = LLMConfig(provider="openai", api_key="sk-test")
        provider = create_provider(config)
        assert provider is not None
        assert type(provider).__name__ == "OpenAICompatibleProvider"

    def test_creates_deepseek_provider(self):
        config = LLMConfig(provider="deepseek", api_key="sk-test")
        provider = create_provider(config)
        assert provider is not None
        assert type(provider).__name__ == "OpenAICompatibleProvider"

    def test_creates_kimi_provider(self):
        config = LLMConfig(provider="kimi", api_key="sk-test")
        provider = create_provider(config)
        assert provider is not None

    def test_uses_default_model_when_empty(self):
        config = LLMConfig(provider="claude", api_key="sk-test", model="")
        provider = create_provider(config)
        assert provider is not None
        assert provider.model == PROVIDER_DEFAULTS["claude"]["model"]

    def test_custom_model_overrides_default(self):
        config = LLMConfig(provider="openai", api_key="sk-test", model="gpt-4-turbo")
        provider = create_provider(config)
        assert provider.model == "gpt-4-turbo"

    def test_deepseek_uses_custom_base_url(self):
        config = LLMConfig(provider="deepseek", api_key="sk-test")
        provider = create_provider(config)
        assert provider.base_url == "https://api.deepseek.com"
