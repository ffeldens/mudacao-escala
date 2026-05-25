/**
 * Server-side Supabase client (Server Components, Route Handlers, Server Actions).
 *
 * Usa cookies da request via next/headers. Permite operações autenticadas
 * com a sessão atual do usuário.
 */

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export function createSupabaseServerClient() {
  const cookieStore = cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Component pode chamar setAll mas a resposta já foi flushed.
            // Middleware cuida do refresh — ignorar aqui é seguro.
          }
        },
      },
    },
  );
}
