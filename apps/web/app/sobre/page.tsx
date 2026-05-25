import Link from "next/link";
import { ArrowRight, Linkedin, Mail, MessageSquare, ExternalLink } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Sobre — MudAção Escala",
  description:
    "Conheça o time por trás do simulador da PEC 8/2025. Um produto da MudAção, consultoria de cultura, estratégia e liderança.",
};

export default function SobrePage() {
  return (
    <>
      <Header />

      <main>
        {/* ============ HERO ============ */}
        <section className="bg-gradient-to-br from-mudacao-50 via-white to-mudacao-50 px-6 py-20">
          <div className="mx-auto max-w-3xl text-center">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Sobre
            </span>
            <h1 className="mt-2 text-4xl font-bold tracking-tight text-mudacao-950 sm:text-5xl">
              Transformação não é um slide.
              <br />
              <span className="text-mudacao-700">É o que acontece depois dele.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
              MudAção Escala é o primeiro produto digital aberto da{" "}
              <a
                href="https://mudacao.com.br"
                target="_blank"
                rel="noreferrer"
                className="text-mudacao-700 underline hover:text-mudacao-900"
              >
                MudAção
              </a>
              — consultoria de cultura, estratégia e liderança.
            </p>
          </div>
        </section>

        {/* ============ POR QUE ESSE SIMULADOR ============ */}
        <section className="px-6 py-20">
          <div className="mx-auto max-w-3xl">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Por que esse simulador
            </span>
            <h2 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              Da intenção à prática
            </h2>
            <div className="mt-6 space-y-5 text-lg leading-relaxed text-slate-700">
              <p>
                A PEC 8/2025 mexe com a operação de qualquer rede de varejo ou
                food service no Brasil. Mas a maior parte das discussões está em
                slides, projeções genéricas e estudos macro.
              </p>
              <p>
                Faltava algo simples: <strong>uma calculadora real, com os
                dados da sua loja</strong>, mostrando exatamente quanto a
                transição vai custar — e quanto dá pra recuperar com
                planejamento inteligente.
              </p>
              <p>
                É isso que MudAção Escala faz. Grátis, em 2 minutos, com
                relatório em PDF no seu email.
              </p>
            </div>
          </div>
        </section>

        {/* ============ FELIPE ============ */}
        <section className="bg-mudacao-50 px-6 py-20">
          <div className="mx-auto max-w-3xl">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Quem está por trás
            </span>
            <h2 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              Felipe Feldens
            </h2>
            <p className="mt-3 text-slate-600">
              Fundador da MudAção · Consultor, autor e conselheiro
            </p>

            <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-700">
              <p>
                18+ anos de liderança em empresas como{" "}
                <strong>Sicredi, 99, Bain &amp; Company, Lojas Renner, SKY e
                Hortifruti Natural da Terra</strong>.
              </p>
              <p>
                Trabalha na interseção de cultura, estratégia e tecnologia —
                com foco em transformações que saem do discurso e entram na
                prática.
              </p>
              <p>
                Criador do <strong>Método RAIZ</strong> (framework de
                implementação com IA), autor de{" "}
                <em>Queime o Plano</em> e <em>Mapa Errado</em> (ambos em
                produção), mentor e conselheiro no Sales Club.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href="https://www.linkedin.com/company/mudacao"
                target="_blank"
                rel="noreferrer"
                className="btn-secondary text-sm"
              >
                <Linkedin className="h-4 w-4" />
                LinkedIn MudAção
              </a>
              <a href="mailto:felipe@feldens.com" className="btn-secondary text-sm">
                <Mail className="h-4 w-4" />
                felipe@feldens.com
              </a>
            </div>
          </div>
        </section>

        {/* ============ MUDAÇÃO ============ */}
        <section className="px-6 py-20">
          <div className="mx-auto max-w-3xl">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              A casa
            </span>
            <h2 className="mt-2 text-3xl font-bold text-mudacao-950 sm:text-4xl">
              MudAção
            </h2>
            <p className="mt-3 text-lg text-slate-600">
              A interseção entre intenção e prática.
            </p>

            <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-700">
              <p>
                A MudAção entra onde a intenção já existe e a prática ainda
                não. Conectamos cultura, estratégia e liderança para mover
                organizações.
              </p>
              <p>
                <strong>Cultura, estratégia e liderança — nessa ordem.</strong>{" "}
                Trabalho em andamento. Resultado mensurável.
              </p>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <PillarCard
                title="Cultura"
                description="Mapear, alinhar, ativar — o sistema imunológico da estratégia."
              />
              <PillarCard
                title="Estratégia"
                description="Clareza acionável com integração de IA via Método RAIZ."
              />
              <PillarCard
                title="Liderança"
                description="Desenvolvimento executivo personalizado, do conselho ao operacional."
              />
            </div>

            <div className="mt-10">
              <a
                href="https://mudacao.com.br"
                target="_blank"
                rel="noreferrer"
                className="btn-primary"
              >
                Conhecer a MudAção
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
        </section>

        {/* ============ CTA FINAL ============ */}
        <section className="bg-gradient-to-br from-mudacao-900 to-mudacao-700 px-6 py-20 text-white">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-3xl font-bold sm:text-4xl">
              Quer entender o impacto da PEC 8 na sua rede?
            </h2>
            <p className="mt-4 text-lg text-mudacao-100">
              Em 2 minutos, sem cadastro inicial, com PDF detalhado no seu email.
            </p>
            <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/simulador"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-lg font-semibold text-mudacao-900 shadow-sm transition hover:bg-mudacao-50"
              >
                Simular grátis <ArrowRight className="h-5 w-5" />
              </Link>
              <a
                href="https://wa.me/5511996325174?text=Oi%20Felipe%2C%20quero%20conversar%20sobre%20o%20simulador%20da%20PEC%208%20para%20minha%20rede"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/30 px-6 py-3 text-lg font-semibold text-white transition hover:bg-white/10"
              >
                <MessageSquare className="h-5 w-5" />
                Falar pelo WhatsApp
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}

function PillarCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-mudacao-200 bg-white p-5">
      <h3 className="font-bold text-mudacao-950">{title}</h3>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </div>
  );
}
