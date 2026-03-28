"""
多 LLM 抽象服务

支持 Claude / ChatGPT / DeepSeek / Kimi，通过管理员设置动态切换。
DeepSeek 和 Kimi 使用 OpenAI-compatible API，复用 openai SDK。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str = ""       # claude / openai / deepseek / kimi
    api_key: str = ""
    model: str = ""
    base_url: str = ""       # DeepSeek/Kimi 自定义 endpoint
    temperature: float = 0.3
    max_tokens: int = 2000


# 各 Provider 默认模型和 base_url
PROVIDER_DEFAULTS = {
    "claude":   {"model": "claude-sonnet-4-20250514", "base_url": ""},
    "openai":   {"model": "gpt-4o", "base_url": ""},
    "deepseek": {"model": "deepseek-chat", "base_url": "https://api.deepseek.com"},
    "kimi":     {"model": "moonshot-v1-8k", "base_url": "https://api.moonshot.cn/v1"},
    "qwen":     {"model": "qwen-plus", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
}


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """发送对话消息，返回 AI 回复文本。"""


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages, temperature=0.3, max_tokens=2000) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        # Claude API 分离 system 和 user messages
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)

        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg or "你是一位衰老研究专家。",
            messages=user_msgs,
        )
        return response.content[0].text


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI SDK 兼容 Provider（ChatGPT / DeepSeek / Kimi 通用）。"""

    def __init__(self, api_key: str, model: str, base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def chat(self, messages, temperature=0.3, max_tokens=2000) -> str:
        from openai import AsyncOpenAI

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        client = AsyncOpenAI(**kwargs)
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


def create_provider(config: LLMConfig) -> LLMProvider | None:
    """根据配置创建 LLM Provider 实例。"""
    if not config.api_key or not config.provider:
        return None

    defaults = PROVIDER_DEFAULTS.get(config.provider, {})
    model = config.model or defaults.get("model", "")
    base_url = config.base_url or defaults.get("base_url", "")

    if config.provider == "claude":
        return ClaudeProvider(api_key=config.api_key, model=model)
    else:
        return OpenAICompatibleProvider(
            api_key=config.api_key,
            model=model,
            base_url=base_url,
        )


async def get_llm_config_from_db(db) -> LLMConfig:
    """从数据库 SystemSettings 读取 LLM 配置。"""
    from sqlalchemy import select
    from app.models.settings import SystemSettings

    config = LLMConfig()
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.category == "llm")
    )
    for row in result.scalars().all():
        if row.key == "provider":
            config.provider = row.value
        elif row.key == "api_key":
            config.api_key = row.value
        elif row.key == "model":
            config.model = row.value
        elif row.key == "base_url":
            config.base_url = row.value
        elif row.key == "temperature":
            config.temperature = float(row.value)
        elif row.key == "max_tokens":
            config.max_tokens = int(row.value)
    return config


async def get_llm_provider(db) -> LLMProvider | None:
    """获取当前配置的 LLM Provider（未配置返回 None）。"""
    config = await get_llm_config_from_db(db)
    return create_provider(config)
