import Link from "next/link";
import { ArrowRight, Calculator, BarChart3, FileText, Mail } from "lucide-react";

export default function HomePage() {
  return (
    <main>
      {/* Hero */}
      <section className="bg-gradient-to-br from-mudacao-50 to-white px-6 py-20">
        <div className="mx-auto max-w-5xl text-center">
          <span className="inline-block rounded-full bg-mudacao-100 px-4 py-1 text-sm font-medium text-mudacao-900">
            ⚖️ PEC 8/2025 · Transição da escala 6x1 → 5x2
          </span>

          <h1 className="mt-6 text-4xl font-bold tracking-tight text-mudacao-950 sm:text-6xl">
            Quanto sua rede vai gastar com a{" "}
            <span className="text-mudacao-700">nova escala 5x2?</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
            Calcule grátis em 2 minutos o impacto da PEC 8/2025 no seu varejo ou
            food service. Veja FTEs extras, aumento de folha e quanto você pode
            economizar com escala inteligente.
          </p>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link href="/simulador" className="btn-primary text-lg">
              Simular agora <ArrowRight className="h-5 w-5" />
            </Link>
            <Link href="#como-funciona" className="btn-secondary text-lg">
              Como funciona
            </Link>
          </div>

          <p className="mt-6 text-sm text-slate-500">
            ✓ Gratuito · ✓ Sem cadastro pra começar · ✓ Resultado em PDF por email
          </p>
        </div>
      </section>

      {/* Como funciona */}
      <section id="como-funciona" className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-bold text-mudacao-950 sm:text-4xl">
            Como funciona
          </h2>
          <p className="mt-4 text-center text-lg text-slate-600">
            3 passos. 2 minutos. Resultado completo.
          </p>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            <Step
              icon={<Calculator className="h-8 w-8" />}
              number="1"
              title="Informe sua loja"
              description="Quantos FTEs, salário médio, porte. Sem CSV, sem complicação."
            />
            <Step
              icon={<BarChart3 className="h-8 w-8" />}
              number="2"
              title="Veja o impacto"
              description="3 cenários (pessimista, neutro, otimista) com gráficos e KPIs."
            />
            <Step
              icon={<FileText className="h-8 w-8" />}
              number="3"
              title="Receba o PDF"
              description="Relatório completo no seu email pra compartilhar com a diretoria."
            />
          </div>
        </div>
      </section>

      {/* PEC 8 explicada */}
      <section className="bg-mudacao-50 px-6 py-20">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-mudacao-950">
            O que é a PEC 8/2025?
          </h2>
          <div className="mt-6 space-y-4 text-lg text-slate-700">
            <p>
              A PEC 8/2025 propõe reduzir a jornada de <strong>44h</strong> para{" "}
              <strong>40h semanais</strong>, eliminando a escala 6x1 (trabalha 6
              dias, folga 1) e migrando todos os trabalhadores pro modelo{" "}
              <strong>5x2</strong> (5 dias úteis + 2 de folga).
            </p>
            <p>
              Para o varejo e food service, o impacto é direto:{" "}
              <strong>cada loja precisa de mais pessoas</strong> pra cobrir o
              mesmo período de operação — geralmente entre <strong>8% e 14%</strong>{" "}
              de aumento de folha (estudo Fitch).
            </p>
            <p>
              A boa notícia: com{" "}
              <strong>Workforce Management baseado em IA</strong>, dá pra
              recuperar parte desse aumento alocando pessoas com mais precisão
              (4 a 7% de economia).
            </p>
          </div>

          <div className="mt-10 text-center">
            <Link href="/simulador" className="btn-primary text-lg">
              Calcular o impacto na minha rede <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <Mail className="mx-auto h-12 w-12 text-mudacao-700" />
          <h2 className="mt-4 text-3xl font-bold text-mudacao-950">
            Pronto pra ver os números?
          </h2>
          <p className="mt-4 text-lg text-slate-600">
            Em menos de 2 minutos você tem um relatório PDF completo no seu email.
          </p>
          <Link href="/simulador" className="btn-primary mt-8 text-lg">
            Simular grátis <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 px-6 py-12">
        <div className="mx-auto max-w-5xl text-center text-sm text-slate-500">
          <p>
            <strong className="text-mudacao-900">MudAção Escala</strong> · um
            sub-produto da{" "}
            <a
              href="https://mudacao.com.br"
              className="underline hover:text-mudacao-700"
            >
              MudAção
            </a>
          </p>
          <p className="mt-2">
            Felipe Feldens ·{" "}
            <a href="mailto:felipe@feldens.com" className="underline">
              felipe@feldens.com
            </a>
          </p>
        </div>
      </footer>
    </main>
  );
}

function Step({
  icon,
  number,
  title,
  description,
}: {
  icon: React.ReactNode;
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="card text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-mudacao-100 text-mudacao-700">
        {icon}
      </div>
      <div className="mt-4 text-sm font-bold uppercase tracking-widest text-mudacao-700">
        Passo {number}
      </div>
      <h3 className="mt-2 text-xl font-bold text-mudacao-950">{title}</h3>
      <p className="mt-2 text-slate-600">{description}</p>
    </div>
  );
}
