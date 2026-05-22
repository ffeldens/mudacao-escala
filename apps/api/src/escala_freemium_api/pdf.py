"""Geração de PDF do resultado da simulação.

Usa WeasyPrint (HTML+CSS → PDF). Em Windows local, libs podem faltar e
o import falha — nesse caso retornamos None e o email vai sem anexo (graceful).
"""

from __future__ import annotations

import logging
from datetime import date

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
    try:
        return HTML(string=html).write_pdf()
    except Exception:
        logger.exception("Falha ao renderizar PDF")
        return None


# =============================================================================
# HTML do PDF
# =============================================================================


def _build_html(r: SimulateResponse) -> str:
    """HTML completo do PDF — tudo inline."""
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Simulação PEC 8/2025 — MudAção Escala</title>
  {_css()}
</head>
<body>
  {_cover(r)}
  <div class="page-break"></div>
  {_kpis(r)}
  {_cenarios(r)}
  {_fte_section(r)}
  {_wfm_section(r)}
  {_inputs_recap(r)}
  {_footer(r)}
</body>
</html>
"""


def _css() -> str:
    return """\
<style>
  @page {
    size: A4;
    margin: 18mm 16mm;
    @bottom-center {
      content: "MudAção Escala · simulaescala.mudacao.com.br · página " counter(page) " de " counter(pages);
      font-size: 9pt;
      color: #94a3b8;
    }
  }
  body {
    font-family: -apple-system, "Segoe UI", sans-serif;
    color: #1a1a1a;
    font-size: 11pt;
    line-height: 1.5;
  }
  h1 { color: #062920; font-size: 24pt; margin: 0 0 4pt; }
  h2 { color: #0a4a3a; font-size: 16pt; margin: 24pt 0 8pt;
       border-bottom: 2pt solid #0a4a3a; padding-bottom: 4pt; }
  h3 { color: #0a4a3a; font-size: 13pt; margin: 16pt 0 6pt; }

  .page-break { page-break-after: always; }

  .cover {
    background: linear-gradient(135deg, #062920 0%, #0a4a3a 100%);
    color: #fff;
    padding: 32pt 28pt;
    border-radius: 12pt;
    margin: 0 0 24pt;
  }
  .cover .label {
    font-size: 10pt;
    letter-spacing: 2pt;
    text-transform: uppercase;
    color: #b8dcc8;
    margin: 0 0 8pt;
  }
  .cover h1 { color: #fff; font-size: 28pt; margin: 0; line-height: 1.15; }
  .cover .subtitle {
    margin: 16pt 0 0;
    color: #b8dcc8;
    font-size: 12pt;
  }

  .kpi-grid {
    display: table;
    width: 100%;
    border-collapse: separate;
    border-spacing: 8pt;
    margin: 0 -8pt 16pt;
  }
  .kpi {
    display: table-cell;
    background: #f5f7f6;
    border-left: 4pt solid #0a4a3a;
    padding: 12pt;
    border-radius: 0 8pt 8pt 0;
    vertical-align: top;
    width: 33%;
  }
  .kpi.accent { background: #0a4a3a; color: #fff; border-color: #b8dcc8; }
  .kpi.accent .kpi-label { color: #b8dcc8; }
  .kpi-label {
    font-size: 9pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1pt;
    margin: 0;
  }
  .kpi-value {
    font-size: 18pt;
    font-weight: 700;
    color: #062920;
    margin: 6pt 0 0;
  }
  .kpi.accent .kpi-value { color: #fff; }
  .kpi-sub { font-size: 9pt; color: #64748b; margin: 4pt 0 0; }
  .kpi.accent .kpi-sub { color: #dbeee4; }

  table.data {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 16pt;
    font-size: 10pt;
  }
  table.data th {
    background: #0a4a3a;
    color: #fff;
    text-align: left;
    padding: 8pt;
    font-weight: 600;
  }
  table.data td {
    padding: 8pt;
    border-bottom: 1pt solid #e2e8f0;
  }
  table.data tr:nth-child(even) td { background: #f8fafc; }

  .callout {
    background: #dbeee4;
    border-left: 4pt solid #0a4a3a;
    padding: 12pt 16pt;
    margin: 16pt 0;
    border-radius: 0 6pt 6pt 0;
  }
  .callout-title {
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 1pt;
    color: #0a4a3a;
    font-weight: 700;
    margin: 0 0 4pt;
  }
  .callout-value {
    font-size: 22pt;
    color: #062920;
    font-weight: 700;
    margin: 0 0 4pt;
  }

  ul { margin: 0 0 12pt; padding-left: 18pt; }
  li { margin: 0 0 4pt; }

  .hash {
    font-family: monospace;
    color: #94a3b8;
    font-size: 9pt;
  }

  .footer-block {
    margin-top: 28pt;
    padding-top: 12pt;
    border-top: 1pt solid #e2e8f0;
    color: #94a3b8;
    font-size: 9pt;
  }
</style>
"""


def _cover(r: SimulateResponse) -> str:
    today = date.today().strftime("%d/%m/%Y")
    return f"""\
<div class="cover">
  <p class="label">MudAção Escala · Simulador PEC 8/2025</p>
  <h1>{r.headline}</h1>
  <p class="subtitle">Análise gerada em {today} · Cenário neutro (premissa Fitch)</p>
</div>
"""


def _kpis(r: SimulateResponse) -> str:
    return f"""\
<h2>Resumo executivo</h2>
<p>
  Os números abaixo refletem o impacto da migração da escala 6x1 (44h/semana)
  para 5x2 (40h/semana) na sua rede de <strong>{r.n_lojas} loja(s)</strong>,
  considerando os parâmetros que você informou.
</p>

<div class="kpi-grid">
  <div class="kpi accent">
    <p class="kpi-label">Aumento mensal (rede)</p>
    <p class="kpi-value">{_brl(r.delta_folha_rede_mes)}</p>
    <p class="kpi-sub">+{_pct(r.delta_folha_pct)} acima da folha atual</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">Impacto em 1 ano</p>
    <p class="kpi-value">{_brl(r.delta_folha_rede_ano)}</p>
    <p class="kpi-sub">{_brl(r.delta_folha_rede_mes)} × 12</p>
  </div>
  <div class="kpi">
    <p class="kpi-label">FTEs extras</p>
    <p class="kpi-value">+{_dec(r.fte_extras_necessarios)}</p>
    <p class="kpi-sub">por loja</p>
  </div>
</div>

<h3>Por loja</h3>
<table class="data">
  <tr><th>Métrica</th><th style="text-align:right">Valor</th></tr>
  <tr><td>Folha atual (6x1)</td><td style="text-align:right">{_brl(r.folha_atual_mes)}</td></tr>
  <tr><td>Folha proposta (5x2)</td><td style="text-align:right">{_brl(r.folha_proposta_mes)}</td></tr>
  <tr><td><strong>Diferença mensal</strong></td>
      <td style="text-align:right"><strong>{_brl(r.delta_folha_mes)} (+{_pct(r.delta_folha_pct)})</strong></td></tr>
</table>
"""


def _cenarios(r: SimulateResponse) -> str:
    nomes = {"pessimista": "Pessimista", "neutro": "Neutro", "otimista": "Otimista"}
    descricoes = {
        "pessimista": "Sem ganho de produtividade — pior caso",
        "neutro": "Premissa padrão (estudo Fitch)",
        "otimista": "Com WFM bem implementado",
    }
    rows = []
    for key in ("pessimista", "neutro", "otimista"):
        c = r.cenarios[key]
        rows.append(
            f"<tr><td><strong>{nomes[key]}</strong><br>"
            f"<span style='color:#64748b;font-size:9pt'>{descricoes[key]}</span></td>"
            f"<td style='text-align:right'>{_dec(c.fte_total)}</td>"
            f"<td style='text-align:right'>{_brl(c.folha_total)}</td>"
            f"<td style='text-align:right'>{_signal(c.delta_folha_pct)}</td></tr>"
        )

    chart_svg = _cenarios_chart_svg(r)

    return f"""\
<h2>Comparação dos 3 cenários</h2>
<p>
  O simulador roda 3 cenários simultaneamente, variando o fator de produtividade
  esperado. O cenário <strong>neutro</strong> usa a premissa do estudo Fitch
  (8-14% de impacto). Pessimista assume zero ganho; otimista assume WFM
  bem implementado recuperando produtividade.
</p>

{chart_svg}

<table class="data">
  <tr><th>Cenário</th><th style="text-align:right">FTE</th>
      <th style="text-align:right">Folha/mês</th>
      <th style="text-align:right">Δ vs hoje</th></tr>
  {"".join(rows)}
</table>
"""


def _cenarios_chart_svg(r: SimulateResponse) -> str:
    """Gera um bar chart SVG inline dos 3 cenários + linha da folha atual.

    SVG é renderizado nativamente pelo WeasyPrint, mantém-se vetorial no PDF
    (sem precisar de matplotlib ou Pillow).
    """
    folha_atual = float(r.folha_atual_mes)
    cenarios = [
        ("Pessimista", float(r.cenarios["pessimista"].folha_total),
         float(r.cenarios["pessimista"].delta_folha_pct), "#dc2626"),
        ("Neutro", float(r.cenarios["neutro"].folha_total),
         float(r.cenarios["neutro"].delta_folha_pct), "#0a4a3a"),
        ("Otimista", float(r.cenarios["otimista"].folha_total),
         float(r.cenarios["otimista"].delta_folha_pct), "#5ea27f"),
    ]

    # Dimensões do SVG (em px lógicos)
    width = 520
    height = 220
    margin_top = 28
    margin_bottom = 40
    margin_left = 70
    margin_right = 20
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # Domínio
    max_val = max(*(c[1] for c in cenarios), folha_atual) * 1.15

    # Geometria das barras
    bar_w = 80
    gap = (plot_w - bar_w * 3) / 4

    bars_svg = []
    for i, (nome, folha, delta_pct, color) in enumerate(cenarios):
        x = margin_left + gap + i * (bar_w + gap)
        bar_h = (folha / max_val) * plot_h
        y = margin_top + (plot_h - bar_h)

        # Label do delta % no topo da barra
        delta_txt = f"+{delta_pct:.1f}%" if delta_pct >= 0 else f"{delta_pct:.1f}%"
        delta_color = "#dc2626" if delta_pct > 0 else "#15803d" if delta_pct < 0 else "#64748b"

        bars_svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="{color}" rx="6" />'
            # Delta % acima da barra
            f'<text x="{x + bar_w / 2}" y="{y - 8}" text-anchor="middle" '
            f'font-size="11" font-weight="700" fill="{delta_color}">{delta_txt}</text>'
            # Nome do cenário abaixo
            f'<text x="{x + bar_w / 2}" y="{margin_top + plot_h + 16}" '
            f'text-anchor="middle" font-size="11" font-weight="600" '
            f'fill="#475569">{nome}</text>'
            # Valor abaixo do nome
            f'<text x="{x + bar_w / 2}" y="{margin_top + plot_h + 30}" '
            f'text-anchor="middle" font-size="9" fill="#94a3b8">{_brl_short(folha)}</text>'
        )

    # Linha de referência da folha atual
    ref_y = margin_top + (plot_h - (folha_atual / max_val) * plot_h)
    ref_line = (
        f'<line x1="{margin_left}" y1="{ref_y}" x2="{width - margin_right}" '
        f'y2="{ref_y}" stroke="#64748b" stroke-width="1" stroke-dasharray="4 3" />'
        f'<text x="{width - margin_right - 4}" y="{ref_y - 4}" text-anchor="end" '
        f'font-size="9" fill="#64748b" font-style="italic">'
        f'Folha atual: {_brl_short(folha_atual)}</text>'
    )

    # Eixo Y (3 ticks: 0, max/2, max)
    y_ticks_svg = []
    for tick_val in (0, max_val / 2, max_val):
        ty = margin_top + (plot_h - (tick_val / max_val) * plot_h)
        y_ticks_svg.append(
            f'<text x="{margin_left - 8}" y="{ty + 3}" text-anchor="end" '
            f'font-size="9" fill="#94a3b8">{_brl_short(tick_val)}</text>'
            f'<line x1="{margin_left}" y1="{ty}" x2="{width - margin_right}" '
            f'y2="{ty}" stroke="#e2e8f0" stroke-width="0.5" />'
        )

    return f"""\
<div style="margin: 12pt 0 8pt;">
<svg width="100%" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg"
     style="background:#f8fafc;border-radius:6pt;font-family:sans-serif;">
  {"".join(y_ticks_svg)}
  {ref_line}
  {"".join(bars_svg)}
</svg>
</div>
"""


def _brl_short(v: float) -> str:
    """Formata BRL compacto: 267638 → 'R$ 268 mil', 3211656 → 'R$ 3,2 mi'."""
    if v >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f} mi".replace(".", ",")
    if v >= 1_000:
        return f"R$ {v / 1_000:.0f} mil"
    return f"R$ {v:.0f}"


def _fte_section(r: SimulateResponse) -> str:
    extras_rede = float(r.fte_extras_necessarios) * r.n_lojas
    return f"""\
<h2>Impacto em headcount</h2>
<table class="data">
  <tr><th>Métrica</th><th style="text-align:right">Valor</th></tr>
  <tr><td>FTEs hoje (6x1) — por loja</td><td style="text-align:right">{_dec(r.fte_atual)}</td></tr>
  <tr><td>FTEs necessários (5x2) — por loja</td><td style="text-align:right">{_dec(r.fte_proposto)}</td></tr>
  <tr><td><strong>Contratações extras por loja</strong></td>
      <td style="text-align:right"><strong>+{_dec(r.fte_extras_necessarios)}</strong></td></tr>
  <tr><td><strong>Contratações extras na rede ({r.n_lojas} lojas)</strong></td>
      <td style="text-align:right"><strong>+{extras_rede:.1f}</strong></td></tr>
</table>

<h3>Alternativas pra reduzir contratações</h3>
<ul>
  <li><strong>Multifunção</strong>: ampliar o escopo (caixa+venda+estoque) reduz FTEs cruzados</li>
  <li><strong>Mix com horistas regulamentados</strong>: 60-70% CLT + horistas pra cobrir picos</li>
  <li><strong>WFM com IA</strong>: ajusta alocação por curva de demanda real (4-7% de economia)</li>
  <li><strong>Piloto em 3 lojas representativas</strong>: testa antes do rollout pra recalibrar</li>
</ul>
"""


def _wfm_section(r: SimulateResponse) -> str:
    return f"""\
<h2>💡 Economia potencial com Workforce Management</h2>
<div class="callout">
  <p class="callout-title">Com escala inteligente, sua rede pode economizar</p>
  <p class="callout-value">{_brl(r.economia_potencial_wfm)} / mês</p>
  <p style="margin:0;font-size:10pt;color:#22553d;">
    ~{_pct(r.economia_potencial_wfm_pct)} da folha proposta —
    alocação inteligente sem cortar headcount
  </p>
</div>

<p>
  O Workforce Management (WFM) baseado em IA aprende a curva de demanda
  específica de cada loja e aloca pessoas com mais precisão. Não substitui
  funcionários — coloca cada pessoa na hora certa, reduzindo ociosidade
  em horários de baixa demanda e cobrindo picos sem horas extras.
</p>

<p>
  No <strong>plano Pro</strong> da MudAção Escala, você tem:
</p>
<ul>
  <li>Planejador automático que resolve a escala respeitando restrições CLT</li>
  <li>Validador jurídico em PDF (artigos 71, 66, 67)</li>
  <li>Comparação contra baseline histórico</li>
  <li>Multi-usuário e histórico de simulações</li>
</ul>

<p style="text-align:center;margin-top:16pt;">
  <a href="https://simulaescala.mudacao.com.br/precos"
     style="display:inline-block;background:#0a4a3a;color:#fff;
            padding:10pt 20pt;text-decoration:none;border-radius:6pt;
            font-weight:600;font-size:11pt;">
    Ver planos →
  </a>
</p>
"""


def _inputs_recap(r: SimulateResponse) -> str:
    return f"""\
<h2>Premissas e auditoria</h2>
<p style="font-size:10pt;color:#64748b;">
  Resultado calculado pela engine MudAção (versão 0.1.0) usando fórmulas
  baseadas em estudo Fitch e validações CLT. Para reprodutibilidade:
</p>
<p class="hash">
  Hash de inputs: <strong>{r.inputs_hash}</strong><br>
  Use esse hash pra recuperar exatamente esta simulação no futuro.
</p>
"""


def _footer(r: SimulateResponse) -> str:
    return """\
<div class="footer-block">
  <p style="margin:0;text-align:center;">
    <strong style="color:#0a4a3a;">MudAção Escala</strong> · Felipe Feldens · felipe@feldens.com<br>
    Este relatório foi gerado automaticamente e não substitui consulta jurídica.
    Para análise customizada do plano de transição da sua rede, considere o plano Enterprise.
  </p>
</div>
"""


# =============================================================================
# Helpers de formatação
# =============================================================================


def _brl(v) -> str:  # type: ignore[no-untyped-def]
    """Formata como R$ 12.345,67."""
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v) -> str:  # type: ignore[no-untyped-def]
    """Formata como 12,3%."""
    return f"{float(v):.1f}%".replace(".", ",")


def _dec(v) -> str:  # type: ignore[no-untyped-def]
    """Formata Decimal com vírgula como separador."""
    return f"{float(v):.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _signal(v) -> str:  # type: ignore[no-untyped-def]
    """+12,3% ou -0,5% com cor."""
    f = float(v)
    color = "#dc2626" if f > 0 else "#15803d"
    sign = "+" if f >= 0 else ""
    return f"<span style='color:{color};font-weight:600'>{sign}{_pct(v)}</span>"
