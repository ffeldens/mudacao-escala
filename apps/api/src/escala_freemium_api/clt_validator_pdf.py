"""Geração de PDF do Validador CLT — relatório auditável.

Diferente do PDF da simulação (foco financeiro), este foca em
**conformidade jurídica**: artigos avaliados, severidade, hash de
auditoria, versão da régua CLT.

Saída: PDF A4 vertical, 2-3 páginas, com:
- Capa: dados da loja + assinatura de auditoria
- Tabela de riscos avaliados (severidade colorida)
- Conformidade vs Violações sumarizada
- Recomendações genéricas + footer auditável
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from escala_freemium_api.schemas import SimulateRequest, SimulateResponse

logger = logging.getLogger(__name__)


def render_clt_validator_pdf(
    req: SimulateRequest,
    result: SimulateResponse,
    *,
    user_email: str | None = None,
    user_nome: str | None = None,
    user_empresa: str | None = None,
) -> bytes | None:
    """Renderiza o relatório CLT como PDF.

    Args:
        req: payload original da simulação (pra contexto da loja)
        result: SimulateResponse com riscos_clt avaliados pelo engine
        user_*: dados do user logado (vão pra capa do PDF)

    Returns:
        PDF bytes, ou None se WeasyPrint indisponível
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415  # import lazy
    except (ImportError, OSError) as e:
        logger.warning("WeasyPrint indisponível (%s) — pulando PDF CLT", e)
        return None

    html = _build_html(
        req=req,
        result=result,
        user_email=user_email,
        user_nome=user_nome,
        user_empresa=user_empresa,
    )
    try:
        return HTML(string=html).write_pdf()
    except Exception:
        logger.exception("Falha ao renderizar PDF CLT")
        return None


# =============================================================================
# HTML do PDF
# =============================================================================

# Engine retorna riscos no outputs JSON. Schema do SimulateResponse não
# expõe riscos_clt diretamente — precisamos extrair via dict do output.


_SEVERIDADE_LABEL = {
    "good": ("OK", "#15803d", "#dcfce7"),
    "info": ("Informativo", "#0a4a3a", "#dbeee4"),
    "warn": ("Atenção", "#b45309", "#fef3c7"),
    "bad": ("Violação / Risco alto", "#dc2626", "#fee2e2"),
}


def _build_html(
    *,
    req: SimulateRequest,
    result: SimulateResponse,
    user_email: str | None,
    user_nome: str | None,
    user_empresa: str | None,
) -> str:
    today_str = datetime.utcnow().strftime("%d/%m/%Y")
    hour_str = datetime.utcnow().strftime("%H:%M UTC")

    user_label = user_nome or (user_email or "Anônimo")
    empresa_label = user_empresa or "—"

    # Riscos vêm do engine via result. Como SimulateResponse não os expõe
    # diretamente, esperamos receber via outputs reconstruído na rota.
    # Pra simplificar, o caller deve passar via attribute ad-hoc.
    risks = getattr(result, "_clt_risks", []) or []
    risk_rows = _build_risk_rows(risks)

    # Contadores
    n_good = sum(1 for r in risks if r.get("severidade") == "good")
    n_info = sum(1 for r in risks if r.get("severidade") == "info")
    n_warn = sum(1 for r in risks if r.get("severidade") == "warn")
    n_bad = sum(1 for r in risks if r.get("severidade") == "bad")

    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Validador CLT — Relatório auditável</title>
  {_css()}
</head>
<body>
  <!-- ========== CAPA ========== -->
  <div class="cover">
    <p class="label">MudAção Escala · Validador CLT</p>
    <h1>Relatório de Conformidade<br>Escala 6x1 → 5x2 (PEC 8/2025)</h1>
    <p class="subtitle">
      Avaliação automatizada de riscos trabalhistas (CLT) sobre o modelo proposto.
    </p>
    <div class="cover-meta">
      <div>
        <p class="meta-label">Solicitado por</p>
        <p class="meta-value">{user_label}</p>
      </div>
      <div>
        <p class="meta-label">Empresa</p>
        <p class="meta-value">{empresa_label}</p>
      </div>
      <div>
        <p class="meta-label">Data</p>
        <p class="meta-value">{today_str} · {hour_str}</p>
      </div>
    </div>
  </div>

  <!-- ========== CONTEXTO DA LOJA ========== -->
  <h2>Contexto da operação avaliada</h2>
  <table class="data">
    <tr><th>Característica</th><th>Valor</th></tr>
    <tr><td>Setor</td><td>{req.setor}</td></tr>
    <tr><td>Porte da loja</td><td>{req.porte}</td></tr>
    <tr><td>FTEs atuais (6x1)</td><td>{req.fte_atual}</td></tr>
    <tr><td>Salário médio</td><td>R$ {_brl(req.salario_medio)}</td></tr>
    <tr><td>Hora de abertura</td><td>{req.hora_abertura}h</td></tr>
    <tr><td>Hora de fechamento</td><td>{req.hora_fechamento}h</td></tr>
    <tr><td>Dias de operação/semana</td><td>{req.dias_operacao_semana}</td></tr>
    <tr><td>Cenário avaliado</td><td>{req.cenario}</td></tr>
  </table>

  <!-- ========== RESUMO DE CONFORMIDADE ========== -->
  <h2>Resumo da avaliação</h2>
  <div class="kpi-grid">
    <div class="kpi accent" style="background:#dcfce7;border-left-color:#15803d;">
      <p class="kpi-label">Conformes</p>
      <p class="kpi-value" style="color:#15803d">{n_good}</p>
    </div>
    <div class="kpi" style="background:#dbeee4;">
      <p class="kpi-label">Informativos</p>
      <p class="kpi-value" style="color:#0a4a3a">{n_info}</p>
    </div>
    <div class="kpi" style="background:#fef3c7;">
      <p class="kpi-label">Atenção</p>
      <p class="kpi-value" style="color:#b45309">{n_warn}</p>
    </div>
    <div class="kpi" style="background:#fee2e2;">
      <p class="kpi-label">Risco alto</p>
      <p class="kpi-value" style="color:#dc2626">{n_bad}</p>
    </div>
  </div>

  <!-- ========== TABELA DE RISCOS ========== -->
  <h2>Avaliação por artigo</h2>
  {risk_rows}

  <!-- ========== RECOMENDAÇÕES ========== -->
  <h2>Recomendações gerais</h2>
  <ul>
    <li>
      Revise os pontos marcados como <strong>Atenção</strong> ou
      <strong>Risco alto</strong> com seu jurídico antes do rollout.
    </li>
    <li>
      Documente a régua aplicada (versão e data) pra defesa em eventual
      auditoria fiscal/trabalhista.
    </li>
    <li>
      Considere piloto em 1-3 lojas representativas antes do rollout completo
      pra calibrar a escala 5x2 real.
    </li>
    <li>
      WFM com IA pode reduzir contratações extras em 4-7% e ainda assim
      manter a conformidade — ver plano Pro pra acesso ao planejador.
    </li>
  </ul>

  <!-- ========== AUDITORIA ========== -->
  <h2>Auditoria</h2>
  <table class="data audit">
    <tr><th>Campo</th><th>Valor</th></tr>
    <tr><td>Hash dos inputs</td><td><code>{result.inputs_hash}</code></td></tr>
    <tr><td>Régua CLT aplicada</td><td><code>2026-04</code></td></tr>
    <tr><td>Engine MudAção</td><td><code>0.1.0</code></td></tr>
    <tr><td>Timestamp UTC</td><td>{today_str} {hour_str}</td></tr>
  </table>

  <p class="footer">
    <strong>MudAção Escala</strong> · Felipe Feldens · felipe@feldens.com<br>
    Este relatório é uma <strong>avaliação automatizada de risco</strong>,
    não substitui parecer jurídico individualizado. Use como instrumento
    de planejamento e prevenção.
  </p>

</body>
</html>
"""


def _build_risk_rows(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return "<p><em>Nenhum risco avaliado pelo engine.</em></p>"

    rows = []
    for r in risks:
        sev = r.get("severidade", "info")
        label, color, bg = _SEVERIDADE_LABEL.get(sev, _SEVERIDADE_LABEL["info"])
        rows.append(
            f"""
            <div class="risk-card" style="background:{bg};border-left-color:{color};">
              <div class="risk-head">
                <span class="risk-badge" style="background:{color};">{label}</span>
                <strong class="risk-title">{r.get("titulo", "")}</strong>
                <span class="risk-artigo">{r.get("artigo", "")}</span>
              </div>
              <p class="risk-desc">{r.get("descricao", "")}</p>
            </div>
            """
        )
    return "".join(rows)


def _css() -> str:
    return """\
<style>
  @page {
    size: A4;
    margin: 18mm 16mm;
    @bottom-center {
      content: "MudAção Escala · Validador CLT · página " counter(page) " de " counter(pages);
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
  h1 { color: #ffffff; font-size: 22pt; margin: 0 0 8pt; }
  h2 {
    color: #0a4a3a; font-size: 15pt; margin: 24pt 0 8pt;
    border-bottom: 2pt solid #0a4a3a; padding-bottom: 4pt;
  }
  .cover {
    background: linear-gradient(135deg, #062920 0%, #0a4a3a 100%);
    color: #fff; padding: 28pt; border-radius: 10pt; margin: 0 0 24pt;
  }
  .cover .label {
    margin: 0 0 16pt;
    font-size: 10pt;
    letter-spacing: 2pt;
    text-transform: uppercase;
    color: #b8dcc8;
  }
  .cover .subtitle {
    margin: 12pt 0 0;
    color: #b8dcc8;
    font-size: 12pt;
  }
  .cover-meta {
    display: table;
    width: 100%;
    margin: 24pt 0 0;
    padding-top: 16pt;
    border-top: 1pt solid rgba(255,255,255,0.2);
  }
  .cover-meta > div {
    display: table-cell;
    width: 33%;
  }
  .meta-label {
    font-size: 9pt;
    color: #b8dcc8;
    text-transform: uppercase;
    letter-spacing: 1pt;
    margin: 0;
  }
  .meta-value {
    color: #fff;
    font-weight: 600;
    margin: 4pt 0 0;
    font-size: 11pt;
  }

  table.data {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 12pt;
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

  .kpi-grid {
    display: table;
    width: 100%;
    border-collapse: separate;
    border-spacing: 6pt;
    margin: 0 -6pt 12pt;
  }
  .kpi {
    display: table-cell;
    border-left: 4pt solid #94a3b8;
    padding: 12pt;
    border-radius: 0 6pt 6pt 0;
    vertical-align: top;
    width: 25%;
    background: #f5f7f6;
  }
  .kpi-label {
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 1pt;
    margin: 0;
    color: #64748b;
  }
  .kpi-value {
    font-size: 24pt;
    font-weight: 700;
    margin: 6pt 0 0;
  }

  .risk-card {
    border-left: 4pt solid #94a3b8;
    padding: 12pt 16pt;
    margin: 8pt 0;
    border-radius: 0 6pt 6pt 0;
  }
  .risk-head {
    display: block;
    margin: 0 0 6pt;
  }
  .risk-badge {
    display: inline-block;
    color: #fff;
    padding: 2pt 8pt;
    border-radius: 4pt;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 1pt;
    font-weight: 700;
    margin-right: 8pt;
  }
  .risk-title { font-size: 11pt; }
  .risk-artigo {
    color: #64748b;
    font-size: 9pt;
    margin-left: 8pt;
  }
  .risk-desc {
    margin: 4pt 0 0;
    color: #334155;
    font-size: 10pt;
  }

  ul { margin: 0 0 12pt; padding-left: 18pt; }
  li { margin: 0 0 6pt; }

  .audit { margin-top: 8pt; }
  code {
    font-family: monospace;
    background: #f5f7f6;
    padding: 1pt 6pt;
    border-radius: 3pt;
    font-size: 9pt;
  }

  .footer {
    margin-top: 28pt;
    padding-top: 12pt;
    border-top: 1pt solid #e2e8f0;
    color: #94a3b8;
    font-size: 9pt;
    text-align: center;
  }
</style>
"""


def _brl(value) -> str:  # type: ignore[no-untyped-def]
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
