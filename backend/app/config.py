import base64
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    database_url: str = "postgresql+asyncpg://app_user:changeme@postgres:5432/genetic_platform"
    database_url_sync: str = "postgresql://app_user:changeme@postgres:5432/genetic_platform"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # MinIO
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_endpoint: str = "minio:9000"
    minio_bucket_idat: str = "idat-raw"
    minio_bucket_reports: str = "reports"
    minio_bucket_knowledge: str = "knowledge-docs"
    minio_use_ssl: bool = False

    # 加密
    file_encryption_key: str = ""  # base64 编码的 32 字节密钥

    # JWT
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30

    # Resend 邮件 API
    resend_api_key: str = ""
    email_from_address: str = "noreply@yourdomain.com"
    email_from_name: str = "基因抗衰老分析平台"

    # 阿里云短信
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_sms_sign_name: str = ""       # 短信签名
    aliyun_sms_template_code: str = ""   # 模板 Code（含 ${code} 变量）

    # 验证码
    verify_code_expire_minutes: int = 10
    password_reset_expire_minutes: int = 30

    # OAuth 第三方登录
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    wechat_app_id: str = ""              # 微信公众号 / 网页登录 AppID
    wechat_app_secret: str = ""          # 微信公众号 / 网页登录 AppSecret
    wechat_miniapp_app_id: str = ""      # 微信小程序独立 AppID（与公众号不同）
    wechat_miniapp_app_secret: str = ""  # 微信小程序 AppSecret
    oauth_redirect_base: str = "http://localhost:8000"

    # 应用
    environment: str = "development"
    log_level: str = "INFO"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"
    consent_version: str = "1.0"

    @property
    def file_encryption_key_bytes(self) -> bytes:
        return base64.b64decode(self.file_encryption_key)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
