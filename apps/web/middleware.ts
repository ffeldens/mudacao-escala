/**
 * Next.js root middleware — roda em toda request pra refresh do Supabase session.
 *
 * O matcher exclui assets estáticos e API routes que não precisam de session.
 */

import { type NextRequest } from "next/server";
import { updateSupabaseSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSupabaseSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths exceto os que começam com:
     * - _next/static (assets estáticos)
     * - _next/image (Image Optimization)
     * - favicon.ico, icon (favicons)
     * - opengraph-image, sitemap.xml, robots.txt
     * - .png/.jpg/.jpeg/.gif/.svg (imagens públicas)
     */
    "/((?!_next/static|_next/image|favicon.ico|icon|opengraph-image|sitemap.xml|robots.txt|.*\\.(?:png|jpg|jpeg|gif|svg|webp)$).*)",
  ],
};
