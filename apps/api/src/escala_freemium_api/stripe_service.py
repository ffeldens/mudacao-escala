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
