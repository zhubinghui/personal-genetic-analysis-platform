"""
邮件发送服务 — Resend API

Resend 是现代邮件 API 服务，免费 3000 封/月。
只需一个 API Key，无需配置 SMTP 服务器。

文档：https://resend.com/docs
"""

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _send_resend(to: str, subject: str, html_body: str) -> None:
    """同步发送邮件（由 asyncio.to_thread 包裹调用）。"""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY 未配置，跳过邮件发送: to=%s", to)
        return

    import resend
    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [to],
            "subject": subject,
            "html": html_body,
        })
        logger.info("Resend 邮件发送成功: to=%s subject=%s", to, subject)
    except Exception as e:
        logger.error("Resend 邮件发送失败: to=%s error=%s", to, e)
        raise


async def send_verification_email(to: str, code: str) -> None:
    """发送邮箱验证码邮件。"""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #16a34a; margin: 8px 0 0;">基因抗衰老分析平台</h2>
      </div>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">您好，</p>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        您的邮箱验证码为：
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <span style="display: inline-block; padding: 16px 40px; background: #f0fdf4; border: 2px solid #16a34a;
                     border-radius: 12px; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #16a34a;">
          {code}
        </span>
      </div>
      <p style="color: #6b7280; font-size: 13px; text-align: center;">
        验证码 {settings.verify_code_expire_minutes} 分钟内有效。如非本人操作，请忽略。
      </p>
    </div>
    """
    await asyncio.to_thread(_send_resend, to, f"验证码 {code} - 基因抗衰老分析平台", html)


async def send_reset_email(to: str, code: str) -> None:
    """发送密码重置验证码邮件。"""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #16a34a; margin: 8px 0 0;">基因抗衰老分析平台</h2>
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
    await asyncio.to_thread(_send_resend, to, f"密码重置验证码 {code} - 基因抗衰老分析平台", html)
