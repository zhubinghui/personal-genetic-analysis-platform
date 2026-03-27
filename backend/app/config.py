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
