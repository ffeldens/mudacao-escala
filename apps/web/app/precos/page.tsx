import Link from "next/link";
import { Check, ArrowRight } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { WaitlistForm } from "@/components/WaitlistForm";
import { SubscribeButton } from "@/components/SubscribeButton";

export const metadata = {
  title: "Planos e preços",
  description:
    "Escolha o plano ideal pra sua rede. Free pra simular, Starter / Pro / Enterprise pra ter planejador automático, validador CLT e auditoria jurídica.",
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
      "Extrapolação para rede",
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
      "Histórico de simulações",
      "Premissas customizadas",
      "Validador CLT em PDF",
      "Comparativo entre cenários",
      "Export Excel + Suporte WhatsApp",
    ],
    cta: "Assinar Starter — 14 dias grátis",
    href: "",
    highlight: true,
    subscribable: "starter" as const,
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
    href: "#waitlist?plano=pro",
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
    cta: "Tenho interesse",
    href: "#waitlist?plano=enterprise",
    highlight: false,
  },
];

export default function PrecosPage() {
  return (
    <>
      <Header />

      <main className="bg-white px-6 py-16">
        <div className="mx-auto max-w-7xl">
          <div className="text-center">
            <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
              Preços
            </span>
            <h1 className="mt-2 text-4xl font-bold text-mudacao-950 sm:text-5xl">
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
                    ? "relative rounded-2xl border-2 border-mudacao-900 bg-white p-8 shadow-lg"
                    : "rounded-2xl border border-slate-200 bg-white p-8"
                }
              >
                {tier.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-mudacao-900 px-3 py-0.5 text-xs font-bold uppercase tracking-widest text-white">
                    Recomendado
                  </div>
                )}
                <h3 className="text-xl font-bold text-mudacao-950">
                  {tier.name}
                </h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-mudacao-950">
                    {tier.price}
                  </span>
                  <span className="ml-1 text-slate-500">{tier.period}</span>
                </div>
                <p className="mt-4 text-sm text-slate-600">
                  {tier.description}
                </p>

                <ul className="mt-6 space-y-3">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-mudacao-700" />
                      <span className="text-slate-700">{f}</span>
                    </li>
                  ))}
                </ul>

                {"subscribable" in tier && tier.subscribable ? (
                  <div className="mt-8">
                    <SubscribeButton
                      plano={tier.subscribable}
                      label={tier.cta}
                      size="sm"
                    />
                  </div>
                ) : (
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
                )}
              </div>
            ))}
          </div>

          {/* Waitlist único — o WaitlistForm lê ?plano=... do hash e pré-seleciona */}
          <div id="waitlist" className="mx-auto mt-20 max-w-2xl space-y-6 scroll-mt-24">
            <WaitlistForm />

            <div className="rounded-xl border border-slate-200 bg-white p-5 text-center text-sm text-slate-600">
              Prefere conversar?{" "}
              <a
                href="https://wa.me/5511996325174?text=Oi%20Felipe%2C%20tenho%20interesse%20nos%20planos%20pagos%20do%20MudA%C3%A7%C3%A3o%20Escala"
                target="_blank"
                rel="noreferrer"
                className="font-semibold text-mudacao-700 underline hover:text-mudacao-900"
              >
                Chama o Felipe no WhatsApp
              </a>{" "}
              ou{" "}
              <a
                href="mailto:felipe@feldens.com?subject=MudA%C3%A7%C3%A3o%20Escala%20Planos"
                className="font-semibold text-mudacao-700 underline hover:text-mudacao-900"
              >
                envia um email
              </a>
              .
            </div>

            <div className="text-center">
              <Link
                href="/simulador"
                className="inline-flex items-center gap-1 text-sm text-mudacao-700 underline hover:text-mudacao-900"
              >
                Ou volte pro simulador grátis <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
