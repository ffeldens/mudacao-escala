"""Settings carregadas de variáveis de ambiente (.env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração do app. Todas as variáveis vêm do .env ou ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"
    APP_PORT_API: int = 8012
    APP_BASE_URL: str = "http://localhost:3000"

    # Database (Supabase Postgres, schema "freemium")
    DATABASE_URL: str = Field(default="", description="postgresql+psycopg://...")
    DB_SCHEMA: str = "freemium"

    # Resend
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "simulador@mudacao.com.br"
    RESEND_REPLY_TO: str = "felipe@feldens.com"

    # Email admin recebe notificação a cada novo lead.
    # Deixe vazio pra desativar.
    ADMIN_NOTIFY_EMAIL: str = "felipe@feldens.com"

    # Supabase (frontend usa anon; backend só usa service role pra writes especiais)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instância singleton de Settings (cacheada)."""
    return Settings()
