"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  LabelList,
} from "recharts";

import type { CenarioOut } from "@/lib/api";
import { brl } from "@/lib/utils";

interface ScenarioChartProps {
  /** Folha atual (pra mostrar a linha de referência) */
  folhaAtualMes: number;
  /** Cenários da API: { pessimista, neutro, otimista } */
  cenarios: Record<string, CenarioOut>;
}

const NOMES_PT = {
  pessimista: "Pessimista",
  neutro: "Neutro",
  otimista: "Otimista",
} as const;

const CORES = {
  pessimista: "#dc2626", // vermelho — pior caso
  neutro: "#0a4a3a", // mudacao verde escuro
  otimista: "#5ea27f", // mudacao verde claro
} as const;

export function ScenarioChart({ folhaAtualMes, cenarios }: ScenarioChartProps) {
  const data = (["pessimista", "neutro", "otimista"] as const).map((key) => {
    const c = cenarios[key];
    return {
      key,
      cenario: NOMES_PT[key],
      folha: parseFloat(c.folha_total),
      delta_pct: parseFloat(c.delta_folha_pct),
    };
  });

  // Domínio do Y com folga de 10% pra labels respirar
  const maxFolha = Math.max(...data.map((d) => d.folha), folhaAtualMes);
  const yMax = Math.ceil(maxFolha * 1.15);

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-mudacao-950">
        Comparação dos 3 cenários
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Folha mensal projetada por loja (linha pontilhada = folha atual em 6x1)
      </p>

      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 30, right: 16, left: 16, bottom: 8 }}
          >
            <XAxis
              dataKey="cenario"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#475569", fontSize: 13, fontWeight: 600 }}
            />
            <YAxis
              domain={[0, yMax]}
              tickFormatter={(v) => brl(v).replace("R$", "R$ ").trim()}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              width={90}
            />
            <Tooltip
              cursor={{ fill: "rgba(10,74,58,0.05)" }}
              content={<CustomTooltip />}
            />
            <ReferenceLine
              y={folhaAtualMes}
              stroke="#64748b"
              strokeDasharray="4 4"
              label={{
                value: "Folha atual (6x1)",
                position: "right",
                fill: "#64748b",
                fontSize: 11,
              }}
            />
            <Bar dataKey="folha" radius={[8, 8, 0, 0]} maxBarSize={80}>
              {data.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={CORES[entry.key as keyof typeof CORES]}
                />
              ))}
              <LabelList
                dataKey="delta_pct"
                position="top"
                formatter={(v: number) =>
                  v >= 0 ? `+${v.toFixed(1)}%` : `${v.toFixed(1)}%`
                }
                style={{
                  fill: "#0f172a",
                  fontSize: 13,
                  fontWeight: 700,
                }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500">
        <Legend cor={CORES.pessimista} label="Sem ganho prod." />
        <Legend cor={CORES.neutro} label="Premissa Fitch" />
        <Legend cor={CORES.otimista} label="Com WFM bem feito" />
      </div>
    </div>
  );
}

function Legend({ cor, label }: { cor: string; label: string }) {
  return (
    <div className="flex items-center justify-center gap-1.5">
      <span
        className="inline-block h-2.5 w-2.5 rounded-sm"
        style={{ background: cor }}
      />
      {label}
    </div>
  );
}

interface TooltipPayload {
  payload: {
    cenario: string;
    folha: number;
    delta_pct: number;
  };
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-lg">
      <p className="text-sm font-bold text-mudacao-950">{item.cenario}</p>
      <p className="mt-1 text-xs text-slate-500">Folha/mês</p>
      <p className="text-lg font-bold text-mudacao-900">{brl(item.folha)}</p>
      <p
        className={`mt-1 text-xs font-semibold ${item.delta_pct >= 0 ? "text-red-600" : "text-green-700"}`}
      >
        {item.delta_pct >= 0 ? "+" : ""}
        {item.delta_pct.toFixed(2)}% vs hoje
      </p>
    </div>
  );
}
