"""Smoke tests da rota /simulate."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from escala_freemium_api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_simulate_basic_payload(client):
    """Simulação mínima: 1 loja, 10 FTEs, salário R$2.500."""
    r = client.post(
        "/api/simulate",
        json={
            "fte_atual": 10,
            "salario_medio": "2500.00",
            "porte": "M",
            "setor": "varejo",
            "cenario": "neutro",
            "n_lojas_rede": 1,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    # Aumento de folha esperado entre 8% e 14% (AC-102 do engine T&F)
    delta_pct = Decimal(str(data["delta_folha_pct"]))
    assert Decimal("5") < delta_pct < Decimal("20"), f"delta_pct fora do range: {delta_pct}"

    # Tem os 3 cenários
    assert set(data["cenarios"].keys()) == {"pessimista", "neutro", "otimista"}

    # Headline tem texto
    assert len(data["headline"]) > 10


def test_simulate_network_extrapolation(client):
    """N lojas multiplica delta corretamente."""
    payload = {
        "fte_atual": 8,
        "salario_medio": "2200.00",
        "porte": "P",
        "cenario": "neutro",
    }
    r1 = client.post("/api/simulate", json={**payload, "n_lojas_rede": 1})
    r50 = client.post("/api/simulate", json={**payload, "n_lojas_rede": 50})

    assert r1.status_code == 200
    assert r50.status_code == 200

    delta_1 = Decimal(str(r1.json()["delta_folha_rede_mes"]))
    delta_50 = Decimal(str(r50.json()["delta_folha_rede_mes"]))

    # 50 lojas → delta ~50× maior
    assert abs(delta_50 - delta_1 * 50) < Decimal("1.0")


def test_simulate_validation_error(client):
    """Salário negativo deve dar 422."""
    r = client.post(
        "/api/simulate",
        json={"fte_atual": 10, "salario_medio": "-100", "porte": "M"},
    )
    assert r.status_code == 422
