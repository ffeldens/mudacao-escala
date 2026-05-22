import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { SimulatorForm } from "@/components/SimulatorForm";

export const metadata = {
  title: "Simulador da PEC 8/2025 — Calcule o impacto da escala 5x2",
  description:
    "Preencha os dados da sua loja e veja o impacto da migração 6x1 → 5x2 em 2 minutos. Grátis.",
};

export default function SimuladorPage() {
  return (
    <>
      <Header />

      <main className="min-h-screen bg-mudacao-50 px-6 py-12">
        <div className="mx-auto max-w-3xl">
          <div className="mb-8 text-center">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Simulador grátis · 2 minutos
            </span>
            <h1 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              Simulador da PEC 8/2025
            </h1>
            <p className="mt-3 text-slate-600">
              Quanto sua rede vai gastar com a transição 6x1 → 5x2?
            </p>
          </div>

          <SimulatorForm />
        </div>
      </main>

      <Footer />
    </>
  );
}
