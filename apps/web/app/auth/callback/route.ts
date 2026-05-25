/**
 * Callback do magic link / OAuth do Supabase.
 *
 * O Supabase Auth manda o usuário pra cá após click no link do email,
 * com um `code` no querystring. Trocamos por sessão e redirecionamos.
 */

import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") || "/minha-conta";

  if (!code) {
    return NextResponse.redirect(
      `${origin}/login?reason=expired`,
    );
  }

  const supabase = createSupabaseServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("Auth callback error:", error.message);
    return NextResponse.redirect(
      `${origin}/login?reason=expired`,
    );
  }

  return NextResponse.redirect(`${origin}${next}`);
}
