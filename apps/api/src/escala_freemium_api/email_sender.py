"""Envio de email via Resend.

API REST simples — não usamos SDK Python pra evitar uma dep a mais.
Doc: https://resend.com/docs/api-reference/emails/send-email
"""

from __future__ import annotations

import base64
import html
import logging
from decimal import Decimal

import httpx

from escala_freemium_api.config import get_settings
from escala_freemium_api.schemas import SimulateResponse

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_admin_notification(
    *,
    lead_email: str,
    lead_nome: str | None,
    lead_whatsapp: str | None,
    lead_empresa: str | None,
    result: SimulateResponse,
) -> bool:
    """Notifica o admin (Felipe) sempre que um novo lead é capturado.

    Email curto, formato admin, com os dados do lead + resumo da simulação.
    """
    settings = get_settings()

    if not settings.RESEND_API_KEY or not settings.ADMIN_NOTIFY_EMAIL:
        return False

    # Escapa campos livres do lead — evita HTML/phishing injection no email
    # que o admin recebe (nome/empresa são strings arbitrárias do formulário).
    nome = html.escape(lead_nome or "(sem nome)")
    empresa = html.escape(lead_empresa or "(sem empresa)")
    whatsapp = html.escape(lead_whatsapp or "(sem WhatsApp)")

    html_body = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Novo lead</title></head>
<body style="font-family:-apple-system,'Segoe UI',sans-serif;color:#1a1a1a;
             line-height:1.5;max-width:600px;margin:0 auto;padding:24px;">
  <div style="background:#0a4a3a;color:#fff;padding:16px 20px;border-radius:8px;">
    <p style="margin:0;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;
              color:#b8dcc8;font-weight:600;">
      🎯 MudAção Escala
    </p>
    <h1 style="margin:6px 0 0;font-size:22px;">Novo lead capturado</h1>
  </div>

  <h2 style="color:#0a4a3a;font-size:16px;margin:24px 0 8px;">Contato</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:6px 0;color:#64748b;width:120px;">Nome</td>
        <td style="padding:6px 0;font-weight:600;">{nome}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Email</td>
        <td style="padding:6px 0;font-weight:600;"><a href="mailto:{lead_email}"
            style="color:#0a4a3a;">{lead_email}</a></td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">WhatsApp</td>
        <td style="padding:6px 0;font-weight:600;"><a href="https://wa.me/{_only_digits(whatsapp)}"
            style="color:#0a4a3a;">{whatsapp}</a></td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Empresa</td>
        <td style="padding:6px 0;">{empresa}</td></tr>
  </table>

  <h2 style="color:#0a4a3a;font-size:16px;margin:24px 0 8px;">Simulação</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:6px 0;color:#64748b;width:200px;">Rede</td>
        <td style="padding:6px 0;font-weight:600;">{result.n_lojas} loja(s)</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Aumento de folha (rede/mês)</td>
        <td style="padding:6px 0;font-weight:600;color:#dc2626;">
          {_brl(result.delta_folha_rede_mes)}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Aumento em 1 ano</td>
        <td style="padding:6px 0;font-weight:600;color:#dc2626;">
          {_brl(result.delta_folha_rede_ano)}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">% acima da folha atual</td>
        <td style="padding:6px 0;font-weight:600;">
          +{_pct(result.delta_folha_pct)}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">FTEs extras/loja</td>
        <td style="padding:6px 0;font-weight:600;">
          +{result.fte_extras_necessarios}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Economia potencial WFM</td>
        <td style="padding:6px 0;font-weight:600;color:#15803d;">
          {_brl(result.economia_potencial_wfm)}/mês</td></tr>
  </table>

  <p style="margin:24px 0 0;padding:12px;background:#f5f7f6;border-radius:6px;
            font-size:12px;color:#64748b;">
    Hash de inputs: <code>{result.inputs_hash}</code><br>
    Lead recebeu email automático com o relatório. Você pode responder
    diretamente clicando no email do lead acima.
  </p>
</body>
</html>
"""

    payload = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [settings.ADMIN_NOTIFY_EMAIL],
        "reply_to": lead_email,  # responder direto pro lead
        "subject": f"🎯 Lead: {nome} ({result.n_lojas} lojas, {_brl(result.delta_folha_rede_mes)}/mês)",
        "html": html_body,
        "tags": [
            {"name": "category", "value": "admin_notification"},
            {"name": "env", "value": settings.APP_ENV},
        ],
    }

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
                logger.error("Resend admin notify retornou %s: %s", r.status_code, r.text)
                return False
            logger.info("Admin notification enviado pra %s", settings.ADMIN_NOTIFY_EMAIL)
            return True
    except httpx.HTTPError as e:
        logger.exception("Falha admin notification: %s", e)
        return False


def _only_digits(s: str) -> str:
    """Remove tudo que não é dígito (pra usar em wa.me/X)."""
    return "".join(c for c in s if c.isdigit())


async def send_starter_welcome_email(
    *,
    to: str,
    nome: str | None,
    trial_end_at: str | None = None,
) -> bool:
    """Email de boas-vindas ao Starter — disparado ao iniciar trial.

    Args:
        to: email do user
        nome: primeiro nome do user (opcional)
        trial_end_at: data de término do trial formatada DD/MM/YYYY
    """
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY vazia — pulando welcome Starter")
        return False

    nome_saudacao = html.escape(nome.split()[0]) if nome else "Olá"
    trial_msg = (
        f"Seu trial gratuito vai até <strong>{trial_end_at}</strong>. "
        if trial_end_at
        else "Seu trial gratuito de 14 dias começou. "
    )

    html_body = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bem-vindo ao MudAção Escala — Starter</title>
</head>
<body style="margin:0;padding:0;background:#f5f7f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             color:#1a1a1a;line-height:1.6;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f5f7f6;padding:32px 16px;">
    <tr><td align="center">

      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:12px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.05);">

        <!-- Header verde -->
        <tr><td style="background:linear-gradient(135deg,#062920 0%,#0a4a3a 100%);
                       padding:32px 32px 28px;color:#ffffff;">
          <p style="margin:0;font-size:13px;letter-spacing:1.5px;
                    text-transform:uppercase;color:#b8dcc8;font-weight:600;">
            🎉 MudAção Escala — Starter
          </p>
          <h1 style="margin:8px 0 0;font-size:26px;font-weight:700;line-height:1.2;">
            {nome_saudacao}, bem-vindo ao Starter!
          </h1>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">

          <p style="margin:0 0 20px;font-size:15px;color:#475569;">
            {trial_msg}Aproveite pra explorar tudo que está disponível agora
            que você é um usuário Starter:
          </p>

          <!-- Lista de features -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 border="0" style="margin:0 0 24px;">
            <tr><td style="padding:12px 0;border-bottom:1px solid #e2e8f0;">
              <strong style="color:#0a4a3a;">✓ Histórico de simulações</strong><br>
              <span style="color:#64748b;font-size:13px;">
                Revisite, refaça e compare todas as suas simulações anteriores.
              </span>
            </td></tr>
            <tr><td style="padding:12px 0;border-bottom:1px solid #e2e8f0;">
              <strong style="color:#0a4a3a;">✓ Premissas customizadas</strong><br>
              <span style="color:#64748b;font-size:13px;">
                Configure encargos, VR/VT e dias úteis específicos da sua empresa.
              </span>
            </td></tr>
            <tr><td style="padding:12px 0;border-bottom:1px solid #e2e8f0;">
              <strong style="color:#0a4a3a;">✓ Validador CLT em PDF</strong><br>
              <span style="color:#64748b;font-size:13px;">
                Relatório com hash de auditoria pros artigos 71, 66, 67 e mais.
              </span>
            </td></tr>
            <tr><td style="padding:12px 0;border-bottom:1px solid #e2e8f0;">
              <strong style="color:#0a4a3a;">✓ Comparativo entre cenários</strong><br>
              <span style="color:#64748b;font-size:13px;">
                Compare 2 ou 3 cenários salvos lado a lado.
              </span>
            </td></tr>
            <tr><td style="padding:12px 0;">
              <strong style="color:#0a4a3a;">✓ Export Excel + Suporte WhatsApp</strong><br>
              <span style="color:#64748b;font-size:13px;">
                Planilha estruturada pra levar pra reunião. Suporte direto comigo.
              </span>
            </td></tr>
          </table>

          <!-- CTA -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 border="0" style="margin:0 0 24px;">
            <tr><td align="center">
              <a href="https://simulaescala.mudacao.com.br/minha-conta"
                 style="display:inline-block;background:#0a4a3a;color:#ffffff;
                        text-decoration:none;padding:14px 28px;border-radius:8px;
                        font-weight:600;font-size:15px;">
                Ir pra minha conta →
              </a>
            </td></tr>
          </table>

          <!-- Mensagem pessoal -->
          <div style="background:#f5f7f6;padding:16px 20px;border-radius:8px;
                      border-left:4px solid #0a4a3a;">
            <p style="margin:0;font-size:14px;color:#475569;">
              Quero te ouvir — qual o maior problema que o Starter precisa
              resolver pra você?<br>
              <a href="mailto:felipe@feldens.com?subject=Feedback%20Starter"
                 style="color:#0a4a3a;font-weight:600;">
                Manda um email
              </a>
              {" "}ou
              <a href="https://wa.me/5511996325174?text=Acabei%20de%20assinar%20o%20Starter%21%20Quero%20conversar%3A"
                 style="color:#0a4a3a;font-weight:600;">
                chama no WhatsApp
              </a>
              {" "}— respondo pessoalmente.
            </p>
          </div>

          <p style="margin:24px 0 0;font-size:12px;color:#94a3b8;
                    border-top:1px solid #e2e8f0;padding-top:16px;">
            Não vai cobrar nada agora. Quando o trial terminar, R$ 99/mês no
            cartão. Cancele a qualquer momento em
            <a href="https://simulaescala.mudacao.com.br/minha-conta"
               style="color:#64748b;text-decoration:underline;">
              Minha conta
            </a>.
          </p>

        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f5f7f6;padding:20px 32px;
                       border-top:1px solid #e2e8f0;">
          <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">
            <strong style="color:#0a4a3a;">MudAção Escala</strong> ·
            Felipe Feldens<br>
            <a href="https://simulaescala.mudacao.com.br" style="color:#64748b;">
              simulaescala.mudacao.com.br
            </a>
            ·
            <a href="mailto:felipe@feldens.com" style="color:#64748b;">
              felipe@feldens.com
            </a>
          </p>
        </td></tr>

      </table>

    </td></tr>
  </table>
</body>
</html>
"""

    payload = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [to],
        "reply_to": settings.RESEND_REPLY_TO,
        "subject": f"🎉 {nome_saudacao}, bem-vindo ao Starter (trial 14 dias)",
        "html": html_body,
        "tags": [
            {"name": "category", "value": "starter_welcome"},
            {"name": "env", "value": settings.APP_ENV},
        ],
    }

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
                logger.error("Resend starter welcome retornou %s: %s",
                             r.status_code, r.text)
                return False
            logger.info("Starter welcome enviado pra %s", to)
            return True
    except httpx.HTTPError as e:
        logger.exception("Falha starter welcome: %s", e)
        return False


async def send_waitlist_admin_notification(
    *,
    nome: str,
    email: str,
    plano: str,
    empresa: str | None,
    n_lojas: int | None,
) -> bool:
    """Notifica o admin (Felipe) quando alguém entra na waitlist dos planos pagos."""
    settings = get_settings()

    if not settings.RESEND_API_KEY or not settings.ADMIN_NOTIFY_EMAIL:
        return False

    PLANOS_PT = {
        "starter": "Starter (R$ 99/mês)",
        "pro": "Pro (R$ 299/mês)",
        "enterprise": "Enterprise (sob consulta)",
    }
    plano_label = PLANOS_PT.get(plano, plano)
    nome = html.escape(nome)
    empresa_label = html.escape(empresa or "(sem empresa)")
    n_lojas_label = str(n_lojas) if n_lojas else "(não informado)"

    html_body = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Novo interesse em plano pago</title></head>
<body style="font-family:-apple-system,'Segoe UI',sans-serif;color:#1a1a1a;
             line-height:1.5;max-width:600px;margin:0 auto;padding:24px;">
  <div style="background:#0a4a3a;color:#fff;padding:16px 20px;border-radius:8px;">
    <p style="margin:0;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;
              color:#b8dcc8;font-weight:600;">
      🚀 MudAção Escala — Waitlist
    </p>
    <h1 style="margin:6px 0 0;font-size:22px;">Novo interesse em plano pago</h1>
  </div>

  <div style="background:#dbeee4;padding:14px;border-radius:6px;margin:16px 0;">
    <p style="margin:0;font-size:12px;color:#0a4a3a;text-transform:uppercase;
              letter-spacing:1px;font-weight:700;">Plano de interesse</p>
    <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#062920;">
      {plano_label}
    </p>
  </div>

  <h2 style="color:#0a4a3a;font-size:16px;margin:24px 0 8px;">Contato</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:6px 0;color:#64748b;width:120px;">Nome</td>
        <td style="padding:6px 0;font-weight:600;">{nome}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Email</td>
        <td style="padding:6px 0;font-weight:600;"><a href="mailto:{email}"
            style="color:#0a4a3a;">{email}</a></td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Empresa</td>
        <td style="padding:6px 0;">{empresa_label}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b;">Lojas na rede</td>
        <td style="padding:6px 0;">{n_lojas_label}</td></tr>
  </table>

  <p style="margin:24px 0 0;padding:12px;background:#f5f7f6;border-radius:6px;
            font-size:12px;color:#64748b;">
    Lead interessado em planos pagos. Quando os planos lançarem oficialmente,
    avisar este contato em primeira mão. Responder este email vai direto pro lead.
  </p>
</body>
</html>
"""

    payload = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [settings.ADMIN_NOTIFY_EMAIL],
        "reply_to": email,
        "subject": f"🚀 Waitlist: {nome} interessado em {plano_label}",
        "html": html_body,
        "tags": [
            {"name": "category", "value": "waitlist_signup"},
            {"name": "plano", "value": plano},
            {"name": "env", "value": settings.APP_ENV},
        ],
    }

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
                logger.error("Resend waitlist notify retornou %s: %s", r.status_code, r.text)
                return False
            logger.info("Waitlist notification enviado pra %s (plano=%s, lead=%s)",
                        settings.ADMIN_NOTIFY_EMAIL, plano, email)
            return True
    except httpx.HTTPError as e:
        logger.exception("Falha waitlist notification: %s", e)
        return False


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

    nome_saudacao = html.escape(nome.split()[0]) if nome else "olá"
    html_body = _render_welcome_html(nome=nome_saudacao, r=result)

    payload: dict = {
        "from": f"MudAção Escala <{settings.RESEND_FROM_EMAIL}>",
        "to": [to],
        "reply_to": settings.RESEND_REPLY_TO,
        "subject": f"{nome_saudacao.capitalize()}, sua simulação PEC 8/2025 está pronta",
        "html": html_body,
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
