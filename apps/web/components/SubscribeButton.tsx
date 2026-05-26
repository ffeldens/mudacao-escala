"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface SubscribeButtonProps {
  plano: "starter";
  label?: string;
  className?: string;
  size?: "sm" | "lg";
}

/**
 * Botão "Assinar plano" que:
 * 1. Verifica se o user está logado (senão manda pra /login)
 * 2. Pega o access token Supabase
 * 3. Chama POST /api/stripe/checkout-session
 * 4. Redireciona pra URL do Stripe Checkout
 */
export function SubscribeButton({
  plano,
  label = "Assinar Starter — R$ 99/mês",
  className,
  size = "lg",
}: SubscribeButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setError(null);

    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      // Se não logado, manda pra login com redirect de volta pra /precos
      if (!session) {
        router.push(
          `/login?reason=assinar&redirect=${encodeURIComponent("/precos?plano=" + plano)}`,
        );
        return;
      }

      const res = await fetch("/api/stripe/checkout-session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ plano }),
      });

      if (!res.ok) {
        const text = await res.text();
        let msg = `Erro ${res.status}`;
        try {
          const json = JSON.parse(text);
          msg = json.detail || msg;
        } catch {
          msg = text.slice(0, 200) || msg;
        }
        throw new Error(msg);
      }

      const data: { session_id: string; url: string } = await res.json();

      // Redireciona pro Stripe Checkout (hosted page)
      window.location.href = data.url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Falha ao iniciar checkout: ${msg}`);
      setLoading(false);
    }
  }

  return (
    <div className={className}>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className={
          size === "lg"
            ? "btn-primary w-full text-lg"
            : "btn-primary w-full text-sm"
        }
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            Redirecionando...
          </>
        ) : (
          <>
            {label}
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>

      {error && (
        <p className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-900">
          {error}
        </p>
      )}

      <p className="mt-2 text-center text-xs text-slate-500">
        14 dias grátis · cancele a qualquer momento
      </p>
    </div>
  );
}
