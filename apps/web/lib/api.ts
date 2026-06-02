/**
 * Cliente da API freemium.
 *
 * Em dev: Next reescreve /api/* → http://127.0.0.1:8012/api/*
 * Em prod: mesma máquina, FastAPI no loopback :8012.
 */

export type Cenario = "pessimista" | "neutro" | "otimista";
export type Porte = "PP" | "P" | "M" | "G";
export type Setor = "varejo" | "food_service" | "outros";

export type ArredondamentoFte = "meio" | "inteiro" | "decimal";

export interface SimulateRequest {
  nome_loja?: string;
  setor: Setor;
  porte: Porte;
  fte_atual: number;
  salario_medio: string; // decimal como string (precisão)
  faturamento_mensal?: string;
  hora_abertura?: number;
  hora_fechamento?: number;
  dias_operacao_semana?: number;
  cenario: Cenario;
  ganho_produtividade_pct?: string;
  manter_salario_nominal?: boolean;
  arredondamento_fte?: ArredondamentoFte;
  n_lojas_rede: number;
}

export interface CenarioOut {
  cenario: string;
  ratio_aplicado: string;
  fte_total: string;
  folha_total: string;
  delta_folha: string;
  delta_folha_pct: string;
}

export interface SimulateResponse {
  inputs_hash: string;
  folha_atual_mes: string;
  folha_proposta_mes: string;
  delta_folha_mes: string;
  delta_folha_pct: string;
  fte_atual: string;
  fte_proposto: string;
  fte_extras_necessarios: string;
  cenarios: Record<string, CenarioOut>;
  n_lojas: number;
  delta_folha_rede_mes: string;
  delta_folha_rede_ano: string;
  headline: string;
  economia_potencial_wfm: string;
  economia_potencial_wfm_pct: string;
}

export interface LeadRequest {
  email: string;
  whatsapp?: string;
  nome?: string;
  empresa?: string;
  n_lojas: number;
  porte: Porte;
  setor: Setor;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}

export async function simulate(payload: SimulateRequest): Promise<SimulateResponse> {
  const r = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    throw new Error(`Simulação falhou: ${r.status} ${await r.text()}`);
  }
  return r.json();
}

export async function leadAndSimulate(
  lead: LeadRequest,
  sim: SimulateRequest,
): Promise<SimulateResponse> {
  const r = await fetch("/api/lead-and-simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lead_req: lead, sim_req: sim }),
  });
  if (!r.ok) {
    throw new Error(`Lead+Simulação falhou: ${r.status} ${await r.text()}`);
  }
  return r.json();
}

// =============================================================================
// Histórico de simulações (Starter+)
// =============================================================================

export interface SimulationHistoryItem {
  id: string;
  nome_loja: string | null;
  n_lojas: number;
  delta_folha_pct: string | null;
  economia_estimada_mes: string | null;
  headline: string | null;
  created_at: string;
}

export interface SimulationHistoryResponse {
  items: SimulationHistoryItem[];
  total: number;
}

/**
 * Lista as simulações do user logado. Precisa de access token Supabase.
 * Requer plano pago (Starter+) — backend retorna 403 se Free.
 */
export async function listMySimulations(
  accessToken: string,
  opts: { limit?: number; offset?: number } = {},
): Promise<SimulationHistoryResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.offset) params.set("offset", String(opts.offset));

  const r = await fetch(`/api/me/simulations?${params}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) {
    throw new Error(
      `Falha ao listar histórico: ${r.status} ${await r.text()}`,
    );
  }
  return r.json();
}

/**
 * Carrega uma simulação salva pelo ID. Retorna o SimulateResponse completo
 * pra ser exibido na página de resultado.
 */
export async function getMySimulation(
  accessToken: string,
  simulationId: string,
): Promise<SimulateResponse> {
  const r = await fetch(`/api/me/simulations/${simulationId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) {
    throw new Error(`Simulação não encontrada: ${r.status}`);
  }
  return r.json();
}
