"""Gyan Sathi application configuration (env-driven)."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Gyan Sathi"
    environment: str = "development"
    log_level: str = "INFO"

    # Database (Supabase Postgres + pgvector)
    database_url: str = ""
    database_schema: str = "public"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    admin_emails: str = "admin@gyansathi.in"

    # Redis
    redis_url: str = ""

    # AI provider
    ai_provider: str = "nvidia"
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    ai_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    ai_model_advanced: str = "nvidia/nemotron-3-super-120b-a12b"
    ai_embedding_model: str = "nvidia/nemotron-3-embed-1b"
    ai_embedding_dim: int = 2048
    ai_request_timeout: int = 120

    # Security
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30
    cors_origins: str = "http://localhost:5173"

    # Uploads
    upload_dir: str = "./uploads"
    upload_max_size: int = 10 * 1024 * 1024
    allowed_upload_types: str = "pdf,png,jpg,jpeg,txt,md,docx"

    # Plans
    free_upload_limit: int = 10
    premium_upload_limit: int = 500
    premium_price_inr: int = 10
    premium_duration_days: int = 365

    # Payments
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    payment_mode: str = "sandbox"  # sandbox | live

    # Direct SMTP email OTP (optional — enables auth without Supabase)
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Gyan Sathi"
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5

    # Cache
    ai_cache_ttl: int = 60 * 60 * 24 * 7  # 7 days for reusable educational answers
    rate_limit_chat_per_min: int = 20
    rate_limit_auth_per_min: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def allowed_types_list(self) -> list[str]:
        return [t.strip().lower() for t in self.allowed_upload_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
