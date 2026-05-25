import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { LoginForm } from "@/components/LoginForm";
import { getCurrentUser } from "@/lib/supabase/auth";

export const metadata = {
  title: "Entrar — MudAção Escala",
  description: "Acesse sua conta MudAção Escala via magic link no email.",
  robots: { index: false, follow: false },
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: { redirect?: string; reason?: string };
}) {
  // Se já estiver logado, vai direto pra minha conta
  const user = await getCurrentUser();
  if (user) {
    redirect(searchParams.redirect || "/minha-conta");
  }

  return (
    <>
      <Header />

      <main className="min-h-[70vh] bg-mudacao-50 px-6 py-16">
        <div className="mx-auto max-w-md">
          <div className="rounded-2xl bg-white p-8 shadow-sm">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Entrar / Criar conta
            </span>
            <h1 className="mt-2 text-3xl font-bold text-mudacao-950">
              Bem-vindo
            </h1>
            <p className="mt-3 text-slate-600">
              Sem senha — você recebe um link mágico no email pra entrar.
              Primeira vez? A conta é criada automaticamente.
            </p>

            <div className="mt-6">
              <LoginForm
                redirectTo={searchParams.redirect}
                reason={searchParams.reason}
              />
            </div>

            <p className="mt-6 text-center text-xs text-slate-500">
              Ao continuar, você concorda com nossos{" "}
              <a href="/termos" className="text-mudacao-700 underline">
                Termos
              </a>{" "}
              e{" "}
              <a href="/privacidade" className="text-mudacao-700 underline">
                Política de Privacidade
              </a>
              .
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
