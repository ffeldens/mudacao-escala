"""Dependency FastAPI que valida JWT do Supabase.

Uso em rotas protegidas:
    from .auth_dep import CurrentUser

    @router.post("/algo")
    async def algo(user: CurrentUser):
        # user.id, user.email — garantido autenticado
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from escala_freemium_api.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    """User autenticado a partir do JWT do Supabase."""

    id: str  # auth.users.id (UUID string)
    email: str


def _decode_token(token: str) -> dict:
    """Decodifica + valida o JWT do Supabase via HS256 + JWT secret."""
    settings = get_settings()
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backend não configurado (SUPABASE_JWT_SECRET vazio)",
        )

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada — entre novamente",
        ) from e
    except jwt.InvalidTokenError as e:
        logger.warning("JWT inválido: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from e


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    """Extrai e valida o user do header Authorization: Bearer <token>."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato inválido — use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(parts[1])
    user_id = payload.get("sub")
    email = payload.get("email", "")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT sem identificação do user",
        )

    return AuthenticatedUser(id=user_id, email=email)


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
