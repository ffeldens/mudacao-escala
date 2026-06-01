"""Pydantic schemas da API — payload simplificado pro frontend.

A API recebe um payload mínimo (porte + headcount + custo médio) e constrói o
SimulationInput completo internamente, isolando a complexidade do engine.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field  # noqa: F401

# =============================================================================
# Inputs simplificados
# =============================================================================

SetorType = Literal["varejo", "food_service", "outros"]
PorteType = Literal["PP", "P", "M", "G"]


class SimulateRequest(BaseModel):
    """Payload simplificado que o frontend envia."""

    # Identificação loja (opcional, só pra contexto)
    nome_loja: str | None = Field(default=None, max_length=120)
    setor: SetorType = "varejo"
    porte: PorteType = "M"

    # Headcount agregado (o frontend pode opcionalmente quebrar por função)
    fte_atual: int = Field(ge=1, le=500, description="Total de FTEs hoje (escala 6x1)")
    salario_medio: Decimal = Field(
        gt=0,
        le=Decimal("50000"),
        description="Salário médio bruto da equipe (R$)",
    )
    faturamento_mensal: Decimal | None = Field(
        default=None,
        ge=0,
        description="Faturamento mensal estimado (opcional, usado pra %folha/fat)",
    )

    # Horário
    hora_abertura: int = Field(default=10, ge=0, le=23)
    hora_fechamento: int = Field(default=22, ge=0, le=23)
    dias_operacao_semana: int = Field(default=7, ge=1, le=7)

    # Cenário escolhido pelo usuário
    cenario: Literal["pessimista", "neutro", "otimista"] = "neutro"
    ganho_produtividade_pct: Decimal = Field(
        default=Decimal("0.05"),
        ge=Decimal("0"),
        le=Decimal("0.30"),
        description="Ganho de produtividade esperado (0-30%)",
    )
    manter_salario_nominal: bool = True

    # Extrapolação rede (free também mostra projeção pra N lojas)
    n_lojas_rede: int = Field(default=1, ge=1, le=10_000)


class CenarioOut(BaseModel):
    """Resultado de um cenário (pessimista/neutro/otimista)."""

    cenario: str
    ratio_aplicado: Decimal
    fte_total: Decimal
    folha_total: Decimal
    delta_folha: Decimal
    delta_folha_pct: Decimal


class SimulateResponse(BaseModel):
    """Resposta enxuta pro frontend."""

    inputs_hash: str
    folha_atual_mes: Decimal
    folha_proposta_mes: Decimal
    delta_folha_mes: Decimal
    delta_folha_pct: Decimal
    fte_atual: Decimal
    fte_proposto: Decimal
    fte_extras_necessarios: Decimal

    # 3 cenários
    cenarios: dict[str, CenarioOut]

    # Extrapolação rede
    n_lojas: int
    delta_folha_rede_mes: Decimal
    delta_folha_rede_ano: Decimal

    # Mensagens
    headline: str  # "Sua rede vai gastar R$ X a mais por mês"
    economia_potencial_wfm: Decimal  # 4-7% da folha proposta
    economia_potencial_wfm_pct: Decimal


# =============================================================================
# Lead capture
# =============================================================================


class LeadRequest(BaseModel):
    """Form de captura de email/WhatsApp antes do resultado."""

    email: EmailStr
    whatsapp: str | None = Field(default=None, max_length=20)
    nome: str | None = Field(default=None, max_length=120)
    empresa: str | None = Field(default=None, max_length=120)
    n_lojas: int = Field(default=1, ge=1)
    porte: PorteType = "M"
    setor: SetorType = "varejo"

    # UTM tracking
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


class LeadResponse(BaseModel):
    """Confirmação de captura — devolve lead_id pra associar à simulação."""

    lead_id: str
    email: str
    email_enviado: bool


# =============================================================================
# Waitlist (avise-me dos planos pagos)
# =============================================================================


PlanoInteresse = Literal["starter", "pro", "enterprise"]


class WaitlistRequest(BaseModel):
    """Form curto da waitlist — capta interesse em planos pagos."""

    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    plano: PlanoInteresse
    empresa: str | None = Field(default=None, max_length=120)
    n_lojas: int | None = Field(default=None, ge=0, le=10_000)

    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


class WaitlistResponse(BaseModel):
    lead_id: str
    email: str


# =============================================================================
# Stripe
# =============================================================================


class CheckoutSessionRequest(BaseModel):
    """Request pra criar checkout — só precisa do plano (user vem do JWT)."""

    plano: Literal["starter"] = "starter"


# Sem body — basta o JWT pro user
# (deixei como classe vazia pra consistência se quiser passar opções no futuro)


class CheckoutSessionResponse(BaseModel):
    """Resposta com URL do Stripe Checkout pra redirecionamento."""

    session_id: str
    url: str


class PortalSessionResponse(BaseModel):
    """Resposta com URL do Stripe Customer Portal pra redirecionamento."""

    url: str


# =============================================================================
# Histórico de simulações
# =============================================================================


class SimulationHistoryItem(BaseModel):
    """Item de lista do histórico — versão enxuta pra performance."""

    id: str
    nome_loja: str | None
    n_lojas: int
    delta_folha_pct: Decimal | None
    economia_estimada_mes: Decimal | None
    headline: str | None
    created_at: str  # ISO


class SimulationHistoryResponse(BaseModel):
    items: list[SimulationHistoryItem]
    total: int


# =============================================================================
# Health/version
# =============================================================================


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class VersionResponse(BaseModel):
    api_version: str
    engine_version: str
    env: str
