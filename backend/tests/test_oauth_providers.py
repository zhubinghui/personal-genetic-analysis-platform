"""OAuth Provider 单元测试"""

import pytest

from app.services.oauth_providers import (
    PROVIDERS,
    GitHubProvider,
    GoogleProvider,
    WeChatProvider,
    generate_state,
    get_provider,
)


class TestGenerateState:
    def test_returns_string(self):
        state = generate_state()
        assert isinstance(state, str)
        assert len(state) > 20

    def test_unique_each_call(self):
        s1 = generate_state()
        s2 = generate_state()
        assert s1 != s2


class TestGetProvider:
    def test_github(self):
        p = get_provider("github")
        assert isinstance(p, GitHubProvider)

    def test_google(self):
        p = get_provider("google")
        assert isinstance(p, GoogleProvider)

    def test_wechat(self):
        p = get_provider("wechat")
        assert isinstance(p, WeChatProvider)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="不支持"):
            get_provider("facebook")


class TestGitHubProvider:
    def test_authorize_url_format(self):
        p = GitHubProvider()
        url = p.get_authorize_url("test-state-123")
        assert "github.com/login/oauth/authorize" in url
        assert "state=test-state-123" in url
        assert "scope=user" in url

    def test_not_configured_without_settings(self):
        p = GitHubProvider()
        # Without actual settings, client_id is empty
        # This tests the is_configured logic
        from app.config import settings
        if not settings.github_client_id:
            assert p.is_configured() is False


class TestGoogleProvider:
    def test_authorize_url_format(self):
        p = GoogleProvider()
        url = p.get_authorize_url("test-state-456")
        assert "accounts.google.com" in url
        assert "state=test-state-456" in url
        assert "scope=openid" in url
        assert "response_type=code" in url


class TestWeChatProvider:
    def test_authorize_url_format(self):
        p = WeChatProvider()
        url = p.get_authorize_url("test-state-789")
        assert "open.weixin.qq.com" in url
        assert "state=test-state-789" in url
        assert url.endswith("#wechat_redirect")

    def test_scope_is_snsapi_login(self):
        p = WeChatProvider()
        url = p.get_authorize_url("s")
        assert "scope=snsapi_login" in url


class TestProviderRegistry:
    def test_all_providers_registered(self):
        assert "github" in PROVIDERS
        assert "google" in PROVIDERS
        assert "wechat" in PROVIDERS
        assert len(PROVIDERS) == 3
