"""Fixtures de teste — isolamento de DB.

Os testes usam TestClient sem `with`, então o lifespan (que chama
init_db) não roda. Sem isso as tabelas não existem. Aqui apontamos
DATABASE_URL pra um SQLite temporário dedicado e criamos o schema uma
vez por sessão — testes nunca tocam o banco de dev/produção.

IMPORTANTE: o env precisa ser setado ANTES de qualquer import de
escala_freemium_api (config/db leem settings no import). Por isso o
os.environ no topo do módulo, fora de fixture.
"""

from __future__ import annotations

import os
import tempfile

# DB de teste isolado (recriado a cada sessão de testes).
_TEST_DB = os.path.join(tempfile.gettempdir(), "escala_freemium_test.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ.setdefault("APP_ENV", "development")

import pytest  # noqa: E402

from escala_freemium_api.db import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> None:
    """Cria todas as tabelas no SQLite de teste uma vez por sessão."""
    init_db()
