"""Geração de PDF do resultado da simulação.

Usa WeasyPrint (HTML+CSS → PDF). Mais bonito e flexível que ReportLab.
Note: WeasyPrint precisa de libs do sistema (pango, cairo). Em prod no Ubuntu,
o setup-vps.sh deve instalar:
    apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2

Em Windows local, pode falhar — nesse caso, pular geração de PDF em dev.
"""

from __future__ import annotations

import logging

from escala_freemium_api.schemas import SimulateResponse

logger = logging.getLogger(__name__)


def render_simulation_pdf(result: SimulateResponse) -> bytes | None:
    """Renderiza o resultado da simulação como PDF.

    Returns:
        Bytes do PDF, ou None se WeasyPrint não estiver disponível (dev sem libs).
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415  # import lazy
    except (ImportError, OSError) as e:
        logger.warning("WeasyPrint indisponível (%s) — pulando PDF", e)
        return None

    html = _build_html(result)
    return HTML(string=html).write_pdf()


def _build_html(r: SimulateResponse) -> str:
    """HTML do PDF. Tudo inline pra ser self-contained."""
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Simulação PEC 8/2025 — MudAção Escala</title>
  <style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: -apple-system, sans-serif; color: #1a1a1a; }}
    h1 {{ color: #0a4a3a; border-bottom: 3px solid #0a4a3a; padding-bottom: 8px; }}
    h2 {{ color: #0a4a3a; margin-top: 24px; }}
    .kpi {{ background: #f5f7f6; padding: 16px; border-left: 4px solid #0a4a3a;
            margin: 16px 0; }}
    .kpi .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
    .kpi .value {{ font-size: 28px; font-weight: 700; color: #0a4a3a; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
    th {{ background: #f5f7f6; font-weight: 600; }}
    .footer {{ margin-top: 32px; font-size: 11px; color: #999;
               border-top: 1px solid #e0e0e0; padding-top: 16px; }}
  </style>
</head>
<body>
  <h1>Simulação PEC 8/2025 — Impacto da escala 5x2</h1>
  <p><strong>{r.headline}</strong></p>

  <h2>KPIs principais</h2>
  <div class="kpi">
    <div class="label">Aumento de folha por mês (1 loja)</div>
    <div class="value">R$ {_brl(r.delta_folha_mes)}</div>
    <div>{r.delta_folha_pct:.1f}% acima do modelo 6x1 atual</div>
  </div>
  <div class="kpi">
    <div class="label">Aumento de folha por mês (rede de {r.n_lojas} lojas)</div>
    <div class="value">R$ {_brl(r.delta_folha_rede_mes)}</div>
    <div>R$ {_brl(r.delta_folha_rede_ano)} por ano</div>
  </div>

  <h2>FTEs (headcount)</h2>
  <table>
    <tr><th>Métrica</th><th>Valor</th></tr>
    <tr><td>FTEs hoje (6x1)</td><td>{r.fte_atual}</td></tr>
    <tr><td>FTEs necessários (5x2)</td><td>{r.fte_proposto}</td></tr>
    <tr><td>Contratações extras</td><td>{r.fte_extras_necessarios}</td></tr>
  </table>

  <h2>Comparação dos 3 cenários</h2>
  <table>
    <tr><th>Cenário</th><th>FTE</th><th>Folha</th><th>Δ %</th></tr>
    {_cenarios_rows(r)}
  </table>

  <h2>💡 Economia potencial com WFM</h2>
  <div class="kpi">
    <div class="label">Economia mensal estimada com Workforce Management</div>
    <div class="value">R$ {_brl(r.economia_potencial_wfm)}</div>
    <div>~{r.economia_potencial_wfm_pct}% da folha proposta — alocação inteligente</div>
  </div>

  <p>
    O Workforce Management baseado em IA aprende a curva de demanda da sua loja
    e aloca pessoas com maior precisão, reduzindo folha em 4 a 7%. Não substitui
    pessoas — coloca cada pessoa na hora certa.
  </p>

  <div class="footer">
    Gerado por MudAção Escala · simulaescala.mudacao.com.br · {_today()}<br>
    Hash de inputs: {r.inputs_hash}
  </div>
</body>
</html>
"""


def _brl(v) -> str:  # type: ignore[no-untyped-def]
    """Formata Decimal/float como BRL: 12345.67 → '12.345,67'."""
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _cenarios_rows(r: SimulateResponse) -> str:
    rows = []
    nomes = {"pessimista": "Pessimista", "neutro": "Neutro", "otimista": "Otimista"}
    for key, c in r.cenarios.items():
        rows.append(
            f"<tr><td>{nomes.get(key, key)}</td>"
            f"<td>{c.fte_total}</td>"
            f"<td>R$ {_brl(c.folha_total)}</td>"
            f"<td>{c.delta_folha_pct:.1f}%</td></tr>"
        )
    return "".join(rows)


def _today() -> str:
    from datetime import date

    return date.today().strftime("%d/%m/%Y")
