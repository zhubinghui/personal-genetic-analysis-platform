"""
OAuth2 第三方登录 Provider

可插拔架构：新增平台只需实现 OAuthProvider 接口 + 注册到 PROVIDERS 字典。
使用 httpx 做 HTTP 请求（项目已有依赖），无需额外 OAuth 库。
"""

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings


@dataclass
class OAuthUserInfo:
    """第三方平台返回的用户信息（标准化格式）"""
    provider: str       # "github" / "google" / "wechat"
    oauth_id: str       # 平台用户唯一 ID
    email: str | None   # 邮箱（微信可能为空）
    name: str | None
    avatar_url: str | None


class OAuthProvider(ABC):
    """OAuth2 Provider 抽象基类"""

    @abstractmethod
    def get_authorize_url(self, state: str) -> str:
        """生成第三方授权页面 URL"""

    @abstractmethod
    async def exchange_token(self, code: str) -> str:
        """用 authorization code 换取 access_token"""

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """用 access_token 获取用户信息"""

    def is_configured(self) -> bool:
        """检查该 Provider 是否已配置（有 client_id）"""
        return False


# ── GitHub ──────────────────────────────────────────────

class GitHubProvider(OAuthProvider):
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def is_configured(self) -> bool:
        return bool(settings.github_client_id and settings.github_client_secret)

    def get_authorize_url(self, state: str) -> str:
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": f"{settings.oauth_redirect_base}/api/v1/auth/oauth/github/callback",
            "scope": "user:email",
            "state": state,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            # 获取基本信息
            resp = await client.get(self.USER_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # GitHub 邮箱可能是 private，需要单独请求
            email = data.get("email")
            if not email:
                email_resp = await client.get(self.EMAILS_URL, headers=headers)
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    email = primary["email"] if primary else (emails[0]["email"] if emails else None)

            return OAuthUserInfo(
                provider="github",
                oauth_id=str(data["id"]),
                email=email,
                name=data.get("name") or data.get("login"),
                avatar_url=data.get("avatar_url"),
            )


# ── Google ──────────────────────────────────────────────

class GoogleProvider(OAuthProvider):
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def is_configured(self) -> bool:
        return bool(settings.google_client_id and settings.google_client_secret)

    def get_authorize_url(self, state: str) -> str:
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": f"{settings.oauth_redirect_base}/api/v1/auth/oauth/google/callback",
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{settings.oauth_redirect_base}/api/v1/auth/oauth/google/callback",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.USER_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            return OAuthUserInfo(
                provider="google",
                oauth_id=data["id"],
                email=data.get("email"),
                name=data.get("name"),
                avatar_url=data.get("picture"),
            )


# ── 微信（预留） ───────────────────────────────────────

class WeChatProvider(OAuthProvider):
    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
    TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    USER_URL = "https://api.weixin.qq.com/sns/userinfo"

    def is_configured(self) -> bool:
        return bool(settings.wechat_app_id and settings.wechat_app_secret)

    def get_authorize_url(self, state: str) -> str:
        params = {
            "appid": settings.wechat_app_id,
            "redirect_uri": f"{settings.oauth_redirect_base}/api/v1/auth/oauth/wechat/callback",
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"

    async def exchange_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.TOKEN_URL,
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if "errcode" in data:
                raise ValueError(f"微信 token 获取失败: {data}")
            # 微信返回 access_token + openid，需要同时保存
            self._openid = data["openid"]
            return data["access_token"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.USER_URL,
                params={
                    "access_token": access_token,
                    "openid": getattr(self, "_openid", ""),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return OAuthUserInfo(
                provider="wechat",
                oauth_id=data.get("unionid") or data.get("openid", ""),
                email=None,  # 微信不提供邮箱
                name=data.get("nickname"),
                avatar_url=data.get("headimgurl"),
            )


# ── Provider 注册表 ─────────────────────────────────────

PROVIDERS: dict[str, OAuthProvider] = {
    "github": GitHubProvider(),
    "google": GoogleProvider(),
    "wechat": WeChatProvider(),
}


def get_provider(name: str) -> OAuthProvider:
    provider = PROVIDERS.get(name)
    if provider is None:
        raise ValueError(f"不支持的登录方式: {name}")
    return provider


def generate_state() -> str:
    """生成 CSRF 防护 state 参数"""
    return secrets.token_urlsafe(32)
