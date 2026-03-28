"""
短信发送服务 — 阿里云短信 API

需要在阿里云控制台完成：
  1. 创建 AccessKey（RAM 用户，仅 SMS 权限）
  2. 创建短信签名（如"基因分析平台"）
  3. 创建短信模板（含 ${code} 变量），审核通过后获取 TemplateCode

文档：https://help.aliyun.com/document_detail/101414.html
"""

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _send_aliyun_sms(phone: str, code: str) -> None:
    """同步发送阿里云短信。"""
    if not settings.aliyun_access_key_id or not settings.aliyun_access_key_secret:
        logger.warning("阿里云短信未配置，跳过发送: phone=%s", phone)
        return

    from alibabacloud_dysmsapi20170525.client import Client
    from alibabacloud_dysmsapi20170525.models import SendSmsRequest
    from alibabacloud_tea_openapi.models import Config

    config = Config(
        access_key_id=settings.aliyun_access_key_id,
        access_key_secret=settings.aliyun_access_key_secret,
        endpoint="dysmsapi.aliyuncs.com",
    )
    client = Client(config)

    request = SendSmsRequest(
        phone_numbers=phone,
        sign_name=settings.aliyun_sms_sign_name,
        template_code=settings.aliyun_sms_template_code,
        template_param=f'{{"code":"{code}"}}',
    )

    try:
        response = client.send_sms(request)
        if response.body.code == "OK":
            logger.info("短信发送成功: phone=%s", phone)
        else:
            logger.error("短信发送失败: phone=%s code=%s message=%s",
                         phone, response.body.code, response.body.message)
            raise RuntimeError(f"短信发送失败: {response.body.message}")
    except Exception as e:
        logger.error("短信发送异常: phone=%s error=%s", phone, e)
        raise


async def send_verification_sms(phone: str, code: str) -> None:
    """发送验证码短信。"""
    await asyncio.to_thread(_send_aliyun_sms, phone, code)


async def send_reset_sms(phone: str, code: str) -> None:
    """发送密码重置验证码短信（复用同一模板）。"""
    await asyncio.to_thread(_send_aliyun_sms, phone, code)
