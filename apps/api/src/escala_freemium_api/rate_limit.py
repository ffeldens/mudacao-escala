"""Limiter compartilhado (slowapi).

Mora num módulo separado pra evitar import circular: tanto main.py
(que registra o handler + state) quanto routes.py (que decora os
endpoints) importam daqui.

Storage é in-memory (default). Funciona pra deploy single-process
(1 worker uvicorn). Se um dia escalar pra múltiplos workers, trocar por
storage Redis via `storage_uri`.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _client_ip(request: Request) -> str:
    """IP real do cliente pro rate limit.

    Atrás do Caddy, request.client.host é sempre 127.0.0.1 (o proxy). Sem
    isso o rate limit viraria GLOBAL (todos os clientes compartilhando o IP
    do proxy) e derrubaria tráfego legítimo. O Caddy injeta X-Forwarded-For;
    pegamos o primeiro IP (cliente original como o Caddy o vê).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
