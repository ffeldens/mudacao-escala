import { z } from "zod";

// =============================================================================
// Helpers
// =============================================================================

/** Aceita string com vírgula ou ponto, devolve número. "2.500,00" → 2500.0 */
const decimalString = (min: number, max: number, msg: string) =>
  z
    .string()
    .min(1, msg)
    .refine(
      (v) => {
        const n = parseFloat(v.replace(/\./g, "").replace(",", "."));
        return !isNaN(n) && n >= min && n <= max;
      },
      { message: msg },
    );

const phoneBR = z
  .string()
  .trim()
  .min(8, "WhatsApp muito curto")
  .max(20, "WhatsApp muito longo")
  .regex(/^[0-9+()\-\s]+$/, "Use só números, espaços, +, ( ) e -");

// =============================================================================
// Simulação
// =============================================================================

export const simulationSchema = z.object({
  // Dados básicos da loja
  fte_atual: z
    .number({ invalid_type_error: "Informe um número" })
    .int("Use número inteiro")
    .min(1, "Mínimo 1 FTE")
    .max(500, "Máximo 500 FTEs por loja"),

  salario_medio: decimalString(
    600,
    50000,
    "Salário entre R$ 600 e R$ 50.000",
  ),

  porte: z.enum(["PP", "P", "M", "G"]),
  setor: z.enum(["varejo", "food_service", "outros"]),

  faturamento_mensal: z.string().optional().or(z.literal("")),

  // Operação (com defaults) — horário seg-sex
  hora_abertura: z.number().int().min(6).max(14).default(10),
  hora_fechamento: z.number().int().min(16).max(24).default(22),

  // Sábado — null = herda dias úteis
  hora_abertura_sabado: z.number().int().min(6).max(14).nullable().default(null),
  hora_fechamento_sabado: z.number().int().min(16).max(24).nullable().default(null),
  sabado_fechado: z.boolean().default(false),

  // Domingo
  hora_abertura_domingo: z.number().int().min(6).max(14).nullable().default(null),
  hora_fechamento_domingo: z.number().int().min(16).max(24).nullable().default(null),
  domingo_fechado: z.boolean().default(false),

  // Deprecated: ainda enviado pra retrocompat com queries antigas
  dias_operacao_semana: z.number().int().min(1).max(7).default(7),

  // Cenário
  cenario: z.enum(["pessimista", "neutro", "otimista"]).default("neutro"),
  ganho_produtividade_pct: z
    .number()
    .min(0, "Min 0%")
    .max(30, "Max 30%")
    .default(5), // em pp (5 = 5%)
  manter_salario_nominal: z.boolean().default(true),

  // Arredondamento de FTEs no resultado
  // 'meio' default (vendedor full ou meio-turno)
  arredondamento_fte: z
    .enum(["meio", "inteiro", "decimal"])
    .default("meio"),

  // Rede
  n_lojas_rede: z
    .number({ invalid_type_error: "Informe o número de lojas" })
    .int("Use número inteiro")
    .min(1, "Mínimo 1 loja")
    .max(10000, "Máximo 10.000 lojas"),
});

export type SimulationFormData = z.infer<typeof simulationSchema>;

// =============================================================================
// Lead
// =============================================================================

export const leadSchema = z
  .object({
    nome: z
      .string()
      .trim()
      .min(2, "Informe seu nome")
      .max(120, "Nome muito longo"),
    email: z.string().email("Email inválido"),
    email_confirm: z.string().email("Confirmação inválida"),
    whatsapp: phoneBR,
    empresa: z.string().trim().max(120).optional().or(z.literal("")),
    aceite_lgpd: z.literal(true, {
      errorMap: () => ({
        message: "Você precisa aceitar os Termos e a Política de Privacidade",
      }),
    }),
    // utm_*: capturados auto da URL pelo componente
  })
  .refine((d) => d.email.toLowerCase() === d.email_confirm.toLowerCase(), {
    message: "Os emails não coincidem",
    path: ["email_confirm"],
  });

export type LeadFormData = z.infer<typeof leadSchema>;

// =============================================================================
// Helpers de conversão pro payload da API
// =============================================================================

export function parseDecimalBR(value: string): number {
  return parseFloat(value.replace(/\./g, "").replace(",", "."));
}

/** Formata Decimal pro payload da API (string com ponto). */
export function toApiDecimal(value: string): string {
  return parseDecimalBR(value).toFixed(2);
}

/** Constrói o payload da API a partir dos dois forms. */
export function buildApiPayload(sim: SimulationFormData, lead: LeadFormData) {
  return {
    lead_req: {
      nome: lead.nome,
      email: lead.email,
      whatsapp: lead.whatsapp,
      empresa: lead.empresa || undefined,
      n_lojas: sim.n_lojas_rede,
      porte: sim.porte,
      setor: sim.setor,
      utm_source: getQueryParam("utm_source"),
      utm_medium: getQueryParam("utm_medium"),
      utm_campaign: getQueryParam("utm_campaign"),
    },
    sim_req: {
      nome_loja: undefined,
      setor: sim.setor,
      porte: sim.porte,
      fte_atual: sim.fte_atual,
      salario_medio: toApiDecimal(sim.salario_medio),
      faturamento_mensal: sim.faturamento_mensal
        ? toApiDecimal(sim.faturamento_mensal)
        : undefined,
      hora_abertura: sim.hora_abertura,
      hora_fechamento: sim.hora_fechamento,
      hora_abertura_sabado: sim.hora_abertura_sabado,
      hora_fechamento_sabado: sim.hora_fechamento_sabado,
      sabado_fechado: sim.sabado_fechado,
      hora_abertura_domingo: sim.hora_abertura_domingo,
      hora_fechamento_domingo: sim.hora_fechamento_domingo,
      domingo_fechado: sim.domingo_fechado,
      dias_operacao_semana: sim.dias_operacao_semana,
      cenario: sim.cenario,
      ganho_produtividade_pct: (sim.ganho_produtividade_pct / 100).toFixed(4),
      manter_salario_nominal: sim.manter_salario_nominal,
      arredondamento_fte: sim.arredondamento_fte,
      n_lojas_rede: sim.n_lojas_rede,
    },
  };
}

function getQueryParam(key: string): string | undefined {
  if (typeof window === "undefined") return undefined;
  const v = new URLSearchParams(window.location.search).get(key);
  return v || undefined;
}
