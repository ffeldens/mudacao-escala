"""escala-engine — motor de cálculo do escala-toolkit.

Pacote Python puro, sem dependência de framework. Responsável por:
- Simular impacto da migração 6x1 → 5x2 (Simulador v1.0)
- Validar escalas contra a régua CLT (Simulador + Planejador)
- Calcular cobertura horária e impacto financeiro
- Gerar dados sintéticos (ticket history, escalas) para demos sem dados reais

Ver `docs/PRD.md` seções 5-8 para especificação completa.
"""

from engine.clt_validator import validate_clt
from engine.compare import (
    ComparisonResult,
    ScheduleMetrics,
    compare_schedules,
    compute_metrics,
)
from engine.core import simulate
from engine.csv_import import (
    TEMPLATES,
    ImportResult,
    parse_employees_csv,
    parse_sales_history_csv,
    parse_schedule_baseline_csv,
)
from engine.models import (
    CLTValidationResult,
    CLTViolation,
    EmployeeRecord,
    FinancialAssumptions,
    FunctionRole,
    Schedule,
    ScheduleEmployee,
    ScheduleShift,
    ScenarioConfig,
    SimulationInput,
    SimulationOutput,
    StoreInput,
    TicketHistoryPoint,
)
from engine.ranking import PESOS_DEFAULT, rank_candidatas_piloto
from engine.scheduler import SchedulerError, plan_schedule
from engine.synthetic_demand import CLUSTER_FACTORS, generate_ticket_history
from engine.synthetic_network import generate_store, generate_synthetic_network
from engine.synthetic_schedule import generate_synthetic_schedule

__version__ = "0.5.0"

__all__ = [
    "simulate",
    "validate_clt",
    "plan_schedule",
    "SchedulerError",
    "generate_ticket_history",
    "generate_synthetic_schedule",
    "generate_synthetic_network",
    "generate_store",
    "rank_candidatas_piloto",
    "PESOS_DEFAULT",
    "CLUSTER_FACTORS",
    "SimulationInput",
    "SimulationOutput",
    "StoreInput",
    "FunctionRole",
    "FinancialAssumptions",
    "ScenarioConfig",
    "TicketHistoryPoint",
    "Schedule",
    "ScheduleEmployee",
    "ScheduleShift",
    "CLTValidationResult",
    "CLTViolation",
    "EmployeeRecord",
    "ImportResult",
    "TEMPLATES",
    "parse_employees_csv",
    "parse_sales_history_csv",
    "parse_schedule_baseline_csv",
    "compare_schedules",
    "compute_metrics",
    "ScheduleMetrics",
    "ComparisonResult",
]
