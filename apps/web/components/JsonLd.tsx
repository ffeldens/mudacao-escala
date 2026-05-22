import { faqItems } from "./FAQ";

/**
 * Microdata Schema.org pra rich snippets do Google.
 *
 * Renderiza 3 objetos:
 * 1. Organization (MudAção)
 * 2. WebApplication (o simulador em si)
 * 3. FAQPage (gerado a partir dos itens do FAQ)
 *
 * Renderizar dentro do <head> ou no topo do body, em <script type="application/ld+json">.
 */
export function JsonLd() {
  const baseUrl = "https://simulaescala.mudacao.com.br";

  const organization = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "MudAção",
    url: "https://mudacao.com.br",
    logo: `${baseUrl}/logo.png`,
    sameAs: ["https://mudacao.com.br"],
    contactPoint: {
      "@type": "ContactPoint",
      email: "felipe@feldens.com",
      contactType: "customer support",
      areaServed: "BR",
      availableLanguage: ["Portuguese"],
    },
  };

  const webApp = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: "MudAção Escala — Simulador PEC 8/2025",
    url: baseUrl,
    description:
      "Calculadora gratuita do impacto financeiro da transição da escala 6x1 para 5x2 (PEC 8/2025) para varejo e food service.",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    inLanguage: "pt-BR",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "BRL",
    },
    creator: {
      "@type": "Organization",
      name: "MudAção",
      url: "https://mudacao.com.br",
    },
  };

  const faqPage = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map(({ q, a }) => ({
      "@type": "Question",
      name: q,
      acceptedAnswer: {
        "@type": "Answer",
        text: a,
      },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(webApp) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqPage) }}
      />
    </>
  );
}
