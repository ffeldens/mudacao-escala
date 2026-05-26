"""Análise do impacto da PEC 8/2025 nos CAFÉS da Track & Field — dados 1T26.

Mesma metodologia da análise das lojas próprias, ajustada pra cargos
diferentes (Atendente, Auxiliar de Cozinha, Barista, Gerente, Líder).

Uso:
    cd apps/api
    uv run --with openpyxl --with pandas python scripts/analise_tf_cafes_1t26.py [comando]
"""

from __future__ import annotations

import io
import math
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

import pandas as pd  # noqa: E402

EXCEL_PATH = Path(r"C:\Users\felip\Downloads\INFORMAÇÃO 1T26 CAFÉ.xlsx")

# =============================================================================
# Engine constants (replicado de packages/engine/src/engine/core.py)
# =============================================================================
JORNADA_6X1 = Decimal("44")
JORNADA_5X2 = Decimal("40")
RATIO_BASE = JORNADA_6X1 / JORNADA_5X2

FATOR_PERDAS = {
    "pessimista": Decimal("1.10"),
    "neutro": Decimal("1.05"),
    "otimista": Decimal("0.98"),
}
PESO_GANHO_PROD = {
    "pessimista": Decimal("0.5"),
    "neutro": Decimal("1.0"),
    "otimista": Decimal("1.5"),
}
GANHO_PROD_DEFAULT = Decimal("0.05")
WFM_ECONOMY_PCT = Decimal("0.05")


def _ratio(cenario: str) -> Decimal:
    fator_perdas = FATOR_PERDAS[cenario]
    peso = PESO_GANHO_PROD[cenario]
    ajuste = Decimal("1") - GANHO_PROD_DEFAULT * peso
    return RATIO_BASE * fator_perdas * ajuste


# =============================================================================
# Domínio
# =============================================================================


@dataclass
class Cafe:
    """Um café TFC com dados do 1T26."""

    nome: str
    faturamento_1t: Decimal
    pessoal_1t: Decimal
    fte_total: int
    atendente: int
    aux_cozinha: int
    barista: int
    gerente: int
    lider: int

    @property
    def pessoal_mensal(self) -> Decimal:
        return (self.pessoal_1t / Decimal("3")).quantize(Decimal("0.01"))

    @property
    def perc_folha_fat(self) -> Decimal:
        if self.faturamento_1t == 0:
            return Decimal("0")
        return (self.pessoal_1t / self.faturamento_1t * 100).quantize(Decimal("0.01"))

    @property
    def custo_medio_por_fte_mes(self) -> Decimal:
        if self.fte_total == 0:
            return Decimal("0")
        return (self.pessoal_mensal / self.fte_total).quantize(Decimal("0.01"))


@dataclass
class ImpactoCafe:
    cafe: Cafe
    ratio: Decimal
    fte_proposto: Decimal
    fte_extras: Decimal
    folha_proposta_mes: Decimal
    delta_folha_mes: Decimal
    delta_folha_pct: Decimal
    economia_wfm_mes: Decimal


# =============================================================================
# Carregar Excel
# =============================================================================


def carregar_cafes() -> list[Cafe]:
    """Lê o Excel e retorna a lista de Cafés.

    Layout das colunas (0-indexed):
      0: Nome do café
      1-3: JANEIRO (fat/folha/%)
      4-6: FEVEREIRO (fat/folha/%)
      7-9: MARÇO (fat/folha/%)
      10-12: 1T2026 (fat/folha/%)
      13: gap
      14: ATENDENTE
      15: AUXILIAR DE COZINHA
      16: BARISTA
      17: GERENTE DE LOJA
      18: LIDER
      19: TOTAL
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="RESUMO CAFÉ", header=None)
    cafes: list[Cafe] = []

    # Linhas 2-11 são os 10 cafés. Linha 12 é TOTAL (skip).
    for i in range(2, 12):
        row = df.iloc[i]
        nome = row[0]
        if pd.isna(nome) or "TOTAL" in str(nome).upper():
            continue
        try:
            cafes.append(
                Cafe(
                    nome=str(nome).strip(),
                    faturamento_1t=Decimal(str(row[10])) if pd.notna(row[10]) else Decimal("0"),
                    pessoal_1t=Decimal(str(row[11])) if pd.notna(row[11]) else Decimal("0"),
                    atendente=int(row[14]) if pd.notna(row[14]) else 0,
                    aux_cozinha=int(row[15]) if pd.notna(row[15]) else 0,
                    barista=int(row[16]) if pd.notna(row[16]) else 0,
                    gerente=int(row[17]) if pd.notna(row[17]) else 0,
                    lider=int(row[18]) if pd.notna(row[18]) else 0,
                    fte_total=int(row[19]) if pd.notna(row[19]) else 0,
                )
            )
        except (ValueError, TypeError) as e:
            print(f"  [aviso] linha {i} ignorada: {e}")
    return cafes


# =============================================================================
# Simulação
# =============================================================================


def simular_cafe(cafe: Cafe, cenario: str = "neutro") -> ImpactoCafe:
    ratio = _ratio(cenario)
    fte_atual = Decimal(cafe.fte_total)
    fte_raw = fte_atual * ratio
    fte_proposto = Decimal(str(math.ceil(fte_raw * 100) / 100))
    fte_extras = fte_proposto - fte_atual

    folha_atual = cafe.pessoal_mensal
    folha_proposta = (folha_atual * ratio).quantize(Decimal("0.01"))
    delta = folha_proposta - folha_atual
    delta_pct = (
        (delta / folha_atual * 100).quantize(Decimal("0.01"))
        if folha_atual > 0
        else Decimal("0")
    )
    economia_wfm = (folha_proposta * WFM_ECONOMY_PCT).quantize(Decimal("0.01"))

    return ImpactoCafe(
        cafe=cafe,
        ratio=ratio.quantize(Decimal("0.0001")),
        fte_proposto=fte_proposto,
        fte_extras=fte_extras,
        folha_proposta_mes=folha_proposta,
        delta_folha_mes=delta,
        delta_folha_pct=delta_pct,
        economia_wfm_mes=economia_wfm,
    )


# =============================================================================
# Formatação
# =============================================================================


def brl(v) -> str:  # type: ignore[no-untyped-def]
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_short(v) -> str:  # type: ignore[no-untyped-def]
    f = float(v)
    if abs(f) >= 1_000_000:
        return f"R$ {f / 1_000_000:.2f} mi".replace(".", ",")
    if abs(f) >= 1_000:
        return f"R$ {f / 1_000:.0f} mil"
    return f"R$ {f:.0f}"


def pct(v) -> str:  # type: ignore[no-untyped-def]
    return f"{float(v):.2f}%".replace(".", ",")


# =============================================================================
# Relatório
# =============================================================================


def analyze() -> None:
    print()
    print("=" * 90)
    print("  ANÁLISE T&F CAFÉS — IMPACTO DA PEC 8/2025 (transição 6x1 → 5x2)")
    print("=" * 90)
    print()

    cafes = carregar_cafes()
    print(f"  Cafés analisados: {len(cafes)}")
    print()

    impactos_por_cenario = {
        cen: [simular_cafe(c, cen) for c in cafes]
        for cen in ("pessimista", "neutro", "otimista")
    }

    # =========================================================================
    # 1. AGREGADOS
    # =========================================================================
    fat_total = sum(c.faturamento_1t for c in cafes)
    folha_1t = sum(c.pessoal_1t for c in cafes)
    folha_mensal = folha_1t / Decimal("3")
    fte_atual_total = sum(c.fte_total for c in cafes)
    pct_folha_fat = (folha_1t / fat_total * 100) if fat_total > 0 else Decimal("0")

    print("┌" + "─" * 88 + "┐")
    print("│  REDE DE CAFÉS (estado atual em 1T26)" + " " * 50 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  Faturamento 1T26 . . . . . . . . . {brl_short(fat_total):>20}" + " " * 22 + "│")
    print(f"│  Folha 1T26 (pessoal). . . . . . .  {brl_short(folha_1t):>20}" + " " * 22 + "│")
    print(f"│  Folha mensal média atual . . . . . {brl_short(folha_mensal):>20}" + " " * 22 + "│")
    alert = " ⚠️ MUITO ALTO" if pct_folha_fat > 30 else ""
    print(f"│  % folha / faturamento . . . . . . . {pct(pct_folha_fat):>19}{alert}" + " " * (22 - len(alert)) + "│")
    print(f"│  FTEs total (6x1 atual) . . . . . . . {fte_atual_total:>19} FTEs" + " " * 17 + "│")
    print("├" + "─" * 88 + "┤")
    print("│  💡 Comparativo: lojas próprias têm 10,95% folha/fat. Cafés operam com" + " " * 17 + "│")
    print("│     margem MUITO mais apertada — impacto da PEC 8 é proporcionalmente" + " " * 18 + "│")
    print("│     mais grave aqui.                                                 " + " " * 18 + "│")
    print("└" + "─" * 88 + "┘")
    print()

    # =========================================================================
    # 2. POR CENÁRIO
    # =========================================================================
    print("┌" + "─" * 88 + "┐")
    print("│  IMPACTO POR CENÁRIO (rede de cafés, mensal)" + " " * 43 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  {'Cenário':<14}{'FTE total':>13}{'Folha mensal':>18}{'Δ mensal':>17}{'Δ %':>12}    │")
    print("├" + "─" * 88 + "┤")
    for cen in ("pessimista", "neutro", "otimista"):
        impactos = impactos_por_cenario[cen]
        fte_prop = sum(i.fte_proposto for i in impactos)
        folha_prop = sum(i.folha_proposta_mes for i in impactos)
        delta = folha_prop - folha_mensal
        delta_pct = (delta / folha_mensal * 100) if folha_mensal > 0 else Decimal("0")
        print(
            f"│  {cen:<14}"
            f"{float(fte_prop):>13.1f}"
            f"{brl_short(folha_prop):>18}"
            f"{brl_short(delta):>17}"
            f"{pct(delta_pct):>12}    │"
        )
    print("└" + "─" * 88 + "┘")
    print()

    # =========================================================================
    # 3. CENÁRIO NEUTRO — DETALHADO
    # =========================================================================
    impactos_neutro = impactos_por_cenario["neutro"]
    fte_prop_neutro = sum(i.fte_proposto for i in impactos_neutro)
    fte_extras = fte_prop_neutro - Decimal(fte_atual_total)
    folha_prop_neutro = sum(i.folha_proposta_mes for i in impactos_neutro)
    delta_mes = folha_prop_neutro - folha_mensal
    delta_ano = delta_mes * 12
    delta_pct_neutro = (delta_mes / folha_mensal * 100) if folha_mensal > 0 else Decimal("0")
    economia_wfm_total = sum(i.economia_wfm_mes for i in impactos_neutro)

    # Impacto no resultado: assume margem operacional 0 (folha = todo o restante).
    # Aumento de folha → cai direto na DRE.
    impacto_fat_pct = (delta_ano / (fat_total * 4) * 100) if fat_total > 0 else Decimal("0")
    # fat_total é 1T, então anualizado é fat * 4

    print("┌" + "─" * 88 + "┐")
    print("│  CENÁRIO NEUTRO — projeção pós-PEC 8 (premissa Fitch)" + " " * 34 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  FTEs proposto (5x2). . . . . . . . . . {float(fte_prop_neutro):>15.1f} FTEs" + " " * 17 + "│")
    print(f"│  FTEs extras (contratações). . . . . . . {float(fte_extras):>14.1f} FTEs" + " " * 17 + "│")
    print(f"│  Folha mensal proposta . . . . . . . . {brl_short(folha_prop_neutro):>17}" + " " * 22 + "│")
    print(f"│  IMPACTO MENSAL NA REDE . . . . . . . . {brl_short(delta_mes):>17} ({pct(delta_pct_neutro):>7})" + " " * 12 + "│")
    print(f"│  IMPACTO ANUAL . . . . . . . . . . . . {brl_short(delta_ano):>17}" + " " * 22 + "│")
    print(f"│  Impacto no faturamento anual . . . . .                   {pct(impacto_fat_pct):>7}" + " " * 22 + "│")
    print("│" + " " * 88 + "│")
    print(f"│  💡 Economia potencial com WFM (5%). . . {brl_short(economia_wfm_total):>17}/mês" + " " * 18 + "│")
    print(f"│     Anualizado . . . . . . . . . . . . {brl_short(economia_wfm_total * 12):>17}" + " " * 22 + "│")
    print("└" + "─" * 88 + "┘")
    print()

    # =========================================================================
    # 4. CAFÉS EM RISCO ESTRUTURAL (% folha/fat > 70%)
    # =========================================================================
    risco_alto = sorted(
        [c for c in cafes if c.perc_folha_fat > 70],
        key=lambda c: c.perc_folha_fat,
        reverse=True,
    )
    if risco_alto:
        print("┌" + "─" * 88 + "┐")
        print("│  ⚠️  CAFÉS EM RISCO ESTRUTURAL — folha já consome >70% do faturamento" + " " * 16 + "│")
        print("│      Pra estes, o impacto da PEC 8 é potencialmente terminal." + " " * 26 + "│")
        print("├" + "─" * 88 + "┤")
        print(f"│  {'Café':<26}{'Fat 1T26':>13}{'Folha/mês':>13}{'% folha/fat':>15}     │")
        print("├" + "─" * 88 + "┤")
        for c in risco_alto:
            nome = c.nome[:24]
            print(
                f"│  {nome:<26}"
                f"{brl_short(c.faturamento_1t):>13}"
                f"{brl_short(c.pessoal_mensal):>13}"
                f"{pct(c.perc_folha_fat):>15}     │"
            )
        print("└" + "─" * 88 + "┘")
        print()

    # =========================================================================
    # 5. TOP IMPACTOS ABSOLUTOS
    # =========================================================================
    top = sorted(impactos_neutro, key=lambda i: i.delta_folha_mes, reverse=True)
    print("┌" + "─" * 88 + "┐")
    print("│  TOP CAFÉS — impacto absoluto mensal (cenário neutro)" + " " * 34 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  {'#':<3}{'Café':<26}{'FTE→':>8}{'Δ FTE':>7}"
          f"{'Folha→':>13}{'Δ mês':>12}{'Δ %':>10}     │")
    print("├" + "─" * 88 + "┤")
    for n, imp in enumerate(top, 1):
        nome = imp.cafe.nome[:24]
        print(
            f"│  {n:<3}{nome:<26}"
            f"{float(imp.fte_proposto):>8.1f}"
            f"{float(imp.fte_extras):>+7.1f}"
            f"{brl_short(imp.folha_proposta_mes):>13}"
            f"{brl_short(imp.delta_folha_mes):>12}"
            f"{pct(imp.delta_folha_pct):>10}     │"
        )
    print("└" + "─" * 88 + "┘")
    print()

    # =========================================================================
    # 6. QUADRO POR FUNÇÃO (totais da rede)
    # =========================================================================
    total_atend = sum(c.atendente for c in cafes)
    total_aux = sum(c.aux_cozinha for c in cafes)
    total_barista = sum(c.barista for c in cafes)
    total_gerente = sum(c.gerente for c in cafes)
    total_lider = sum(c.lider for c in cafes)

    print("┌" + "─" * 88 + "┐")
    print("│  QUADRO POR FUNÇÃO (rede atual)" + " " * 56 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  Atendente . . . . . . . . . . . . . . {total_atend:>5} FTEs ({total_atend/fte_atual_total*100:.0f}%)" + " " * 23 + "│")
    print(f"│  Barista . . . . . . . . . . . . . . . {total_barista:>5} FTEs ({total_barista/fte_atual_total*100:.0f}%)" + " " * 23 + "│")
    print(f"│  Gerente de Loja . . . . . . . . . . . {total_gerente:>5} FTEs ({total_gerente/fte_atual_total*100:.0f}%)" + " " * 23 + "│")
    print(f"│  Líder . . . . . . . . . . . . . . . . {total_lider:>5} FTEs ({total_lider/fte_atual_total*100:.0f}%)" + " " * 23 + "│")
    print(f"│  Auxiliar de Cozinha . . . . . . . . . {total_aux:>5} FTEs ({total_aux/fte_atual_total*100:.0f}%)" + " " * 23 + "│")
    print(f"│  ─" + "─" * 84 + "│")
    print(f"│  TOTAL . . . . . . . . . . . . . . . . {fte_atual_total:>5} FTEs" + " " * 32 + "│")
    print("└" + "─" * 88 + "┘")
    print()

    # =========================================================================
    # 7. DETALHE POR CAFÉ
    # =========================================================================
    print("=" * 90)
    print("  DETALHE POR CAFÉ (cenário neutro, ordenado por impacto mensal absoluto)")
    print("=" * 90)
    print(
        f"  {'Café':<26}{'Fat 1T26':>13}{'Folha/mês':>13}{'%f/f':>8}"
        f"{'FTE':>5}{'FTE→':>7}{'Δ folha mês':>15}"
    )
    print("-" * 90)
    for imp in top:
        nome = imp.cafe.nome[:24]
        print(
            f"  {nome:<26}"
            f"{brl_short(imp.cafe.faturamento_1t):>13}"
            f"{brl_short(imp.cafe.pessoal_mensal):>13}"
            f"{pct(imp.cafe.perc_folha_fat):>8}"
            f"{imp.cafe.fte_total:>5}"
            f"{float(imp.fte_proposto):>7.1f}"
            f"{brl_short(imp.delta_folha_mes):>15}"
        )
    print()

    # =========================================================================
    # 8. COMPARATIVO COM LOJAS PRÓPRIAS
    # =========================================================================
    print("=" * 90)
    print("  COMPARATIVO: CAFÉS vs LOJAS PRÓPRIAS (mesma metodologia, ambos 1T26)")
    print("=" * 90)
    print()
    print(f"  {'Métrica':<35}{'Cafés':>20}{'Lojas Próprias':>22}")
    print("  " + "-" * 80)
    print(f"  {'Unidades':<35}{len(cafes):>20}{55:>22}")
    print(f"  {'Faturamento 1T26':<35}{brl_short(fat_total):>20}{brl_short(192_339_879):>22}")
    print(f"  {'Folha 1T26':<35}{brl_short(folha_1t):>20}{brl_short(21_068_490):>22}")
    print(f"  {'% folha/faturamento':<35}{pct(pct_folha_fat):>20}{pct(10.95):>22}")
    print(f"  {'FTEs (6x1)':<35}{fte_atual_total:>20}{728:>22}")
    print(f"  {'Δ folha mês (neutro)':<35}{brl_short(delta_mes):>20}{brl_short(683_000):>22}")
    print(f"  {'Δ folha ano (neutro)':<35}{brl_short(delta_ano):>20}{brl_short(8_200_000):>22}")
    print(f"  {'Δ ano / Faturamento ano':<35}{pct(impacto_fat_pct):>20}{pct(1.07):>22}")
    print()
    print("  💡 Conclusão: em valor absoluto o impacto é menor nos cafés (R$ X vs R$ 8,2 mi),")
    print("     mas em % SOBRE O FATURAMENTO o cafés sofrem MUITO mais — porque a estrutura")
    print("     de margem deles já está pressionada por folha em ~56% do faturamento.")
    print()

    # =========================================================================
    # 9. EXPORT CSV
    # =========================================================================
    out_dir = Path(__file__).resolve().parents[1] / "tmp"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "analise_tf_cafes_1t26.csv"
    _export_csv(impactos_por_cenario, cafes, csv_path)
    print(f"[OK] CSV exportado em: {csv_path}")
    print()


def _export_csv(impactos_por_cenario, cafes, path: Path) -> None:
    rows = []
    for c in cafes:
        row = {
            "cafe": c.nome,
            "faturamento_1t": float(c.faturamento_1t),
            "pessoal_1t": float(c.pessoal_1t),
            "folha_mensal_atual": float(c.pessoal_mensal),
            "pct_folha_fat": float(c.perc_folha_fat),
            "custo_medio_fte_mes": float(c.custo_medio_por_fte_mes),
            "fte_total_atual": c.fte_total,
            "atendente": c.atendente,
            "aux_cozinha": c.aux_cozinha,
            "barista": c.barista,
            "gerente": c.gerente,
            "lider": c.lider,
        }
        for cen in ("pessimista", "neutro", "otimista"):
            imp = next(i for i in impactos_por_cenario[cen] if i.cafe.nome == c.nome)
            row[f"fte_{cen}"] = float(imp.fte_proposto)
            row[f"folha_{cen}"] = float(imp.folha_proposta_mes)
            row[f"delta_mes_{cen}"] = float(imp.delta_folha_mes)
            row[f"delta_pct_{cen}"] = float(imp.delta_folha_pct)
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False, sep=";", encoding="utf-8-sig")


# =============================================================================
# CLI
# =============================================================================


def inspect() -> None:
    print(f"[arquivo] {EXCEL_PATH}")
    xl = pd.ExcelFile(EXCEL_PATH)
    print(f"[sheets] {xl.sheet_names}")
    for sn in xl.sheet_names:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sn)
        print(f"  - '{sn}': {len(df)} linhas x {len(df.columns)} colunas")


def dump_raw() -> None:
    df = pd.read_excel(EXCEL_PATH, sheet_name="RESUMO CAFÉ", header=None)
    for i in range(len(df)):
        row = df.iloc[i].tolist()
        cells = [str(x)[:18] if pd.notna(x) else "(nan)" for x in row]
        print(f"  [{i:>2}] " + " | ".join(f"{c:<18}" for c in cells))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "inspect":
        inspect()
    elif cmd == "raw":
        dump_raw()
    elif cmd == "analyze":
        analyze()
    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
