"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Mail, ArrowLeft } from "lucide-react";

import type { SimulateResponse } from "@/lib/api";
import { brl } from "@/lib/utils";

type StoredResult = SimulateResponse & {
  _lead_nome?: string;
  _lead_email?: string;
};

export function ResultadoView() {
  const [data, setData] = useState<StoredResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("mudacao_simulacao_resultado");
      if (raw) {
        setData(JSON.parse(raw));
      }
    } catch {
      // ignora
    }
    setLoading(false);
  }, []);

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

  // D4 vai refinar isso com Recharts; por agora, layout texto + KPI cards
  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="rounded-2xl bg-mudacao-900 p-8 text-white shadow-lg">
        <p className="text-sm font-bold uppercase tracking-widest text-mudacao-100">
          Resultado da simulação
        </p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">{data.headline}</h1>
        {data._lead_email && (
          <p className="mt-4 flex items-center gap-2 text-sm text-mudacao-100">
            <Mail className="h-4 w-4" />
            Enviamos o PDF detalhado pra <strong>{data._lead_email}</strong>
          </p>
        )}
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard
          label="Aumento mensal (rede)"
          value={brl(parseFloat(data.delta_folha_rede_mes))}
          accent
        />
        <KpiCard
          label="Aumento anual (rede)"
          value={brl(parseFloat(data.delta_folha_rede_ano))}
        />
        <KpiCard
          label="% acima da folha atual"
          value={`${parseFloat(data.delta_folha_pct).toFixed(1).replace(".", ",")}%`}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard
          label="FTEs hoje (6x1)"
          value={parseFloat(data.fte_atual).toFixed(0)}
        />
        <KpiCard
          label="FTEs necessários (5x2)"
          value={parseFloat(data.fte_proposto).toFixed(2)}
        />
        <KpiCard
          label="Contratações extras"
          value={parseFloat(data.fte_extras_necessarios).toFixed(2)}
        />
      </div>

      {/* WFM card */}
      <div className="card border-2 border-mudacao-200">
        <p className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
          💡 Economia potencial com WFM
        </p>
        <h2 className="mt-2 text-3xl font-bold text-mudacao-950">
          {brl(parseFloat(data.economia_potencial_wfm))} / mês
        </h2>
        <p className="mt-2 text-slate-600">
          Com Workforce Management baseado em IA, sua rede pode reduzir{" "}
          <strong>
            ~{parseFloat(data.economia_potencial_wfm_pct).toFixed(1).replace(".", ",")}
            %
          </strong>{" "}
          da folha proposta — alocando pessoas com mais precisão vs. demanda.
        </p>
        <Link href="/precos" className="btn-primary mt-6 inline-flex">
          Quero a versão completa <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {/* Comparação 3 cenários (texto, vira gráfico no D4) */}
      <div className="card">
        <h2 className="text-xl font-bold text-mudacao-950">
          Comparação dos 3 cenários
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Gráfico visual chega no D4. Por enquanto, em formato tabela:
        </p>
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="pb-2">Cenário</th>
              <th className="pb-2 text-right">FTE</th>
              <th className="pb-2 text-right">Folha/mês</th>
              <th className="pb-2 text-right">Δ %</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.cenarios).map(([key, c]) => (
              <tr key={key} className="border-b border-slate-100">
                <td className="py-2 font-medium capitalize text-mudacao-950">
                  {c.cenario}
                </td>
                <td className="py-2 text-right">{parseFloat(c.fte_total).toFixed(2)}</td>
                <td className="py-2 text-right">{brl(parseFloat(c.folha_total))}</td>
                <td className="py-2 text-right">
                  {parseFloat(c.delta_folha_pct).toFixed(1).replace(".", ",")}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Voltar */}
      <Link
        href="/simulador"
        className="inline-flex items-center gap-1 text-sm text-mudacao-700 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Fazer nova simulação
      </Link>
    </div>
  );
}

function KpiCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={
        accent
          ? "rounded-xl bg-mudacao-700 p-5 text-white"
          : "card"
      }
    >
      <p
        className={
          accent
            ? "text-xs font-semibold uppercase tracking-widest text-mudacao-100"
            : "text-xs font-semibold uppercase tracking-widest text-slate-500"
        }
      >
        {label}
      </p>
      <p
        className={
          accent
            ? "mt-2 text-2xl font-bold"
            : "mt-2 text-2xl font-bold text-mudacao-950"
        }
      >
        {value}
      </p>
    </div>
  );
}
