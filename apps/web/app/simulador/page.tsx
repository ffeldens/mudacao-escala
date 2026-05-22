import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Simulador da PEC 8/2025 — Calcule o impacto da escala 5x2",
  description:
    "Preencha os dados da sua loja e veja o impacto da migração 6x1 → 5x2 em 2 minutos.",
};

export default function SimuladorPage() {
  return (
    <>
      <Header />

      <main className="min-h-screen bg-mudacao-50 px-6 py-12">
        <div className="mx-auto max-w-2xl">
          <div className="rounded-2xl bg-white p-8 shadow-sm">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Simulador grátis
            </span>
            <h1 className="mt-2 text-3xl font-bold text-mudacao-950">
              Simulador da PEC 8/2025
            </h1>
            <p className="mt-3 text-slate-600">
              Em 2 minutos você tem o impacto da nova escala 5x2 na sua rede.
            </p>

            {/* TODO D3: form completo aqui */}
            <div className="mt-8 rounded-xl border-2 border-dashed border-mudacao-200 p-12 text-center">
              <p className="text-slate-500">
                🚧 Form do simulador — em desenvolvimento (Dia 3 do sprint)
              </p>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
