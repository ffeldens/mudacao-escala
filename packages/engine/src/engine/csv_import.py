"""Parsers de CSV para carregar dados reais do cliente.

Três tipos de import:

1. **Cadastro de colaboradores** (RH)
   Colunas: employee_id, funcao, store_codigo, salario_medio, comissionado, ativo

2. **Histórico de vendas/cupons** (BI)
   Dois formatos suportados, auto-detectados pelas colunas:
   - Semana típica: dia_semana, hora, media_tickets, desvio_padrao
   - Histórico real: data, hora, tickets → agrega em media por (DOW, hora)

3. **Escala baseline** (estado atual antes da migração)
   Colunas: employee_id, data, inicio, fim, intrajornada_inicio, intrajornada_fim

Cada parser retorna (parsed: list, errors: list[str]). Erros NÃO levantam
exceção — são reportados linha a linha. Caller decide se ignora ou rejeita.

Princípio: tolerante a variações comuns (delimitador, BOM, encoding,
nomes de coluna em pt-BR ou en).
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from engine.models import (
    Brand,
    EmployeeRecord,
    Schedule,
    ScheduleEmployee,
    ScheduleShift,
    TicketHistoryPoint,
)


# =============================================================================
# Resultado padrão
# =============================================================================
@dataclass
class ImportResult:
    """Resultado de um parse de CSV."""

    parsed: list  # type depende do parser
    errors: list[str]
    warnings: list[str]
    rows_total: int
    rows_ok: int

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


# =============================================================================
# Helpers
# =============================================================================
def _normalize_key(key: str) -> str:
    """Normaliza nomes de coluna: lowercase, remove acentos, troca espaços."""
    table = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return key.strip().lower().translate(table).replace(" ", "_").replace("-", "_")


def _read_csv_rows(csv_text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Lê CSV e devolve (rows, errors). Auto-detecta delimitador.

    Filtra linhas comentário (começam com #) e linhas em branco. Tolera
    linhas com mais campos que o header (extras viram lista, normalizamos
    juntando com vírgula — útil quando user envia decimal BR com vírgula).
    """
    # Remove BOM se presente
    if csv_text.startswith("﻿"):
        csv_text = csv_text[1:]
    errors: list[str] = []

    # Filtra linhas-comentário (#) e em branco ANTES do parser CSV
    lines = [
        ln for ln in csv_text.split("\n")
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not lines:
        return [], errors
    cleaned = "\n".join(lines)

    # Sniff delimiter
    sample = cleaned[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(cleaned), dialect=dialect)
    rows = []
    for raw in reader:
        normalized: dict[str, str] = {}
        for k, v in raw.items():
            if k is None:
                continue  # campos extras (linha mais larga que header) — descarta
            if isinstance(v, list):
                # csv.DictReader devolve list para campos extras agrupados.
                # Aqui significa que a linha tinha mais campos que o header
                # (provavelmente decimal BR com vírgula). Junta de volta.
                v = ",".join(str(x) for x in v if x is not None)
            normalized[_normalize_key(k or "")] = (v or "").strip()
        rows.append(normalized)
    return rows, errors


def _parse_bool(s: str) -> bool:
    """Aceita 'sim/não', 'yes/no', 'true/false', '1/0', 's/n'."""
    s = s.strip().lower()
    return s in {"sim", "s", "yes", "y", "true", "t", "1", "verdadeiro", "v"}


def _parse_decimal(s: str) -> Decimal | None:
    """Decimal tolerante: aceita '2.200,50' ou '2200.50' ou '2200'."""
    s = s.strip().replace("R$", "").replace(" ", "")
    if not s:
        return None
    # Detecta formato BR (vírgula decimal) vs US (ponto decimal)
    if "," in s and "." in s:
        # Provável BR (1.234,56) ou US (1,234.56). Olha qual vem por último.
        if s.rindex(",") > s.rindex("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_iso_date(s: str) -> date | None:
    """Aceita ISO (2026-05-04) ou BR (04/05/2026)."""
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_hhmm(s: str) -> str | None:
    """Aceita '10:00', '10h00', '10', '10:00:00'. Retorna 'HH:MM'."""
    s = s.strip().lower().replace("h", ":").replace(".", ":")
    if not s:
        return None
    parts = s.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        if not (0 <= h <= 24 and 0 <= m < 60):
            return None
        return f"{h:02d}:{m:02d}"
    except (ValueError, IndexError):
        return None


# =============================================================================
# 1. Parser: Employees (cadastro de colaboradores)
# =============================================================================
def parse_employees_csv(csv_text: str) -> ImportResult:
    """Parse de CSV de cadastro de colaboradores.

    Colunas esperadas (case-insensitive, aceita acentos):
        employee_id (ou: codigo, matricula)
        funcao (ou: cargo)
        store_codigo (ou: loja, codigo_loja)
        salario_medio (ou: salario)
        comissionado (sim/nao) — opcional
        ativo (sim/nao) — opcional, default true
        data_admissao — opcional
    """
    rows, _ = _read_csv_rows(csv_text)
    parsed: list[EmployeeRecord] = []
    errors: list[str] = []
    warnings: list[str] = []

    aliases = {
        "employee_id": ["employee_id", "codigo", "matricula", "id", "id_colaborador"],
        "funcao": ["funcao", "cargo"],
        "store_codigo": ["store_codigo", "loja", "codigo_loja", "loja_codigo"],
        "salario_medio": ["salario_medio", "salario", "sal_medio"],
        "comissionado": ["comissionado", "comissionista"],
        "ativo": ["ativo", "status"],
        "data_admissao": ["data_admissao", "admissao", "data_entrada"],
    }

    def pick(row: dict, field: str) -> str:
        for alias in aliases[field]:
            v = row.get(alias)
            if v is not None and v != "":
                return v
        return ""

    for line_n, row in enumerate(rows, start=2):  # linha 1 é header
        try:
            emp_id = pick(row, "employee_id")
            funcao = pick(row, "funcao")
            store = pick(row, "store_codigo")
            sal_raw = pick(row, "salario_medio")
            if not emp_id or not funcao or not store:
                errors.append(
                    f"Linha {line_n}: faltam campos obrigatórios "
                    f"(employee_id={emp_id!r}, funcao={funcao!r}, store_codigo={store!r})"
                )
                continue
            sal = _parse_decimal(sal_raw)
            if sal is None or sal <= 0:
                errors.append(f"Linha {line_n} ({emp_id}): salario_medio inválido: {sal_raw!r}")
                continue

            rec = EmployeeRecord(
                employee_id=emp_id,
                funcao=funcao,
                store_codigo=store,
                salario_medio=sal,
                comissionado=_parse_bool(pick(row, "comissionado")),
                ativo=_parse_bool(pick(row, "ativo")) if pick(row, "ativo") else True,
                data_admissao=pick(row, "data_admissao") or None,
            )
            parsed.append(rec)
        except Exception as e:  # pragma: no cover (defesa final)
            errors.append(f"Linha {line_n}: erro inesperado: {e}")

    # Duplicate employee_id check
    seen: dict[str, int] = {}
    for i, rec in enumerate(parsed):
        if rec.employee_id in seen:
            warnings.append(
                f"employee_id duplicado: {rec.employee_id} "
                f"(linhas {seen[rec.employee_id]} e {i + 2})"
            )
        else:
            seen[rec.employee_id] = i + 2

    return ImportResult(
        parsed=parsed,
        errors=errors,
        warnings=warnings,
        rows_total=len(rows),
        rows_ok=len(parsed),
    )


# =============================================================================
# 2. Parser: Sales history (auto-detecta formato semana-típica vs histórico real)
# =============================================================================
def parse_sales_history_csv(csv_text: str) -> ImportResult:
    """Parse de CSV de vendas/cupons. Auto-detecta dois formatos:

    Formato A — semana típica (perfil pré-agregado):
        Colunas: dia_semana (0-6), hora (0-23), media_tickets, desvio_padrao

    Formato B — histórico real (agrega em semana típica):
        Colunas: data (YYYY-MM-DD ou DD/MM/YYYY), hora (0-23), tickets

    Retorna list[TicketHistoryPoint] em ambos os casos.
    """
    rows, _ = _read_csv_rows(csv_text)
    errors: list[str] = []
    warnings: list[str] = []

    if not rows:
        return ImportResult(
            parsed=[], errors=["CSV vazio"], warnings=[], rows_total=0, rows_ok=0
        )

    # Detecta formato pelos nomes de coluna
    cols = set(rows[0].keys())
    has_data = "data" in cols or "date" in cols
    has_dia_semana = "dia_semana" in cols or "dow" in cols or "weekday" in cols
    has_media = "media_tickets" in cols or "tickets_medio" in cols

    if has_dia_semana and has_media:
        formato = "semana_tipica"
    elif has_data:
        formato = "historico_real"
    else:
        return ImportResult(
            parsed=[],
            errors=[
                "CSV não reconhecido. Use colunas (dia_semana, hora, media_tickets) "
                "ou (data, hora, tickets)."
            ],
            warnings=[],
            rows_total=len(rows),
            rows_ok=0,
        )

    if formato == "semana_tipica":
        return _parse_sales_semana_tipica(rows, errors, warnings)
    else:
        return _parse_sales_historico_real(rows, errors, warnings)


def _parse_sales_semana_tipica(
    rows: list[dict], errors: list[str], warnings: list[str]
) -> ImportResult:
    parsed: list[TicketHistoryPoint] = []
    for line_n, row in enumerate(rows, start=2):
        try:
            dow_s = row.get("dia_semana") or row.get("dow") or row.get("weekday") or ""
            hora_s = row.get("hora") or row.get("hour") or ""
            media_s = row.get("media_tickets") or row.get("tickets_medio") or ""
            desvio_s = row.get("desvio_padrao") or row.get("desvio") or "0"

            dow = int(dow_s)
            hora = int(hora_s)
            if not (0 <= dow <= 6 and 0 <= hora <= 23):
                errors.append(
                    f"Linha {line_n}: dia_semana={dow}, hora={hora} fora dos limites (0-6, 0-23)"
                )
                continue
            media = _parse_decimal(media_s) or Decimal("0")
            desvio = _parse_decimal(desvio_s) or Decimal("0")
            parsed.append(
                TicketHistoryPoint(
                    dia_semana=dow, hora=hora, media_tickets=media, desvio_padrao=desvio
                )
            )
        except (ValueError, TypeError) as e:
            errors.append(f"Linha {line_n}: {e}")

    return ImportResult(
        parsed=parsed,
        errors=errors,
        warnings=warnings,
        rows_total=len(rows),
        rows_ok=len(parsed),
    )


def _parse_sales_historico_real(
    rows: list[dict], errors: list[str], warnings: list[str]
) -> ImportResult:
    """Agrega histórico real (date × hora × tickets) em semana típica
    (dia_semana × hora × media)."""
    bucket: dict[tuple[int, int], list[Decimal]] = defaultdict(list)

    for line_n, row in enumerate(rows, start=2):
        data_s = row.get("data") or row.get("date") or ""
        hora_s = row.get("hora") or row.get("hour") or ""
        tickets_s = row.get("tickets") or row.get("cupons") or ""
        d = _parse_iso_date(data_s)
        if d is None:
            errors.append(f"Linha {line_n}: data inválida: {data_s!r}")
            continue
        try:
            hora = int(hora_s)
            if not (0 <= hora <= 23):
                errors.append(f"Linha {line_n}: hora fora dos limites: {hora}")
                continue
            tickets = _parse_decimal(tickets_s)
            if tickets is None:
                errors.append(f"Linha {line_n}: tickets inválido: {tickets_s!r}")
                continue
            bucket[(d.weekday(), hora)].append(tickets)
        except (ValueError, TypeError) as e:
            errors.append(f"Linha {line_n}: {e}")

    # Agrega
    parsed: list[TicketHistoryPoint] = []
    for (dow, hora), valores in sorted(bucket.items()):
        n = len(valores)
        media = sum(valores) / Decimal(n)
        # Desvio padrão amostral simples
        if n > 1:
            var = sum((v - media) ** 2 for v in valores) / Decimal(n - 1)
            desvio = var.sqrt() if hasattr(var, "sqrt") else Decimal(str(float(var) ** 0.5))
        else:
            desvio = Decimal("0")
        parsed.append(
            TicketHistoryPoint(
                dia_semana=dow,
                hora=hora,
                media_tickets=media.quantize(Decimal("0.01")),
                desvio_padrao=desvio.quantize(Decimal("0.01")),
            )
        )

    if not parsed and not errors:
        warnings.append("Nenhuma linha válida foi agregada.")

    return ImportResult(
        parsed=parsed,
        errors=errors,
        warnings=warnings,
        rows_total=len(rows),
        rows_ok=sum(len(v) for v in bucket.values()),
    )


# =============================================================================
# 3. Parser: Schedule baseline (escala atual)
# =============================================================================
def parse_schedule_baseline_csv(
    csv_text: str, store_codigo: str, brand: Brand
) -> ImportResult:
    """Parse de CSV de escala atual da loja.

    Colunas: employee_id, data, inicio, fim, intrajornada_inicio (opc),
             intrajornada_fim (opc).

    Retorna parsed = [Schedule] (lista de 1 item) ou [] se houver erro grave.
    """
    rows, _ = _read_csv_rows(csv_text)
    errors: list[str] = []
    warnings: list[str] = []

    if not rows:
        return ImportResult(
            parsed=[],
            errors=["CSV vazio"],
            warnings=[],
            rows_total=0,
            rows_ok=0,
        )

    shifts: list[ScheduleShift] = []
    employee_funcoes: dict[str, str] = {}  # vai sair vazio se CSV não tem 'funcao'
    has_funcao_col = "funcao" in rows[0] or "cargo" in rows[0]
    min_date: date | None = None
    max_date: date | None = None
    employee_ids: set[str] = set()

    for line_n, row in enumerate(rows, start=2):
        emp_id = (row.get("employee_id") or row.get("codigo") or row.get("matricula") or "").strip()
        data_s = (row.get("data") or row.get("date") or "").strip()
        inicio_s = (row.get("inicio") or row.get("entrada") or row.get("start") or "").strip()
        fim_s = (row.get("fim") or row.get("saida") or row.get("end") or "").strip()

        if not emp_id or not data_s or not inicio_s or not fim_s:
            errors.append(
                f"Linha {line_n}: faltam campos obrigatórios "
                f"(employee_id, data, inicio, fim)"
            )
            continue

        d = _parse_iso_date(data_s)
        if d is None:
            errors.append(f"Linha {line_n}: data inválida: {data_s!r}")
            continue

        inicio = _parse_time_hhmm(inicio_s)
        fim = _parse_time_hhmm(fim_s)
        if inicio is None or fim is None:
            errors.append(f"Linha {line_n}: horário inválido (inicio={inicio_s!r}, fim={fim_s!r})")
            continue

        intra_inicio = _parse_time_hhmm(
            row.get("intrajornada_inicio") or row.get("intervalo_inicio") or ""
        )
        intra_fim = _parse_time_hhmm(
            row.get("intrajornada_fim") or row.get("intervalo_fim") or ""
        )

        shifts.append(
            ScheduleShift(
                employee_id=emp_id,
                employee_nome=emp_id,
                data=d.isoformat(),
                inicio=inicio,
                fim=fim,
                intrajornada_inicio=intra_inicio,
                intrajornada_fim=intra_fim,
            )
        )

        employee_ids.add(emp_id)
        if has_funcao_col:
            funcao = (row.get("funcao") or row.get("cargo") or "").strip()
            if funcao:
                employee_funcoes[emp_id] = funcao
        min_date = d if min_date is None or d < min_date else min_date
        max_date = d if max_date is None or d > max_date else max_date

    if not shifts:
        return ImportResult(
            parsed=[],
            errors=errors or ["Nenhum shift válido"],
            warnings=warnings,
            rows_total=len(rows),
            rows_ok=0,
        )

    # Constrói lista de employees (sem comissionado info — vem do cadastro)
    employees = [
        ScheduleEmployee(
            employee_id=eid,
            funcao=employee_funcoes.get(eid, "Desconhecida"),
            comissionado=False,  # cruzar com cadastro de RH em pos-processing
        )
        for eid in sorted(employee_ids)
    ]
    if not has_funcao_col:
        warnings.append(
            "CSV não tem coluna 'funcao'. Funções marcadas como 'Desconhecida'. "
            "Considere cruzar com o cadastro de colaboradores depois."
        )

    schedule = Schedule(
        store_codigo=store_codigo,
        brand=brand,
        periodo_inicio=(min_date or date.today()).isoformat(),
        periodo_fim=(max_date or date.today()).isoformat(),
        employees=employees,
        shifts=shifts,
    )

    return ImportResult(
        parsed=[schedule],
        errors=errors,
        warnings=warnings,
        rows_total=len(rows),
        rows_ok=len(shifts),
    )


# =============================================================================
# Templates CSV (download)
# =============================================================================
TEMPLATES: dict[str, str] = {
    "employees": (
        "employee_id,funcao,store_codigo,salario_medio,comissionado,ativo,data_admissao\n"
        "TF-SP-JK-001-V-01,Vendedor,TF-SP-JK-001,2200.00,sim,sim,2023-03-15\n"
        "TF-SP-JK-001-V-02,Vendedor,TF-SP-JK-001,2350.00,sim,sim,2022-08-10\n"
        "TF-SP-JK-001-C-01,Caixa,TF-SP-JK-001,2000.00,nao,sim,2024-01-20\n"
        "TF-SP-JK-001-G-01,Gerencia,TF-SP-JK-001,5500.00,nao,sim,2021-04-01\n"
    ),
    "sales_history_semana_tipica": (
        "dia_semana,hora,media_tickets,desvio_padrao\n"
        "0,10,12.5,2.1\n"
        "0,11,15.3,2.8\n"
        "0,12,20.0,3.5\n"
        "0,13,18.5,3.2\n"
        "0,14,22.0,4.0\n"
        "# dia_semana: 0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sab, 6=dom\n"
    ),
    "sales_history_real": (
        "data,hora,tickets\n"
        "2026-04-01,10,12\n"
        "2026-04-01,11,15\n"
        "2026-04-01,12,21\n"
        "2026-04-01,13,18\n"
        "2026-04-02,10,14\n"
        "2026-04-02,11,17\n"
    ),
    "schedule_baseline": (
        "employee_id,funcao,data,inicio,fim,intrajornada_inicio,intrajornada_fim\n"
        "TF-SP-JK-001-V-01,Vendedor,2026-04-01,10:00,18:00,13:00,14:00\n"
        "TF-SP-JK-001-V-01,Vendedor,2026-04-02,10:00,18:00,13:00,14:00\n"
        "TF-SP-JK-001-V-02,Vendedor,2026-04-01,14:00,22:00,17:00,18:00\n"
        "TF-SP-JK-001-C-01,Caixa,2026-04-01,10:00,18:00,13:00,14:00\n"
    ),
}
