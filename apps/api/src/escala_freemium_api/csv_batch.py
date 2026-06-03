"""Batch CSV → consolidated .xlsx (Sprint 3 #4).

Parsing de CSV com 1 loja por linha + roda `run_simulation` em batch e
devolve planilha consolidada. Síncrono — limite 50 lojas por upload pra
evitar timeout (engine processa ~50ms/loja, 50 lojas = ~2.5s).

Template do CSV: ver `BATCH_CSV_TEMPLATE_HEADER` + `BATCH_CSV_TEMPLATE_SAMPLE`.
"""

from __future__ import annotations

import csv
import io
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from escala_freemium_api.schemas import SimulateRequest, SimulateResponse
from escala_freemium_api.simulation_adapter import run_simulation

logger = logging.getLogger(__name__)


MAX_LOJAS_POR_UPLOAD = 50


# Header esperado no CSV (case-sensitive, separador `,`)
BATCH_CSV_COLUMNS = [
    "nome_loja",
    "setor",
    "porte",
    "fte_atual",
    "salario_medio",
    "hora_abertura",
    "hora_fechamento",
    "sabado_fechado",
    "hora_abertura_sabado",
    "hora_fechamento_sabado",
    "domingo_fechado",
    "hora_abertura_domingo",
    "hora_fechamento_domingo",
    "cenario",
    "arredondamento_fte",
]


BATCH_CSV_TEMPLATE = (
    ",".join(BATCH_CSV_COLUMNS)
    + "\n"
    + "Loja Centro,varejo,M,5,3000.00,10,22,false,,,false,14,20,neutro,meio\n"
    + "Loja Shopping,varejo,M,8,3200.00,10,22,false,10,22,false,12,20,neutro,meio\n"
    + "Loja Bairro,food_service,P,3,2500.00,11,23,false,,,true,,,neutro,meio\n"
)


class BatchCsvError(Exception):
    """Erro estrutural no CSV (header faltando, encoding inválido)."""


class BatchRowError(Exception):
    """Erro em uma linha específica do CSV."""

    def __init__(self, line: int, msg: str) -> None:
        super().__init__(f"Linha {line}: {msg}")
        self.line = line
        self.msg = msg


def _coerce_bool(value: str) -> bool:
    v = (value or "").strip().lower()
    return v in {"true", "1", "sim", "yes", "y", "x"}


def _coerce_int_or_none(value: str) -> int | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError as e:
        raise ValueError(f"esperado inteiro, recebi '{value}'") from e


def _coerce_int(value: str, default: int | None = None) -> int:
    v = (value or "").strip()
    if not v and default is not None:
        return default
    try:
        return int(v)
    except ValueError as e:
        raise ValueError(f"esperado inteiro, recebi '{value}'") from e


def _coerce_decimal(value: str) -> Decimal:
    v = (value or "").strip().replace(",", ".")
    if not v:
        raise ValueError("salário médio é obrigatório")
    try:
        return Decimal(v)
    except InvalidOperation as e:
        raise ValueError(f"esperado decimal, recebi '{value}'") from e


def _row_to_request(row: dict[str, str], line: int) -> SimulateRequest:
    """Converte uma row do CSV em SimulateRequest validado."""
    try:
        # Boolean fields
        sabado_fechado = _coerce_bool(row.get("sabado_fechado", ""))
        domingo_fechado = _coerce_bool(row.get("domingo_fechado", ""))

        # Optional saturday/sunday hours (None se fechado)
        hora_ab_sab = None if sabado_fechado else _coerce_int_or_none(row.get("hora_abertura_sabado", ""))
        hora_fc_sab = None if sabado_fechado else _coerce_int_or_none(row.get("hora_fechamento_sabado", ""))
        hora_ab_dom = None if domingo_fechado else _coerce_int_or_none(row.get("hora_abertura_domingo", ""))
        hora_fc_dom = None if domingo_fechado else _coerce_int_or_none(row.get("hora_fechamento_domingo", ""))

        payload: dict[str, Any] = {
            "nome_loja": (row.get("nome_loja") or "").strip() or None,
            "setor": (row.get("setor") or "varejo").strip().lower(),
            "porte": (row.get("porte") or "M").strip().upper(),
            "fte_atual": _coerce_int(row.get("fte_atual", "")),
            "salario_medio": _coerce_decimal(row.get("salario_medio", "")),
            "hora_abertura": _coerce_int(row.get("hora_abertura", ""), default=10),
            "hora_fechamento": _coerce_int(row.get("hora_fechamento", ""), default=22),
            "sabado_fechado": sabado_fechado,
            "hora_abertura_sabado": hora_ab_sab,
            "hora_fechamento_sabado": hora_fc_sab,
            "domingo_fechado": domingo_fechado,
            "hora_abertura_domingo": hora_ab_dom,
            "hora_fechamento_domingo": hora_fc_dom,
            "cenario": (row.get("cenario") or "neutro").strip().lower(),
            "arredondamento_fte": (row.get("arredondamento_fte") or "meio").strip().lower(),
            "n_lojas_rede": 1,  # batch processa loja-a-loja, não rede
        }

        return SimulateRequest(**payload)

    except ValidationError as e:
        # Pega o primeiro erro pra mensagem amigável
        first = e.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", ()))
        raise BatchRowError(line, f"campo '{loc}' inválido — {first.get('msg', 'erro de validação')}") from e
    except ValueError as e:
        raise BatchRowError(line, str(e)) from e


def parse_batch_csv(content: bytes) -> list[SimulateRequest]:
    """Parseia bytes do CSV → lista de SimulateRequest validados.

    Lança BatchCsvError pra problema estrutural (encoding, header faltando)
    ou BatchRowError pra linha específica inválida — propaga primeira falha.
    """
    # Tenta utf-8 com BOM, depois latin-1 (Excel BR salva nesse)
    text: str | None = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise BatchCsvError("CSV com encoding inválido. Salve como UTF-8 ou Latin-1.")

    # Detecta separador (vírgula ou ponto-e-vírgula — Excel BR usa ;)
    sample = text[:2048]
    sep = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    if not reader.fieldnames:
        raise BatchCsvError("CSV vazio ou sem header.")

    # Normaliza fieldnames (trim + lowercase)
    fieldnames = [(f or "").strip().lower() for f in reader.fieldnames]

    # Valida colunas obrigatórias
    required = {"setor", "porte", "fte_atual", "salario_medio"}
    missing = required - set(fieldnames)
    if missing:
        raise BatchCsvError(
            f"Colunas obrigatórias faltando: {', '.join(sorted(missing))}. "
            f"Use o template (botão 'Baixar template')."
        )

    requests: list[SimulateRequest] = []
    for line, row in enumerate(reader, start=2):  # linha 1 é header
        # Normaliza keys (trim + lowercase)
        norm_row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}

        # Skip linhas vazias (Excel adiciona ; ; ; ; no fim)
        if not any(norm_row.values()):
            continue

        req = _row_to_request(norm_row, line)
        requests.append(req)

        if len(requests) > MAX_LOJAS_POR_UPLOAD:
            raise BatchCsvError(
                f"CSV excede limite de {MAX_LOJAS_POR_UPLOAD} lojas por upload. "
                f"Divida em mais arquivos."
            )

    if not requests:
        raise BatchCsvError("CSV sem linhas válidas — apenas o header foi encontrado.")

    return requests


def run_batch(
    requests: list[SimulateRequest],
    *,
    custom_financial: Any | None = None,
) -> list[tuple[str, SimulateRequest, SimulateResponse]]:
    """Roda run_simulation pra cada request. Falhas individuais propagam."""
    results: list[tuple[str, SimulateRequest, SimulateResponse]] = []
    for i, req in enumerate(requests, start=1):
        try:
            result = run_simulation(req, custom_financial=custom_financial)
        except Exception as e:
            logger.exception("Falha simulação batch loja %d", i)
            raise BatchRowError(
                i + 1,  # +1 pra match com linha do CSV (header é linha 1)
                f"falha ao simular '{req.nome_loja or f'linha {i + 1}'}': {e}",
            ) from e
        label = req.nome_loja or f"Loja {i}"
        results.append((label, req, result))
    return results
