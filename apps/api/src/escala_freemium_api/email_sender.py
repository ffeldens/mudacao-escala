"""Envio de email via Resend.

API REST simples — não usamos SDK Python pra evitar uma dep a mais.
Doc: https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import base64
import logging
from decimal import Decimal

import httpx

from escala_freemium_api.config import get_settings
from escala_freemium_api.schemas import SimulateResponse

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_lead_welcome_email(
    *,
    to: str,
    nome: str | None,
    result: SimulateResponse,
    pdf_bytes: bytes | None = None,
) -> bool:
    """Envia o email de boas-vindas com o resumo do resultado e PDF anexo.

    Returns:
        True se enviou (HTTP 200), False caso contrário (loga o erro).
    """
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY vazia — pulando envio de email (dev?)")
        return False

    nome_saudacao = nome.split()[0] if nome else "olá"
    html = _render_welcome_html(nome=nome_saudacao, r=result)

    payload: dict = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [to],
        "reply_to": settings.RESEND_REPLY_TO,
        "subject": f"{nome_saudacao.capitalize()}, sua simulação PEC 8/2025 está pronta",
        "html": html,
        "tags": [
            {"name": "category", "value": "lead_welcome"},
            {"name": "env", "value": settings.APP_ENV},
        ],
    }

    if pdf_bytes:
        payload["attachments"] = [
            {
                "filename": "simulacao-pec-8-mudacao.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code >= 400:
                logger.error("Resend retornou %s: %s", r.status_code, r.text)
                return False
            logger.info("Email enviado pra %s (id=%s)", to, r.json().get("id"))
            return True
    except httpx.HTTPError as e:
        logger.exception("Falha no envio Resend: %s", e)
        return False


# =============================================================================
# Helpers privados
# =============================================================================


def _brl(value: Decimal | str | float) -> str:
    """Formata como R$ 12.345,67."""
    f = float(value)
    return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: Decimal | str | float) -> str:
    """Formata como 12,3%."""
    return f"{float(value):.1f}%".replace(".", ",")


def _render_welcome_html(*, nome: str, r: SimulateResponse) -> str:
    """HTML inline self-contained — funciona em Gmail, Outlook, Apple Mail."""
    delta_pct_fmt = _pct(r.delta_folha_pct)
    delta_rede_mes_fmt = _brl(r.delta_folha_rede_mes)
    delta_rede_ano_fmt = _brl(r.delta_folha_rede_ano)
    economia_wfm_fmt = _brl(r.economia_potencial_wfm)
    fte_extras_fmt = str(r.fte_extras_necessarios).replace(".", ",")

    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sua simulação PEC 8/2025</title>
</head>
<body style="margin:0;padding:0;background:#f5f7f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             color:#1a1a1a;line-height:1.6;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f5f7f6;padding:32px 16px;">
    <tr><td align="center">

      <!-- Container -->
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:12px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.05);">

        <!-- Header verde -->
        <tr><td style="background:linear-gradient(135deg,#062920 0%,#0a4a3a 100%);
                       padding:32px 32px 24px;color:#ffffff;">
          <p style="margin:0;font-size:13px;letter-spacing:1.5px;
                    text-transform:uppercase;color:#b8dcc8;font-weight:600;">
            MudAção Escala
          </p>
          <h1 style="margin:8px 0 0;font-size:26px;font-weight:700;line-height:1.2;">
            {nome.capitalize()}, sua simulação está pronta
          </h1>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">

          <p style="margin:0 0 24px;font-size:15px;color:#475569;">
            Obrigado por usar o MudAção Escala! Aqui vai o resumo do impacto da
            PEC 8/2025 na sua rede:
          </p>

          <!-- Headline destacado -->
          <div style="background:#f5f7f6;border-left:4px solid #0a4a3a;
                      padding:20px;margin:0 0 28px;border-radius:0 8px 8px 0;">
            <p style="margin:0;font-size:17px;font-weight:600;color:#0a4a3a;line-height:1.4;">
              {r.headline}
            </p>
          </div>

          <!-- KPIs em grid 2x2 -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 border="0" style="margin:0 0 28px;">
            <tr>
              <td width="50%" style="padding:0 8px 8px 0;">
                <div style="background:#0a4a3a;color:#fff;padding:16px;
                            border-radius:8px;">
                  <p style="margin:0;font-size:11px;letter-spacing:1px;
                            text-transform:uppercase;color:#b8dcc8;">
                    Aumento mensal
                  </p>
                  <p style="margin:6px 0 0;font-size:22px;font-weight:700;">
                    {delta_rede_mes_fmt}
                  </p>
                </div>
              </td>
              <td width="50%" style="padding:0 0 8px 8px;">
                <div style="background:#f5f7f6;padding:16px;border-radius:8px;
                            border:1px solid #e2e8f0;">
                  <p style="margin:0;font-size:11px;letter-spacing:1px;
                            text-transform:uppercase;color:#64748b;">
                    Em 1 ano
                  </p>
                  <p style="margin:6px 0 0;font-size:22px;font-weight:700;color:#0a4a3a;">
                    {delta_rede_ano_fmt}
                  </p>
                </div>
              </td>
            </tr>
            <tr>
              <td width="50%" style="padding:8px 8px 0 0;">
                <div style="background:#f5f7f6;padding:16px;border-radius:8px;
                            border:1px solid #e2e8f0;">
                  <p style="margin:0;font-size:11px;letter-spacing:1px;
                            text-transform:uppercase;color:#64748b;">
                    Acima da folha atual
                  </p>
                  <p style="margin:6px 0 0;font-size:22px;font-weight:700;color:#0a4a3a;">
                    +{delta_pct_fmt}
                  </p>
                </div>
              </td>
              <td width="50%" style="padding:8px 0 0 8px;">
                <div style="background:#f5f7f6;padding:16px;border-radius:8px;
                            border:1px solid #e2e8f0;">
                  <p style="margin:0;font-size:11px;letter-spacing:1px;
                            text-transform:uppercase;color:#64748b;">
                    Contratações/loja
                  </p>
                  <p style="margin:6px 0 0;font-size:22px;font-weight:700;color:#0a4a3a;">
                    +{fte_extras_fmt}
                  </p>
                </div>
              </td>
            </tr>
          </table>

          <!-- WFM pitch -->
          <div style="background:#dbeee4;padding:20px;border-radius:8px;
                      margin:0 0 28px;">
            <p style="margin:0;font-size:13px;font-weight:700;color:#0a4a3a;
                      letter-spacing:1px;text-transform:uppercase;">
              💡 E se você pudesse economizar?
            </p>
            <p style="margin:8px 0 0;font-size:20px;font-weight:700;color:#062920;">
              Até {economia_wfm_fmt} por mês
            </p>
            <p style="margin:8px 0 0;font-size:14px;color:#22553d;">
              Com Workforce Management baseado em IA, sua rede pode reduzir
              folha em ~5% através de alocação inteligente de pessoas vs. demanda.
            </p>
          </div>

          <!-- CTA -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 border="0" style="margin:0 0 28px;">
            <tr><td align="center">
              <a href="https://simulaescala.mudacao.com.br/precos"
                 style="display:inline-block;background:#0a4a3a;color:#ffffff;
                        text-decoration:none;padding:14px 28px;border-radius:8px;
                        font-weight:600;font-size:15px;">
                Ver planos com escala inteligente →
              </a>
            </td></tr>
          </table>

          <p style="margin:0;font-size:14px;color:#64748b;border-top:1px solid #e2e8f0;
                    padding-top:20px;">
            📎 O <strong>PDF detalhado</strong> da sua simulação está anexo neste email.<br>
            Dúvidas? <a href="mailto:felipe@feldens.com" style="color:#0a4a3a;">
            Responda este email</a> — leio pessoalmente.
          </p>

        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f5f7f6;padding:20px 32px;border-top:1px solid #e2e8f0;">
          <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">
            <strong style="color:#0a4a3a;">MudAção Escala</strong> · Felipe Feldens<br>
            <a href="https://simulaescala.mudacao.com.br" style="color:#64748b;">
              simulaescala.mudacao.com.br
            </a>
            ·
            <a href="mailto:felipe@feldens.com" style="color:#64748b;">
              felipe@feldens.com
            </a>
          </p>
          <p style="margin:8px 0 0;font-size:11px;color:#94a3b8;text-align:center;">
            Você recebeu este email porque solicitou uma simulação no nosso site.
          </p>
        </td></tr>

      </table>

    </td></tr>
  </table>
</body>
</html>
"""
