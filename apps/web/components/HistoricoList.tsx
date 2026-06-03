"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Loader2,
  FileText,
  Building2,
  TrendingUp,
  Calendar,
  ArrowRight,
  Download,
} from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import {
  downloadExcelFromHistory,
  listMySimulations,
  type SimulationHistoryItem,
} from "@/lib/api";
import { brl, pct } from "@/lib/utils";

export function HistoricoList() {
  const [items, setItems] = useState<SimulationHistoryItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let canceled = false;

    async function load() {
      try {
        const supabase = createSupabaseBrowserClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) {
          setError("Sessão expirada — recarregue a página");
          return;
        }
        const resp = await listMySimulations(session.access_token, {
          limit: 100,
        });
        if (canceled) return;
        setItems(resp.items);
        setTotal(resp.total);
      } catch (e) {
        if (canceled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setError(`Falha ao carregar: ${msg}`);
      }
    }
    load();

    return () => {
      canceled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        {error}
      </div>
    );
  }

  if (items === null) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando histórico…
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <FileText className="mx-auto h-10 w-10 text-slate-300" />
        <p className="mt-4 text-slate-500">
          Você ainda não rodou nenhuma simulação como usuário Starter.
        </p>
        <Link href="/simulador" className="btn-primary mt-4 inline-flex">
          Rodar a primeira <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500">
        {total} {total === 1 ? "simulação" : "simulações"} encontradas.
      </p>

      {items.map((sim) => (
        <SimulationRow key={sim.id} sim={sim} />
      ))}
    </div>
  );
}

function SimulationRow({ sim }: { sim: SimulationHistoryItem }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const date = sim.created_at
    ? new Date(sim.created_at).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

  const delta = sim.delta_folha_pct
    ? pct(parseFloat(sim.delta_folha_pct))
    : "—";

  async function handleExportExcel(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setError(null);
    setDownloading(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setError("Sessão expirada");
        return;
      }
      await downloadExcelFromHistory(session.access_token, sim.id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white transition hover:border-mudacao-300 hover:shadow-sm">
      <Link
        href={`/simulador/resultado?id=${sim.id}`}
        className="block p-5"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <p className="text-sm font-semibold text-mudacao-950">
              {sim.nome_loja || `Simulação`}
            </p>
            {sim.headline && (
              <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                {sim.headline}
              </p>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3 w-3" /> {date}
              </span>
              <span className="inline-flex items-center gap-1">
                <Building2 className="h-3 w-3" /> {sim.n_lojas}{" "}
                {sim.n_lojas === 1 ? "loja" : "lojas"}
              </span>
              <span className="inline-flex items-center gap-1 font-semibold text-mudacao-700">
                <TrendingUp className="h-3 w-3" /> +{delta}
              </span>
            </div>
          </div>

          <ArrowRight className="h-5 w-5 flex-shrink-0 text-slate-400" />
        </div>
      </Link>

      <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-2.5">
        {error && (
          <span className="text-xs text-red-600" title={error}>
            Falhou
          </span>
        )}
        <button
          onClick={handleExportExcel}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-mudacao-300 hover:bg-mudacao-50 hover:text-mudacao-900 disabled:opacity-50"
        >
          {downloading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Gerando…
            </>
          ) : (
            <>
              <Download className="h-3.5 w-3.5" /> Exportar Excel
            </>
          )}
        </button>
      </div>
    </div>
  );
}
