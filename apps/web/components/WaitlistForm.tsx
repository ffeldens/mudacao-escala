"use client";

import { useState, useEffect } from "react";
import { sendGAEvent } from "@next/third-parties/google";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import { z } from "zod";

export type PlanoInteresse = "starter" | "pro" | "enterprise";

/** Lê ?plano=starter/pro/enterprise do hash da URL (ex: #waitlist?plano=pro). */
function readPlanoFromHash(): PlanoInteresse | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash || "";
  const m = hash.match(/[?&]plano=(starter|pro|enterprise)/);
  return m ? (m[1] as PlanoInteresse) : null;
}

const PLANOS_LABEL: Record<PlanoInteresse, string> = {
  starter: "Starter (R$ 99/mês)",
  pro: "Pro (R$ 299/mês)",
  enterprise: "Enterprise",
};

const waitlistSchema = z.object({
  nome: z.string().trim().min(2, "Informe seu nome").max(120),
  email: z.string().email("Email inválido"),
  plano: z.enum(["starter", "pro", "enterprise"]),
  empresa: z.string().trim().max(120).optional().or(z.literal("")),
  n_lojas: z
    .union([z.number().int().min(0).max(10000), z.literal("")])
    .optional(),
});

type WaitlistFormData = z.infer<typeof waitlistSchema>;

interface WaitlistFormProps {
  defaultPlano?: PlanoInteresse;
}

export function WaitlistForm({ defaultPlano = "starter" }: WaitlistFormProps) {
  const [form, setForm] = useState({
    nome: "",
    email: "",
    plano: defaultPlano as PlanoInteresse,
    empresa: "",
    n_lojas: "" as number | "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Lê ?plano= do hash da URL no mount + escuta mudanças (quando user clica em outro card).
  // Também garante que o form fique visível ao chegar aqui via clique do card.
  useEffect(() => {
    const apply = () => {
      const p = readPlanoFromHash();
      if (p) {
        setForm((f) => ({ ...f, plano: p }));
        // Browser pode não rolar quando o hash contém '?' — fazemos manual.
        document.getElementById("waitlist")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});
    setServerError(null);

    const result = waitlistSchema.safeParse({
      ...form,
      n_lojas: form.n_lojas === "" ? undefined : Number(form.n_lojas),
    });

    if (!result.success) {
      const map: Record<string, string> = {};
      for (const issue of result.error.errors) {
        const key = issue.path[0] as string;
        if (key && !map[key]) map[key] = issue.message;
      }
      setErrors(map);
      return;
    }

    setSubmitting(true);
    try {
      const utmSource = new URLSearchParams(window.location.search).get(
        "utm_source",
      );
      const utmMedium = new URLSearchParams(window.location.search).get(
        "utm_medium",
      );
      const utmCampaign = new URLSearchParams(window.location.search).get(
        "utm_campaign",
      );

      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: result.data.nome,
          email: result.data.email,
          plano: result.data.plano,
          empresa: result.data.empresa || undefined,
          n_lojas: typeof result.data.n_lojas === "number"
            ? result.data.n_lojas
            : undefined,
          utm_source: utmSource ?? undefined,
          utm_medium: utmMedium ?? undefined,
          utm_campaign: utmCampaign ?? undefined,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro ${res.status}: ${text.slice(0, 200)}`);
      }

      sendGAEvent("event", "waitlist_signup", {
        value: 1,
        plano: result.data.plano,
      });

      setSuccess(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setServerError(`Falha ao cadastrar: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="rounded-2xl border border-mudacao-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-mudacao-100 text-mudacao-700">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h3 className="mt-4 text-2xl font-bold text-mudacao-950">
          Você está na lista!
        </h3>
        <p className="mt-2 text-slate-600">
          Vamos te avisar pessoalmente no email <strong>{form.email}</strong>{" "}
          assim que o plano <strong>{PLANOS_LABEL[form.plano]}</strong>{" "}
          estiver disponível.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-mudacao-200 bg-white p-6 shadow-sm sm:p-8"
    >
      <h3 className="text-2xl font-bold text-mudacao-950">
        🚀 Lista de espera
      </h3>
      <p className="mt-2 text-slate-600">
        Os planos pagos estão em construção. Cadastre-se pra ser avisado no
        lançamento — primeira leva ganha condições especiais.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <FieldWrap label="Plano de interesse" error={errors.plano}>
          <select
            className="input"
            value={form.plano}
            onChange={(e) =>
              setForm({ ...form, plano: e.target.value as PlanoInteresse })
            }
          >
            <option value="starter">Starter — R$ 99/mês</option>
            <option value="pro">Pro — R$ 299/mês</option>
            <option value="enterprise">Enterprise — sob consulta</option>
          </select>
        </FieldWrap>

        <FieldWrap label="Nome" error={errors.nome}>
          <input
            type="text"
            className="input"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            placeholder="Seu nome"
          />
        </FieldWrap>

        <FieldWrap label="Email" error={errors.email}>
          <input
            type="email"
            className="input"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="seu@email.com"
            autoComplete="email"
          />
        </FieldWrap>

        <FieldWrap label="Empresa (opcional)" error={errors.empresa}>
          <input
            type="text"
            className="input"
            value={form.empresa}
            onChange={(e) => setForm({ ...form, empresa: e.target.value })}
            placeholder="Sua rede"
          />
        </FieldWrap>

        <FieldWrap
          label="Lojas na rede (opcional)"
          error={errors.n_lojas}
          hint="Pra entender o tamanho da sua operação"
        >
          <input
            type="number"
            inputMode="numeric"
            min={0}
            className="input"
            value={form.n_lojas}
            onChange={(e) =>
              setForm({
                ...form,
                n_lojas: e.target.value === "" ? "" : Number(e.target.value),
              })
            }
            placeholder="ex: 50"
          />
        </FieldWrap>
      </div>

      {serverError && (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {serverError}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="btn-primary mt-6 w-full text-lg"
      >
        {submitting ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Cadastrando...
          </>
        ) : (
          <>
            Entrar na lista <ArrowRight className="h-5 w-5" />
          </>
        )}
      </button>

      <p className="mt-3 text-center text-xs text-slate-500">
        Sem spam. Você só recebe quando o plano lançar.
      </p>
    </form>
  );
}

function FieldWrap({
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
