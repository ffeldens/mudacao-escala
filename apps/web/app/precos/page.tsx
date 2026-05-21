import Link from "next/link";
import { Check, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Planos e preços — MudAção Escala",
  description:
    "Escolha o plano ideal pra sua rede. Starter, Pro ou Enterprise — todos com simulador, planejador automático e auditoria CLT.",
};

const tiers = [
  {
    name: "Free",
    price: "R$ 0",
    period: "pra sempre",
    description: "Pra quem quer entender o impacto da PEC 8/2025",
    features: [
      "Simulador 1 loja",
      "3 cenários (pess/neutro/otim)",
      "Extrapolação rede",
      "PDF do resultado por email",
    ],
    cta: "Simular grátis",
    href: "/simulador",
    highlight: false,
  },
  {
    name: "Starter",
    price: "R$ 99",
    period: "/mês",
    description: "Pra lojas únicas e franquias pequenas",
    features: [
      "Tudo do Free",
      "Até 5 lojas",
      "Histórico de simulações",
      "Validador CLT em PDF",
      "Import CSV de RH",
      "Suporte por email",
    ],
    cta: "Avise-me no lançamento",
    href: "#waitlist",
    highlight: true,
  },
  {
    name: "Pro",
    price: "R$ 299",
    period: "/mês",
    description: "Pra redes pequenas e médias com gestão profissional",
    features: [
      "Tudo do Starter",
      "Até 30 lojas",
      "Planejador automático (CSP)",
      "Comparação com baseline",
      "Multi-usuário",
      "Suporte prioritário",
    ],
    cta: "Avise-me no lançamento",
    href: "#waitlist",
    highlight: false,
  },
  {
    name: "Enterprise",
    price: "Sob consulta",
    period: "",
    description: "Pra grandes redes e consultorias",
    features: [
      "Tudo do Pro",
      "Lojas ilimitadas",
      "Auditoria jurídica (hash CLT)",
      "SLA e onboarding dedicado",
      "Integrações customizadas",
      "Treinamento equipe RH",
    ],
    cta: "Falar com Felipe",
    href: "mailto:felipe@feldens.com?subject=MudAção%20Escala%20Enterprise",
    highlight: false,
  },
];

export default function PrecosPage() {
  return (
    <main className="min-h-screen bg-white px-6 py-16">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <Link href="/" className="text-sm text-mudacao-700 hover:underline">
            ← Início
          </Link>
          <h1 className="mt-4 text-4xl font-bold text-mudacao-950 sm:text-5xl">
            Planos e preços
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            Comece grátis. Cresça quando precisar.
          </p>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={
                tier.highlight
                  ? "rounded-2xl border-2 border-mudacao-900 bg-white p-8 shadow-lg"
                  : "rounded-2xl border border-slate-200 bg-white p-8"
              }
            >
              {tier.highlight && (
                <div className="mb-4 inline-block rounded-full bg-mudacao-100 px-3 py-1 text-xs font-semibold text-mudacao-900">
                  RECOMENDADO
                </div>
              )}
              <h3 className="text-xl font-bold text-mudacao-950">{tier.name}</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-mudacao-950">
                  {tier.price}
                </span>
                <span className="ml-1 text-slate-500">{tier.period}</span>
              </div>
              <p className="mt-4 text-sm text-slate-600">{tier.description}</p>

              <ul className="mt-6 space-y-3">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-mudacao-700" />
                    <span className="text-slate-700">{f}</span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.href}
                className={
                  tier.highlight
                    ? "btn-primary mt-8 w-full"
                    : "btn-secondary mt-8 w-full"
                }
              >
                {tier.cta} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ))}
        </div>

        <div
          id="waitlist"
          className="mx-auto mt-20 max-w-2xl rounded-2xl bg-mudacao-50 p-8 text-center"
        >
          <h2 className="text-2xl font-bold text-mudacao-950">
            🚀 Lançamento dos planos pagos em breve
          </h2>
          <p className="mt-3 text-slate-600">
            Use o simulador grátis hoje. Quando os planos pagos estiverem ativos,
            você é o primeiro a saber.
          </p>
          <Link href="/simulador" className="btn-primary mt-6">
            Simular agora <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </main>
  );
}
