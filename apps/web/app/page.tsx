import Link from "next/link";
import {
  ArrowRight,
  Calculator,
  BarChart3,
  FileText,
  Mail,
  Shield,
  Zap,
  TrendingDown,
  Clock,
} from "lucide-react";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { FAQ } from "@/components/FAQ";
import { JsonLd } from "@/components/JsonLd";

export default function HomePage() {
  return (
    <>
      <JsonLd />
      <Header />

      <main>
        {/* ============ HERO ============ */}
        <section className="relative overflow-hidden bg-gradient-to-br from-mudacao-50 via-white to-mudacao-50 px-6 py-20 sm:py-28">
          <div className="mx-auto max-w-5xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full bg-mudacao-100 px-4 py-1.5 text-sm font-medium text-mudacao-900">
              ⚖️ PEC 8/2025 · Transição da escala 6x1 → 5x2
            </span>

            <h1 className="mt-6 text-4xl font-bold tracking-tight text-mudacao-950 sm:text-6xl">
              Quanto sua rede vai gastar com a{" "}
              <span className="bg-gradient-to-r from-mudacao-700 to-mudacao-500 bg-clip-text text-transparent">
                nova escala 5x2?
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 sm:text-xl">
              Calcule grátis em <strong>2 minutos</strong> o impacto da PEC
              8/2025 no seu varejo ou food service. Veja FTEs extras, aumento
              de folha e quanto você pode economizar com escala inteligente.
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link href="/simulador" className="btn-primary text-lg">
                Simular agora <ArrowRight className="h-5 w-5" />
              </Link>
              <Link href="#como-funciona" className="btn-secondary text-lg">
                Como funciona
              </Link>
            </div>

            {/* Trust bar */}
            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-500">
              <span className="flex items-center gap-1.5">
                <Zap className="h-4 w-4 text-mudacao-600" /> Resultado em 2 minutos
              </span>
              <span className="flex items-center gap-1.5">
                <Shield className="h-4 w-4 text-mudacao-600" /> Sem cadastro inicial
              </span>
              <span className="flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-mudacao-600" /> PDF por email
              </span>
            </div>
          </div>
        </section>

        {/* ============ COMO FUNCIONA ============ */}
        <section id="como-funciona" className="px-6 py-20">
          <div className="mx-auto max-w-5xl">
            <div className="text-center">
              <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
                Como funciona
              </span>
              <h2 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
                3 passos. 2 minutos. Resultado completo.
              </h2>
            </div>

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
                description="3 cenários (pessimista, neutro, otimista) com gráficos e KPIs claros."
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

        {/* ============ MÉTRICAS / SOCIAL PROOF ============ */}
        <section className="bg-mudacao-900 px-6 py-16 text-white">
          <div className="mx-auto max-w-5xl">
            <div className="grid gap-8 text-center md:grid-cols-3">
              <Metric value="+R$ 2,8 mi" label="Custo anual médio por rede de 50 lojas" />
              <Metric value="8 a 14%" label="Aumento típico de folha (estudo Fitch)" />
              <Metric value="4 a 7%" label="Economia possível com WFM inteligente" />
            </div>
          </div>
        </section>

        {/* ============ PEC 8 EXPLICADA ============ */}
        <section id="pec-8" className="bg-mudacao-50 px-6 py-20">
          <div className="mx-auto max-w-3xl">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Contexto
            </span>
            <h2 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              O que é a PEC 8/2025?
            </h2>
            <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-700">
              <p>
                A PEC 8/2025 propõe reduzir a jornada de{" "}
                <strong>44h</strong> para <strong>40h semanais</strong>,
                eliminando a escala 6x1 (trabalha 6 dias, folga 1) e migrando
                todos os trabalhadores pro modelo <strong>5x2</strong> (5 dias
                úteis + 2 de folga).
              </p>
              <p>
                Para varejo e food service, o impacto é direto:{" "}
                <strong>cada loja precisa de mais pessoas</strong> pra cobrir o
                mesmo período de operação — geralmente entre{" "}
                <strong>8% e 14%</strong> de aumento de folha (estudo Fitch).
              </p>
              <p>
                A boa notícia: com{" "}
                <strong>Workforce Management baseado em IA</strong>, dá pra
                recuperar parte desse aumento alocando pessoas com mais
                precisão (4 a 7% de economia).
              </p>
            </div>

            <div className="mt-12 grid gap-4 sm:grid-cols-2">
              <BenefitCard
                icon={<TrendingDown className="h-5 w-5" />}
                title="Reduza o impacto"
                description="Veja exatamente quantos FTEs precisa contratar e quanto isso custa por mês"
              />
              <BenefitCard
                icon={<Clock className="h-5 w-5" />}
                title="Planeje com antecedência"
                description="Quanto antes começar a se adaptar, menor o risco de surpresa orçamentária"
              />
            </div>

            <div className="mt-12 text-center">
              <Link href="/simulador" className="btn-primary text-lg">
                Calcular o impacto na minha rede{" "}
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </section>

        {/* ============ FAQ ============ */}
        <FAQ />

        {/* ============ CTA FINAL ============ */}
        <section className="bg-gradient-to-br from-mudacao-900 to-mudacao-700 px-6 py-20 text-white">
          <div className="mx-auto max-w-3xl text-center">
            <Mail className="mx-auto h-12 w-12 text-mudacao-100" />
            <h2 className="mt-4 text-3xl font-bold sm:text-4xl">
              Pronto pra ver os números?
            </h2>
            <p className="mt-4 text-lg text-mudacao-100">
              Em menos de 2 minutos você tem um relatório PDF completo no seu
              email — pronto pra levar pra reunião.
            </p>
            <Link
              href="/simulador"
              className="mt-8 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-lg font-semibold text-mudacao-900 shadow-sm transition hover:bg-mudacao-50"
            >
              Simular grátis <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}

// ============================================================================
// Componentes auxiliares
// ============================================================================

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
    <div className="card relative text-center">
      <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-mudacao-900 px-3 py-0.5 text-xs font-bold uppercase tracking-widest text-white">
        Passo {number}
      </div>
      <div className="mx-auto mt-4 flex h-16 w-16 items-center justify-center rounded-full bg-mudacao-100 text-mudacao-700">
        {icon}
      </div>
      <h3 className="mt-4 text-xl font-bold text-mudacao-950">{title}</h3>
      <p className="mt-2 text-slate-600">{description}</p>
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-4xl font-bold sm:text-5xl">{value}</div>
      <div className="mt-2 text-sm text-mudacao-100">{label}</div>
    </div>
  );
}

function BenefitCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-mudacao-200 bg-white p-5">
      <div className="flex items-center gap-2 text-mudacao-700">
        {icon}
        <h3 className="font-bold text-mudacao-950">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </div>
  );
}
