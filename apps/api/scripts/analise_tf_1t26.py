"""Análise do impacto da PEC 8/2025 nas lojas próprias T&F — dados 1T26.

Aplica a fórmula do engine MudAção Escala em cada uma das 55 lojas próprias
e agrega o impacto na rede inteira + por cluster.

Uso:
    cd apps/api
    uv run --with openpyxl --with pandas python scripts/analise_tf_1t26.py [comando]

Comandos:
    inspect   — lista sheets e colunas (debug)
    raw       — dump das primeiras 30 linhas raw
    analyze   — roda a análise completa e imprime relatório (default)
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

# Força UTF-8 no stdout (Windows console default é cp1252)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

import math  # noqa: E402

import pandas as pd  # noqa: E402

EXCEL_PATH = Path(r"C:\Users\felip\Downloads\INFORMAÇÕES 1T26.xlsx")

# =============================================================================
# Constantes do engine MudAção (replicadas — mesmas de packages/engine/core.py)
# =============================================================================
JORNADA_6X1 = Decimal("44")
JORNADA_5X2 = Decimal("40")
RATIO_BASE = JORNADA_6X1 / JORNADA_5X2  # 1.10

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
GANHO_PROD_DEFAULT = Decimal("0.05")  # 5%

# Economia WFM (% da folha proposta — pitch dos planos pagos)
WFM_ECONOMY_PCT = Decimal("0.05")  # 5%


def _ratio(cenario: str) -> Decimal:
    fator_perdas = FATOR_PERDAS[cenario]
    peso = PESO_GANHO_PROD[cenario]
    ajuste = Decimal("1") - GANHO_PROD_DEFAULT * peso
    return RATIO_BASE * fator_perdas * ajuste


RATIO_PESSIMISTA = _ratio("pessimista")  # ~1.18
RATIO_NEUTRO = _ratio("neutro")  # ~1.097
RATIO_OTIMISTA = _ratio("otimista")  # ~0.997


# =============================================================================
# Modelos de domínio
# =============================================================================


@dataclass
class Loja:
    """Loja T&F com os dados do 1T26."""

    cluster: str
    nome: str
    faturamento_1t: Decimal
    pessoal_1t: Decimal  # acumulado trimestral, com encargos
    fte_total: int
    # Quadro por função (qtd FTEs)
    auxiliar: int
    vendedor: int
    estoquista: int
    gerente: int
    op_caixa: int
    sub_gerente: int

    @property
    def pessoal_mensal(self) -> Decimal:
        """Folha mensal (média do trimestre)."""
        return (self.pessoal_1t / Decimal("3")).quantize(Decimal("0.01"))

    @property
    def custo_medio_por_fte_mes(self) -> Decimal:
        """Custo médio por FTE/mês (já com encargos)."""
        if self.fte_total == 0:
            return Decimal("0")
        return (self.pessoal_mensal / self.fte_total).quantize(Decimal("0.01"))

    @property
    def perc_folha_fat(self) -> Decimal:
        """% da folha sobre o faturamento."""
        if self.faturamento_1t == 0:
            return Decimal("0")
        return (self.pessoal_1t / self.faturamento_1t * 100).quantize(Decimal("0.01"))


@dataclass
class ImpactoLoja:
    """Resultado da simulação 5x2 pra uma loja."""

    loja: Loja
    ratio: Decimal
    fte_proposto: Decimal
    fte_extras: Decimal
    folha_proposta_mes: Decimal
    delta_folha_mes: Decimal
    delta_folha_pct: Decimal
    economia_wfm_mes: Decimal


# =============================================================================
# Leitura do Excel
# =============================================================================


def carregar_lojas() -> list[Loja]:
    """Lê o Excel e retorna a lista de Lojas."""
    df = pd.read_excel(EXCEL_PATH, sheet_name="1Q26", header=None)

    lojas: list[Loja] = []
    # Dados começam na linha 3 (índices 0-2 são headers/título)
    for i in range(3, len(df)):
        row = df.iloc[i]
        cluster = row[0]
        nome = row[1]
        # Pula linhas vazias ou de totalização
        if pd.isna(cluster) or pd.isna(nome):
            continue
        try:
            lojas.append(
                Loja(
                    cluster=str(cluster).strip(),
                    nome=str(nome).strip(),
                    faturamento_1t=Decimal(str(row[2])) if pd.notna(row[2]) else Decimal("0"),
                    pessoal_1t=Decimal(str(row[3])) if pd.notna(row[3]) else Decimal("0"),
                    auxiliar=int(row[6]) if pd.notna(row[6]) else 0,
                    vendedor=int(row[7]) if pd.notna(row[7]) else 0,
                    estoquista=int(row[8]) if pd.notna(row[8]) else 0,
                    gerente=int(row[9]) if pd.notna(row[9]) else 0,
                    op_caixa=int(row[10]) if pd.notna(row[10]) else 0,
                    sub_gerente=int(row[11]) if pd.notna(row[11]) else 0,
                    fte_total=int(row[12]) if pd.notna(row[12]) else 0,
                )
            )
        except (ValueError, TypeError) as e:
            print(f"  [aviso] linha {i} ignorada: {e}")
    return lojas


# =============================================================================
# Simulação
# =============================================================================


def simular_loja(loja: Loja, cenario: str = "neutro") -> ImpactoLoja:
    """Aplica a fórmula do engine MudAção Escala numa loja.

    Premissas:
      - manter_salario_nominal = True (custo médio por FTE preservado)
      - ganho_produtividade = 5%
      - folha proposta = folha atual × ratio (proporcionalidade)
      - FTE proposto = ceil(FTE atual × ratio, 2 casas)
    """
    ratio = _ratio(cenario)

    fte_atual = Decimal(loja.fte_total)
    fte_raw = fte_atual * ratio
    fte_proposto = Decimal(str(math.ceil(fte_raw * 100) / 100))
    fte_extras = fte_proposto - fte_atual

    folha_atual = loja.pessoal_mensal
    folha_proposta = (folha_atual * ratio).quantize(Decimal("0.01"))
    delta_folha = folha_proposta - folha_atual
    delta_pct = (
        (delta_folha / folha_atual * 100).quantize(Decimal("0.01"))
        if folha_atual > 0
        else Decimal("0")
    )

    economia_wfm = (folha_proposta * WFM_ECONOMY_PCT).quantize(Decimal("0.01"))

    return ImpactoLoja(
        loja=loja,
        ratio=ratio.quantize(Decimal("0.0001")),
        fte_proposto=fte_proposto,
        fte_extras=fte_extras,
        folha_proposta_mes=folha_proposta,
        delta_folha_mes=delta_folha,
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
    print("  ANÁLISE T&F 1T26 — IMPACTO DA PEC 8/2025 (transição 6x1 → 5x2)")
    print("=" * 90)
    print()

    lojas = carregar_lojas()
    print(f"  Lojas próprias analisadas: {len(lojas)}")
    print()

    # Roda os 3 cenários
    impactos_por_cenario = {
        cen: [simular_loja(loja, cen) for loja in lojas]
        for cen in ("pessimista", "neutro", "otimista")
    }

    # ===========================================================================
    # 1. AGREGADOS DA REDE
    # ===========================================================================
    fat_total_1t = sum(loja.faturamento_1t for loja in lojas)
    folha_1t = sum(loja.pessoal_1t for loja in lojas)
    folha_mensal_atual = folha_1t / Decimal("3")
    fte_atual_total = sum(loja.fte_total for loja in lojas)

    print("┌" + "─" * 88 + "┐")
    print("│  REDE COMPLETA (estado atual em 1T26)" + " " * 50 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  Faturamento 1T26 . . . . . . . . . {brl_short(fat_total_1t):>20}" + " " * 22 + "│")
    print(f"│  Folha 1T26 (pessoal). . . . . . .  {brl_short(folha_1t):>20}" + " " * 22 + "│")
    print(f"│  Folha mensal média atual . . . . . {brl_short(folha_mensal_atual):>20}" + " " * 22 + "│")
    pct_folha = (folha_1t / fat_total_1t * 100) if fat_total_1t > 0 else Decimal("0")
    print(f"│  % folha / faturamento . . . . . . . {pct(pct_folha):>19}" + " " * 22 + "│")
    print(f"│  FTEs total (6x1 atual) . . . . . . . {fte_atual_total:>19} FTEs" + " " * 17 + "│")
    print("└" + "─" * 88 + "┘")
    print()

    # ===========================================================================
    # 2. POR CENÁRIO (RESUMO)
    # ===========================================================================
    print("┌" + "─" * 88 + "┐")
    print("│  IMPACTO POR CENÁRIO (rede inteira, mensal)" + " " * 44 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  {'Cenário':<14}{'FTE total':>13}{'Folha mensal':>18}{'Δ mensal':>17}{'Δ %':>12}    │")
    print("├" + "─" * 88 + "┤")
    for cen in ("pessimista", "neutro", "otimista"):
        impactos = impactos_por_cenario[cen]
        fte_proposto_total = sum(i.fte_proposto for i in impactos)
        folha_proposta_total = sum(i.folha_proposta_mes for i in impactos)
        delta = folha_proposta_total - folha_mensal_atual
        delta_pct = (delta / folha_mensal_atual * 100) if folha_mensal_atual > 0 else Decimal("0")
        print(
            f"│  {cen:<14}"
            f"{float(fte_proposto_total):>13.1f}"
            f"{brl_short(folha_proposta_total):>18}"
            f"{brl_short(delta):>17}"
            f"{pct(delta_pct):>12}    │"
        )
    print("└" + "─" * 88 + "┘")
    print()

    # ===========================================================================
    # 3. CENÁRIO NEUTRO — DETALHADO
    # ===========================================================================
    impactos_neutro = impactos_por_cenario["neutro"]
    fte_proposto = sum(i.fte_proposto for i in impactos_neutro)
    fte_extras_total = fte_proposto - Decimal(fte_atual_total)
    folha_proposta = sum(i.folha_proposta_mes for i in impactos_neutro)
    delta_mes = folha_proposta - folha_mensal_atual
    delta_ano = delta_mes * 12
    delta_pct_neutro = (delta_mes / folha_mensal_atual * 100) if folha_mensal_atual > 0 else Decimal("0")
    economia_wfm_total = sum(i.economia_wfm_mes for i in impactos_neutro)

    print("┌" + "─" * 88 + "┐")
    print("│  CENÁRIO NEUTRO (premissa Fitch) — projeção pós-PEC 8" + " " * 34 + "│")
    print("├" + "─" * 88 + "┤")
    print(f"│  FTEs proposto (5x2). . . . . . . . . . {float(fte_proposto):>15.1f} FTEs" + " " * 17 + "│")
    print(f"│  FTEs extras (contratações). . . . . . . {float(fte_extras_total):>14.1f} FTEs" + " " * 17 + "│")
    print(f"│  Folha mensal proposta . . . . . . . . {brl_short(folha_proposta):>17}" + " " * 22 + "│")
    print(f"│  IMPACTO MENSAL NA REDE . . . . . . . . {brl_short(delta_mes):>17} ({pct(delta_pct_neutro):>7})" + " " * 12 + "│")
    print(f"│  IMPACTO ANUAL . . . . . . . . . . . . {brl_short(delta_ano):>17}" + " " * 22 + "│")
    print("│" + " " * 88 + "│")
    print(f"│  💡 Economia potencial com WFM (5%). . . {brl_short(economia_wfm_total):>17}/mês" + " " * 18 + "│")
    print(f"│     Anualizado . . . . . . . . . . . . {brl_short(economia_wfm_total * 12):>17}" + " " * 22 + "│")
    print("└" + "─" * 88 + "┘")
    print()

    # ===========================================================================
    # 4. POR CLUSTER
    # ===========================================================================
    print("┌" + "─" * 88 + "┐")
    print("│  POR CLUSTER (cenário neutro)" + " " * 58 + "│")
    print("├" + "─" * 88 + "┤")
    print(
        f"│  {'Cluster':<10}{'Lojas':>7}{'Fat 1T26':>13}{'Folha/mês':>13}"
        f"{'FTE→':>10}{'Δ FTE':>8}{'Δ folha mês':>16}    │"
    )
    print("├" + "─" * 88 + "┤")

    # Agrupa por cluster
    por_cluster: dict[str, list[ImpactoLoja]] = {}
    for imp in impactos_neutro:
        por_cluster.setdefault(imp.loja.cluster, []).append(imp)

    ordem = ["alto", "médio", "baixo", "Outlet"]
    for cluster in ordem + [c for c in por_cluster if c not in ordem]:
        if cluster not in por_cluster:
            continue
        grupo = por_cluster[cluster]
        n_lojas = len(grupo)
        fat_grupo = sum(i.loja.faturamento_1t for i in grupo)
        folha_grupo = sum(i.loja.pessoal_mensal for i in grupo)
        fte_atual_grupo = sum(i.loja.fte_total for i in grupo)
        fte_prop_grupo = sum(i.fte_proposto for i in grupo)
        delta_grupo = sum(i.delta_folha_mes for i in grupo)
        print(
            f"│  {cluster:<10}"
            f"{n_lojas:>7}"
            f"{brl_short(fat_grupo):>13}"
            f"{brl_short(folha_grupo):>13}"
            f"{float(fte_prop_grupo):>10.1f}"
            f"{float(fte_prop_grupo - Decimal(fte_atual_grupo)):>+8.1f}"
            f"{brl_short(delta_grupo):>16}    │"
        )
    print("└" + "─" * 88 + "┘")
    print()

    # ===========================================================================
    # 5. TOP 10 LOJAS POR IMPACTO ABSOLUTO
    # ===========================================================================
    top10 = sorted(impactos_neutro, key=lambda i: i.delta_folha_mes, reverse=True)[:10]
    print("┌" + "─" * 88 + "┐")
    print("│  TOP 10 LOJAS — maior impacto absoluto mensal (cenário neutro)" + " " * 25 + "│")
    print("├" + "─" * 88 + "┤")
    print(
        f"│  {'#':<3}{'Loja':<28}{'Clust':<8}{'FTE→':>8}{'Δ FTE':>7}"
        f"{'Folha→':>13}{'Δ mês':>12}{'Δ %':>10}    │"
    )
    print("├" + "─" * 88 + "┤")
    for n, imp in enumerate(top10, 1):
        nome_short = imp.loja.nome[:26]
        print(
            f"│  {n:<3}{nome_short:<28}{imp.loja.cluster[:7]:<8}"
            f"{float(imp.fte_proposto):>8.1f}"
            f"{float(imp.fte_extras):>+7.1f}"
            f"{brl_short(imp.folha_proposta_mes):>13}"
            f"{brl_short(imp.delta_folha_mes):>12}"
            f"{pct(imp.delta_folha_pct):>10}    │"
        )
    print("└" + "─" * 88 + "┘")
    print()

    # ===========================================================================
    # 6. TODAS AS LOJAS — TABELA DETALHADA
    # ===========================================================================
    print("=" * 90)
    print("  DETALHE POR LOJA (cenário neutro, ordenado por impacto mensal absoluto)")
    print("=" * 90)
    print(
        f"  {'Loja':<26}{'Clust':<8}{'Fat 1T26':>13}{'Folha/mês':>13}"
        f"{'FTE':>6}{'FTE→':>7}{'Δ folha mês':>15}"
    )
    print("-" * 90)
    todas_ordenadas = sorted(impactos_neutro, key=lambda i: i.delta_folha_mes, reverse=True)
    for imp in todas_ordenadas:
        nome_short = imp.loja.nome[:24]
        print(
            f"  {nome_short:<26}"
            f"{imp.loja.cluster[:7]:<8}"
            f"{brl_short(imp.loja.faturamento_1t):>13}"
            f"{brl_short(imp.loja.pessoal_mensal):>13}"
            f"{imp.loja.fte_total:>6}"
            f"{float(imp.fte_proposto):>7.1f}"
            f"{brl_short(imp.delta_folha_mes):>15}"
        )

    # ===========================================================================
    # 7. EXPORT CSV
    # ===========================================================================
    out_dir = Path(__file__).resolve().parents[1] / "tmp"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "analise_tf_1t26.csv"
    _export_csv(impactos_por_cenario, lojas, csv_path)
    print()
    print(f"[OK] CSV exportado em: {csv_path}")
    print()


def _export_csv(impactos_por_cenario, lojas, path: Path) -> None:
    """Gera um CSV detalhado com todos os cenários por loja."""
    rows = []
    for loja in lojas:
        row = {
            "cluster": loja.cluster,
            "loja": loja.nome,
            "faturamento_1t": float(loja.faturamento_1t),
            "pessoal_1t": float(loja.pessoal_1t),
            "folha_mensal_atual": float(loja.pessoal_mensal),
            "pct_folha_fat": float(loja.perc_folha_fat),
            "custo_medio_fte_mes": float(loja.custo_medio_por_fte_mes),
            "fte_total_atual": loja.fte_total,
            "auxiliar": loja.auxiliar,
            "vendedor": loja.vendedor,
            "estoquista": loja.estoquista,
            "gerente": loja.gerente,
            "op_caixa": loja.op_caixa,
            "sub_gerente": loja.sub_gerente,
        }
        for cen in ("pessimista", "neutro", "otimista"):
            imp = next(i for i in impactos_por_cenario[cen] if i.loja.nome == loja.nome)
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
    """Lista sheets, dimensões e primeiras linhas de cada sheet."""
    print(f"[arquivo] {EXCEL_PATH}")
    xl = pd.ExcelFile(EXCEL_PATH)
    print(f"[sheets] {len(xl.sheet_names)} encontradas: {xl.sheet_names}")
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
        print(f"  - '{sheet_name}': {len(df)} linhas x {len(df.columns)} colunas")


def dump_raw() -> None:
    df = pd.read_excel(EXCEL_PATH, sheet_name="1Q26", header=None)
    for i in range(min(30, len(df))):
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
