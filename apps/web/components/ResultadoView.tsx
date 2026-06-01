"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  Mail,
  ArrowLeft,
  Sparkles,
  Lightbulb,
  Share2,
  Download,
  Loader2,
} from "lucide-react";

import type { SimulateResponse } from "@/lib/api";
import { getMySimulation } from "@/lib/api";
import { brl } from "@/lib/utils";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { ScenarioChart } from "@/components/charts/ScenarioChart";
import { NetworkImpactCard } from "@/components/charts/NetworkImpactCard";
import { FteBreakdown } from "@/components/charts/FteBreakdown";

type StoredResult = SimulateResponse & {
  _lead_nome?: string;
  _lead_email?: string;
};

export function ResultadoView() {
  const searchParams = useSearchParams();
  const simId = searchParams.get("id");

  const [data, setData] = useState<StoredResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let canceled = false;

    async function load() {
      // Cenário 1: ?id=... → carrega do backend (histórico)
      if (simId) {
        try {
          const supabase = createSupabaseBrowserClient();
          const {
            data: { session },
          } = await supabase.auth.getSession();
          if (!session) {
            setLoading(false);
            return;
          }
          const result = await getMySimulation(session.access_token, simId);
          if (!canceled) setData(result);
        } catch {
          // ignora — exibe estado vazio
        } finally {
          if (!canceled) setLoading(false);
        }
        return;
      }

      // Cenário 2: sem id → tenta sessionStorage (fluxo direto pós-form)
      try {
        const raw = sessionStorage.getItem("mudacao_simulacao_resultado");
        if (raw && !canceled) setData(JSON.parse(raw));
      } catch {
        // ignora
      }
      if (!canceled) setLoading(false);
    }
    load();

    return () => {
      canceled = true;
    };
  }, [simId]);

  if (loading) {
    return (
      <div className="card text-center">
        <p className="text-slate-500">Carregando...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card text-center">
        <h2 className="text-2xl font-bold text-mudacao-950">
          Nenhum resultado pra mostrar
        </h2>
        <p className="mt-2 text-slate-600">
          Volte ao simulador e preencha os dados pra ver seu resultado.
        </p>
        <Link href="/simulador" className="btn-primary mt-6 inline-flex">
          Ir ao simulador <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  // Parse strings → números (API retorna Decimals como string)
  const deltaPorLojaMes = parseFloat(data.delta_folha_mes);
  const deltaRedeMes = parseFloat(data.delta_folha_rede_mes);
  const deltaRedeAno = parseFloat(data.delta_folha_rede_ano);
  const deltaPct = parseFloat(data.delta_folha_pct);
  const fteAtual = parseFloat(data.fte_atual);
  const fteProposto = parseFloat(data.fte_proposto);
  const fteExtras = parseFloat(data.fte_extras_necessarios);
  const folhaAtual = parseFloat(data.folha_atual_mes);
  const economiaWfm = parseFloat(data.economia_potencial_wfm);
  const economiaWfmPct = parseFloat(data.economia_potencial_wfm_pct);

  return (
    <div className="space-y-6">
      {/* ============ HERO RESULTADO ============ */}
      <div className="rounded-2xl bg-mudacao-900 p-8 text-white shadow-lg">
        <p className="text-sm font-bold uppercase tracking-widest text-mudacao-100">
          {data._lead_nome
            ? `${data._lead_nome}, aqui está seu resultado`
            : "Resultado da simulação"}
        </p>
        <h1 className="mt-2 text-3xl font-bold leading-tight sm:text-4xl">
          {data.headline}
        </h1>

        {data._lead_email && (
          <p className="mt-4 flex items-center gap-2 text-sm text-mudacao-100">
            <Mail className="h-4 w-4" />
            Enviamos o PDF detalhado pra{" "}
            <strong className="text-white">{data._lead_email}</strong>
          </p>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs">
            +{deltaPct.toFixed(1)}% acima da folha atual
          </span>
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs">
            Cenário {data.cenarios.neutro ? "neutro" : "—"}
          </span>
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs">
            Hash: {data.inputs_hash.slice(0, 8)}
          </span>
        </div>
      </div>

      {/* ============ IMPACTO REDE ============ */}
      <NetworkImpactCard
        nLojas={data.n_lojas}
        deltaPorLojaMes={deltaPorLojaMes}
        deltaRedeMes={deltaRedeMes}
        deltaRedeAno={deltaRedeAno}
      />

      {/* ============ GRÁFICO 3 CENÁRIOS ============ */}
      <ScenarioChart folhaAtualMes={folhaAtual} cenarios={data.cenarios} />

      {/* ============ FTE BREAKDOWN ============ */}
      <FteBreakdown
        fteAtual={fteAtual}
        fteProposto={fteProposto}
        fteExtras={fteExtras}
        nLojas={data.n_lojas}
      />

      {/* ============ CTA WFM (PITCH PAGO) ============ */}
      <div className="rounded-2xl border-2 border-mudacao-200 bg-gradient-to-br from-white to-mudacao-50 p-8">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-mudacao-100 text-mudacao-700">
            <Lightbulb className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              💡 E se você pudesse economizar?
            </p>
            <h2 className="mt-2 text-2xl font-bold text-mudacao-950 sm:text-3xl">
              Com escala inteligente, sua rede economiza até{" "}
              <span className="text-mudacao-700">{brl(economiaWfm)}/mês</span>
            </h2>
            <p className="mt-3 leading-relaxed text-slate-700">
              Workforce Management baseado em IA aprende a curva de demanda da
              sua loja e aloca pessoas com mais precisão. Reduz folha em{" "}
              <strong>~{economiaWfmPct.toFixed(1).replace(".", ",")}%</strong>{" "}
              sem cortar headcount — apenas colocando cada pessoa na hora certa.
            </p>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <FeatureLi text="Curva de demanda por hora" />
              <FeatureLi text="Respeita restrições CLT" />
              <FeatureLi text="Cobertura sem ociosidade" />
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/precos" className="btn-primary">
                <Sparkles className="h-4 w-4" />
                Quero a versão completa
              </Link>
              <Link href="/precos#waitlist" className="btn-secondary">
                Avise-me no lançamento
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ============ AÇÕES ============ */}
      <div className="flex flex-col gap-3 rounded-xl bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-mudacao-950">Compartilhe ou refaça</p>
          <p className="text-sm text-slate-600">
            O PDF completo já está no seu email — também dá pra compartilhar com sua equipe.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ShareButton headline={data.headline} />
          <Link
            href="/simulador"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" /> Nova simulação
          </Link>
        </div>
      </div>

      {/* ============ DISCLAIMER ============ */}
      <p className="text-center text-xs text-slate-500">
        Resultado baseado em premissas Fitch + fórmulas internas MudAção. Para
        análise jurídica e plano de transição customizado, considere o plano
        Enterprise.
      </p>
    </div>
  );
}

function FeatureLi({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-700">
      <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-mudacao-700 text-xs text-white">
        ✓
      </span>
      {text}
    </div>
  );
}

function ShareButton({ headline }: { headline: string }) {
  function handleShare() {
    const text = `${headline}\n\nSimule a sua em: https://simulaescala.mudacao.com.br`;
    if (typeof navigator !== "undefined" && navigator.share) {
      navigator
        .share({ title: "MudAção Escala — Simulação", text })
        .catch(() => {});
    } else if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      alert("Texto copiado pro clipboard!");
    }
  }

  return (
    <button
      onClick={handleShare}
      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
    >
      <Share2 className="h-4 w-4" /> Compartilhar
    </button>
  );
}
