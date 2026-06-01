"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2, RotateCcw } from "lucide-react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface PremissasFormProps {
  initial: {
    encargos_pct: string;
    vr_dia: string;
    vt_dia: string;
    dias_uteis_mes: string;
  };
  defaults: {
    encargos_pct: number;
    vr_dia: number;
    vt_dia: number;
    dias_uteis_mes: number;
  };
}

export function PremissasForm({ initial, defaults }: PremissasFormProps) {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        setError("Sessão expirada — recarregue a página");
        return;
      }

      // Converte strings → tipos do DB. "" → null (volta pro default).
      const parsedEncargosPct = form.encargos_pct.trim()
        ? parseFloat(form.encargos_pct.replace(",", ".")) / 100
        : null;
      const parsedVr = form.vr_dia.trim()
        ? parseFloat(form.vr_dia.replace(",", "."))
        : null;
      const parsedVt = form.vt_dia.trim()
        ? parseFloat(form.vt_dia.replace(",", "."))
        : null;
      const parsedDias = form.dias_uteis_mes.trim()
        ? parseInt(form.dias_uteis_mes, 10)
        : null;

      // Validações leves
      if (
        parsedEncargosPct !== null &&
        (parsedEncargosPct < 0 || parsedEncargosPct > 2)
      ) {
        setError("Encargos deve estar entre 0% e 200%");
        return;
      }
      if (parsedDias !== null && (parsedDias < 18 || parsedDias > 26)) {
        setError("Dias úteis no mês entre 18 e 26");
        return;
      }

      const { error: err } = await supabase
        .schema("freemium")
        .from("user_profiles")
        .update({
          pref_encargos_pct: parsedEncargosPct,
          pref_vr_dia: parsedVr,
          pref_vt_dia: parsedVt,
          pref_dias_uteis_mes: parsedDias,
        })
        .eq("id", user.id);

      if (err) {
        setError(`Falha ao salvar: ${err.message}`);
        return;
      }

      setSaved(true);
      router.refresh();
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(`Erro: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  function handleReset() {
    setForm({
      encargos_pct: "",
      vr_dia: "",
      vt_dia: "",
      dias_uteis_mes: "",
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Encargos (%)"
          hint={`Default ${defaults.encargos_pct}% (INSS+FGTS+13+férias+rescisão)`}
        >
          <div className="relative">
            <input
              type="text"
              inputMode="decimal"
              className="input pr-10"
              value={form.encargos_pct}
              onChange={(e) =>
                setForm({ ...form, encargos_pct: e.target.value })
              }
              placeholder={defaults.encargos_pct.toString()}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">
              %
            </span>
          </div>
        </Field>

        <Field
          label="Dias úteis/mês"
          hint={`Default ${defaults.dias_uteis_mes} (calendário comercial padrão)`}
        >
          <input
            type="number"
            inputMode="numeric"
            min={18}
            max={26}
            className="input"
            value={form.dias_uteis_mes}
            onChange={(e) =>
              setForm({ ...form, dias_uteis_mes: e.target.value })
            }
            placeholder={defaults.dias_uteis_mes.toString()}
          />
        </Field>

        <Field label="Vale Refeição (R$/dia)" hint={`Default R$ ${defaults.vr_dia}`}>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">
              R$
            </span>
            <input
              type="text"
              inputMode="decimal"
              className="input pl-10"
              value={form.vr_dia}
              onChange={(e) => setForm({ ...form, vr_dia: e.target.value })}
              placeholder={defaults.vr_dia.toString()}
            />
          </div>
        </Field>

        <Field label="Vale Transporte (R$/dia)" hint={`Default R$ ${defaults.vt_dia}`}>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">
              R$
            </span>
            <input
              type="text"
              inputMode="decimal"
              className="input pl-10"
              value={form.vt_dia}
              onChange={(e) => setForm({ ...form, vt_dia: e.target.value })}
              placeholder={defaults.vt_dia.toString()}
            />
          </div>
        </Field>
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button
          type="button"
          onClick={handleReset}
          disabled={saving}
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-mudacao-700"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Voltar pros defaults
        </button>

        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1 text-sm text-mudacao-700">
              <CheckCircle2 className="h-4 w-4" />
              Salvo!
            </span>
          )}
          <button
            type="submit"
            disabled={saving}
            className="btn-primary text-sm"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Salvando...
              </>
            ) : (
              "Salvar premissas"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
