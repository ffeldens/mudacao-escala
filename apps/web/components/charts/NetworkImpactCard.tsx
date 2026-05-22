"use client";

import { TrendingUp, Building2, Calendar } from "lucide-react";
import { brl } from "@/lib/utils";

interface NetworkImpactCardProps {
  nLojas: number;
  deltaPorLojaMes: number;
  deltaRedeMes: number;
  deltaRedeAno: number;
}

export function NetworkImpactCard({
  nLojas,
  deltaPorLojaMes,
  deltaRedeMes,
  deltaRedeAno,
}: NetworkImpactCardProps) {
  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-mudacao-950 p-8 text-white shadow-xl">
      <div className="flex items-center gap-2 text-mudacao-100">
        <TrendingUp className="h-5 w-5" />
        <span className="text-xs font-bold uppercase tracking-widest">
          Impacto na sua rede
        </span>
      </div>

      <div className="mt-4 flex items-baseline gap-3">
        <p className="text-5xl font-bold sm:text-6xl">{brl(deltaRedeMes)}</p>
        <span className="text-xl text-mudacao-100">/mês</span>
      </div>
      <p className="mt-2 text-mudacao-100">
        de aumento de folha na sua rede de {nLojas}{" "}
        {nLojas === 1 ? "loja" : "lojas"}
      </p>

      {/* Equação visual */}
      <div className="mt-8 flex flex-wrap items-center gap-2 text-sm">
        <div className="rounded-lg bg-white/10 px-3 py-2 backdrop-blur">
          <div className="text-xs text-mudacao-100">Por loja/mês</div>
          <div className="font-bold">{brl(deltaPorLojaMes)}</div>
        </div>
        <span className="text-2xl text-mudacao-200">×</span>
        <div className="rounded-lg bg-white/10 px-3 py-2 backdrop-blur">
          <div className="flex items-center gap-1 text-xs text-mudacao-100">
            <Building2 className="h-3 w-3" />
            Lojas
          </div>
          <div className="font-bold">{nLojas}</div>
        </div>
        <span className="text-2xl text-mudacao-200">=</span>
        <div className="rounded-lg bg-mudacao-700 px-3 py-2">
          <div className="text-xs text-mudacao-100">Por mês</div>
          <div className="font-bold">{brl(deltaRedeMes)}</div>
        </div>
      </div>

      {/* Anualizado */}
      <div className="mt-6 flex items-center gap-3 border-t border-white/10 pt-6">
        <Calendar className="h-5 w-5 text-mudacao-100" />
        <p className="text-sm text-mudacao-100">
          Em 1 ano:{" "}
          <strong className="text-white">{brl(deltaRedeAno)}</strong>
        </p>
      </div>
    </div>
  );
}
