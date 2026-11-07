from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://livesrl:livesrl@db:5432/livesrl"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str  # No default credential; generated once by the container entrypoint.
    app_base_url: str = "http://localhost:3000"
    cookie_secure: bool = False
    session_minutes: int = 60
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    smtp_from: str = "LiveSRL <noreply@livesrl.test>"
    orcid_client_id: str = ""
    orcid_client_secret: str = ""
    orcid_redirect_uri: str = "http://localhost:3000/api/auth/orcid/callback"

    storage_backend: str = "s3"
    storage_dir: str = "/data/reviews"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "livesrl-local"
    s3_secret_key: str = "livesrl-local-only"
    s3_bucket: str = "livesrl"
    grobid_url: str = "http://grobid:8070"
    openalex_api_key: str = ""
    project_contact: str = "https://github.com/IpialesJuan15/Vigilancia"
    max_pdf_bytes: int = 20 * 1024 * 1024

    @model_validator(mode="after")
    def secure_settings(self):
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres")
        if self.app_base_url.startswith("https://") and not self.cookie_secure:
            raise ValueError("HTTPS requiere COOKIE_SECURE=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
