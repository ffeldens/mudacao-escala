/**
 * Callback do magic link / OAuth do Supabase.
 *
 * O Supabase Auth manda o usuário pra cá após click no link do email,
 * com um `code` no querystring. Trocamos por sessão e redirecionamos.
 *
 * Atrás do Caddy/proxy reverso, request.url tem o host interno
 * (localhost:8011). Pra evitar vazar isso nas URLs de redirect,
 * usamos:
 *   1. NEXT_PUBLIC_APP_BASE_URL (env explícita) — prioridade máxima
 *   2. X-Forwarded-Host + X-Forwarded-Proto (Caddy injeta) — fallback
 *   3. host header puro — último recurso
 */

import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";

function getPublicOrigin(request: NextRequest): string {
  // 1. Env var explícita (recomendado pra prod)
  const envUrl = process.env.NEXT_PUBLIC_APP_BASE_URL;
  if (envUrl) return envUrl.replace(/\/$/, "");

  // 2. Headers do proxy reverso (Caddy)
  const fwdHost = request.headers.get("x-forwarded-host");
  const fwdProto = request.headers.get("x-forwarded-proto");
  if (fwdHost) {
    return `${fwdProto || "https"}://${fwdHost}`;
  }

  // 3. Fallback: usa host nativo (dev local)
  return new URL(request.url).origin;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") || "/minha-conta";

  const origin = getPublicOrigin(request);

  if (!code) {
    return NextResponse.redirect(`${origin}/login?reason=expired`);
  }

  const supabase = createSupabaseServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("Auth callback error:", error.message);
    return NextResponse.redirect(`${origin}/login?reason=expired`);
  }

  return NextResponse.redirect(`${origin}${next}`);
}
