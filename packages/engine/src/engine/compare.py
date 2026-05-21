"""Comparativo entre escala baseline (atual) e escala otimizada (solver).

Pitch: o cliente sobe a escala 6x1 atual; o sistema valida vs CLT; mostra
quantas violações já existem HOJE (independente da PEC); depois roda o
solver e gera a escala otimizada; compara lado-a-lado.

Métricas comparativas:
- Violações CLT (total + por artigo)
- Horas trabalhadas (total + média por colaborador)
- Cobertura por hora do dia (média de colaboradores simultâneos)
- Distribuição de fim de semana (sáb + dom)

NÃO inclui custo financeiro neste sprint — depende de cruzar baseline
com cadastro de colaboradores (salário por funcionário), o que pode ser
adicionado em iteração futura.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from engine.clt_validator import validate_clt
from engine.models import FinancialAssumptions, Schedule


# Estimativa CONSERVADORA de passivo trabalhista por violação CLT
# Baseado em jurisprudência média varejo:
#  - Art 58 (jornada >8h sem acordo): ~R$ 200/dia
#  - Art 66 (interjornada <11h): ~R$ 500/dia
#  - Art 67 (DSR semanal): ~R$ 1.000/semana
#  - Art 71 (intrajornada): 50% sobre hora suprimida → ~R$ 300/dia
#  - Lei 10.101 (4 domingos): ~R$ 800/ciclo
#  - Brand T&F: ~R$ 100/dia (interno, não legal)
# Média ponderada conservadora: R$ 500/violação detectada
VALOR_PASSIVO_POR_VIOLACAO: Decimal = Decimal("500.00")


@dataclass
class ScheduleMetrics:
    """Métricas computadas de uma escala (baseline ou proposta)."""

    label: str
    store_codigo: str
    periodo_inicio: str
    periodo_fim: str
    employees_count: int
    shifts_count: int

    is_valid: bool
    violations_count: int
    warnings_count: int
    violations_by_artigo: dict[str, int]

    total_horas_trabalhadas: float
    horas_media_por_colab: float
    weekend_shifts_count: int  # sáb + dom

    cobertura_por_hora: dict[int, float]  # hora → média colab/dia operado
    cobertura_por_dow: dict[int, float]  # DOW (0=seg..6=dom) → média colab/dia

    # CUSTOS — calculados quando salary_by_employee_id + financial são fornecidos.
    # Se não fornecidos, ficam em Decimal("0") (visualmente "não computado").
    custo_folha_mensal: Decimal = Decimal("0")
    custo_passivos_estimados: Decimal = Decimal("0")
    custo_total_mensal: Decimal = Decimal("0")  # folha + passivos
    custo_anualizado: Decimal = Decimal("0")  # custo_total × 12


@dataclass
class ComparisonResult:
    """Resultado do compare: lado a lado + deltas."""

    baseline: ScheduleMetrics
    optimized: ScheduleMetrics

    delta_violations: int  # opt - base (negativo = melhor)
    delta_violations_pct: float  # % redução (positivo = melhor)
    delta_horas: float
    delta_horas_pct: float
    delta_shifts: int
    delta_weekend_shifts: int

    violations_artigos_removidos: list[str]  # apareciam na baseline, sumem na proposta
    violations_artigos_persistentes: list[str]  # aparecem em ambas
    violations_artigos_novos: list[str]  # só na proposta (idealmente vazio)

    cobertura_delta_por_hora: dict[int, float]  # opt - base por hora

    # CUSTOS (delta = opt - base; negativo = economia)
    delta_custo_folha: Decimal = Decimal("0")
    delta_custo_passivos: Decimal = Decimal("0")
    delta_custo_total_mes: Decimal = Decimal("0")
    delta_custo_anualizado: Decimal = Decimal("0")
    custo_computado: bool = False  # True se salary_by_employee_id foi fornecido

    @property
    def melhorou_clt(self) -> bool:
        """True se a otimizada tem MENOS violações que a baseline."""
        return self.delta_violations < 0

    @property
    def economia_passivos_anual(self) -> Decimal:
        """Quanto a empresa economiza por ano em passivos eliminados (positivo = boa)."""
        return -self.delta_custo_passivos * Decimal("12")


def compute_metrics(
    schedule: Schedule,
    label: str,
    clt_version: str = "2026-04",
    brand_rules_version: str = "",
    *,
    salary_by_employee_id: dict[str, Decimal] | None = None,
    salary_by_funcao: dict[str, Decimal] | None = None,
    financial: FinancialAssumptions | None = None,
) -> ScheduleMetrics:
    """Calcula métricas isoladas de uma escala (sem comparação).

    Args:
        salary_by_employee_id: mapping employee_id → salário bruto mensal.
            Quando fornecido (junto com `financial`), calcula custo_folha_mensal.
            Se ausente, custos ficam em Decimal("0").
        financial: encargos, VR/VT. Default = FinancialAssumptions() típica
            quando salary_by_employee_id é fornecido.
    """
    if not brand_rules_version:
        brand_rules_version = (
            "tfc-1.0.0" if schedule.brand == "tfc" else "track-field-1.0.0"
        )

    val = validate_clt(
        schedule=schedule,
        clt_version=clt_version,
        brand_rules_version=brand_rules_version,
    )
    violations_by_artigo = dict(Counter(v.artigo for v in val.violations))

    # Horas trabalhadas
    total_horas = 0.0
    for s in schedule.shifts:
        h_inicio = int(s.inicio.split(":")[0]) + int(s.inicio.split(":")[1]) / 60
        h_fim = int(s.fim.split(":")[0]) + int(s.fim.split(":")[1]) / 60
        duracao = h_fim - h_inicio
        if s.intrajornada_inicio and s.intrajornada_fim:
            ii = (
                int(s.intrajornada_inicio.split(":")[0])
                + int(s.intrajornada_inicio.split(":")[1]) / 60
            )
            iif = (
                int(s.intrajornada_fim.split(":")[0])
                + int(s.intrajornada_fim.split(":")[1]) / 60
            )
            duracao -= iif - ii
        total_horas += duracao

    n_emp = max(1, len(schedule.employees))
    horas_media = total_horas / n_emp

    # Weekend shifts
    wknd_count = 0
    for s in schedule.shifts:
        try:
            dow = date.fromisoformat(s.data).weekday()
            if dow in (5, 6):  # sáb, dom
                wknd_count += 1
        except (ValueError, AttributeError):
            pass

    # Cobertura por hora (média de colaboradores simultâneos)
    # Para cada (dia, hora), conta quantos colabs estão trabalhando
    hour_day_counts: dict[tuple[str, int], int] = defaultdict(int)
    for s in schedule.shifts:
        h_inicio = int(s.inicio.split(":")[0])
        h_fim = int(s.fim.split(":")[0])
        for h in range(h_inicio, h_fim):
            hour_day_counts[(s.data, h)] += 1

    cob_por_hora: dict[int, list[int]] = defaultdict(list)
    for (_data, hora), count in hour_day_counts.items():
        cob_por_hora[hora].append(count)
    cobertura_por_hora = {
        h: round(sum(vals) / len(vals), 2) for h, vals in cob_por_hora.items()
    }

    # Cobertura por DOW (média de colabs simultâneos no dia, ignorando hora)
    # Calcula # colabs únicos trabalhando por data, e tira média por DOW
    colabs_por_dia: dict[str, set] = defaultdict(set)
    for s in schedule.shifts:
        colabs_por_dia[s.data].add(s.employee_id)
    cob_dow: dict[int, list[int]] = defaultdict(list)
    for data_str, colabs in colabs_por_dia.items():
        try:
            dow = date.fromisoformat(data_str).weekday()
            cob_dow[dow].append(len(colabs))
        except (ValueError, AttributeError):
            pass
    cobertura_por_dow = {
        dow: round(sum(vals) / len(vals), 2) for dow, vals in cob_dow.items()
    }

    # CUSTOS — calcula folha quando há cadastro de salários disponível.
    # Estratégia de matching em 3 níveis (decrescente em confiança):
    #   1. employee_id direto (escalas onde IDs batem com cadastro)
    #   2. função (solver gera employee_ids sintéticos que não batem com
    #      cadastro do RH, mas a função bate — usamos salário médio da função)
    #   3. média geral do cadastro (último recurso)
    custo_folha = Decimal("0")
    custo_passivos = Decimal("0")
    if salary_by_employee_id:
        fin = financial or FinancialAssumptions()
        beneficios_mes = (fin.vr_dia + fin.vt_dia) * Decimal(fin.dias_uteis_mes)
        avg_geral = (
            sum(salary_by_employee_id.values()) / Decimal(len(salary_by_employee_id))
            if salary_by_employee_id else Decimal("0")
        )

        for emp in schedule.employees:
            salario = salary_by_employee_id.get(emp.employee_id)
            if salario is None and salary_by_funcao and emp.funcao:
                salario = salary_by_funcao.get(emp.funcao)
            if salario is None:
                salario = avg_geral  # último recurso
            if salario > 0:
                custo_folha += salario * (Decimal("1") + fin.encargos_pct) + beneficios_mes
        custo_folha = custo_folha.quantize(Decimal("0.01"))

    # Passivos: sempre calcula (não depende de salário)
    custo_passivos = (
        VALOR_PASSIVO_POR_VIOLACAO * Decimal(len(val.violations))
    ).quantize(Decimal("0.01"))
    custo_total = (custo_folha + custo_passivos).quantize(Decimal("0.01"))
    custo_anual = (custo_total * Decimal("12")).quantize(Decimal("0.01"))

    return ScheduleMetrics(
        label=label,
        store_codigo=schedule.store_codigo,
        periodo_inicio=schedule.periodo_inicio,
        periodo_fim=schedule.periodo_fim,
        employees_count=len(schedule.employees),
        shifts_count=len(schedule.shifts),
        is_valid=val.is_valid,
        violations_count=len(val.violations),
        warnings_count=len(val.warnings),
        violations_by_artigo=violations_by_artigo,
        total_horas_trabalhadas=round(total_horas, 1),
        horas_media_por_colab=round(horas_media, 1),
        weekend_shifts_count=wknd_count,
        cobertura_por_hora=cobertura_por_hora,
        cobertura_por_dow=cobertura_por_dow,
        custo_folha_mensal=custo_folha,
        custo_passivos_estimados=custo_passivos,
        custo_total_mensal=custo_total,
        custo_anualizado=custo_anual,
    )


def compare_schedules(
    baseline: Schedule,
    optimized: Schedule,
    *,
    baseline_label: str = "Escala atual (baseline)",
    optimized_label: str = "Escala otimizada (solver)",
    clt_version: str = "2026-04",
    salary_by_employee_id: dict[str, Decimal] | None = None,
    salary_by_funcao: dict[str, Decimal] | None = None,
    financial: FinancialAssumptions | None = None,
) -> ComparisonResult:
    """Compara duas escalas e retorna métricas + deltas.

    Quando salary_by_employee_id é fornecido (vindo do cadastro de employees
    importado), também computa delta de folha + passivos + anualização.

    salary_by_funcao é fallback usado quando employee_ids da escala (ex:
    solver gera sintéticos) não batem com o cadastro original.
    """
    base = compute_metrics(
        baseline, baseline_label, clt_version=clt_version,
        salary_by_employee_id=salary_by_employee_id,
        salary_by_funcao=salary_by_funcao,
        financial=financial,
    )
    opt = compute_metrics(
        optimized, optimized_label, clt_version=clt_version,
        salary_by_employee_id=salary_by_employee_id,
        salary_by_funcao=salary_by_funcao,
        financial=financial,
    )

    # Deltas
    delta_viol = opt.violations_count - base.violations_count
    delta_viol_pct = (
        -100.0 * delta_viol / base.violations_count
        if base.violations_count > 0
        else (0.0 if delta_viol == 0 else 100.0)
    )
    delta_horas = opt.total_horas_trabalhadas - base.total_horas_trabalhadas
    delta_horas_pct = (
        100.0 * delta_horas / base.total_horas_trabalhadas
        if base.total_horas_trabalhadas > 0
        else 0.0
    )

    # Por artigo
    artigos_base = set(base.violations_by_artigo.keys())
    artigos_opt = set(opt.violations_by_artigo.keys())
    removidos = sorted(artigos_base - artigos_opt)
    persistentes = sorted(artigos_base & artigos_opt)
    novos = sorted(artigos_opt - artigos_base)

    # Cobertura delta por hora
    horas_all = set(base.cobertura_por_hora.keys()) | set(opt.cobertura_por_hora.keys())
    cob_delta = {
        h: round(
            opt.cobertura_por_hora.get(h, 0.0) - base.cobertura_por_hora.get(h, 0.0), 2
        )
        for h in sorted(horas_all)
    }

    # Deltas de custo
    delta_folha = (opt.custo_folha_mensal - base.custo_folha_mensal).quantize(Decimal("0.01"))
    delta_passivos = (opt.custo_passivos_estimados - base.custo_passivos_estimados).quantize(Decimal("0.01"))
    delta_total_mes = (delta_folha + delta_passivos).quantize(Decimal("0.01"))
    delta_anual = (delta_total_mes * Decimal("12")).quantize(Decimal("0.01"))

    return ComparisonResult(
        baseline=base,
        optimized=opt,
        delta_violations=delta_viol,
        delta_violations_pct=round(delta_viol_pct, 1),
        delta_horas=round(delta_horas, 1),
        delta_horas_pct=round(delta_horas_pct, 1),
        delta_shifts=opt.shifts_count - base.shifts_count,
        delta_weekend_shifts=opt.weekend_shifts_count - base.weekend_shifts_count,
        violations_artigos_removidos=removidos,
        violations_artigos_persistentes=persistentes,
        violations_artigos_novos=novos,
        cobertura_delta_por_hora=cob_delta,
        delta_custo_folha=delta_folha,
        delta_custo_passivos=delta_passivos,
        delta_custo_total_mes=delta_total_mes,
        delta_custo_anualizado=delta_anual,
        custo_computado=salary_by_employee_id is not None,
    )
