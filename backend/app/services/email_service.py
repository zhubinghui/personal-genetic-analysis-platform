"""
邮件发送服务 — 阿里云邮件推送（DirectMail）

国内高校/企业邮箱投递稳定，与阿里云短信共用同一 AccessKey。
使用 httpx 直接调用 REST API，无需额外 SDK 依赖。

控制台配置步骤：
  1. 开通阿里云邮件推送服务
  2. 添加发信域名并完成 DNS 验证
  3. 创建发信地址（如 noreply@yourdomain.com），类型选「触发邮件」
  4. 将发信地址填入 .env 的 ALIYUN_DM_ACCOUNT_NAME

文档：https://help.aliyun.com/document_detail/29444.html
"""

import asyncio
import hashlib
import hmac
import logging
import urllib.parse
import uuid
from base64 import b64encode
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DM_ENDPOINT = "https://dm.aliyuncs.com/"


def _sign(params: dict[str, str], secret: str) -> str:
    """阿里云 API HMAC-SHA1 签名。"""
    sorted_query = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    string_to_sign = f"GET&%2F&{urllib.parse.quote(sorted_query, safe='')}"
    key = (secret + "&").encode()
    digest = hmac.new(key, string_to_sign.encode(), hashlib.sha1).digest()
    return b64encode(digest).decode()


def _send_directmail(to: str, subject: str, html_body: str) -> None:
    """同步发送邮件（由 asyncio.to_thread 包裹调用）。"""
    if not settings.aliyun_access_key_id or not settings.aliyun_dm_account_name:
        raise RuntimeError(
            "阿里云 DirectMail 未配置（缺少 ALIYUN_ACCESS_KEY_ID 或 ALIYUN_DM_ACCOUNT_NAME），"
            "无法发送邮件"
        )

    params: dict[str, str] = {
        "Format": "JSON",
        "Version": "2015-11-23",
        "AccessKeyId": settings.aliyun_access_key_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Action": "SingleSendMail",
        "AccountName": settings.aliyun_dm_account_name,
        "ReplyToAddress": "false",
        "AddressType": "1",
        "ToAddress": to,
        "Subject": subject,
        "HtmlBody": html_body,
        "FromAlias": settings.email_from_name,
    }
    params["Signature"] = _sign(params, settings.aliyun_access_key_secret)

    try:
        resp = httpx.get(_DM_ENDPOINT, params=params, timeout=15.0)
        data = resp.json()
        if "Code" in data:
            raise RuntimeError(f"DirectMail 错误: {data.get('Code')} - {data.get('Message')}")
        logger.info("DirectMail 邮件发送成功: to=%s", to)
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("DirectMail 邮件发送失败: to=%s error=%s", to, e)
        raise


async def send_verification_email(to: str, code: str) -> None:
    """发送邮箱验证码邮件。"""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #0284c7; margin: 8px 0 0;">基因抗衰老分析平台</h2>
      </div>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">您好，</p>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        您的邮箱验证码为：
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <span style="display: inline-block; padding: 16px 40px; background: #f0f9ff; border: 2px solid #0284c7;
                     border-radius: 12px; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #0284c7;">
          {code}
        </span>
      </div>
      <p style="color: #6b7280; font-size: 13px; text-align: center;">
        验证码 {settings.verify_code_expire_minutes} 分钟内有效。如非本人操作，请忽略。
      </p>
    </div>
    """
    await asyncio.to_thread(_send_directmail, to, f"验证码 {code} - 基因抗衰老分析平台", html)


async def send_reset_email(to: str, code: str) -> None:
    """发送密码重置验证码邮件。"""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #0284c7; margin: 8px 0 0;">基因抗衰老分析平台</h2>
      </div>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">您好，</p>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        您的密码重置验证码为：
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <span style="display: inline-block; padding: 16px 40px; background: #fef3c7; border: 2px solid #f59e0b;
                     border-radius: 12px; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #b45309;">
          {code}
        </span>
      </div>
      <p style="color: #6b7280; font-size: 13px; text-align: center;">
        验证码 {settings.verify_code_expire_minutes} 分钟内有效。如非本人操作，请忽略。
      </p>
    </div>
    """
    await asyncio.to_thread(_send_directmail, to, f"密码重置验证码 {code} - 基因抗衰老分析平台", html)
