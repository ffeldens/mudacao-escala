"""Rotas da API."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from escala_freemium_api import __version__
from escala_freemium_api.auth_dep import AuthenticatedUser, CurrentUser, OptionalUser
from escala_freemium_api.clt_extras import compute_clt_risks
from escala_freemium_api.clt_validator_pdf import render_clt_validator_pdf
from escala_freemium_api.config import get_settings
from escala_freemium_api.csv_batch import (
    BATCH_CSV_TEMPLATE,
    BatchCsvError,
    BatchRowError,
    parse_batch_csv,
    run_batch,
)
from escala_freemium_api.db import (
    Lead,
    Simulation,
    StripeWebhookEvent,
    UserProfile,
    get_db,
)
from escala_freemium_api.email_sender import (
    send_admin_notification,
    send_lead_welcome_email,
    send_starter_welcome_email,
    send_waitlist_admin_notification,
)
from escala_freemium_api.excel_export import build_batch_xlsx, build_single_xlsx
from escala_freemium_api.pdf import render_simulation_pdf
from escala_freemium_api.rate_limit import limiter
from escala_freemium_api.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    HealthResponse,
    LeadRequest,
    LeadResponse,
    PortalSessionResponse,
    SimulateRequest,
    SimulateResponse,
    SimulationHistoryItem,
    SimulationHistoryResponse,
    VersionResponse,
    WaitlistRequest,
    WaitlistResponse,
)
from escala_freemium_api.simulation_adapter import run_simulation
from escala_freemium_api.stripe_service import (
    create_checkout_session,
    create_portal_session,
    handle_subscription_deleted,
    sync_subscription_to_profile,
    verify_webhook_signature,
)

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
@limiter.limit("20/minute")
async def simulate(
    request: Request,
    req: SimulateRequest,
    db: DbSession,
    user: OptionalUser = None,
) -> SimulateResponse:
    """Roda a simulação e persiste o resultado.

    Se Authorization header presente com JWT válido, associa ao user.
    Pra user Starter+, aplica premissas customizadas do profile
    (encargos, VR/VT, dias úteis).
    """
    # Premissas customizadas pra user pago
    custom_financial = None
    if user:
        profile = db.get(UserProfile, UUID(user.id))
        if profile and profile.plan_tier in _PAID_PLANS:
            custom_financial = _build_custom_financial(profile)

    try:
        result = run_simulation(req, custom_financial=custom_financial)
    except Exception as e:
        logger.exception("Falha na simulação")
        raise HTTPException(status_code=400, detail=str(e)) from e

    sim = Simulation(
        user_id=UUID(user.id) if user else None,
        nome_loja=req.nome_loja,
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


def _build_custom_financial(profile: UserProfile):
    """Constrói FinancialAssumptions a partir das premissas do profile.

    Campos None ficam com default do engine. Só sobrescreve os que
    foram explicitamente setados pelo user.
    """
    from engine.models import FinancialAssumptions  # noqa: PLC0415

    defaults = FinancialAssumptions()
    return FinancialAssumptions(
        encargos_pct=profile.pref_encargos_pct
        if profile.pref_encargos_pct is not None
        else defaults.encargos_pct,
        vr_dia=profile.pref_vr_dia
        if profile.pref_vr_dia is not None
        else defaults.vr_dia,
        vt_dia=profile.pref_vt_dia
        if profile.pref_vt_dia is not None
        else defaults.vt_dia,
        dias_uteis_mes=profile.pref_dias_uteis_mes
        if profile.pref_dias_uteis_mes is not None
        else defaults.dias_uteis_mes,
    )


# =============================================================================
# Lead capture
# =============================================================================


@router.post("/lead", response_model=LeadResponse, tags=["leads"])
@limiter.limit("10/minute")
async def capture_lead(
    request: Request,
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
# Histórico de simulações (Starter+)
# =============================================================================


# Plans que tem acesso ao histórico
_PAID_PLANS = {"starter", "pro", "enterprise"}


def _require_paid_plan(user: AuthenticatedUser, db: Session) -> UserProfile:
    """Carrega profile e garante que tier é pago."""
    profile = db.get(UserProfile, UUID(user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    if profile.plan_tier not in _PAID_PLANS:
        raise HTTPException(
            status_code=403,
            detail="Recurso disponível apenas no plano Starter ou superior",
        )
    return profile


@router.get(
    "/me/simulations",
    response_model=SimulationHistoryResponse,
    tags=["simulator"],
)
async def list_my_simulations(
    user: CurrentUser,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> SimulationHistoryResponse:
    """Lista as simulações do user logado. Paywalled Starter+."""
    _require_paid_plan(user, db)

    user_uuid = UUID(user.id)

    total = (
        db.query(Simulation)
        .filter(Simulation.user_id == user_uuid)
        .count()
    )

    rows = (
        db.query(Simulation)
        .filter(Simulation.user_id == user_uuid)
        .order_by(desc(Simulation.created_at))
        .limit(min(limit, 200))
        .offset(offset)
        .all()
    )

    items = []
    for sim in rows:
        # Extrai headline do JSON de outputs (cached pra performance)
        headline = None
        if isinstance(sim.outputs, dict):
            headline = sim.outputs.get("headline")

        items.append(
            SimulationHistoryItem(
                id=str(sim.id),
                nome_loja=sim.nome_loja,
                n_lojas=sim.n_lojas_extrapolacao,
                delta_folha_pct=sim.delta_folha_pct,
                economia_estimada_mes=sim.economia_estimada_mes,
                headline=headline,
                created_at=sim.created_at.isoformat() if sim.created_at else "",
            )
        )

    return SimulationHistoryResponse(items=items, total=total)


@router.post(
    "/me/validate-clt",
    tags=["simulator"],
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF do validador CLT",
        },
    },
)
async def validate_clt(
    req: SimulateRequest,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    """Roda a simulação + valida riscos CLT + retorna PDF auditável.

    Paywalled Starter+. PDF inclui hash de inputs + clt_version pra
    reprodutibilidade jurídica.
    """
    profile = _require_paid_plan(user, db)

    # Premissas customizadas (igual ao /simulate)
    custom_financial = None
    if profile.plan_tier in _PAID_PLANS:
        custom_financial = _build_custom_financial(profile)

    try:
        result = run_simulation(req, custom_financial=custom_financial)
    except Exception as e:
        logger.exception("Falha simulação no validador CLT")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Riscos CLT (engine + extras), pipeline centralizado em clt_extras
    result._clt_risks = compute_clt_risks(  # type: ignore[attr-defined]
        req, result, custom_financial=custom_financial
    )

    pdf_bytes = render_clt_validator_pdf(
        req=req,
        result=result,
        user_email=profile.email,
        user_nome=profile.nome,
        user_empresa=profile.empresa,
    )

    if pdf_bytes is None:
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar PDF — WeasyPrint pode estar indisponível",
        )

    filename = f"validador-clt-{result.inputs_hash}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/me/simulations/{simulation_id}",
    response_model=SimulateResponse,
    tags=["simulator"],
)
async def get_my_simulation(
    simulation_id: str,
    user: CurrentUser,
    db: DbSession,
) -> SimulateResponse:
    """Retorna o resultado completo de uma simulação salva.

    Permite o frontend re-abrir uma simulação no /simulador/resultado
    sem precisar refazer o cálculo. Paywalled Starter+.
    """
    _require_paid_plan(user, db)

    try:
        sim_uuid = UUID(simulation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="ID inválido") from e

    sim = db.get(Simulation, sim_uuid)
    if not sim or str(sim.user_id) != user.id:
        raise HTTPException(status_code=404, detail="Simulação não encontrada")

    if not isinstance(sim.outputs, dict):
        raise HTTPException(
            status_code=500,
            detail="Dados da simulação corrompidos",
        )

    # outputs já está no formato SimulateResponse (serializado)
    return SimulateResponse(**sim.outputs)


# =============================================================================
# Export Excel — single (Sprint 3 #4)
# =============================================================================


_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post(
    "/me/export-excel",
    tags=["simulator"],
    responses={200: {"content": {_XLSX_MEDIA: {}}, "description": ".xlsx multi-aba"}},
)
async def export_excel(
    req: SimulateRequest,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    """Roda simulação + valida CLT + retorna .xlsx multi-aba.

    Paywalled Starter+. Mesmo payload do /simulate, retorna .xlsx em vez de JSON.
    """
    profile = _require_paid_plan(user, db)
    custom_financial = _build_custom_financial(profile)

    try:
        result = run_simulation(req, custom_financial=custom_financial)
    except Exception as e:
        logger.exception("Falha simulação export-excel")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Riscos CLT (mesma lógica do validate-clt — pipeline centralizado).
    # Falha graceful: gera planilha sem aba de riscos se o engine quebrar.
    clt_risks: list[dict] = []
    try:
        clt_risks = compute_clt_risks(req, result, custom_financial=custom_financial)
    except Exception:
        logger.exception("Falha CLT no export-excel — gerando sem aba de riscos")

    try:
        xlsx_bytes = build_single_xlsx(
            req=req,
            result=result,
            user_nome=profile.nome,
            user_empresa=profile.empresa,
            clt_risks=clt_risks or None,
        )
    except Exception as e:
        logger.exception("Falha ao gerar .xlsx")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar Excel: {e}") from e

    filename = f"simulacao-{result.inputs_hash}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/me/simulations/{simulation_id}/export-excel",
    tags=["simulator"],
    responses={200: {"content": {_XLSX_MEDIA: {}}, "description": ".xlsx multi-aba"}},
)
async def export_excel_from_history(
    simulation_id: str,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    """Exporta .xlsx de uma simulação salva no histórico.

    Reaproveita inputs persistidos + recalcula riscos CLT (snapshot fiel).
    """
    profile = _require_paid_plan(user, db)

    try:
        sim_uuid = UUID(simulation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="ID inválido") from e

    sim = db.get(Simulation, sim_uuid)
    if not sim or str(sim.user_id) != user.id:
        raise HTTPException(status_code=404, detail="Simulação não encontrada")

    if not isinstance(sim.inputs, dict) or not isinstance(sim.outputs, dict):
        raise HTTPException(status_code=500, detail="Dados da simulação corrompidos")

    try:
        req = SimulateRequest(**sim.inputs)
        result = SimulateResponse(**sim.outputs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inputs/outputs inválidos: {e}") from e

    # Re-avalia riscos CLT (sempre fresh — régua pode ter sido atualizada)
    clt_risks: list[dict] = []
    try:
        custom_financial = _build_custom_financial(profile)
        clt_risks = compute_clt_risks(req, result, custom_financial=custom_financial)
    except Exception:
        logger.exception("Falha CLT no export-excel histórico")

    try:
        xlsx_bytes = build_single_xlsx(
            req=req,
            result=result,
            user_nome=profile.nome,
            user_empresa=profile.empresa,
            clt_risks=clt_risks or None,
        )
    except Exception as e:
        logger.exception("Falha ao gerar .xlsx histórico")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar Excel: {e}") from e

    filename = f"simulacao-{result.inputs_hash}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Batch CSV — upload N lojas → .xlsx consolidado (Sprint 3 #4)
# =============================================================================


@router.get("/me/batch-csv/template", tags=["simulator"])
async def batch_csv_template(user: CurrentUser, db: DbSession) -> Response:
    """Baixa um CSV de exemplo com colunas obrigatórias + 3 linhas-modelo."""
    _require_paid_plan(user, db)
    return Response(
        content=BATCH_CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="template-avaliacao-rede.csv"',
        },
    )


@router.post(
    "/me/batch-csv",
    tags=["simulator"],
    responses={200: {"content": {_XLSX_MEDIA: {}}, "description": ".xlsx consolidado"}},
)
async def batch_csv_upload(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> Response:
    """Recebe CSV multi-loja, roda batch, devolve .xlsx consolidado.

    Síncrono — limite MAX_LOJAS_POR_UPLOAD lojas por upload pra evitar timeout.
    Paywalled Starter+.
    """
    profile = _require_paid_plan(user, db)

    # Lê o arquivo (limite ~1 MB pra evitar abuse — CSV de 50 lojas é < 10 kB)
    content = await file.read()
    if len(content) > 1_000_000:
        raise HTTPException(status_code=413, detail="Arquivo grande demais (>1 MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    try:
        requests = parse_batch_csv(content)
    except BatchCsvError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except BatchRowError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    custom_financial = _build_custom_financial(profile)

    try:
        results = run_batch(requests, custom_financial=custom_financial)
    except BatchRowError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Persiste cada simulação no histórico (audit trail)
    for _label, req, result in results:
        sim = Simulation(
            user_id=UUID(user.id),
            nome_loja=req.nome_loja,
            inputs_hash=result.inputs_hash,
            inputs=req.model_dump(mode="json"),
            outputs=result.model_dump(mode="json"),
            n_lojas_extrapolacao=req.n_lojas_rede,
            delta_folha_pct=result.delta_folha_pct,
            economia_estimada_mes=result.economia_potencial_wfm,
        )
        db.add(sim)
    db.commit()

    try:
        xlsx_bytes = build_batch_xlsx(
            results,
            user_nome=profile.nome,
            user_empresa=profile.empresa,
        )
    except Exception as e:
        logger.exception("Falha ao gerar .xlsx batch")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar Excel: {e}") from e

    filename = f"avaliacao-rede-{len(results)}-lojas.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Waitlist (avise-me sobre planos pagos)
# =============================================================================


@router.post("/waitlist", response_model=WaitlistResponse, tags=["leads"])
@limiter.limit("10/minute")
async def waitlist_signup(
    request: Request,
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


async def _send_starter_welcome_safe(
    *,
    to: str,
    nome: str | None,
    trial_end_at: str | None,
) -> None:
    """Tenta enviar welcome do Starter. Loga erro mas nunca propaga."""
    try:
        await send_starter_welcome_email(
            to=to,
            nome=nome,
            trial_end_at=trial_end_at,
        )
    except Exception:
        logger.exception("Falha starter welcome pra %s", to)


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
@limiter.limit("10/minute")
async def lead_and_simulate(
    request: Request,
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
# Stripe — Customer Portal (gerenciar assinatura)
# =============================================================================


@router.post(
    "/stripe/portal-session",
    response_model=PortalSessionResponse,
    tags=["billing"],
)
async def stripe_portal(
    user: CurrentUser,
    db: DbSession,
) -> PortalSessionResponse:
    """Cria URL do Stripe Customer Portal pra user gerenciar assinatura.

    No portal o user pode:
    - Trocar cartão
    - Cancelar / reativar assinatura
    - Baixar invoices
    - Atualizar endereço de cobrança

    Requer Authorization: Bearer <jwt do Supabase>.
    """
    profile = db.get(UserProfile, user.id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado",
        )

    if not profile.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="Você ainda não tem assinatura — assine um plano primeiro",
        )

    settings = get_settings()
    return_url = f"{settings.APP_BASE_URL.rstrip('/')}/minha-conta"

    try:
        result = create_portal_session(profile=profile, return_url=return_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return PortalSessionResponse(**result)


# =============================================================================
# Stripe — Webhook
# =============================================================================


@router.post("/stripe/webhook", tags=["billing"], include_in_schema=False)
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    stripe_signature: str | None = Header(default=None),
) -> dict:
    """Recebe eventos do Stripe e sincroniza com user_profiles.

    O endpoint é público (sem auth de user) mas valida a assinatura HMAC
    via STRIPE_WEBHOOK_SECRET pra garantir que veio do Stripe mesmo.

    Eventos tratados:
    - checkout.session.completed: confirma fim do checkout
    - customer.subscription.created/updated: sync de status + plan_tier
    - customer.subscription.deleted: marca como canceled
    - invoice.payment_failed: loga warning (sub atualiza via subscription.updated)
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing stripe-signature header",
        )

    # Endpoint público: rejeita body absurdo ANTES de bufferizar em memória.
    # Payloads Stripe legítimos são < 100 KB. Defesa adicional deve existir
    # no Caddy (request body limit) — esse check é a última linha.
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 256_000:
        raise HTTPException(status_code=413, detail="Payload too large")

    payload = await request.body()

    try:
        event = verify_webhook_signature(payload, stripe_signature)
    except Exception as e:
        logger.exception("Webhook signature inválida: %s", e)
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature",
        ) from e

    event_type = event["type"]
    event_id = event["id"]
    obj = event["data"]["object"]

    logger.info("Stripe webhook recebido: %s (id=%s)", event_type, event_id)

    # Idempotência: o Stripe reentrega eventos (retries). Se já processamos
    # este event_id, retorna OK sem reprocessar — evita welcome email duplicado
    # e re-sync redundante. INSERT serve de lock atômico via PK.
    if db.get(StripeWebhookEvent, event_id):
        logger.info("Evento Stripe já processado (id=%s) — ignorando replay", event_id)
        return {"received": True, "event_type": event_type, "duplicate": True}
    db.add(StripeWebhookEvent(event_id=event_id, event_type=event_type))
    try:
        db.commit()
    except Exception:
        # Corrida: outro worker inseriu o mesmo event_id entre o get e o commit.
        db.rollback()
        logger.info("Evento Stripe em corrida (id=%s) — ignorando replay", event_id)
        return {"received": True, "event_type": event_type, "duplicate": True}

    if event_type == "checkout.session.completed":
        # Sessão concluída — a subscription já foi criada pelo Stripe
        # e o customer.subscription.created vem em seguida. Não precisamos
        # fazer nada aqui exceto logar.
        logger.info(
            "Checkout completed: customer=%s subscription=%s",
            obj.get("customer"), obj.get("subscription"),
        )

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.trial_will_end",
    ):
        sync_subscription_to_profile(db, obj)

        # No created: dispara welcome do Starter em background.
        # Disparar só uma vez (na criação), não em updated. Reactivations
        # vêm como .updated, então não duplicamos email.
        if event_type == "customer.subscription.created":
            customer_id = obj.get("customer")
            if customer_id:
                profile = (
                    db.query(UserProfile)
                    .filter(UserProfile.stripe_customer_id == customer_id)
                    .first()
                )
                if profile:
                    trial_end_str = (
                        profile.trial_end_at.strftime("%d/%m/%Y")
                        if profile.trial_end_at
                        else None
                    )
                    background_tasks.add_task(
                        _send_starter_welcome_safe,
                        to=profile.email,
                        nome=profile.nome,
                        trial_end_at=trial_end_str,
                    )

    elif event_type == "customer.subscription.deleted":
        handle_subscription_deleted(db, obj)

    elif event_type == "invoice.payment_failed":
        # Cartão recusado — o status da subscription vira past_due automático
        # e o customer.subscription.updated trata. Aqui só loga + (futuro)
        # manda email pro user reativar.
        logger.warning(
            "Payment failed: customer=%s invoice=%s",
            obj.get("customer"), obj.get("id"),
        )

    else:
        # Outros eventos (charge.*, payment_intent.*) — ignoramos no MVP
        logger.debug("Evento ignorado: %s", event_type)

    return {"received": True, "event_type": event_type}


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
