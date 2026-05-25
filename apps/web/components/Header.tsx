import Link from "next/link";
import { ArrowRight, User as UserIcon } from "lucide-react";
import { getCurrentUser } from "@/lib/supabase/auth";
import { LogoutButton } from "./LogoutButton";

export async function Header() {
  const user = await getCurrentUser();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/60 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-mudacao-900"
        >
          <Logo />
          <span className="text-lg">
            MudAção <span className="text-mudacao-700">Escala</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-8 text-sm font-medium text-slate-700 md:flex">
          <Link href="/#como-funciona" className="hover:text-mudacao-900">
            Como funciona
          </Link>
          <Link href="/#pec-8" className="hover:text-mudacao-900">
            PEC 8/2025
          </Link>
          <Link href="/#faq" className="hover:text-mudacao-900">
            FAQ
          </Link>
          <Link href="/precos" className="hover:text-mudacao-900">
            Preços
          </Link>
          <Link href="/sobre" className="hover:text-mudacao-900">
            Sobre
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <Link
                href="/minha-conta"
                className="hidden items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 sm:inline-flex"
              >
                <UserIcon className="h-4 w-4" />
                Minha conta
              </Link>
              <LogoutButton />
            </>
          ) : (
            <Link
              href="/login"
              className="hidden rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 sm:inline-block"
            >
              Entrar
            </Link>
          )}
          <Link href="/simulador" className="btn-primary text-sm">
            Simular grátis <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function Logo() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <rect width="32" height="32" rx="8" fill="#0a4a3a" />
      <path
        d="M8 10h4v12H8zM14 14h4v8h-4zM20 8h4v14h-4z"
        fill="#fff"
      />
    </svg>
  );
}
