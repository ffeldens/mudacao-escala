/**
 * Browser-side Supabase client (Client Components).
 *
 * Mesma sessão (cookies) que o server, sincronizada pelo middleware.
 */

"use client";

import { createBrowserClient } from "@supabase/ssr";

export function createSupabaseBrowserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
