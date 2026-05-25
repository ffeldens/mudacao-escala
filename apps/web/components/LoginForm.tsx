"use client";

import { useState } from "react";
import { ArrowRight, Loader2, Mail, CheckCircle2, Info } from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface LoginFormProps {
  redirectTo?: string;
  reason?: string;
}

const REASONS: Record<string, string> = {
  protected: "Você precisa estar logado pra acessar essa página.",
  assinar: "Faça login pra assinar o plano Starter.",
  expired: "Sua sessão expirou — entre novamente.",
};

export function LoginForm({ redirectTo, reason }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmed = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError("Email inválido.");
      return;
    }

    setSubmitting(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const origin = window.location.origin;
      const next = redirectTo
        ? `?next=${encodeURIComponent(redirectTo)}`
        : "";

      const { error: err } = await supabase.auth.signInWithOtp({
        email: trimmed,
        options: {
          emailRedirectTo: `${origin}/auth/callback${next}`,
        },
      });

      if (err) {
        setError(`Falha ao enviar: ${err.message}`);
        return;
      }

      setSuccess(true);
    } catch (e) {
      setError(`Erro inesperado: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="rounded-xl border border-mudacao-200 bg-mudacao-50 p-6 text-center">
        <CheckCircle2 className="mx-auto h-10 w-10 text-mudacao-700" />
        <h3 className="mt-3 text-lg font-bold text-mudacao-950">
          Link enviado!
        </h3>
        <p className="mt-2 text-sm text-slate-700">
          Cheque sua inbox em <strong>{email}</strong>. Clica no link mágico
          que enviamos pra entrar.
        </p>
        <p className="mt-3 text-xs text-slate-500">
          O email pode levar 1-2 minutos. Confere o spam se não chegar.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {reason && REASONS[reason] && (
        <div className="flex items-start gap-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-900">
          <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{REASONS[reason]}</span>
        </div>
      )}

      <div>
        <label className="label" htmlFor="email">
          Email
        </label>
        <div className="relative">
          <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            className="input pl-10"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@email.com"
            disabled={submitting}
          />
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="btn-primary w-full"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Enviando...
          </>
        ) : (
          <>
            Receber link mágico <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>
    </form>
  );
}
