import { redirect } from "next/navigation";
import Link from "next/link";
import { Crown, ArrowRight, Settings } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { PremissasForm } from "@/components/PremissasForm";
import { getCurrentUser, getUserProfile } from "@/lib/supabase/auth";

export const metadata = {
  title: "Premissas customizadas — MudAção Escala",
  description: "Configure encargos, VR/VT e dias úteis específicos da sua empresa.",
  robots: { index: false, follow: false },
};

const PAID_TIERS = new Set(["starter", "pro", "enterprise"]);

const ENGINE_DEFAULTS = {
  encargos_pct: 78,    // %
  vr_dia: 32,          // R$
  vt_dia: 14,          // R$
  dias_uteis_mes: 22,  // dias
};

export default async function PremissasPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?reason=protected&redirect=/minha-conta/premissas");
  }

  const profile = await getUserProfile();
  const isPaid = profile && PAID_TIERS.has(profile.plan_tier);

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
                Premissas customizadas é feature do Starter
              </h1>
              <p className="mt-3 text-mudacao-100">
                Cada empresa tem encargos diferentes (varia 65-95%), valores
                de VR/VT próprios e calendário de dias úteis específico.
                Configure uma vez no Starter e todas as suas simulações usam
                esses valores automaticamente.
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
        <div className="mx-auto max-w-3xl space-y-6">
          <div>
            <Link
              href="/minha-conta"
              className="text-sm text-mudacao-700 hover:underline"
            >
              ← Minha conta
            </Link>

            <div className="mt-4 flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-mudacao-100 text-mudacao-700">
                <Settings className="h-5 w-5" />
              </div>
              <div>
                <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
                  Premissas
                </span>
                <h1 className="mt-1 text-3xl font-bold text-mudacao-950 sm:text-4xl">
                  Suas premissas financeiras
                </h1>
                <p className="mt-2 text-slate-600">
                  Aplicadas automaticamente em todas as suas simulações. Deixe
                  em branco pra usar o default do engine.
                </p>
              </div>
            </div>
          </div>

          <div className="card">
            <PremissasForm
              initial={{
                encargos_pct: profile?.pref_encargos_pct
                  ? (parseFloat(profile.pref_encargos_pct) * 100).toString()
                  : "",
                vr_dia: profile?.pref_vr_dia ?? "",
                vt_dia: profile?.pref_vt_dia ?? "",
                dias_uteis_mes: profile?.pref_dias_uteis_mes?.toString() ?? "",
              }}
              defaults={ENGINE_DEFAULTS}
            />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
            <p className="font-semibold text-mudacao-950">💡 Como funciona</p>
            <p className="mt-2">
              Quando você roda uma simulação <strong>logado como Starter+</strong>,
              o backend pega esses valores aqui e aplica em vez dos defaults.
              Cada simulação salva no histórico mantém a snapshot das premissas
              usadas naquele momento — então alterar aqui não retroage.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
