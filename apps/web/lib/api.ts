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

// =============================================================================
// Export Excel (Sprint 3 #4)
// =============================================================================

/**
 * Baixa .xlsx multi-aba de uma simulação salva (histórico).
 * Dispara o download direto no navegador.
 */
export async function downloadExcelFromHistory(
  accessToken: string,
  simulationId: string,
): Promise<void> {
  const r = await fetch(
    `/api/me/simulations/${simulationId}/export-excel`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  if (!r.ok) {
    let msg = `Falha ao exportar: ${r.status}`;
    try {
      const j = await r.json();
      if (j.detail) msg = j.detail;
    } catch {
      /* ignora */
    }
    throw new Error(msg);
  }
  await _downloadBlob(r, `simulacao-${simulationId.slice(0, 8)}.xlsx`);
}

/**
 * Baixa .xlsx multi-aba enviando um SimulateRequest completo
 * (pra fluxo pós-simulação sem ter ID salvo).
 */
export async function downloadExcelFromRequest(
  accessToken: string,
  payload: SimulateRequest,
): Promise<void> {
  const r = await fetch("/api/me/export-excel", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    let msg = `Falha ao exportar: ${r.status}`;
    try {
      const j = await r.json();
      if (j.detail) msg = j.detail;
    } catch {
      /* ignora */
    }
    throw new Error(msg);
  }
  await _downloadBlob(r, "simulacao.xlsx");
}

// =============================================================================
// Avaliação de rede via CSV (Sprint 3 #4)
// =============================================================================

/** Baixa o template CSV (3 linhas-exemplo + header). */
export async function downloadBatchCsvTemplate(accessToken: string): Promise<void> {
  const r = await fetch("/api/me/batch-csv/template", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) {
    throw new Error(`Falha ao baixar template: ${r.status}`);
  }
  await _downloadBlob(r, "template-avaliacao-rede.csv");
}

/**
 * Faz upload do CSV multi-loja e baixa o .xlsx consolidado retornado.
 * Síncrono — pode levar até ~10s pra 50 lojas.
 */
export async function uploadBatchCsv(
  accessToken: string,
  file: File,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);

  const r = await fetch("/api/me/batch-csv", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form,
  });
  if (!r.ok) {
    let msg = `Falha no batch: ${r.status}`;
    try {
      const j = await r.json();
      if (j.detail) msg = j.detail;
    } catch {
      /* ignora */
    }
    throw new Error(msg);
  }
  const fileName =
    _extractFilename(r) ?? `avaliacao-rede-${Date.now()}.xlsx`;
  await _downloadBlob(r, fileName);
}

// =============================================================================
// Helpers internos
// =============================================================================

async function _downloadBlob(r: Response, fallbackName: string): Promise<void> {
  const blob = await r.blob();
  const fileName = _extractFilename(r) ?? fallbackName;
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function _extractFilename(r: Response): string | null {
  const cd = r.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="([^"]+)"/);
  return m ? m[1] : null;
}
