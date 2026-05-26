"""Dependency FastAPI que valida JWT do Supabase.

Suporta dois modos automaticamente:
- HS256 com SUPABASE_JWT_SECRET (Supabase legacy / chave simétrica)
- RS256/ES256 via JWKS (Supabase moderno com asymmetric signing keys)

Tenta HS256 primeiro. Se falhar com "alg not allowed", cai pra JWKS.

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
from jwt import PyJWKClient

from escala_freemium_api.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    """User autenticado a partir do JWT do Supabase."""

    id: str  # auth.users.id (UUID string)
    email: str


# Cache global do JWKS client (1 por processo)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        if not settings.SUPABASE_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SUPABASE_URL não configurada",
            )
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        logger.info("Inicializando JWKS client: %s", jwks_url)
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _decode_token(token: str) -> dict:
    """Decodifica + valida o JWT do Supabase.

    Tenta HS256 com SUPABASE_JWT_SECRET primeiro (legado).
    Se algoritmo não bater ou secret faltar, tenta JWKS (RS256/ES256).
    """
    settings = get_settings()

    # ====== Tentativa 1: HS256 com secret simétrico ======
    if settings.SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.InvalidAlgorithmError:
            logger.debug("HS256 não é o alg do token — tentando JWKS")
        except jwt.InvalidSignatureError:
            logger.debug("Assinatura HS256 não bate — tentando JWKS")
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada — entre novamente",
            ) from e
        except jwt.InvalidAudienceError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Audience inválida no token",
            ) from e
        except jwt.InvalidTokenError as e:
            # Outros erros HS256 — pode ser que o token seja RS256
            logger.debug("HS256 falhou (%s) — tentando JWKS", e)

    # ====== Tentativa 2: JWKS (asymmetric keys) ======
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada — entre novamente",
        ) from e
    except jwt.InvalidTokenError as e:
        logger.warning("JWT inválido via JWKS: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from e
    except Exception as e:
        logger.exception("Falha inesperada na validação JWT: %s", e)
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
