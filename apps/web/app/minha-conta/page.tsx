import Link from "next/link";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ProfileForm } from "@/components/ProfileForm";
import { PlanCard } from "@/components/PlanCard";
import { getCurrentUser, getUserProfile } from "@/lib/supabase/auth";

export const metadata = {
  title: "Minha conta — MudAção Escala",
  description: "Gerencie sua conta, plano e dados pessoais.",
  robots: { index: false, follow: false },
};

export default async function MinhaContaPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?reason=protected&redirect=/minha-conta");
  }

  const profile = await getUserProfile();

  return (
    <>
      <Header />

      <main className="min-h-[70vh] bg-mudacao-50 px-6 py-12">
        <div className="mx-auto max-w-3xl space-y-6">
          <div>
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Minha conta
            </span>
            <h1 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              Olá{profile?.nome ? `, ${profile.nome.split(" ")[0]}` : ""}
            </h1>
            <p className="mt-2 text-slate-600">
              Logado como <strong>{user.email}</strong>
            </p>
          </div>

          {/* Plano atual */}
          <PlanCard profile={profile} />

          {/* Dados pessoais */}
          <section className="card">
            <h2 className="text-xl font-bold text-mudacao-950">
              Dados pessoais
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Esses dados são usados nas simulações e no contato.
            </p>
            <div className="mt-6">
              <ProfileForm
                initial={{
                  nome: profile?.nome ?? "",
                  empresa: profile?.empresa ?? "",
                  whatsapp: profile?.whatsapp ?? "",
                }}
              />
            </div>
          </section>

          {/* Próximos passos */}
          <section className="card">
            <h2 className="text-xl font-bold text-mudacao-950">
              Próximos passos
            </h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <span className="font-semibold text-mudacao-700">▸</span>
                <div>
                  <Link
                    href="/simulador"
                    className="font-semibold text-mudacao-700 hover:underline"
                  >
                    Rodar uma nova simulação
                  </Link>{" "}
                  — todos os planos têm acesso ao simulador grátis.
                </div>
              </li>
              {profile?.plan_tier === "free" && (
                <li className="flex items-start gap-2">
                  <span className="font-semibold text-mudacao-700">▸</span>
                  <div>
                    <Link
                      href="/precos"
                      className="font-semibold text-mudacao-700 hover:underline"
                    >
                      Conhecer o plano Starter
                    </Link>{" "}
                    — histórico de simulações, validador CLT em PDF,
                    premissas customizadas. R$ 99/mês com 14 dias grátis.
                  </div>
                </li>
              )}
              <li className="flex items-start gap-2">
                <span className="font-semibold text-mudacao-700">▸</span>
                <div>
                  Dúvida ou sugestão? Escreve direto pro Felipe:{" "}
                  <a
                    href="mailto:felipe@feldens.com"
                    className="font-semibold text-mudacao-700 hover:underline"
                  >
                    felipe@feldens.com
                  </a>
                </div>
              </li>
            </ul>
          </section>
        </div>
      </main>

      <Footer />
    </>
  );
}
