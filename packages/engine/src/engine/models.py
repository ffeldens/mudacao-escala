"""Modelos Pydantic do engine.

Ver PRD seção 5.3-5.4 para especificação completa.

⚠️ Princípios:
- Modelos são FONTE DE VERDADE da forma dos dados
- Sempre validar com Pydantic, nunca confiar em dict cru
- Decimal para valores monetários (nunca float)
- Campo `brand` discrimina T&F vs TFC (regras diferentes)
- Vendedores T&F com `comissionado=True` têm restrição de não folgar sábado
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Tipos auxiliares
# =============================================================================

Brand = Literal["track_field", "tfc"]
StoreType = Literal["shopping", "rua", "outlet"]
StoreCluster = Literal["PP", "P", "M", "G"]
ContractType = Literal["clt_5x2", "clt_6x1_legado", "horista_pj"]
ScenarioType = Literal["pessimista", "neutro", "otimista"]
SeverityLevel = Literal["info", "good", "warn", "bad"]


# =============================================================================
# Inputs do simulador
# =============================================================================


class FunctionRole(BaseModel):
    """Uma função/cargo dentro de uma loja, com headcount e custo."""

    nome: str = Field(description="Ex: 'Vendedor', 'Caixa', 'Estoque', 'Gerencia'")
    qtd_atual: int = Field(ge=0, description="Headcount atual (na escala 6x1)")
    salario_medio: Decimal = Field(gt=0, description="Salário médio bruto (R$)")
    comissionado: bool = Field(
        default=False,
        description="Se True, função tem restrição estrutural (ex: vendedor T&F não folga sábado)",
    )
    presenca_minima_simultanea: int = Field(
        ge=0,
        default=1,
        description="Quantos precisam estar presentes simultaneamente em horário de pico",
    )
    restricoes_folga_estruturais: list[str] = Field(
        default_factory=list,
        description="Dias da semana que esta função não pode folgar. Ex: ['sabado'] para comissionados",
    )
    pode_cobrir_funcoes: list[str] = Field(
        default_factory=list,
        description=(
            "Outras funções que esta pode cobrir em multifunção. Ex: gerente "
            "T&F cobre 'Caixa' quando o caixa está em folga. Usado pelo "
            "Planejador (Fase 2A) para satisfazer presenca_minima_simultanea."
        ),
    )


class TicketHistoryPoint(BaseModel):
    """Ponto da curva de demanda — quantidade de tickets em uma janela.

    Substitui faturamento como proxy de esforço operacional. Decisão semântica:
    queremos medir esforço, não dinheiro. Várias compras pequenas exigem mais
    pessoas que uma compra grande.
    """

    dia_semana: int = Field(ge=0, le=6, description="0=segunda, 6=domingo")
    hora: int = Field(ge=0, le=23)
    media_tickets: Decimal = Field(ge=0, description="Média histórica de tickets nesta janela")
    desvio_padrao: Decimal = Field(default=Decimal("0"))


class StoreInput(BaseModel):
    """Dados de uma loja para simulação."""

    codigo: str = Field(description="Código único da loja no tenant")
    nome: str
    brand: Brand = Field(description="track_field ou tfc — condiciona regras de negócio")
    tipo: StoreType
    cluster: StoreCluster = Field(description="Tamanho por volume típico de tickets/dia")
    hora_abertura: int = Field(ge=6, le=14)
    hora_fechamento: int = Field(ge=16, le=24)
    dias_operacao_semana: int = Field(ge=1, le=7)
    faturamento_mensal: Decimal | None = Field(
        default=None,
        description="Opcional, apenas para análise. Não é usado como proxy de demanda.",
    )
    ticket_history: list[TicketHistoryPoint] = Field(
        default_factory=list,
        description="Histórico de tickets por dia × hora. Proxy real de demanda.",
    )
    funcoes: list[FunctionRole] = Field(min_length=1)

    @field_validator("hora_fechamento")
    @classmethod
    def fechamento_depois_abertura(cls, v: int, info) -> int:
        if "hora_abertura" in info.data and v <= info.data["hora_abertura"]:
            raise ValueError("hora_fechamento deve ser maior que hora_abertura")
        return v


class FinancialAssumptions(BaseModel):
    """Premissas financeiras (encargos, benefícios, dias úteis)."""

    encargos_pct: Decimal = Field(
        default=Decimal("0.78"),
        ge=0,
        le=2,
        description="INSS+FGTS+13º+férias+rescisão. Default 78%",
    )
    vr_dia: Decimal = Field(default=Decimal("32"), ge=0)
    vt_dia: Decimal = Field(default=Decimal("14"), ge=0)
    dias_uteis_mes: int = Field(default=22, ge=20, le=23)


class ScenarioConfig(BaseModel):
    """Configuração do cenário de simulação."""

    manter_salario_nominal: bool = Field(
        default=True,
        description="True: mantém salário nominal (mercado). False: reduz proporcional 40/44.",
    )
    ganho_produtividade_pct: Decimal = Field(
        default=Decimal("0.05"),
        ge=0,
        le=Decimal("0.30"),
        description="Ganho esperado em decimal. 0.05 = 5%",
    )
    cenario: ScenarioType = "neutro"
    permitir_aumento_quadro: bool = Field(
        default=False,
        description="v1.0: default False — não sugere contratação automaticamente",
    )


class SimulationInput(BaseModel):
    """Input completo para uma simulação de migração 6x1 → 5x2."""

    store: StoreInput
    financial: FinancialAssumptions = Field(default_factory=FinancialAssumptions)
    scenario: ScenarioConfig = Field(default_factory=ScenarioConfig)
    clt_version: str = Field(default="2026-04", description="Versão da régua CLT aplicada")
    brand_rules_version: str = Field(
        default="0.0.0",
        description="Hash/versão do brand-rules.md aplicado (auditoria)",
    )


# =============================================================================
# Outputs do simulador
# =============================================================================


class CoverageHourPoint(BaseModel):
    """Cobertura de FTEs em uma hora específica do dia."""

    hora: int = Field(ge=0, le=23)
    fte_atual: Decimal = Field(description="FTEs disponíveis em escala 6x1")
    fte_proposto: Decimal = Field(description="FTEs disponíveis em escala 5x2")
    demanda_proxy: Decimal = Field(description="Demanda estimada (em FTEs equivalentes)")


class FunctionImpact(BaseModel):
    """Impacto da migração em uma função específica."""

    nome: str
    fte_atual: Decimal
    fte_proposto: Decimal
    custo_atual_mes: Decimal
    custo_proposto_mes: Decimal
    delta_custo: Decimal = Field(description="custo_proposto - custo_atual")


class CLTRiskItem(BaseModel):
    """Risco trabalhista identificado pelo simulador."""

    severidade: SeverityLevel
    artigo: str = Field(description="Ex: 'CLT Art. 71'")
    titulo: str
    descricao: str


class Recomendacao(BaseModel):
    """Recomendação acionável priorizada."""

    prioridade: int = Field(ge=1, le=10, description="1 = mais alta")
    titulo: str
    descricao: str
    impacto_estimado: str | None = None


class ScenarioResult(BaseModel):
    """Resultado de um cenário (pessimista / neutro / otimista)."""

    cenario: ScenarioType
    ratio_aplicado: Decimal
    fte_total: Decimal
    folha_total: Decimal
    delta_folha: Decimal
    delta_folha_pct: Decimal


class SimulationOutput(BaseModel):
    """Output completo de uma simulação."""

    # Auditoria
    inputs_hash: str = Field(description="SHA-256 dos inputs para idempotência")
    clt_version: str
    brand_rules_version: str

    # KPIs principais
    folha_atual_mes: Decimal
    folha_proposta_mes: Decimal
    delta_folha_mes: Decimal
    delta_folha_pct: Decimal
    fte_atual_total: Decimal
    fte_proposto_total: Decimal
    folha_sobre_faturamento_atual: Decimal | None = None
    folha_sobre_faturamento_proposto: Decimal | None = None

    # Detalhamento
    impacto_por_funcao: list[FunctionImpact]
    cobertura_horaria: list[CoverageHourPoint]

    # Análise CLT
    riscos_clt: list[CLTRiskItem]

    # Cenários (pess/neut/otim)
    cenarios: dict[ScenarioType, ScenarioResult]

    # Recomendações priorizadas
    recomendacoes: list[Recomendacao]


# =============================================================================
# Modelos para o validador CLT (input independente do simulador)
# =============================================================================


class ScheduleShift(BaseModel):
    """Um turno individual de um colaborador em uma data."""

    employee_id: str
    employee_nome: str | None = None
    data: str = Field(description="ISO date YYYY-MM-DD")
    inicio: str = Field(description="HH:MM")
    fim: str = Field(description="HH:MM")
    intrajornada_inicio: str | None = None
    intrajornada_fim: str | None = None


class ScheduleEmployee(BaseModel):
    """Colaborador participante de uma escala — usado para validar regras
    que dependem da função (ex: comissionado T&F não folga sábado)."""

    employee_id: str
    funcao: str = Field(description="Nome da função (espelha FunctionRole.nome)")
    comissionado: bool = False


class Schedule(BaseModel):
    """Escala completa de uma loja em um período."""

    store_codigo: str
    brand: Brand
    periodo_inicio: str = Field(description="ISO date")
    periodo_fim: str = Field(description="ISO date")
    employees: list[ScheduleEmployee] = Field(
        default_factory=list,
        description="Lista de colaboradores na escala. Necessária para regras "
        "de marca que dependem da função (ex: comissionado).",
    )
    shifts: list[ScheduleShift]


class CLTViolation(BaseModel):
    """Violação CLT detectada na validação."""

    artigo: str
    severidade: SeverityLevel
    employee_id: str | None = None
    data: str | None = None
    descricao: str
    sugestao_correcao: str | None = None


class EmployeeRecord(BaseModel):
    """Cadastro individual de colaborador (vindo de CSV de RH).

    Diferente de `ScheduleEmployee` (que é usado dentro de uma escala
    específica), `EmployeeRecord` representa um cadastro persistente —
    inclui salário, loja, data de admissão.
    """

    employee_id: str
    funcao: str
    store_codigo: str
    salario_medio: Decimal = Field(gt=0)
    comissionado: bool = False
    data_admissao: str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    ativo: bool = True
    restricoes: list[str] = Field(default_factory=list, description="tags livres: estudante, PCD, gestante, etc")


class CLTValidationResult(BaseModel):
    """Resultado da validação CLT de uma escala."""

    schedule_id: str | None = None
    clt_version: str
    brand_rules_version: str
    is_valid: bool = Field(description="True se ZERO violações")
    violations: list[CLTViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
