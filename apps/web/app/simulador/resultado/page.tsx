import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ResultadoView } from "@/components/ResultadoView";

export const metadata = {
  title: "Seu resultado — Simulador PEC 8/2025",
  description: "Resultado completo da sua simulação 6x1 → 5x2.",
  robots: { index: false, follow: false }, // página privada de resultado
};

export default function ResultadoPage() {
  return (
    <>
      <Header />

      <main className="min-h-screen bg-mudacao-50 px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <ResultadoView />
        </div>
      </main>

      <Footer />
    </>
  );
}
