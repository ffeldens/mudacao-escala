"""Settings carregadas de variáveis de ambiente (.env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env mora na raiz do monorepo, mas uvicorn roda de apps/api/.
# Caminhamos pela árvore: apps/api/src/escala_freemium_api/config.py
#   ↓ parent             config.py
#   ↓ parent             escala_freemium_api/
#   ↓ parent             src/
#   ↓ parent             apps/api/
#   ↓ parent             apps/
#   ↓ parent             <root>
_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Configuração do app. Todas as variáveis vêm do .env ou ambiente."""

    model_config = SettingsConfigDict(
        # Procura .env na raiz do monorepo, e também o local (apps/api/.env)
        # como fallback. Variáveis de ambiente do shell têm precedência sobre ambos.
        env_file=(_ROOT_ENV, ".env"),
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

    # JWT secret pro backend validar tokens (Supabase → Settings → API → JWT Secret)
    SUPABASE_JWT_SECRET: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""           # sk_test_... ou sk_live_...
    STRIPE_PUBLISHABLE_KEY: str = ""      # pk_test_... ou pk_live_...
    STRIPE_WEBHOOK_SECRET: str = ""       # whsec_... (validar webhooks)
    STRIPE_PRICE_ID_STARTER: str = ""     # price_... (criado no dashboard Stripe)
    STRIPE_TRIAL_DAYS: int = 14

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """True só quando APP_ENV é explicitamente dev/local.

        Usado como gate fail-safe pra vazamento de traceback: qualquer
        valor inesperado de APP_ENV (incluindo o default) NÃO é dev, então
        nunca vaza stack trace por engano de config.
        """
        return self.APP_ENV in ("development", "local", "dev")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instância singleton de Settings (cacheada)."""
    return Settings()
