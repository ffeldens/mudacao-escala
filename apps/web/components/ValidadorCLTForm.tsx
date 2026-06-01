"use client";

import { useState } from "react";
import { ArrowRight, Loader2, Download } from "lucide-react";
import { z } from "zod";

import {
  simulationSchema,
  type SimulationFormData,
} from "@/lib/schemas";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type FormErrors<T> = Partial<Record<keyof T, string>>;

type FormState = {
  fte_atual: string;
  salario_medio: string;
  porte: "PP" | "P" | "M" | "G";
  setor: "varejo" | "food_service" | "outros";
  hora_abertura: number;
  hora_fechamento: number;
  dias_operacao_semana: number;
  cenario: "pessimista" | "neutro" | "otimista";
  ganho_produtividade_pct: number;
  manter_salario_nominal: boolean;
  n_lojas_rede: string;
};

const INITIAL: FormState = {
  fte_atual: "",
  salario_medio: "",
  porte: "M",
  setor: "varejo",
  hora_abertura: 10,
  hora_fechamento: 22,
  dias_operacao_semana: 7,
  cenario: "neutro",
  ganho_produtividade_pct: 5,
  manter_salario_nominal: true,
  n_lojas_rede: "1",
};

export function ValidadorCLTForm() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [errors, setErrors] = useState<FormErrors<FormState>>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);

    const parsed = {
      ...form,
      fte_atual: parseInt(form.fte_atual || "0", 10),
      n_lojas_rede: parseInt(form.n_lojas_rede || "0", 10),
      ganho_produtividade_pct: Number(form.ganho_produtividade_pct),
    };

    const result = simulationSchema.safeParse(parsed);
    if (!result.success) {
      setErrors(zodErrorsToMap(result.error));
      return;
    }
    setErrors({});

    setSubmitting(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setServerError("Sessão expirada — recarregue a página");
        return;
      }

      // Payload pra API (mesmo formato do /simulate)
      const data = result.data as SimulationFormData;
      const payload = {
        setor: data.setor,
        porte: data.porte,
        fte_atual: data.fte_atual,
        salario_medio: toApiDecimal(data.salario_medio),
        hora_abertura: data.hora_abertura,
        hora_fechamento: data.hora_fechamento,
        dias_operacao_semana: data.dias_operacao_semana,
        cenario: data.cenario,
        ganho_produtividade_pct: (data.ganho_produtividade_pct / 100).toFixed(4),
        manter_salario_nominal: data.manter_salario_nominal,
        n_lojas_rede: data.n_lojas_rede,
      };

      const res = await fetch("/api/me/validate-clt", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let msg = `Erro ${res.status}`;
        try {
          const txt = await res.text();
          const json = JSON.parse(txt);
          msg = json.detail || msg;
        } catch {
          // ignora
        }
        throw new Error(msg);
      }

      // Download do PDF
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `validador-clt-${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setServerError(`Falha ao gerar relatório: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-mudacao-950">
          Dados da loja
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Preencha os mesmos dados que você usaria no simulador.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Setor" error={errors.setor}>
          <select
            className="input"
            value={form.setor}
            onChange={(e) =>
              setForm({ ...form, setor: e.target.value as FormState["setor"] })
            }
          >
            <option value="varejo">Varejo</option>
            <option value="food_service">Food service</option>
            <option value="outros">Outros</option>
          </select>
        </Field>

        <Field label="Porte" error={errors.porte}>
          <select
            className="input"
            value={form.porte}
            onChange={(e) =>
              setForm({ ...form, porte: e.target.value as FormState["porte"] })
            }
          >
            <option value="PP">PP — micro</option>
            <option value="P">P — pequeno</option>
            <option value="M">M — médio</option>
            <option value="G">G — grande</option>
          </select>
        </Field>

        <Field
          label="FTEs hoje (escala 6x1)"
          error={errors.fte_atual}
        >
          <input
            type="number"
            inputMode="numeric"
            min={1}
            max={500}
            className="input"
            value={form.fte_atual}
            onChange={(e) => setForm({ ...form, fte_atual: e.target.value })}
            placeholder="ex: 10"
          />
        </Field>

        <Field label="Salário médio (R$)" error={errors.salario_medio}>
          <input
            type="text"
            inputMode="decimal"
            className="input"
            value={form.salario_medio}
            onChange={(e) =>
              setForm({ ...form, salario_medio: e.target.value })
            }
            placeholder="ex: 2.500,00"
          />
        </Field>

        <Field
          label={`Abertura: ${form.hora_abertura}h`}
          hint="6h–14h"
        >
          <input
            type="range"
            min={6}
            max={14}
            step={1}
            value={form.hora_abertura}
            onChange={(e) =>
              setForm({ ...form, hora_abertura: Number(e.target.value) })
            }
            className="w-full accent-mudacao-700"
          />
        </Field>

        <Field
          label={`Fechamento: ${form.hora_fechamento}h`}
          hint="16h–24h"
        >
          <input
            type="range"
            min={16}
            max={24}
            step={1}
            value={form.hora_fechamento}
            onChange={(e) =>
              setForm({ ...form, hora_fechamento: Number(e.target.value) })
            }
            className="w-full accent-mudacao-700"
          />
        </Field>

        <Field
          label={`Dias de operação/sem: ${form.dias_operacao_semana}`}
          hint="1–7"
        >
          <input
            type="range"
            min={1}
            max={7}
            step={1}
            value={form.dias_operacao_semana}
            onChange={(e) =>
              setForm({
                ...form,
                dias_operacao_semana: Number(e.target.value),
              })
            }
            className="w-full accent-mudacao-700"
          />
        </Field>

        <Field label="Cenário" error={errors.cenario}>
          <select
            className="input"
            value={form.cenario}
            onChange={(e) =>
              setForm({
                ...form,
                cenario: e.target.value as FormState["cenario"],
              })
            }
          >
            <option value="pessimista">Pessimista</option>
            <option value="neutro">Neutro (Fitch)</option>
            <option value="otimista">Otimista (com WFM)</option>
          </select>
        </Field>
      </div>

      {serverError && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {serverError}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="btn-primary w-full text-lg"
      >
        {submitting ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Gerando PDF...
          </>
        ) : (
          <>
            <Download className="h-5 w-5" />
            Gerar relatório CLT (PDF)
          </>
        )}
      </button>

      <p className="text-center text-xs text-slate-500">
        Hash de inputs + régua CLT incluídos no PDF pra auditoria.
      </p>
    </form>
  );
}

// ============================================================================

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

function toApiDecimal(value: string): string {
  return parseFloat(value.replace(/\./g, "").replace(",", ".")).toFixed(2);
}

function zodErrorsToMap<T>(err: z.ZodError): FormErrors<T> {
  const map: FormErrors<T> = {};
  for (const issue of err.errors) {
    const key = issue.path[0] as keyof T;
    if (key && !map[key]) map[key] = issue.message;
  }
  return map;
}
