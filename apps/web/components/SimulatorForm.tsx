"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { sendGAEvent } from "@next/third-parties/google";
import {
  ArrowRight,
  Building2,
  CalendarDays,
  Mail,
  Loader2,
  ChevronDown,
  ChevronUp,
  Info,
  CheckCircle2,
} from "lucide-react";
import { z } from "zod";

import {
  simulationSchema,
  leadSchema,
  buildApiPayload,
  type SimulationFormData,
  type LeadFormData,
} from "@/lib/schemas";
import { cn } from "@/lib/utils";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type FormErrors<T> = Partial<Record<keyof T, string>>;

// Tipo flexível pro estado do form (campos vêm como string dos inputs)
type SimFormState = {
  fte_atual: string;
  salario_medio: string;
  porte: "PP" | "P" | "M" | "G";
  setor: "varejo" | "food_service" | "outros";
  faturamento_mensal: string;
  hora_abertura: number;
  hora_fechamento: number;
  dias_operacao_semana: number;
  cenario: "pessimista" | "neutro" | "otimista";
  ganho_produtividade_pct: number;
  manter_salario_nominal: boolean;
  n_lojas_rede: string;
};

const INITIAL_SIM: SimFormState = {
  fte_atual: "",
  salario_medio: "",
  porte: "M",
  setor: "varejo",
  faturamento_mensal: "",
  hora_abertura: 10,
  hora_fechamento: 22,
  dias_operacao_semana: 7,
  cenario: "neutro",
  ganho_produtividade_pct: 5,
  manter_salario_nominal: true,
  n_lojas_rede: "1",
};

const INITIAL_LEAD: LeadFormData = {
  nome: "",
  email: "",
  email_confirm: "",
  whatsapp: "",
  empresa: "",
  aceite_lgpd: false as unknown as true,
};

export function SimulatorForm() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [sim, setSim] = useState<SimFormState>(INITIAL_SIM);
  const [lead, setLead] = useState<LeadFormData>(INITIAL_LEAD);
  const [simErrors, setSimErrors] = useState<FormErrors<SimFormState>>({});
  const [leadErrors, setLeadErrors] = useState<FormErrors<LeadFormData>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const step2Ref = useRef<HTMLFormElement>(null);

  // Se logado, pulamos o gate. Carregamos session no mount.
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    (async () => {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setAccessToken(session?.access_token ?? null);
      setAuthChecked(true);
    })();
  }, []);

  const isLogged = !!accessToken;

  // ============ Step 1 → Step 2 (ou pula direto se logado) ============
  async function handleSimSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    // Converte sim → tipos do schema (parseFloat, parseInt)
    const parsed = {
      ...sim,
      fte_atual: parseInt(sim.fte_atual || "0", 10),
      n_lojas_rede: parseInt(sim.n_lojas_rede || "0", 10),
      ganho_produtividade_pct: Number(sim.ganho_produtividade_pct),
    };

    const result = simulationSchema.safeParse(parsed);
    if (!result.success) {
      setSimErrors(zodErrorsToMap(result.error));
      return;
    }
    setSimErrors({});

    // GA4: usuário completou step 1 (interesse alto, antes do gate)
    sendGAEvent("event", "simulator_step1_complete", {
      porte: parsed.porte,
      setor: parsed.setor,
      n_lojas_rede: parsed.n_lojas_rede,
      cenario: parsed.cenario,
    });

    // Se logado: pula gate, chama /api/simulate direto com Bearer
    // (salva user_id no DB pra histórico)
    if (isLogged && accessToken) {
      await submitLoggedSimulation(result.data as SimulationFormData);
      return;
    }

    // Anônimo: vai pro step 2 (gate de captura)
    setStep(2);
    setTimeout(() => {
      step2Ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  // ============ Submit direto pra user logado ============
  async function submitLoggedSimulation(data: SimulationFormData) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = buildApiPayload(data, {
        nome: "",
        email: "logged@user.placeholder",
        email_confirm: "logged@user.placeholder",
        whatsapp: "",
        empresa: "",
        aceite_lgpd: true as const,
      });
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload.sim_req),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Erro ${res.status}: ${errBody.slice(0, 200)}`);
      }
      const result = await res.json();

      sessionStorage.setItem(
        "mudacao_simulacao_resultado",
        JSON.stringify(result),
      );

      sendGAEvent("event", "logged_simulation", {
        value: 1,
        porte: data.porte,
        setor: data.setor,
      });

      router.push("/simulador/resultado");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setSubmitError(`Falha ao calcular: ${msg}`);
      setSubmitting(false);
    }
  }

  // ============ Step 2 (gate) → API → redirect ============
  async function handleLeadSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setLeadErrors({});

    // Valida lead
    const leadResult = leadSchema.safeParse(lead);
    if (!leadResult.success) {
      setLeadErrors(zodErrorsToMap(leadResult.error));
      return;
    }

    // Valida sim (de novo, defensivo)
    const simParsed = {
      ...sim,
      fte_atual: parseInt(sim.fte_atual || "0", 10),
      n_lojas_rede: parseInt(sim.n_lojas_rede || "0", 10),
      ganho_produtividade_pct: Number(sim.ganho_produtividade_pct),
    };
    const simResult = simulationSchema.safeParse(simParsed);
    if (!simResult.success) {
      setSubmitError("Dados da simulação inválidos. Volte e revise.");
      return;
    }

    const payload = buildApiPayload(
      simResult.data as SimulationFormData,
      leadResult.data as LeadFormData,
    );

    setSubmitting(true);
    try {
      const res = await fetch("/api/lead-and-simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Erro ${res.status}: ${errBody.slice(0, 200)}`);
      }
      const data = await res.json();

      // Persiste resultado no sessionStorage pra próxima página ler
      sessionStorage.setItem(
        "mudacao_simulacao_resultado",
        JSON.stringify({
          ...data,
          _lead_nome: leadResult.data.nome,
          _lead_email: leadResult.data.email,
        }),
      );

      // GA4: lead capturado (conversão principal — monitorar essa métrica)
      sendGAEvent("event", "lead_capture", {
        value: 1,
        n_lojas: leadResult.data.email && simParsed.n_lojas_rede,
        porte: simParsed.porte,
        setor: simParsed.setor,
        delta_folha_pct: parseFloat(data.delta_folha_pct),
      });

      router.push("/simulador/resultado");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setSubmitError(`Falha ao calcular: ${msg}`);
      setSubmitting(false);
    }
  }

  // ============ UI ============
  return (
    <div className="space-y-8">
      {/* Progress — só mostra pra anônimo (logged user pula gate) */}
      {!isLogged && authChecked && (
        <ol className="flex items-center justify-center gap-4 text-sm">
          <ProgressStep n={1} label="Sua loja" active={step === 1} done={step === 2} />
          <div className="h-px w-12 bg-slate-200" />
          <ProgressStep n={2} label="Receba o resultado" active={step === 2} done={false} />
        </ol>
      )}

      {/* Aviso pra user logado */}
      {isLogged && authChecked && (
        <div className="rounded-xl border border-mudacao-200 bg-mudacao-50 p-4 text-sm text-mudacao-900">
          <p className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4" /> Você está logado
          </p>
          <p className="mt-1 text-mudacao-800">
            Sua simulação será salva automaticamente no{" "}
            <a href="/minha-conta/historico" className="font-semibold underline">
              histórico
            </a>{" "}
            (sem precisar preencher contato).
          </p>
        </div>
      )}

      {/* ============================ STEP 1 ============================ */}
      {step === 1 && (
        <form onSubmit={handleSimSubmit} className="space-y-6">
          {/* Seção: Loja */}
          <Section
            icon={<Building2 className="h-5 w-5" />}
            title="Dados da loja"
            description="Tudo agregado — não precisa de detalhes por funcionário"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Setor"
                error={simErrors.setor}
                hint="Tipo de operação"
              >
                <select
                  className="input"
                  value={sim.setor}
                  onChange={(e) =>
                    setSim({ ...sim, setor: e.target.value as SimFormState["setor"] })
                  }
                >
                  <option value="varejo">Varejo</option>
                  <option value="food_service">Food service</option>
                  <option value="outros">Outros</option>
                </select>
              </Field>

              <Field
                label="Porte da loja"
                error={simErrors.porte}
                hint="Baseado no volume típico"
              >
                <select
                  className="input"
                  value={sim.porte}
                  onChange={(e) =>
                    setSim({ ...sim, porte: e.target.value as SimFormState["porte"] })
                  }
                >
                  <option value="PP">PP — micro (até 50 tickets/dia)</option>
                  <option value="P">P — pequeno (50-150)</option>
                  <option value="M">M — médio (150-400)</option>
                  <option value="G">G — grande (400+)</option>
                </select>
              </Field>

              <Field
                label="FTEs hoje (escala 6x1)"
                error={simErrors.fte_atual}
                hint="Quantos funcionários CLT no quadro atual"
              >
                <input
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={500}
                  className="input"
                  value={sim.fte_atual}
                  onChange={(e) => setSim({ ...sim, fte_atual: e.target.value })}
                  placeholder="ex: 10"
                />
              </Field>

              <Field
                label="Salário médio (R$)"
                error={simErrors.salario_medio}
                hint="Bruto, sem encargos"
              >
                <input
                  type="text"
                  inputMode="decimal"
                  className="input"
                  value={sim.salario_medio}
                  onChange={(e) => setSim({ ...sim, salario_medio: e.target.value })}
                  placeholder="ex: 2.500,00"
                />
              </Field>

              <Field
                label="Lojas na rede"
                error={simErrors.n_lojas_rede}
                hint="Pra extrapolar o impacto total"
              >
                <input
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={10000}
                  className="input"
                  value={sim.n_lojas_rede}
                  onChange={(e) => setSim({ ...sim, n_lojas_rede: e.target.value })}
                  placeholder="ex: 50"
                />
              </Field>

              <Field
                label="Faturamento mensal (opcional)"
                error={undefined}
                hint="Pra calcular % folha/faturamento"
              >
                <input
                  type="text"
                  inputMode="decimal"
                  className="input"
                  value={sim.faturamento_mensal}
                  onChange={(e) =>
                    setSim({ ...sim, faturamento_mensal: e.target.value })
                  }
                  placeholder="ex: 350.000,00"
                />
              </Field>
            </div>
          </Section>

          {/* Seção: Cenário */}
          <Section
            icon={<CalendarDays className="h-5 w-5" />}
            title="Cenário"
            description="Pode usar o padrão (neutro) e ajustar depois"
          >
            <div className="grid gap-3 sm:grid-cols-3">
              {(["pessimista", "neutro", "otimista"] as const).map((c) => (
                <label
                  key={c}
                  className={cn(
                    "flex cursor-pointer items-center justify-between rounded-lg border-2 p-4 transition",
                    sim.cenario === c
                      ? "border-mudacao-700 bg-mudacao-50"
                      : "border-slate-200 hover:border-slate-300",
                  )}
                >
                  <div>
                    <div className="font-medium capitalize text-mudacao-950">
                      {c}
                    </div>
                    <div className="text-xs text-slate-500">
                      {c === "pessimista" && "Sem ganho de produtividade"}
                      {c === "neutro" && "Premissa padrão Fitch"}
                      {c === "otimista" && "Com WFM bem implementado"}
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="cenario"
                    value={c}
                    checked={sim.cenario === c}
                    onChange={() => setSim({ ...sim, cenario: c })}
                    className="accent-mudacao-700"
                  />
                </label>
              ))}
            </div>

            {/* Premissas avançadas (colapsável) */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="mt-4 inline-flex items-center gap-1 text-sm text-mudacao-700 hover:underline"
            >
              {showAdvanced ? (
                <>
                  <ChevronUp className="h-4 w-4" /> Esconder premissas
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4" /> Mostrar premissas avançadas
                </>
              )}
            </button>

            {showAdvanced && (
              <div className="mt-4 grid gap-4 rounded-lg bg-slate-50 p-4 sm:grid-cols-2">
                <Field
                  label={`Ganho de produtividade: ${sim.ganho_produtividade_pct}%`}
                  hint="Quanto WFM/processo recupera"
                >
                  <input
                    type="range"
                    min={0}
                    max={20}
                    step={1}
                    value={sim.ganho_produtividade_pct}
                    onChange={(e) =>
                      setSim({
                        ...sim,
                        ganho_produtividade_pct: Number(e.target.value),
                      })
                    }
                    className="w-full accent-mudacao-700"
                  />
                </Field>

                <Field label="Manter salário nominal?" hint="Default: sim (mercado)">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={sim.manter_salario_nominal}
                      onChange={(e) =>
                        setSim({
                          ...sim,
                          manter_salario_nominal: e.target.checked,
                        })
                      }
                      className="accent-mudacao-700"
                    />
                    Manter R$ atual sem reduzir 40/44
                  </label>
                </Field>

                <Field label={`Abertura: ${sim.hora_abertura}h`} hint="">
                  <input
                    type="range"
                    min={6}
                    max={14}
                    step={1}
                    value={sim.hora_abertura}
                    onChange={(e) =>
                      setSim({ ...sim, hora_abertura: Number(e.target.value) })
                    }
                    className="w-full accent-mudacao-700"
                  />
                </Field>

                <Field label={`Fechamento: ${sim.hora_fechamento}h`} hint="">
                  <input
                    type="range"
                    min={16}
                    max={24}
                    step={1}
                    value={sim.hora_fechamento}
                    onChange={(e) =>
                      setSim({
                        ...sim,
                        hora_fechamento: Number(e.target.value),
                      })
                    }
                    className="w-full accent-mudacao-700"
                  />
                </Field>

                <Field
                  label={`Dias de operação/semana: ${sim.dias_operacao_semana}`}
                  hint=""
                >
                  <input
                    type="range"
                    min={1}
                    max={7}
                    step={1}
                    value={sim.dias_operacao_semana}
                    onChange={(e) =>
                      setSim({
                        ...sim,
                        dias_operacao_semana: Number(e.target.value),
                      })
                    }
                    className="w-full accent-mudacao-700"
                  />
                </Field>
              </div>
            )}
          </Section>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full text-lg"
          >
            {submitting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" /> Calculando...
              </>
            ) : isLogged ? (
              <>
                Calcular minha simulação <ArrowRight className="h-5 w-5" />
              </>
            ) : (
              <>
                Calcular o impacto na minha rede <ArrowRight className="h-5 w-5" />
              </>
            )}
          </button>

          {submitError && (
            <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
              {submitError}
            </p>
          )}
        </form>
      )}

      {/* ============================ STEP 2 (Gate) — só anônimo ============================ */}
      {step === 2 && !isLogged && (
        <form
          ref={step2Ref}
          onSubmit={handleLeadSubmit}
          className="space-y-6"
        >
          <Section
            icon={<Mail className="h-5 w-5" />}
            title="Receba seu resultado completo"
            description="O PDF detalhado vai pro seu email em segundos"
          >
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-mudacao-50 p-3 text-sm text-mudacao-900">
              <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                <strong>Quase lá!</strong> Seus dados são usados apenas pra
                enviar o relatório. Você pode descadastrar a qualquer momento.
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Seu nome" error={leadErrors.nome}>
                <input
                  type="text"
                  className="input"
                  value={lead.nome}
                  onChange={(e) => setLead({ ...lead, nome: e.target.value })}
                  placeholder="ex: Felipe Feldens"
                  autoFocus
                />
              </Field>

              <Field label="Email" error={leadErrors.email}>
                <input
                  type="email"
                  className="input"
                  value={lead.email}
                  onChange={(e) => setLead({ ...lead, email: e.target.value })}
                  placeholder="seu@email.com"
                  autoComplete="email"
                />
              </Field>

              <Field
                label="Confirmar email"
                error={leadErrors.email_confirm}
                hint="Digite de novo pra evitar typos"
              >
                <input
                  type="email"
                  className="input"
                  value={lead.email_confirm}
                  onChange={(e) =>
                    setLead({ ...lead, email_confirm: e.target.value })
                  }
                  placeholder="seu@email.com"
                  autoComplete="email"
                  onPaste={(e) => e.preventDefault()}
                />
              </Field>

              <Field label="WhatsApp" error={leadErrors.whatsapp}>
                <input
                  type="tel"
                  className="input"
                  value={lead.whatsapp}
                  onChange={(e) =>
                    setLead({ ...lead, whatsapp: e.target.value })
                  }
                  placeholder="ex: (11) 99999-9999"
                />
              </Field>

              <Field label="Empresa (opcional)" error={leadErrors.empresa}>
                <input
                  type="text"
                  className="input"
                  value={lead.empresa}
                  onChange={(e) => setLead({ ...lead, empresa: e.target.value })}
                  placeholder="ex: Sua Rede S.A."
                />
              </Field>
            </div>

            {/* LGPD consent */}
            <div className="mt-6 border-t border-slate-100 pt-4">
              <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-5 w-5 cursor-pointer accent-mudacao-700"
                  checked={!!lead.aceite_lgpd}
                  onChange={(e) =>
                    setLead({
                      ...lead,
                      aceite_lgpd: e.target.checked as unknown as true,
                    })
                  }
                />
                <span>
                  Li e concordo com os{" "}
                  <a
                    href="/termos"
                    target="_blank"
                    rel="noreferrer"
                    className="text-mudacao-700 underline hover:text-mudacao-900"
                  >
                    Termos de Uso
                  </a>{" "}
                  e a{" "}
                  <a
                    href="/privacidade"
                    target="_blank"
                    rel="noreferrer"
                    className="text-mudacao-700 underline hover:text-mudacao-900"
                  >
                    Política de Privacidade
                  </a>
                  . Autorizo o uso dos meus dados pra entregar o relatório e
                  manter contato sobre o produto.
                </span>
              </label>
              {leadErrors.aceite_lgpd && (
                <p className="mt-1 text-xs text-red-600">
                  {leadErrors.aceite_lgpd}
                </p>
              )}
            </div>
          </Section>

          {submitError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
              {submitError}
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => setStep(1)}
              disabled={submitting}
              className="btn-secondary"
            >
              ← Voltar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary flex-1 text-lg"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" /> Calculando...
                </>
              ) : (
                <>
                  Receber meu resultado <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>
          </div>

          <p className="text-center text-xs text-slate-500">
            Ao clicar você concorda em receber o relatório por email.
            Não compartilhamos seu contato.
          </p>
        </form>
      )}
    </div>
  );
}

// ============================================================================
// Componentes auxiliares
// ============================================================================

function Section({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="mb-5 flex items-start gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-mudacao-100 text-mudacao-700">
          {icon}
        </div>
        <div>
          <h2 className="text-xl font-bold text-mudacao-950">{title}</h2>
          {description && (
            <p className="text-sm text-slate-600">{description}</p>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {error ? (
        <p className="mt-1 text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  );
}

function ProgressStep({
  n,
  label,
  active,
  done,
}: {
  n: number;
  label: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <li className="flex items-center gap-2">
      <div
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold",
          done
            ? "bg-mudacao-700 text-white"
            : active
              ? "bg-mudacao-900 text-white"
              : "bg-slate-200 text-slate-500",
        )}
      >
        {done ? "✓" : n}
      </div>
      <span
        className={cn(
          "font-medium",
          active || done ? "text-mudacao-950" : "text-slate-500",
        )}
      >
        {label}
      </span>
    </li>
  );
}

function zodErrorsToMap<T>(err: z.ZodError): FormErrors<T> {
  const map: FormErrors<T> = {};
  for (const issue of err.errors) {
    const key = issue.path[0] as keyof T;
    if (key && !map[key]) {
      map[key] = issue.message;
    }
  }
  return map;
}
