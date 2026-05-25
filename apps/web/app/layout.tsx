import type { Metadata } from "next";
import { GoogleAnalytics } from "@next/third-parties/google";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://simulaescala.mudacao.com.br"),
  title: {
    default: "Simulador PEC 8/2025 — Calcule o impacto da escala 5x2 | MudAção",
    template: "%s | MudAção Escala",
  },
  description:
    "Calcule grátis quanto sua rede de varejo ou food service vai gastar com a transição da escala 6x1 para 5x2 (PEC 8/2025). Veja FTEs extras, aumento de folha e economia possível com WFM.",
  keywords: [
    "PEC 8 2025",
    "PEC 8/2025",
    "escala 5x2",
    "escala 6x1",
    "calculadora folha",
    "redução jornada",
    "44 horas 40 horas",
    "varejo",
    "food service",
    "workforce management",
    "MudAção",
  ],
  authors: [{ name: "MudAção", url: "https://mudacao.com.br" }],
  creator: "MudAção",
  publisher: "MudAção",
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://simulaescala.mudacao.com.br",
    siteName: "MudAção Escala",
    title: "Simulador PEC 8/2025 — Calcule o impacto da escala 5x2",
    description:
      "Quanto sua rede vai gastar com a nova escala 5x2? Simule grátis em 2 minutos.",
    // Next pega o opengraph-image.tsx automaticamente
  },
  twitter: {
    card: "summary_large_image",
    title: "Simulador PEC 8/2025 — MudAção Escala",
    description: "Calcule grátis o impacto da escala 5x2 na sua rede.",
    // Next reaproveita o opengraph-image.tsx pro Twitter card
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

// Referência direta a process.env.NEXT_PUBLIC_GA_ID (sem var intermediária)
// pra garantir que o Next bake o valor em build time. Default vazio = GA off.
// Em dev local, deixar a env var unset desativa silenciosamente.

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const gaId = process.env.NEXT_PUBLIC_GA_ID ?? "";

  return (
    <html lang="pt-BR">
      <body>{children}</body>
      {gaId.startsWith("G-") && <GoogleAnalytics gaId={gaId} />}
    </html>
  );
}
