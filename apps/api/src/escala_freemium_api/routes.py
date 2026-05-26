"""Rotas da API."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from escala_freemium_api import __version__
from escala_freemium_api.auth_dep import CurrentUser
from escala_freemium_api.config import get_settings
from escala_freemium_api.db import Lead, Simulation, UserProfile, get_db
from escala_freemium_api.email_sender import (
    send_admin_notification,
    send_lead_welcome_email,
    send_waitlist_admin_notification,
)
from escala_freemium_api.pdf import render_simulation_pdf
from escala_freemium_api.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    HealthResponse,
    LeadRequest,
    LeadResponse,
    SimulateRequest,
    SimulateResponse,
    VersionResponse,
    WaitlistRequest,
    WaitlistResponse,
)
from escala_freemium_api.simulation_adapter import run_simulation
from escala_freemium_api.stripe_service import create_checkout_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

DbSession = Annotated[Session, Depends(get_db)]


# =============================================================================
# Health / version
# =============================================================================


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    try:
        from engine import __version__ as engine_version  # noqa: PLC0415
    except ImportError:
        engine_version = "unknown"

    return VersionResponse(
        api_version=__version__,
        engine_version=engine_version,
        env=get_settings().APP_ENV,
    )


# =============================================================================
# Simulação
# =============================================================================


@router.post("/simulate", response_model=SimulateResponse, tags=["simulator"])
async def simulate(req: SimulateRequest, db: DbSession) -> SimulateResponse:
    """Roda a simulação e persiste o resultado (sem lead — anônimo)."""
    try:
        result = run_simulation(req)
    except Exception as e:
        logger.exception("Falha na simulação")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Persiste pra ter base analítica mesmo sem lead
    sim = Simulation(
        inputs_hash=result.inputs_hash,
        inputs=req.model_dump(mode="json"),
        outputs=result.model_dump(mode="json"),
        n_lojas_extrapolacao=req.n_lojas_rede,
        delta_folha_pct=result.delta_folha_pct,
        economia_estimada_mes=result.economia_potencial_wfm,
    )
    db.add(sim)
    db.commit()

    return result


# =============================================================================
# Lead capture
# =============================================================================


@router.post("/lead", response_model=LeadResponse, tags=["leads"])
async def capture_lead(
    req: LeadRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> LeadResponse:
    """Captura email/WhatsApp e dispara email de boas-vindas em background."""
    lead = Lead(
        email=req.email,
        whatsapp=req.whatsapp,
        nome=req.nome,
        empresa=req.empresa,
        n_lojas=req.n_lojas,
        porte=req.porte,
        setor=req.setor,
        source="simulator_gate",
        utm_source=req.utm_source,
        utm_medium=req.utm_medium,
        utm_campaign=req.utm_campaign,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Rota /lead (sem simulação) não dispara email — não temos resultado
    # pra enviar. O fluxo principal usa /lead-and-simulate que dispara.

    return LeadResponse(
        lead_id=str(lead.id),
        email=lead.email,
        email_enviado=False,
    )


# =============================================================================
# Waitlist (avise-me sobre planos pagos)
# =============================================================================


@router.post("/waitlist", response_model=WaitlistResponse, tags=["leads"])
async def waitlist_signup(
    req: WaitlistRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> WaitlistResponse:
    """Cadastra na waitlist dos planos pagos + dispara notificação admin."""
    # Reaproveita a tabela `leads` com source distintivo
    lead = Lead(
        email=req.email,
        nome=req.nome,
        empresa=req.empresa,
        n_lojas=req.n_lojas or 0,
        porte="M",  # placeholder — waitlist não pede porte
        setor="outros",  # placeholder
        source=f"waitlist_{req.plano}",
        utm_source=req.utm_source,
        utm_medium=req.utm_medium,
        utm_campaign=req.utm_campaign,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Notification admin em background
    background_tasks.add_task(
        _send_waitlist_notification_safe,
        nome=req.nome,
        email=req.email,
        plano=req.plano,
        empresa=req.empresa,
        n_lojas=req.n_lojas,
    )

    return WaitlistResponse(lead_id=str(lead.id), email=lead.email)


async def _send_waitlist_notification_safe(
    *,
    nome: str,
    email: str,
    plano: str,
    empresa: str | None,
    n_lojas: int | None,
) -> None:
    try:
        await send_waitlist_admin_notification(
            nome=nome,
            email=email,
            plano=plano,
            empresa=empresa,
            n_lojas=n_lojas,
        )
    except Exception:
        logger.exception("Falha waitlist notify (plano=%s, lead=%s)", plano, email)


# =============================================================================
# Lead + simulação combinados (atalho do frontend)
# =============================================================================


@router.post("/lead-and-simulate", response_model=SimulateResponse, tags=["simulator"])
async def lead_and_simulate(
    lead_req: LeadRequest,
    sim_req: SimulateRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> SimulateResponse:
    """Captura lead + roda simulação em uma chamada (fluxo principal do frontend)."""
    # 1. Roda simulação
    try:
        result = run_simulation(sim_req)
    except Exception as e:
        logger.exception("Falha na simulação")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 2. Persiste lead
    lead = Lead(
        email=lead_req.email,
        whatsapp=lead_req.whatsapp,
        nome=lead_req.nome,
        empresa=lead_req.empresa,
        n_lojas=lead_req.n_lojas,
        porte=lead_req.porte,
        setor=lead_req.setor,
        source="simulator_gate",
        utm_source=lead_req.utm_source,
        utm_medium=lead_req.utm_medium,
        utm_campaign=lead_req.utm_campaign,
    )
    db.add(lead)
    db.flush()  # gera lead.id sem commitar ainda

    # 3. Persiste simulação ligada ao lead
    sim = Simulation(
        lead_id=lead.id,
        inputs_hash=result.inputs_hash,
        inputs=sim_req.model_dump(mode="json"),
        outputs=result.model_dump(mode="json"),
        n_lojas_extrapolacao=sim_req.n_lojas_rede,
        delta_folha_pct=result.delta_folha_pct,
        economia_estimada_mes=result.economia_potencial_wfm,
    )
    db.add(sim)
    db.commit()

    # 4. Email em background (com PDF se possível)
    background_tasks.add_task(
        _send_welcome_email_with_pdf_safe,
        to=lead_req.email,
        nome=lead_req.nome,
        result=result,
    )

    # 5. Notificação admin (Felipe é avisado de cada novo lead)
    background_tasks.add_task(
        _send_admin_notification_safe,
        lead_email=lead_req.email,
        lead_nome=lead_req.nome,
        lead_whatsapp=lead_req.whatsapp,
        lead_empresa=lead_req.empresa,
        result=result,
    )

    return result


# =============================================================================
# Stripe — Checkout
# =============================================================================


@router.post(
    "/stripe/checkout-session",
    response_model=CheckoutSessionResponse,
    tags=["billing"],
)
async def stripe_checkout(
    req: CheckoutSessionRequest,
    user: CurrentUser,
    db: DbSession,
) -> CheckoutSessionResponse:
    """Cria uma Stripe Checkout Session pro plano selecionado.

    Requer Authorization: Bearer <jwt do Supabase>.
    """
    settings = get_settings()

    # Busca profile do user (DB sempre tem após o trigger handle_new_user)
    profile = db.get(UserProfile, user.id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado — recarregue a página",
        )

    # URLs de retorno do Stripe (após sucesso/cancelamento)
    base = settings.APP_BASE_URL.rstrip("/")
    success_url = (
        f"{base}/minha-conta?checkout=success"
        "&session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = f"{base}/precos?checkout=canceled"

    try:
        result = create_checkout_session(
            db=db,
            profile=profile,
            plano=req.plano,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except ValueError as e:
        # Erros previsíveis (assinatura já ativa, plano inválido)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        # Configuração faltando
        raise HTTPException(status_code=500, detail=str(e)) from e

    return CheckoutSessionResponse(**result)


# =============================================================================
# Helpers privados (background tasks)
# =============================================================================


async def _send_welcome_email_with_pdf_safe(
    *,
    to: str,
    nome: str | None,
    result: SimulateResponse,
) -> None:
    """Tenta gerar PDF e enviar email. Loga erro mas nunca propaga."""
    try:
        pdf_bytes = render_simulation_pdf(result)
        await send_lead_welcome_email(
            to=to,
            nome=nome,
            result=result,
            pdf_bytes=pdf_bytes,
        )
    except Exception:
        logger.exception("Falha no background email c/ PDF pra %s", to)


async def _send_admin_notification_safe(
    *,
    lead_email: str,
    lead_nome: str | None,
    lead_whatsapp: str | None,
    lead_empresa: str | None,
    result: SimulateResponse,
) -> None:
    """Envia notificação admin. Loga erro mas nunca propaga."""
    try:
        await send_admin_notification(
            lead_email=lead_email,
            lead_nome=lead_nome,
            lead_whatsapp=lead_whatsapp,
            lead_empresa=lead_empresa,
            result=result,
        )
    except Exception:
        logger.exception("Falha admin notify pra lead %s", lead_email)
