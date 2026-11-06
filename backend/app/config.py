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
