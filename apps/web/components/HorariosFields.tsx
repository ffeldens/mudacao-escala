"use client";

import { cn } from "@/lib/utils";

/**
 * Componente reusável pra controlar horários de funcionamento por dia
 * (seg-sex / sáb / dom). Usado no SimulatorForm e ValidadorCLTForm.
 */

export interface HorariosState {
  hora_abertura: number;
  hora_fechamento: number;
  hora_abertura_sabado: number | null;
  hora_fechamento_sabado: number | null;
  sabado_fechado: boolean;
  hora_abertura_domingo: number | null;
  hora_fechamento_domingo: number | null;
  domingo_fechado: boolean;
}

interface HorariosFieldsProps {
  value: HorariosState;
  onChange: (next: HorariosState) => void;
}

export function HorariosFields({ value: h, onChange }: HorariosFieldsProps) {
  const sab_ab = h.hora_abertura_sabado ?? h.hora_abertura;
  const sab_fc = h.hora_fechamento_sabado ?? h.hora_fechamento;
  const dom_ab = h.hora_abertura_domingo ?? h.hora_abertura;
  const dom_fc = h.hora_fechamento_domingo ?? h.hora_fechamento;

  return (
    <div className="space-y-4">
      {/* SEG-SEX */}
      <DayBlock title="Segunda a sexta" required>
        <RangeFields
          abertura={h.hora_abertura}
          fechamento={h.hora_fechamento}
          onAbertura={(v) => onChange({ ...h, hora_abertura: v })}
          onFechamento={(v) => onChange({ ...h, hora_fechamento: v })}
        />
      </DayBlock>

      {/* SÁBADO */}
      <DayBlock
        title="Sábado"
        closed={h.sabado_fechado}
        onToggleClosed={(v) => onChange({ ...h, sabado_fechado: v })}
      >
        {!h.sabado_fechado && (
          <RangeFields
            abertura={sab_ab}
            fechamento={sab_fc}
            onAbertura={(v) => onChange({ ...h, hora_abertura_sabado: v })}
            onFechamento={(v) =>
              onChange({ ...h, hora_fechamento_sabado: v })
            }
          />
        )}
      </DayBlock>

      {/* DOMINGO */}
      <DayBlock
        title="Domingo"
        closed={h.domingo_fechado}
        onToggleClosed={(v) => onChange({ ...h, domingo_fechado: v })}
      >
        {!h.domingo_fechado && (
          <RangeFields
            abertura={dom_ab}
            fechamento={dom_fc}
            onAbertura={(v) => onChange({ ...h, hora_abertura_domingo: v })}
            onFechamento={(v) =>
              onChange({ ...h, hora_fechamento_domingo: v })
            }
          />
        )}
      </DayBlock>
    </div>
  );
}

function DayBlock({
  title,
  required,
  closed,
  onToggleClosed,
  children,
}: {
  title: string;
  required?: boolean;
  closed?: boolean;
  onToggleClosed?: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        closed ? "border-slate-200 bg-slate-50" : "border-mudacao-200 bg-white",
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-mudacao-950">
          {title}
        </span>
        {!required && onToggleClosed && (
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={!!closed}
              onChange={(e) => onToggleClosed(e.target.checked)}
              className="accent-mudacao-700"
            />
            Fechado
          </label>
        )}
      </div>
      {children}
    </div>
  );
}

function RangeFields({
  abertura,
  fechamento,
  onAbertura,
  onFechamento,
}: {
  abertura: number;
  fechamento: number;
  onAbertura: (v: number) => void;
  onFechamento: (v: number) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <label className="text-xs text-slate-500">
          Abertura: <strong>{abertura}h</strong>
        </label>
        <input
          type="range"
          min={6}
          max={14}
          step={1}
          value={abertura}
          onChange={(e) => onAbertura(Number(e.target.value))}
          className="w-full accent-mudacao-700"
        />
      </div>
      <div>
        <label className="text-xs text-slate-500">
          Fechamento: <strong>{fechamento}h</strong>
        </label>
        <input
          type="range"
          min={16}
          max={24}
          step={1}
          value={fechamento}
          onChange={(e) => onFechamento(Number(e.target.value))}
          className="w-full accent-mudacao-700"
        />
      </div>
    </div>
  );
}
