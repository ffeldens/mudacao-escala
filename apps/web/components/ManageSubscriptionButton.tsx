"use client";

import { useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

/**
 * Botão "Gerenciar assinatura" que abre o Stripe Customer Portal.
 *
 * 1. Pega session do Supabase
 * 2. Chama POST /api/stripe/portal-session com Bearer token
 * 3. Redireciona pra URL hospedada do Stripe
 */
export function ManageSubscriptionButton({
  className,
}: {
  className?: string;
}) {
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

      if (!session) {
        setError("Sessão expirada — recarregue a página");
        return;
      }

      const res = await fetch("/api/stripe/portal-session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
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

      const data: { url: string } = await res.json();
      window.location.href = data.url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setLoading(false);
    }
  }

  return (
    <div className={className}>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-lg bg-white/15 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-white/25 disabled:opacity-50"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Abrindo portal...
          </>
        ) : (
          <>
            <ExternalLink className="h-4 w-4" />
            Gerenciar assinatura
          </>
        )}
      </button>
      {error && (
        <p className="mt-2 rounded-lg bg-red-100 px-3 py-2 text-xs text-red-900">
          {error}
        </p>
      )}
    </div>
  );
}
