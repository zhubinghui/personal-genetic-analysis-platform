"""
SMTP 邮件发送服务

支持邮箱验证和密码重置两种场景。
使用 Python 内置 smtplib（无需额外依赖），通过 asyncio.to_thread 异步发送。
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to: str, subject: str, html_body: str) -> None:
    """同步发送邮件（由 asyncio.to_thread 包裹调用）。"""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP 未配置，跳过邮件发送: to=%s subject=%s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email or settings.smtp_user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("邮件发送成功: to=%s subject=%s", to, subject)
    except Exception as e:
        logger.error("邮件发送失败: to=%s error=%s", to, e)
        raise


async def send_verification_email(to: str, token: str) -> None:
    """发送邮箱验证邮件。"""
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #16a34a; margin: 8px 0 0;">基因抗衰老分析平台</h2>
      </div>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">您好，</p>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        感谢您注册基因抗衰老分析平台！请点击下方按钮验证您的邮箱地址：
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{verify_url}"
           style="display: inline-block; padding: 12px 32px; background: #16a34a; color: white;
                  text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">
          验证邮箱
        </a>
      </div>
      <p style="color: #6b7280; font-size: 13px;">
        如果按钮无法点击，请复制以下链接到浏览器：<br>
        <a href="{verify_url}" style="color: #16a34a; word-break: break-all;">{verify_url}</a>
      </p>
      <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
        此链接 {settings.email_verify_expire_hours} 小时内有效。如果您没有注册过，请忽略此邮件。
      </p>
    </div>
    """
    await asyncio.to_thread(_send_smtp, to, "请验证您的邮箱 - 基因抗衰老分析平台", html)


async def send_reset_email(to: str, token: str) -> None:
    """发送密码重置邮件。"""
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 24px;">
        <span style="font-size: 36px;">🧬</span>
        <h2 style="color: #16a34a; margin: 8px 0 0;">基因抗衰老分析平台</h2>
      </div>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">您好，</p>
      <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        我们收到了您的密码重置请求。请点击下方按钮设置新密码：
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{reset_url}"
           style="display: inline-block; padding: 12px 32px; background: #16a34a; color: white;
                  text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">
          重置密码
        </a>
      </div>
      <p style="color: #6b7280; font-size: 13px;">
        如果按钮无法点击，请复制以下链接到浏览器：<br>
        <a href="{reset_url}" style="color: #16a34a; word-break: break-all;">{reset_url}</a>
      </p>
      <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
        此链接 {settings.password_reset_expire_minutes} 分钟内有效。如果您没有请求重置密码，请忽略此邮件。
      </p>
    </div>
    """
    await asyncio.to_thread(_send_smtp, to, "密码重置 - 基因抗衰老分析平台", html)
