"use client";

import { Users, UserPlus } from "lucide-react";

interface FteBreakdownProps {
  fteAtual: number;
  fteProposto: number;
  fteExtras: number;
  nLojas: number;
}

export function FteBreakdown({
  fteAtual,
  fteProposto,
  fteExtras,
  nLojas,
}: FteBreakdownProps) {
  const extrasNoBom = fteExtras > 0;
  const extrasRede = Math.ceil(fteExtras * nLojas * 100) / 100;

  // Pra visualização: largura da barra "atual" e "proposto"
  // Normaliza pra largura relativa (proposto sempre 100%)
  const atualPct = (fteAtual / fteProposto) * 100;

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-mudacao-950">
            Quantos FTEs sua loja precisa?
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Headcount necessário pra cobrir o mesmo período de operação
          </p>
        </div>
        <Users className="h-8 w-8 flex-shrink-0 text-mudacao-700" />
      </div>

      <div className="mt-6 space-y-4">
        {/* Barra: hoje */}
        <BarRow
          label="Hoje (escala 6x1)"
          value={fteAtual}
          widthPct={atualPct}
          color="bg-slate-300"
          textColor="text-slate-700"
        />
        {/* Barra: proposto */}
        <BarRow
          label="Necessário (escala 5x2)"
          value={fteProposto}
          widthPct={100}
          color="bg-mudacao-700"
          textColor="text-white"
        />
      </div>

      {extrasNoBom && (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <UserPlus className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-700" />
            <div>
              <p className="font-semibold text-amber-900">
                {formatFte(fteExtras)} FTEs extras por loja
              </p>
              <p className="mt-1 text-sm text-amber-800">
                Na sua rede de {nLojas}{" "}
                {nLojas === 1 ? "loja" : "lojas"}, isso significa{" "}
                <strong>~{formatFte(extrasRede)} contratações</strong> no
                total — ou redistribuição via multifunção/horistas.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BarRow({
  label,
  value,
  widthPct,
  color,
  textColor,
}: {
  label: string;
  value: number;
  widthPct: number;
  color: string;
  textColor: string;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-bold text-mudacao-950">{formatFte(value)} FTEs</span>
      </div>
      <div className="relative h-10 rounded-lg bg-slate-100">
        <div
          className={`${color} flex h-full items-center justify-end rounded-lg px-3 transition-all`}
          style={{ width: `${widthPct}%` }}
        >
          <span className={`text-sm font-bold ${textColor}`}>
            {formatFte(value)}
          </span>
        </div>
      </div>
    </div>
  );
}

function formatFte(value: number): string {
  return value.toFixed(2).replace(".", ",").replace(/,?0+$/, "");
}
