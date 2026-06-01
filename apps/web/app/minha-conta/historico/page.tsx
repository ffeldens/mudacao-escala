import { redirect } from "next/navigation";
import Link from "next/link";
import { Crown, ArrowRight } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { HistoricoList } from "@/components/HistoricoList";
import { getCurrentUser, getUserProfile } from "@/lib/supabase/auth";

export const metadata = {
  title: "Histórico de simulações — MudAção Escala",
  description: "Veja todas as simulações que você rodou.",
  robots: { index: false, follow: false },
};

const PAID_TIERS = new Set(["starter", "pro", "enterprise"]);

export default async function HistoricoPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?reason=protected&redirect=/minha-conta/historico");
  }

  const profile = await getUserProfile();
  const isPaid = profile && PAID_TIERS.has(profile.plan_tier);

  // Paywall pra Free
  if (!isPaid) {
    return (
      <>
        <Header />
        <main className="min-h-[70vh] bg-mudacao-50 px-6 py-16">
          <div className="mx-auto max-w-2xl">
            <Link
              href="/minha-conta"
              className="text-sm text-mudacao-700 hover:underline"
            >
              ← Minha conta
            </Link>

            <div className="mt-6 rounded-2xl bg-gradient-to-br from-mudacao-900 to-mudacao-700 p-8 text-white">
              <Crown className="h-10 w-10 text-mudacao-100" />
              <h1 className="mt-4 text-2xl font-bold">
                Histórico é uma feature do Starter
              </h1>
              <p className="mt-3 text-mudacao-100">
                Pra ver e gerenciar todas as simulações que você roda, assine
                o plano <strong>Starter</strong>. R$ 99/mês com 14 dias grátis.
              </p>
              <Link
                href="/precos"
                className="mt-6 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-mudacao-900 shadow-sm transition hover:bg-mudacao-50"
              >
                Conhecer planos pagos
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />

      <main className="min-h-[70vh] bg-mudacao-50 px-6 py-12">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/minha-conta"
            className="text-sm text-mudacao-700 hover:underline"
          >
            ← Minha conta
          </Link>

          <div className="mt-4">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Histórico
            </span>
            <h1 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              Suas simulações
            </h1>
            <p className="mt-2 text-slate-600">
              Todas as análises que você rodou. Clica em qualquer uma pra
              reabrir o resultado completo.
            </p>
          </div>

          <div className="mt-8">
            <HistoricoList />
          </div>

          <div className="mt-10 rounded-xl border border-slate-200 bg-white p-5 text-center">
            <p className="text-sm text-slate-600">
              Quer rodar uma nova análise?
            </p>
            <Link
              href="/simulador"
              className="btn-primary mt-3 inline-flex text-sm"
            >
              Nova simulação <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
