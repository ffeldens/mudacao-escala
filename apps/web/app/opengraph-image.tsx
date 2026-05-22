import { ImageResponse } from "next/og";

// Next.js gera dinamicamente o OG image em /opengraph-image
// (substitui o /og-image.png estático). Acessível em:
//   https://simulaescala.mudacao.com.br/opengraph-image

export const runtime = "edge";
export const alt = "MudAção Escala — Simulador PEC 8/2025";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #062920 0%, #0a4a3a 50%, #22553d 100%)",
          color: "white",
          fontFamily: "sans-serif",
          padding: "80px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
            fontSize: "28px",
            fontWeight: 600,
            color: "#dbeee4",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              background: "#dbeee4",
              borderRadius: "12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#0a4a3a",
              fontWeight: 800,
              fontSize: "28px",
            }}
          >
            M
          </div>
          MudAção Escala
        </div>

        <div
          style={{
            fontSize: "72px",
            fontWeight: 800,
            textAlign: "center",
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
          }}
        >
          Quanto sua rede vai gastar
        </div>
        <div
          style={{
            fontSize: "72px",
            fontWeight: 800,
            textAlign: "center",
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            color: "#8dc3a5",
            marginTop: "8px",
          }}
        >
          com a escala 5x2?
        </div>

        <div
          style={{
            marginTop: "48px",
            fontSize: "28px",
            color: "#b8dcc8",
            textAlign: "center",
          }}
        >
          Simulador grátis da PEC 8/2025 · 2 minutos · resultado em PDF
        </div>
      </div>
    ),
    { ...size },
  );
}
