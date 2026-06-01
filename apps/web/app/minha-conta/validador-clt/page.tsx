import { redirect } from "next/navigation";
import Link from "next/link";
import { Crown, ArrowRight, Shield } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ValidadorCLTForm } from "@/components/ValidadorCLTForm";
import { getCurrentUser, getUserProfile } from "@/lib/supabase/auth";

export const metadata = {
  title: "Validador CLT — MudAção Escala",
  description: "Avaliação automatizada de riscos CLT em PDF auditável.",
  robots: { index: false, follow: false },
};

const PAID_TIERS = new Set(["starter", "pro", "enterprise"]);

export default async function ValidadorCLTPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?reason=protected&redirect=/minha-conta/validador-clt");
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
                Validador CLT é feature do Starter
              </h1>
              <p className="mt-3 text-mudacao-100">
                Gere um PDF auditável com a análise dos artigos 71, 66, 67 e
                outros sobre o modelo 5x2 da sua loja. Hash de inputs +
                versão da régua CLT pra defesa em eventual auditoria.
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
          <Link
            href="/minha-conta"
            className="text-sm text-mudacao-700 hover:underline"
          >
            ← Minha conta
          </Link>

          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-mudacao-100 text-mudacao-700">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
                Validador CLT
              </span>
              <h1 className="mt-1 text-3xl font-bold text-mudacao-950 sm:text-4xl">
                Relatório auditável em PDF
              </h1>
              <p className="mt-2 text-slate-600">
                Avaliação automatizada dos artigos 71, 66, 67 e outros sobre o
                modelo 5x2 da sua loja. Preencha os dados e baixe o PDF com
                hash de inputs + versão da régua CLT.
              </p>
            </div>
          </div>

          <div className="card">
            <ValidadorCLTForm />
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            <p className="font-semibold">⚠️ Importante</p>
            <p className="mt-2">
              O relatório é uma <strong>avaliação automatizada</strong> baseada
              na régua CLT vigente. Não substitui parecer jurídico individualizado
              — use como instrumento de planejamento e prevenção, e leve pra
              seu jurídico antes do rollout.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
