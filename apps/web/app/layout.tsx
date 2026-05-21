import type { Metadata } from "next";
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
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "MudAção Escala — Simulador PEC 8/2025",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Simulador PEC 8/2025 — MudAção Escala",
    description: "Calcule grátis o impacto da escala 5x2 na sua rede.",
    images: ["/og-image.png"],
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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>
        {children}
      </body>
    </html>
  );
}
