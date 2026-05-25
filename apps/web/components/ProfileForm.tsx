"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2 } from "lucide-react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface ProfileFormProps {
  initial: {
    nome: string;
    empresa: string;
    whatsapp: string;
  };
}

export function ProfileForm({ initial }: ProfileFormProps) {
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
        setError("Sessão expirada. Recarregue a página.");
        return;
      }

      const { error: err } = await supabase
        .schema("freemium")
        .from("user_profiles")
        .update({
          nome: form.nome.trim() || null,
          empresa: form.empresa.trim() || null,
          whatsapp: form.whatsapp.trim() || null,
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

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nome">
          <input
            type="text"
            className="input"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            placeholder="Seu nome"
          />
        </Field>

        <Field label="Empresa">
          <input
            type="text"
            className="input"
            value={form.empresa}
            onChange={(e) => setForm({ ...form, empresa: e.target.value })}
            placeholder="Sua loja / rede"
          />
        </Field>

        <Field label="WhatsApp" hint="Pra contato — formato (11) 99999-9999">
          <input
            type="tel"
            className="input"
            value={form.whatsapp}
            onChange={(e) => setForm({ ...form, whatsapp: e.target.value })}
            placeholder="(11) 99999-9999"
          />
        </Field>
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between gap-3">
        {saved && (
          <span className="flex items-center gap-1 text-sm text-mudacao-700">
            <CheckCircle2 className="h-4 w-4" />
            Salvo!
          </span>
        )}
        <button
          type="submit"
          disabled={saving}
          className="btn-primary ml-auto text-sm"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Salvando...
            </>
          ) : (
            "Salvar"
          )}
        </button>
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
