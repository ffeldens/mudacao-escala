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

    # Grade de cobertura teórica (atual vs proposto)
    grade_block = _build_grade_block(req, result)

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

  <!-- ========== GRADE DE COBERTURA TEÓRICA ========== -->
  {grade_block}

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


DIAS_LABEL = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _calcular_grade_cobertura(
    fte_count: float,
    jornada_h: float,
    hora_abertura: int,
    hora_fechamento: int,
    dias_op: int,
) -> list[list[float]]:
    """Distribui FTE-horas pelos slots da semana com pesos de pico.

    Lógica: cada slot (dia × hora) recebe um peso (1.0 base, 1.3 em
    sex/sáb/dom, 1.2 em 14h-21h, multiplicativo). Soma normalizada
    bate com fte_count × jornada_h.

    Returns:
        Matriz [7 dias][horas_de_operacao] com FTEs presentes (float)
    """
    horas_dia = hora_fechamento - hora_abertura
    if horas_dia <= 0 or dias_op <= 0:
        return [[0.0] * max(1, horas_dia) for _ in range(7)]

    fte_horas_disp = fte_count * jornada_h

    pesos: list[list[float]] = []
    for dia in range(7):
        linha = []
        ativo = dia < dias_op
        for h in range(hora_abertura, hora_fechamento):
            if not ativo:
                linha.append(0.0)
                continue
            peso = 1.0
            if dia >= 4:  # sex, sáb, dom
                peso *= 1.3
            if 14 <= h < 21:  # pico
                peso *= 1.2
            linha.append(peso)
        pesos.append(linha)

    soma = sum(sum(linha) for linha in pesos)
    if soma == 0:
        return pesos
    fator = fte_horas_disp / soma
    return [[p * fator for p in linha] for linha in pesos]


def _color_for_fte(fte: float, min_required: float = 1.0) -> str:
    """Retorna cor de fundo baseado em quantos FTEs estão presentes.

    < min_required → vermelho (sub-cobertura)
    = min_required (até 1.5x) → amarelo (apertado)
    1.5x a 3x → verde claro
    > 3x → verde escuro
    """
    if fte == 0:
        return "#f1f5f9"  # cinza claro (fechado)
    if fte < min_required:
        return "#fee2e2"  # red-100
    if fte < min_required * 1.5:
        return "#fef3c7"  # amber-100
    if fte < min_required * 3:
        return "#dbeee4"  # mudacao verde claro
    return "#b8dcc8"  # mudacao verde mais escuro


def _build_grade_block(req: SimulateRequest, result: SimulateResponse) -> str:
    horas_dia = req.hora_fechamento - req.hora_abertura
    if horas_dia <= 0:
        return ""

    grade_atual = _calcular_grade_cobertura(
        fte_count=req.fte_atual,
        jornada_h=44,  # 6x1
        hora_abertura=req.hora_abertura,
        hora_fechamento=req.hora_fechamento,
        dias_op=req.dias_operacao_semana,
    )
    grade_prop = _calcular_grade_cobertura(
        fte_count=float(result.fte_proposto),
        jornada_h=40,  # 5x2
        hora_abertura=req.hora_abertura,
        hora_fechamento=req.hora_fechamento,
        dias_op=req.dias_operacao_semana,
    )

    horas = list(range(req.hora_abertura, req.hora_fechamento))

    def render_tabela(grade: list[list[float]], titulo: str, subtitulo: str) -> str:
        # Cabeçalho de horas
        thead_horas = "".join(
            f'<th class="hr">{h}h</th>' for h in horas
        )
        tbody_rows = ""
        for i, dia_label in enumerate(DIAS_LABEL):
            cells = ""
            for j, h in enumerate(horas):
                fte = grade[i][j]
                color = _color_for_fte(fte)
                text = f"{fte:.1f}" if fte > 0 else "—"
                cells += (
                    f'<td class="slot" style="background:{color};">{text}</td>'
                )
            tbody_rows += f"<tr><th class='dia'>{dia_label}</th>{cells}</tr>"

        return f"""
        <div class="grade-card">
          <h3>{titulo}</h3>
          <p class="grade-sub">{subtitulo}</p>
          <table class="grade">
            <thead>
              <tr><th class="dia-h"></th>{thead_horas}</tr>
            </thead>
            <tbody>{tbody_rows}</tbody>
          </table>
        </div>
        """

    sub_atual = f"{req.fte_atual} FTE × 44h/sem (6x1)"
    sub_prop = f"{float(result.fte_proposto):.1f} FTE × 40h/sem (5x2)"

    legenda = """
    <div class="grade-legend">
      <span class="lg-item"><span class="sw" style="background:#fee2e2;"></span> &lt; 1 FTE (sub-cobertura)</span>
      <span class="lg-item"><span class="sw" style="background:#fef3c7;"></span> 1–1.5 FTE (apertado)</span>
      <span class="lg-item"><span class="sw" style="background:#dbeee4;"></span> 1.5–3 FTE (ok)</span>
      <span class="lg-item"><span class="sw" style="background:#b8dcc8;"></span> 3+ FTE (folgado)</span>
      <span class="lg-item"><span class="sw" style="background:#f1f5f9;"></span> Fechado</span>
    </div>
    """

    return f"""
    <h2>Grade de cobertura teórica (semana modelo)</h2>
    <p>
      Distribuição teórica de FTE × hora × dia, com peso de pico em
      sex/sáb/dom e horário 14h–21h. <strong>Cada célula é o número
      esperado de pessoas trabalhando naquela hora-dia</strong>.
    </p>

    <div class="grade-row">
      {render_tabela(grade_atual, "Modelo atual 6x1", sub_atual)}
      {render_tabela(grade_prop, "Modelo proposto 5x2", sub_prop)}
    </div>

    {legenda}

    <div class="grade-disclaimer">
      <strong>⚠️ Isto é uma distribuição teórica</strong>, não uma escala
      operacional. Pra escala real otimizada respeitando absenteísmo, picos
      históricos, comissionistas e restrições por função, use o
      <em>Planejador Automático</em> do plano Pro.
    </div>
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

  /* ===== Grade de cobertura teórica ===== */
  .grade-row {
    display: table;
    width: 100%;
    border-collapse: separate;
    border-spacing: 8pt;
    margin: 0 -8pt 8pt;
  }
  .grade-card {
    display: table-cell;
    width: 50%;
    vertical-align: top;
    background: #f8fafc;
    border: 1pt solid #e2e8f0;
    border-radius: 6pt;
    padding: 10pt;
  }
  .grade-card h3 {
    color: #0a4a3a;
    font-size: 11pt;
    margin: 0 0 2pt;
    border: none;
    padding: 0;
  }
  .grade-card .grade-sub {
    color: #64748b;
    font-size: 8pt;
    margin: 0 0 8pt;
  }
  table.grade {
    width: 100%;
    border-collapse: collapse;
    font-size: 7pt;
  }
  table.grade th, table.grade td {
    border: 0.5pt solid #cbd5e1;
    padding: 3pt 2pt;
    text-align: center;
    font-weight: 500;
  }
  table.grade th.dia-h { width: 22pt; }
  table.grade th.hr {
    background: #0a4a3a;
    color: #fff;
    font-size: 7pt;
    font-weight: 600;
  }
  table.grade th.dia {
    background: #0a4a3a;
    color: #fff;
    font-size: 8pt;
    font-weight: 600;
    text-align: center;
  }
  table.grade td.slot {
    color: #1a1a1a;
    font-variant-numeric: tabular-nums;
  }

  .grade-legend {
    display: block;
    margin: 8pt 0 8pt;
    font-size: 9pt;
    color: #475569;
  }
  .grade-legend .lg-item {
    display: inline-block;
    margin-right: 12pt;
    line-height: 1.6;
  }
  .grade-legend .sw {
    display: inline-block;
    width: 10pt;
    height: 10pt;
    border: 0.5pt solid #cbd5e1;
    vertical-align: middle;
    margin-right: 3pt;
  }
  .grade-disclaimer {
    background: #fef3c7;
    border-left: 4pt solid #b45309;
    padding: 10pt 14pt;
    margin: 10pt 0 16pt;
    font-size: 10pt;
    color: #78350f;
    border-radius: 0 4pt 4pt 0;
  }
</style>
"""


def _brl(value) -> str:  # type: ignore[no-untyped-def]
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
