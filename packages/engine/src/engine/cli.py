"""CLI do engine — entrypoint via `engine`.

Uso:
    engine simulate --input fixture.json --scenario neutro
    engine simulate --input fixture.json --output result.json
    engine validate-clt --escala escala.json
    engine info
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from engine import __version__
from engine.clt_validator import validate_clt
from engine.core import simulate
from engine.models import Schedule, SimulationInput

console = Console()


@click.group()
@click.version_option(__version__, prog_name="escala-engine")
def main() -> None:
    """Motor de cálculo do escala-toolkit."""


@main.command(name="simulate")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON com SimulationInput",
)
@click.option(
    "--scenario",
    type=click.Choice(["pessimista", "neutro", "otimista"]),
    default=None,
    help="Sobrescreve o cenário do input (opcional)",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Salva o resultado em arquivo JSON (opcional)",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Não imprime tabela; útil para piping",
)
def simulate_cmd(
    input_path: Path,
    scenario: str | None,
    output_path: Path | None,
    quiet: bool,
) -> None:
    """Roda uma simulação 6x1 → 5x2."""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    sim_input = SimulationInput(**data)
    if scenario:
        sim_input.scenario.cenario = scenario  # type: ignore[assignment]

    result = simulate(sim_input)

    if output_path:
        output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[green]✓[/green] Resultado salvo em {output_path}")

    if quiet:
        click.echo(result.model_dump_json())
        return

    _print_simulation_result(sim_input, result)


@main.command(name="validate-clt")
@click.option(
    "--escala",
    "escala_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON com Schedule",
)
@click.option(
    "--clt-version",
    default="2026-04",
    help="Versão da régua CLT a aplicar",
)
def validate_clt_cmd(escala_path: Path, clt_version: str) -> None:
    """Valida uma escala contra a régua CLT."""
    with open(escala_path, encoding="utf-8") as f:
        data = json.load(f)

    schedule = Schedule(**data)
    result = validate_clt(schedule=schedule, clt_version=clt_version)

    if result.is_valid:
        console.print(
            Panel(
                "[bold green]✓ Escala válida[/bold green]\n"
                f"CLT versão: {clt_version}\n"
                f"Shifts validados: {len(schedule.shifts)}",
                title="Validação CLT",
            )
        )
        return

    console.print(
        Panel(
            f"[bold red]✗ {len(result.violations)} violação(ões) detectada(s)[/bold red]",
            title="Validação CLT",
        )
    )

    table = Table(show_header=True, header_style="bold red")
    table.add_column("Artigo", width=14)
    table.add_column("Colaborador", width=20)
    table.add_column("Data", width=12)
    table.add_column("Descrição")

    for v in result.violations:
        table.add_row(
            v.artigo,
            v.employee_id or "-",
            v.data or "-",
            v.descricao,
        )

    console.print(table)
    sys.exit(1)


@main.command(name="info")
def info_cmd() -> None:
    """Mostra informações do engine."""
    console.print(
        Panel(
            f"[bold]escala-engine[/bold] v{__version__}\n\n"
            "Motor de cálculo do escala-toolkit.\n"
            "Simula impacto da migração 6x1 → 5x2 e valida escalas contra a CLT.\n\n"
            "Comandos:\n"
            "  • engine simulate     — roda uma simulação\n"
            "  • engine validate-clt — valida uma escala\n"
            "  • engine info         — esta tela",
            title="ℹ️  Sobre",
        )
    )


def _print_simulation_result(input_: SimulationInput, output) -> None:
    """Imprime resultado da simulação no terminal."""
    console.print()
    console.print(
        Panel(
            f"[bold]{input_.store.nome}[/bold] · {input_.store.codigo} · "
            f"brand={input_.store.brand} · cluster={input_.store.cluster}\n"
            f"Cenário: [cyan]{input_.scenario.cenario}[/cyan] · "
            f"CLT: {input_.clt_version}",
            title="Simulação 6x1 → 5x2",
        )
    )

    # KPIs principais
    table = Table(title="KPIs principais", show_header=True, header_style="bold cyan")
    table.add_column("Métrica")
    table.add_column("Atual (6x1)", justify="right")
    table.add_column("Proposto (5x2)", justify="right")
    table.add_column("Delta", justify="right")

    table.add_row(
        "Folha mensal",
        f"R$ {output.folha_atual_mes:,.2f}",
        f"R$ {output.folha_proposta_mes:,.2f}",
        f"[red]+R$ {output.delta_folha_mes:,.2f}[/red] "
        f"({output.delta_folha_pct:+.1f}%)",
    )
    table.add_row(
        "FTEs total",
        f"{output.fte_atual_total}",
        f"{output.fte_proposto_total}",
        f"[yellow]+{output.fte_proposto_total - output.fte_atual_total}[/yellow]",
    )
    if output.folha_sobre_faturamento_atual:
        table.add_row(
            "Folha / Faturamento",
            f"{output.folha_sobre_faturamento_atual:.1f}%",
            f"{output.folha_sobre_faturamento_proposto:.1f}%",
            "",
        )
    console.print(table)

    # Cenários
    table_c = Table(title="Cenários", show_header=True, header_style="bold magenta")
    table_c.add_column("Cenário")
    table_c.add_column("Ratio FTE", justify="right")
    table_c.add_column("FTE total", justify="right")
    table_c.add_column("Δ folha", justify="right")
    for cenario, r in output.cenarios.items():
        table_c.add_row(
            cenario.capitalize(),
            f"{r.ratio_aplicado:.3f}×",
            f"{r.fte_total}",
            f"{r.delta_folha_pct:+.1f}%",
        )
    console.print(table_c)

    # Riscos
    if output.riscos_clt:
        table_r = Table(title="Riscos CLT & operacionais", show_header=True)
        table_r.add_column("Severidade", width=10)
        table_r.add_column("Artigo", width=14)
        table_r.add_column("Título", width=30)
        table_r.add_column("Descrição")
        for risco in output.riscos_clt:
            cor = {
                "good": "green",
                "info": "cyan",
                "warn": "yellow",
                "bad": "red",
            }.get(risco.severidade, "white")
            table_r.add_row(
                f"[{cor}]{risco.severidade.upper()}[/{cor}]",
                risco.artigo,
                risco.titulo,
                risco.descricao,
            )
        console.print(table_r)


if __name__ == "__main__":
    main()
