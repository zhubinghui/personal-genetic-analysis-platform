import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    phone: str | None = None
    is_admin: bool = False
    email_verified: bool = False
    consent_version: str | None
    consent_given_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ConsentRequest(BaseModel):
    version: str = "1.0"


# ── 用户资料编辑 ─────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("新密码至少 8 位")
        return v


# ── 管理员用户管理 ───────────────────────────

class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_admin: bool
    consent_version: str | None
    consent_given_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserOut]


class AdminSetRoleRequest(BaseModel):
    is_admin: bool


class AdminSetStatusRequest(BaseModel):
    is_active: bool


# ── 邮箱验证 & 密码重置 ─────────────────

class SendCodeRequest(BaseModel):
    """发送验证码（邮箱或手机二选一）"""
    channel: str  # "email" 或 "sms"
    target: str   # 邮箱地址或手机号


class VerifyCodeRequest(BaseModel):
    """校验验证码"""
    channel: str  # "email" 或 "sms"
    target: str   # 邮箱地址或手机号
    code: str     # 6 位验证码


class ForgotPasswordRequest(BaseModel):
    channel: str  # "email" 或 "sms"
    target: str   # 邮箱地址或手机号


class ResetPasswordRequest(BaseModel):
    channel: str
    target: str
    code: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("新密码至少 8 位")
        return v
