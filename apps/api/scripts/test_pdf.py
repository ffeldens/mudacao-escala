"""Gera um PDF de exemplo no disco, sem passar pela API.

Útil pra validar que WeasyPrint funciona (depois de instalar GTK no Windows).

Uso:
    cd apps/api
    uv run python scripts/test_pdf.py

Output:
    apps/api/tmp/test-simulacao.pdf
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

# Permite importar o pacote sem instalação
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from escala_freemium_api.pdf import render_simulation_pdf
from escala_freemium_api.schemas import CenarioOut, SimulateResponse


def make_sample_result() -> SimulateResponse:
    """Resultado de exemplo equivalente ao seu smoke test (10 FTEs, R$2.500, M, 50 lojas)."""
    return SimulateResponse(
        inputs_hash="16688ea130c4051c",
        folha_atual_mes=Decimal("54620.00"),
        folha_proposta_mes=Decimal("59972.76"),
        delta_folha_mes=Decimal("5352.76"),
        delta_folha_pct=Decimal("9.80"),
        fte_atual=Decimal("10"),
        fte_proposto=Decimal("10.98"),
        fte_extras_necessarios=Decimal("0.98"),
        cenarios={
            "pessimista": CenarioOut(
                cenario="pessimista",
                ratio_aplicado=Decimal("1.1798"),
                fte_total=Decimal("11.8"),
                folha_total=Decimal("64451.60"),
                delta_folha=Decimal("9831.60"),
                delta_folha_pct=Decimal("18.00"),
            ),
            "neutro": CenarioOut(
                cenario="neutro",
                ratio_aplicado=Decimal("1.0972"),
                fte_total=Decimal("10.98"),
                folha_total=Decimal("59972.76"),
                delta_folha=Decimal("5352.76"),
                delta_folha_pct=Decimal("9.80"),
            ),
            "otimista": CenarioOut(
                cenario="otimista",
                ratio_aplicado=Decimal("0.9972"),
                fte_total=Decimal("9.98"),
                folha_total=Decimal("54510.76"),
                delta_folha=Decimal("-109.24"),
                delta_folha_pct=Decimal("-0.20"),
            ),
        },
        n_lojas=50,
        delta_folha_rede_mes=Decimal("267638.00"),
        delta_folha_rede_ano=Decimal("3211656.00"),
        headline="Sua rede de 50 lojas vai gastar R$ 267.638,00 a mais por mês com a escala 5x2.",
        economia_potencial_wfm=Decimal("149931.90"),
        economia_potencial_wfm_pct=Decimal("5.00"),
    )


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "tmp"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "test-simulacao.pdf"

    result = make_sample_result()
    print("🔧 Gerando PDF de teste...")
    pdf_bytes = render_simulation_pdf(result)

    if pdf_bytes is None:
        print("❌ Falha: WeasyPrint indisponível (libs GTK não instaladas?)")
        print("   No Windows, instala: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        sys.exit(1)

    out_file.write_bytes(pdf_bytes)
    size_kb = len(pdf_bytes) / 1024
    print(f"✓ PDF gerado: {out_file} ({size_kb:.1f} KB)")
    print(f"  Abre pra ver: start {out_file}")


if __name__ == "__main__":
    main()
