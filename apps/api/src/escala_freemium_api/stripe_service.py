"""Helpers de integração com Stripe.

Encapsula:
- Criação/recuperação de Customer (1 Stripe customer por user_profile)
- Criação de Checkout Session com trial
- Validação de webhook

A SDK Stripe é configurada lazy (na primeira chamada) pra não quebrar
import se a API key estiver vazia em dev.
"""

from __future__ import annotations

import logging
from typing import Any

import stripe
from sqlalchemy.orm import Session

from escala_freemium_api.config import get_settings
from escala_freemium_api.db import UserProfile

logger = logging.getLogger(__name__)


def _ensure_stripe_configured() -> None:
    """Configura a SDK Stripe na primeira chamada."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError(
            "STRIPE_SECRET_KEY não configurada — não dá pra criar checkout"
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_customer(
    db: Session,
    profile: UserProfile,
) -> str:
    """Retorna o stripe_customer_id do user, criando se ainda não existir.

    Args:
        db: sessão SQLAlchemy
        profile: UserProfile do user logado

    Returns:
        stripe_customer_id (str)
    """
    _ensure_stripe_configured()

    if profile.stripe_customer_id:
        return profile.stripe_customer_id

    # Cria novo Customer no Stripe
    metadata: dict[str, str] = {
        "user_id": str(profile.id),
        "source": "mudacao_escala",
    }
    if profile.empresa:
        metadata["empresa"] = profile.empresa[:50]  # Stripe limit

    customer = stripe.Customer.create(
        email=profile.email,
        name=profile.nome or profile.email.split("@")[0],
        phone=profile.whatsapp,
        metadata=metadata,
    )

    logger.info(
        "Stripe customer criado: %s (user_id=%s)", customer.id, profile.id
    )

    # Persiste no banco
    profile.stripe_customer_id = customer.id
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return customer.id


def create_checkout_session(
    db: Session,
    profile: UserProfile,
    plano: str,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Cria uma Stripe Checkout Session pro plano dado.

    Args:
        db: sessão
        profile: UserProfile
        plano: 'starter' (por enquanto, único plano ativo)
        success_url: URL pra onde Stripe redireciona após sucesso
        cancel_url: URL pra onde Stripe redireciona se cancelar

    Returns:
        dict com 'session_id' e 'url' (URL hospedada do Checkout)
    """
    _ensure_stripe_configured()
    settings = get_settings()

    # Resolve price_id baseado no plano
    if plano == "starter":
        price_id = settings.STRIPE_PRICE_ID_STARTER
    else:
        raise ValueError(f"Plano '{plano}' ainda não tem price configurado")

    if not price_id:
        raise RuntimeError(
            f"STRIPE_PRICE_ID_{plano.upper()} não configurado no .env"
        )

    customer_id = get_or_create_customer(db, profile)

    # Bloqueia múltiplas subscriptions
    if profile.stripe_subscription_id and profile.subscription_status in (
        "trialing",
        "active",
    ):
        raise ValueError(
            f"Já existe uma assinatura ativa ({profile.subscription_status})"
        )

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        subscription_data={
            "trial_period_days": settings.STRIPE_TRIAL_DAYS,
            "metadata": {
                "user_id": str(profile.id),
                "plano": plano,
            },
        },
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        billing_address_collection="auto",
        # Captura nome correto na cobrança
        customer_update={"name": "auto", "address": "auto"},
        # Marca a sessão com metadados úteis pro webhook
        metadata={
            "user_id": str(profile.id),
            "plano": plano,
        },
        # Locale BR
        locale="pt-BR",
    )

    logger.info(
        "Checkout session criado: %s (user=%s, plano=%s)",
        session.id, profile.id, plano,
    )

    return {
        "session_id": session.id,
        "url": session.url,
    }


def create_portal_session(
    profile: UserProfile,
    return_url: str,
) -> dict[str, str]:
    """Cria uma Stripe Billing Portal Session.

    O Customer Portal é uma página hospedada pelo Stripe onde o user
    pode: trocar cartão, cancelar assinatura, ver invoices, atualizar
    endereço de cobrança. Não precisamos construir nada — só fornecer
    a URL.

    Args:
        profile: UserProfile com stripe_customer_id válido
        return_url: URL pra onde o Stripe redireciona ao sair do portal

    Returns:
        dict com 'url' (URL hospedada do portal)
    """
    _ensure_stripe_configured()

    if not profile.stripe_customer_id:
        raise ValueError(
            "Usuário ainda não tem stripe_customer_id "
            "(nunca passou por checkout)"
        )

    session = stripe.billing_portal.Session.create(
        customer=profile.stripe_customer_id,
        return_url=return_url,
        locale="pt-BR",
    )

    logger.info(
        "Portal session criado: %s (customer=%s)",
        session.id, profile.stripe_customer_id,
    )

    return {"url": session.url}


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
) -> stripe.Event:
    """Valida assinatura do webhook do Stripe e retorna o Event tipado.

    Raises:
        stripe.SignatureVerificationError se inválido
    """
    _ensure_stripe_configured()
    settings = get_settings()

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET não configurado")

    return stripe.Webhook.construct_event(
        payload,
        signature_header,
        settings.STRIPE_WEBHOOK_SECRET,
    )


# =============================================================================
# Sync Stripe → UserProfile
# =============================================================================


def _stripe_status_to_plan_tier(status: str | None) -> str:
    """Mapeia status do Stripe pra plan_tier no nosso DB.

    Stripe statuses: 'trialing', 'active', 'past_due', 'canceled', 'unpaid',
    'incomplete', 'incomplete_expired', 'paused'.

    A regra: durante trialing/active → "starter". Caso contrário → "free"
    (perde acesso aos recursos pagos).
    """
    if status in ("trialing", "active", "past_due"):
        # past_due ainda dá acesso por 1-2 ciclos enquanto tentamos cobrar
        return "starter"
    return "free"


def sync_subscription_to_profile(
    db: Session,
    subscription: dict,
) -> str | None:
    """Atualiza o UserProfile baseado em um Subscription event do Stripe.

    Args:
        db: sessão SQLAlchemy
        subscription: dict do Stripe Subscription (do event.data.object)

    Returns:
        user_id atualizado, ou None se não encontrou profile
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    customer_id = subscription.get("customer")
    if not customer_id:
        logger.warning("Subscription sem customer — ignorando")
        return None

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.stripe_customer_id == customer_id)
        .first()
    )
    if not profile:
        logger.warning(
            "Profile nao encontrado pra customer_id=%s (subscription=%s)",
            customer_id, subscription.get("id"),
        )
        return None

    status = subscription.get("status")
    profile.stripe_subscription_id = subscription.get("id")
    profile.subscription_status = status
    profile.plan_tier = _stripe_status_to_plan_tier(status)
    profile.cancel_at_period_end = bool(
        subscription.get("cancel_at_period_end", False)
    )

    # Datas — Stripe envia timestamps unix
    trial_end = subscription.get("trial_end")
    period_end = subscription.get("current_period_end")

    profile.trial_end_at = (
        datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None
    )
    profile.subscription_current_period_end = (
        datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info(
        "Subscription sync: user=%s status=%s plan=%s sub=%s",
        profile.id, status, profile.plan_tier, profile.stripe_subscription_id,
    )

    return str(profile.id)


def handle_subscription_deleted(
    db: Session,
    subscription: dict,
) -> str | None:
    """Marca subscription como cancelada no profile."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return None

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.stripe_customer_id == customer_id)
        .first()
    )
    if not profile:
        return None

    profile.subscription_status = "canceled"
    profile.plan_tier = "free"
    # Mantém stripe_subscription_id pra histórico

    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info(
        "Subscription canceled: user=%s sub=%s",
        profile.id, subscription.get("id"),
    )
    return str(profile.id)
