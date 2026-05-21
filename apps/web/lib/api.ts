/**
 * Cliente da API freemium.
 *
 * Em dev: Next reescreve /api/* → http://127.0.0.1:8012/api/*
 * Em prod: mesma máquina, FastAPI no loopback :8012.
 */

export type Cenario = "pessimista" | "neutro" | "otimista";
export type Porte = "PP" | "P" | "M" | "G";
export type Setor = "varejo" | "food_service" | "outros";

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
