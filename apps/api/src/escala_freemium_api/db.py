"""Conexão com Postgres (Supabase) — schema `freemium`.

Padrão dual SQLite/Postgres. Em produção sempre Postgres (Supabase).
SQLite fica como fallback se DATABASE_URL não estiver preenchida —
útil pra dev local sem Supabase.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from escala_freemium_api.config import get_settings

settings = get_settings()

# =============================================================================
# Engine + Session
# =============================================================================

_db_url = settings.DATABASE_URL or "sqlite:///./freemium.db"
_is_postgres = _db_url.startswith("postgresql")

_engine_kwargs: dict = {}
if _is_postgres:
    # Transaction pooler (PgBouncer) não suporta prepared statements.
    _engine_kwargs["connect_args"] = {"prepare_threshold": None}
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(_db_url, **_engine_kwargs)

# Define search_path = freemium em toda conexão (só Postgres)
if _is_postgres:

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_conn, _):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute(f"SET search_path TO {settings.DB_SCHEMA}, public")
        cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# Models
# =============================================================================


# Schema explícito no metadata (só Postgres — SQLite ignora schema).
# Sem isso, create_all() ignora o search_path e cria tudo no schema padrão.
from sqlalchemy import MetaData  # noqa: E402

_metadata = MetaData(schema=settings.DB_SCHEMA if _is_postgres else None)


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy 2.0."""

    metadata = _metadata


class Lead(Base):
    """Lead capturado no simulador free."""

    __tablename__ = "leads"

    # Uuid nativo do SQLAlchemy 2.0:
    # - Postgres: usa tipo UUID nativo
    # - SQLite/MySQL: armazena como CHAR(32) hex, aceita/retorna objetos UUID
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(120), nullable=True)
    n_lojas: Mapped[int] = mapped_column(Integer, default=1)
    porte: Mapped[str | None] = mapped_column(String(20), nullable=True)
    setor: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(60), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    """Mirror da tabela freemium.user_profiles (criada via SQL).

    O backend usa essa model pra ler/atualizar dados do user (plano,
    stripe_customer_id, etc) sem precisar passar pelo PostgREST/RLS.
    """

    __tablename__ = "user_profiles"

    # id = auth.users.id (FK definida em SQL, não em SQLAlchemy pra evitar
    # cross-schema FK issues)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plan_tier: Mapped[str] = mapped_column(String(20), default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trial_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    # Flag "cancelamento agendado pro fim do período" — quando true,
    # user continua com acesso até subscription_current_period_end
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)

    # Premissas customizadas (None = usa defaults do engine)
    # Aplicadas automaticamente nas simulações do user logado.
    pref_encargos_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    pref_vr_dia: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    pref_vt_dia: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    pref_dias_uteis_mes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Simulation(Base):
    """Cada simulação rodada (com ou sem lead, com ou sem user logado)."""

    __tablename__ = "simulations"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # User logado que rodou (None = anônimo). FK pra auth.users.id
    # via SQL — não declaramos FK em SQLAlchemy pra evitar cross-schema FK.
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=True,
        index=True,
    )
    # Label opcional pra user identificar a simulação no histórico
    nome_loja: Mapped[str | None] = mapped_column(String(120), nullable=True)
    inputs_hash: Mapped[str] = mapped_column(String(64), index=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    outputs: Mapped[dict] = mapped_column(JSON)
    n_lojas_extrapolacao: Mapped[int] = mapped_column(Integer, default=1)
    delta_folha_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    economia_estimada_mes: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =============================================================================
# Lifecycle
# =============================================================================


def init_db() -> None:
    """Cria tabelas se ainda não existem.

    Em Postgres: garante schema `freemium` antes de criar tabelas.
    """
    if _is_postgres:
        with engine.connect() as conn:
            conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")
            conn.commit()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI: sessão por request, fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
