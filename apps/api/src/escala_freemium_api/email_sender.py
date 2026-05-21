"""Envio de email via Resend.

API REST simples — não usamos SDK Python pra evitar uma dep a mais.
Doc: https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import logging

import httpx

from escala_freemium_api.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_lead_welcome_email(
    *,
    to: str,
    nome: str | None,
    headline: str,
    economia_potencial: str,
    n_lojas: int,
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
    html = _render_welcome_html(
        nome=nome_saudacao,
        headline=headline,
        economia_potencial=economia_potencial,
        n_lojas=n_lojas,
    )

    payload: dict = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [to],
        "reply_to": settings.RESEND_REPLY_TO,
        "subject": "Sua simulação da PEC 8/2025 — MudAção Escala",
        "html": html,
        "tags": [
            {"name": "category", "value": "lead_welcome"},
            {"name": "env", "value": settings.APP_ENV},
        ],
    }

    if pdf_bytes:
        import base64

        payload["attachments"] = [
            {
                "filename": "simulacao-pec-8.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
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


def _render_welcome_html(
    *,
    nome: str,
    headline: str,
    economia_potencial: str,
    n_lojas: int,
) -> str:
    """HTML inline — sem template engine, mantém self-contained."""
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Sua simulação PEC 8/2025</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             color:#1a1a1a;line-height:1.6;max-width:600px;margin:0 auto;padding:24px;">
  <h1 style="color:#0a4a3a;font-size:24px;margin:0 0 16px;">Olá, {nome}!</h1>

  <p>Obrigado por usar o <strong>MudAção Escala</strong>. Aqui está o resumo da sua simulação:</p>

  <div style="background:#f5f7f6;border-left:4px solid #0a4a3a;padding:16px;margin:24px 0;">
    <p style="margin:0;font-size:18px;font-weight:600;">{headline}</p>
  </div>

  <h2 style="color:#0a4a3a;font-size:18px;margin-top:32px;">💡 E se tivesse uma ferramenta inteligente?</h2>
  <p>
    Com Workforce Management baseado em IA, sua rede de <strong>{n_lojas} loja(s)</strong>
    pode economizar até <strong>{economia_potencial}</strong> por mês através de
    melhor alocação de pessoas vs. demanda.
  </p>

  <p style="margin:32px 0;">
    <a href="https://simulaescala.mudacao.com.br/precos"
       style="background:#0a4a3a;color:#fff;padding:14px 24px;text-decoration:none;
              border-radius:8px;display:inline-block;font-weight:600;">
      Quero a versão completa →
    </a>
  </p>

  <p style="color:#666;font-size:14px;">
    O PDF detalhado da sua simulação está anexo.<br>
    Dúvidas? Responda este email — leio pessoalmente.
  </p>

  <hr style="border:none;border-top:1px solid #e0e0e0;margin:32px 0;">

  <p style="color:#999;font-size:12px;">
    MudAção · Felipe Feldens · felipe@feldens.com<br>
    Você recebeu este email porque solicitou uma simulação no
    <a href="https://simulaescala.mudacao.com.br">simulaescala.mudacao.com.br</a>.
  </p>
</body>
</html>
"""
