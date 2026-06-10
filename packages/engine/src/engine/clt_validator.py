"""Validador CLT — verifica escalas contra a régua jurídica vigente.

Carrega a régua de `packages/clt-rules/config/clt-{version}.yaml` e valida
hard constraints. Quando regras de marca conflitam com CLT, **CLT vence**.

Cobertura atual:
- Art. 58 — jornada máxima diária
- Art. 66 — interjornada ≥11h
- Art. 67 + Lei 10.101 — DSR ≥24h consecutivas + ≥1 domingo/4 semanas
- Art. 71 — intrajornada
- Custom — sem mais de 6 dias seguidos sem folga
- Brand rule T&F — comissionado não folga sábado
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from engine.models import (
    Brand,
    CLTValidationResult,
    CLTViolation,
    Schedule,
    ScheduleEmployee,
    ScheduleShift,
)


# Path padrão dos YAMLs de régua.
# __file__ = .../packages/engine/src/engine/clt_validator.py
# parents[3] = .../packages/  →  + "clt-rules" + "config"
DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "clt-rules" / "config"


def validate_clt(
    schedule: Schedule,
    clt_version: str = "2026-04",
    brand_rules_version: str = "0.0.0",
    rules_path: Path | None = None,
) -> CLTValidationResult:
    """Valida uma escala contra a régua CLT.

    Args:
        schedule: escala completa de uma loja em um período.
        clt_version: versão da régua a aplicar.
        brand_rules_version: versão das regras de marca aplicadas.
        rules_path: pasta dos YAMLs (default: packages/clt-rules/config/).

    Returns:
        CLTValidationResult com lista de violações detectadas.
    """
    rules = _load_rules(clt_version, rules_path or DEFAULT_RULES_PATH)
    violations: list[CLTViolation] = []
    warnings: list[str] = []

    # Map employee_id → ScheduleEmployee (para regras de marca)
    employee_meta: dict[str, ScheduleEmployee] = {
        e.employee_id: e for e in schedule.employees
    }

    # Agrupar shifts por colaborador
    shifts_por_employee: dict[str, list[ScheduleShift]] = {}
    for shift in schedule.shifts:
        shifts_por_employee.setdefault(shift.employee_id, []).append(shift)

    for emp_id, shifts in shifts_por_employee.items():
        shifts_sorted = sorted(shifts, key=lambda s: (s.data, s.inicio))

        # Per-shift checks: Art. 58 e Art. 71
        for shift in shifts_sorted:
            violations.extend(_check_art_58(shift, emp_id, rules))
            violations.extend(_check_art_71(shift, emp_id, rules))

        # Pairwise checks: Art. 66 (interjornada)
        violations.extend(_check_art_66(shifts_sorted, emp_id, rules))

        # Per-employee aggregations: Art. 67, custom, brand rules
        violations.extend(_check_art_67_dsr(shifts_sorted, emp_id, schedule))
        violations.extend(_check_custom_max_dias_seguidos(shifts_sorted, emp_id, rules))
        violations.extend(
            _check_brand_comissionado_sabado(
                shifts_sorted, emp_id, schedule, employee_meta
            )
        )

    # Avisos globais
    if not schedule.employees:
        warnings.append(
            "Schedule sem `employees` populados — regras de marca "
            "(comissionado-sábado) não foram verificadas."
        )

    # Separa violações hard ('bad') das soft ('warn'). is_valid só considera hard.
    hard: list[CLTViolation] = []
    soft_msgs: list[str] = []
    for v in violations:
        if v.severidade == "warn":
            soft_msgs.append(
                f"{v.artigo} ({v.employee_id or '—'} {v.data or ''}): {v.descricao}"
            )
        else:
            hard.append(v)

    return CLTValidationResult(
        clt_version=clt_version,
        brand_rules_version=brand_rules_version,
        is_valid=len(hard) == 0,
        violations=hard,
        warnings=warnings + soft_msgs,
    )


# =============================================================================
# Art. 58 — Jornada normal ≤8h/dia
# =============================================================================
def _check_art_58(
    shift: ScheduleShift, emp_id: str, rules: dict
) -> list[CLTViolation]:
    duracao = _duracao_horas(shift.inicio, shift.fim)
    jornada_max = rules.get("art_58", {}).get("jornada_max_dia_horas", 8)
    if duracao <= jornada_max:
        return []
    return [
        CLTViolation(
            artigo="CLT Art. 58",
            severidade="bad",
            employee_id=emp_id,
            data=shift.data,
            descricao=(
                f"Jornada de {duracao:.1f}h excede o máximo legal "
                f"de {jornada_max}h sem hora extra acordada."
            ),
            sugestao_correcao=(
                "Reduzir o turno para 8h ou registrar como hora extra (Art. 59)."
            ),
        )
    ]


# =============================================================================
# Art. 71 — Intrajornada
# =============================================================================
def _check_art_71(
    shift: ScheduleShift, emp_id: str, rules: dict
) -> list[CLTViolation]:
    duracao = _duracao_horas(shift.inicio, shift.fim)
    cfg = rules.get("art_71", {}).get(
        "intrajornada_min_horas_se_jornada_maior_que",
        {"jornada": 6, "min": 1},
    )
    if duracao <= cfg["jornada"]:
        return []
    if not shift.intrajornada_inicio or not shift.intrajornada_fim:
        return [
            CLTViolation(
                artigo="CLT Art. 71",
                severidade="bad",
                employee_id=emp_id,
                data=shift.data,
                descricao=(
                    f"Jornada >{cfg['jornada']}h exige intrajornada de pelo "
                    f"menos {cfg['min']}h, não declarada."
                ),
                sugestao_correcao=(
                    f"Adicionar intrajornada com pelo menos {cfg['min']}h de pausa."
                ),
            )
        ]
    pausa = _duracao_horas(shift.intrajornada_inicio, shift.intrajornada_fim)
    if pausa < cfg["min"]:
        return [
            CLTViolation(
                artigo="CLT Art. 71",
                severidade="bad",
                employee_id=emp_id,
                data=shift.data,
                descricao=(
                    f"Intrajornada de {pausa:.2f}h é menor que o mínimo de {cfg['min']}h."
                ),
                sugestao_correcao=(
                    f"Estender pausa para no mínimo {cfg['min']}h."
                ),
            )
        ]
    return []


# =============================================================================
# Art. 66 — Interjornada ≥11h
# =============================================================================
def _check_art_66(
    shifts_sorted: list[ScheduleShift], emp_id: str, rules: dict
) -> list[CLTViolation]:
    interjornada_min = rules.get("art_66", {}).get("interjornada_min_horas", 11)
    out: list[CLTViolation] = []
    for i in range(len(shifts_sorted) - 1):
        curr, next_ = shifts_sorted[i], shifts_sorted[i + 1]
        if curr.data == next_.data:
            continue  # mesmo dia (caso raro): não conta interjornada
        fim_curr = datetime.fromisoformat(f"{curr.data}T{curr.fim}")
        inicio_next = datetime.fromisoformat(f"{next_.data}T{next_.inicio}")
        gap_horas = (inicio_next - fim_curr).total_seconds() / 3600
        if gap_horas < interjornada_min:
            out.append(
                CLTViolation(
                    artigo="CLT Art. 66",
                    severidade="bad",
                    employee_id=emp_id,
                    data=next_.data,
                    descricao=(
                        f"Interjornada de {gap_horas:.1f}h entre {curr.data} e "
                        f"{next_.data} é menor que o mínimo de {interjornada_min}h."
                    ),
                    sugestao_correcao=(
                        f"Adiar entrada do dia seguinte ou antecipar "
                        f"fechamento para garantir {interjornada_min}h."
                    ),
                )
            )
    return out


# =============================================================================
# Art. 67 + Lei 10.101 — DSR (24h consecutivas) e ≥1 domingo de folga / 4 semanas
# =============================================================================
def _check_art_67_dsr(
    shifts_sorted: list[ScheduleShift],
    emp_id: str,
    schedule: Schedule,
) -> list[CLTViolation]:
    """Valida DSR: cada semana ISO precisa ter pelo menos 1 dia inteiro folgado.
    Adicionalmente: pelo menos 1 domingo folgado a cada 4 semanas (Lei 10.101)."""
    out: list[CLTViolation] = []

    # Datas trabalhadas (set de strings ISO)
    datas_trabalhadas = {s.data for s in shifts_sorted}

    inicio = date.fromisoformat(schedule.periodo_inicio)
    fim = date.fromisoformat(schedule.periodo_fim)

    # 1. DSR semanal: cada semana ISO precisa ter ao menos 1 dia totalmente folgado
    semanas: dict[tuple[int, int], list[date]] = {}
    d = inicio
    while d <= fim:
        key = (d.isocalendar().year, d.isocalendar().week)
        semanas.setdefault(key, []).append(d)
        d += timedelta(days=1)

    for (iso_year, iso_week), dias in semanas.items():
        # Conta apenas semanas completas dentro do período (≥6 dias)
        if len(dias) < 6:
            continue
        folgou_algum_dia = any(dia.isoformat() not in datas_trabalhadas for dia in dias)
        if not folgou_algum_dia:
            out.append(
                CLTViolation(
                    artigo="CLT Art. 67",
                    severidade="bad",
                    employee_id=emp_id,
                    data=dias[0].isoformat(),
                    descricao=(
                        f"Semana ISO {iso_year}-W{iso_week:02d} sem nenhum dia "
                        f"de folga (DSR ≥24h obrigatório)."
                    ),
                    sugestao_correcao="Garantir pelo menos 1 dia de folga na semana.",
                )
            )

    # 2. Lei 10.101 — 1 domingo de folga a cada 4 semanas
    domingos = [
        inicio + timedelta(days=i)
        for i in range((fim - inicio).days + 1)
        if (inicio + timedelta(days=i)).weekday() == 6
    ]
    for janela_inicio in range(0, len(domingos), 4):
        janela = domingos[janela_inicio : janela_inicio + 4]
        if len(janela) < 4:
            continue  # janela incompleta, ignora
        folgou_algum_domingo = any(d.isoformat() not in datas_trabalhadas for d in janela)
        if not folgou_algum_domingo:
            out.append(
                CLTViolation(
                    artigo="Lei 10.101",
                    severidade="bad",
                    employee_id=emp_id,
                    data=janela[0].isoformat(),
                    descricao=(
                        f"Trabalhou em 4 domingos consecutivos ({janela[0]} a "
                        f"{janela[-1]}). Lei 10.101 exige ao menos 1 folga em domingo "
                        f"a cada 4 semanas."
                    ),
                    sugestao_correcao=(
                        "Folgar 1 domingo na janela de 4 semanas (rotação de domingos)."
                    ),
                )
            )

    return out


# =============================================================================
# Custom — sem mais de 6 dias seguidos sem folga
# =============================================================================
def _check_custom_max_dias_seguidos(
    shifts_sorted: list[ScheduleShift], emp_id: str, rules: dict
) -> list[CLTViolation]:
    max_dias = rules.get("custom", {}).get("dias_seguidos_sem_folga_max", 6)
    if not shifts_sorted:
        return []

    datas_trabalhadas = sorted({s.data for s in shifts_sorted})
    if not datas_trabalhadas:
        return []

    out: list[CLTViolation] = []
    streak_inicio = date.fromisoformat(datas_trabalhadas[0])
    streak_fim = streak_inicio
    for data_str in datas_trabalhadas[1:]:
        d = date.fromisoformat(data_str)
        if d == streak_fim + timedelta(days=1):
            streak_fim = d
        else:
            streak_dias = (streak_fim - streak_inicio).days + 1
            if streak_dias > max_dias:
                out.append(
                    _violation_streak(emp_id, streak_inicio, streak_fim, streak_dias, max_dias)
                )
            streak_inicio = d
            streak_fim = d

    # Último streak
    streak_dias = (streak_fim - streak_inicio).days + 1
    if streak_dias > max_dias:
        out.append(
            _violation_streak(emp_id, streak_inicio, streak_fim, streak_dias, max_dias)
        )

    return out


def _violation_streak(
    emp_id: str, inicio: date, fim: date, dias: int, max_dias: int
) -> CLTViolation:
    return CLTViolation(
        artigo="Custom (boas práticas)",
        severidade="warn",
        employee_id=emp_id,
        data=inicio.isoformat(),
        descricao=(
            f"Trabalhou {dias} dias seguidos ({inicio} a {fim}). "
            f"Limite recomendado: {max_dias} dias."
        ),
        sugestao_correcao="Inserir uma folga intermediária no streak.",
    )


# =============================================================================
# Brand rule T&F — comissionado não folga sábado
# =============================================================================
def _check_brand_comissionado_sabado(
    shifts_sorted: list[ScheduleShift],
    emp_id: str,
    schedule: Schedule,
    employee_meta: dict[str, ScheduleEmployee],
) -> list[CLTViolation]:
    """Comissionado T&F deve trabalhar todo sábado em que a loja opera."""
    if schedule.brand != "track_field":
        return []
    emp = employee_meta.get(emp_id)
    if not emp or not emp.comissionado:
        return []

    inicio = date.fromisoformat(schedule.periodo_inicio)
    fim = date.fromisoformat(schedule.periodo_fim)
    sabados = [
        inicio + timedelta(days=i)
        for i in range((fim - inicio).days + 1)
        if (inicio + timedelta(days=i)).weekday() == 5
    ]
    datas_trabalhadas = {s.data for s in shifts_sorted}

    out: list[CLTViolation] = []
    for sab in sabados:
        if sab.isoformat() not in datas_trabalhadas:
            out.append(
                CLTViolation(
                    artigo="Brand rule T&F",
                    severidade="bad",
                    employee_id=emp_id,
                    data=sab.isoformat(),
                    descricao=(
                        f"Comissionado T&F não trabalhou em {sab.isoformat()} (sábado). "
                        f"Vendedores comissionistas não folgam aos sábados — "
                        f"contrato e meta dependem disso."
                    ),
                    sugestao_correcao=(
                        "Realocar a folga deste colaborador para outro dia da "
                        "semana e escalar o sábado."
                    ),
                )
            )
    return out


# =============================================================================
# Helpers
# =============================================================================
def _duracao_horas(inicio: str, fim: str) -> float:
    """Duração em horas entre dois horários HH:MM.

    Trata turnos que cruzam a meia-noite: se o fim for menor ou igual ao
    início (ex: 22:00 → 02:00), assume que o fim é no dia seguinte e soma
    24h. Sem isso, turnos noturnos retornavam duração negativa e os checks
    de jornada (Art. 58/71) passavam com falso "OK".
    """
    h1, m1 = map(int, inicio.split(":"))
    h2, m2 = map(int, fim.split(":"))
    dur = (h2 - h1) + (m2 - m1) / 60
    if dur <= 0:
        dur += 24
    return dur


def _load_rules(version: str, rules_path: Path) -> dict:
    file = rules_path / f"clt-{version}.yaml"
    if not file.exists():
        raise FileNotFoundError(
            f"Régua CLT versão {version} não encontrada em {rules_path}. "
            f"Esperado: {file}"
        )
    with open(file, encoding="utf-8") as f:
        return yaml.safe_load(f)
