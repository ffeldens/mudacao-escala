import Link from "next/link";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-200 bg-slate-50 px-6 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-8 md:grid-cols-4">
          <div className="md:col-span-2">
            <p className="text-lg font-bold text-mudacao-900">
              MudAção <span className="text-mudacao-700">Escala</span>
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Simulador gratuito do impacto da PEC 8/2025 (transição 6x1 → 5x2)
              para varejo e food service.
            </p>
            <p className="mt-4 text-sm text-slate-600">
              Um sub-produto da{" "}
              <a
                href="https://mudacao.com.br"
                className="text-mudacao-700 underline hover:text-mudacao-900"
              >
                MudAção
              </a>{" "}
              · consultoria em transformação operacional.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              Produto
            </h3>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              <li>
                <Link href="/simulador" className="hover:text-mudacao-900">
                  Simulador
                </Link>
              </li>
              <li>
                <Link href="/precos" className="hover:text-mudacao-900">
                  Preços
                </Link>
              </li>
              <li>
                <Link href="/sobre" className="hover:text-mudacao-900">
                  Sobre
                </Link>
              </li>
              <li>
                <Link href="/#faq" className="hover:text-mudacao-900">
                  FAQ
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
              Contato
            </h3>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              <li>
                <a
                  href="mailto:felipe@mudacao.com.br"
                  className="hover:text-mudacao-900"
                >
                  felipe@mudacao.com.br
                </a>
              </li>
              <li>
                <a
                  href="https://wa.me/5511996325174"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-mudacao-900"
                >
                  WhatsApp: (11) 99632-5174
                </a>
              </li>
              <li>
                <a
                  href="https://www.linkedin.com/company/mudacao"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-mudacao-900"
                >
                  LinkedIn
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-slate-200 pt-6 text-center text-xs text-slate-500">
          © {year} MudAção. Todos os direitos reservados.
        </div>
      </div>
    </footer>
  );
}
