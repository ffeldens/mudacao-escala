import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Termos de Uso — MudAção Escala",
  description: "Termos de uso do simulador da PEC 8/2025 da MudAção.",
  robots: { index: true, follow: true },
};

export default function TermosPage() {
  return (
    <>
      <Header />

      <main className="bg-white px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
            Termos
          </span>
          <h1 className="mt-2 text-4xl font-bold text-mudacao-950">
            Termos de Uso
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            Última atualização: 25 de maio de 2026
          </p>

          <div className="prose-mudacao mt-10 space-y-6 text-slate-700">
            <Section title="1. Sobre o serviço">
              <p>
                O <strong>MudAção Escala</strong> (acessível em{" "}
                <a href="/" className="text-mudacao-700 underline">
                  simulaescala.mudacao.com.br
                </a>
                ) é um simulador gratuito do impacto financeiro da PEC 8/2025
                (transição da escala 6x1 para 5x2) para varejo, food service e
                operações em geral.
              </p>
              <p>
                O serviço é oferecido por <strong>MudAção</strong> —
                consultoria de cultura, estratégia e liderança, com sede em
                Porto Alegre/RS, representada por Felipe Feldens
                (felipe@mudacao.com.br).
              </p>
            </Section>

            <Section title="2. Aceitação">
              <p>
                Ao utilizar o simulador, você declara que leu, compreendeu e
                concorda integralmente com estes Termos de Uso e com a{" "}
                <Link href="/privacidade" className="text-mudacao-700 underline">
                  Política de Privacidade
                </Link>
                . Se não concordar, não utilize o serviço.
              </p>
            </Section>

            <Section title="3. Uso do simulador">
              <p>
                A simulação é fornecida em caráter informativo e gratuito. Os
                cálculos baseiam-se em premissas públicas (estudo Fitch) e
                fórmulas paramétricas. <strong>Os resultados não substituem
                consultoria jurídica, contábil ou trabalhista</strong> — eles
                são uma referência inicial para planejamento.
              </p>
              <p>
                Você concorda em fornecer informações verdadeiras e atualizadas.
                Não nos responsabilizamos por decisões tomadas exclusivamente
                com base nos resultados do simulador.
              </p>
            </Section>

            <Section title="4. Propriedade intelectual">
              <p>
                Todo o conteúdo do site (textos, gráficos, código, logotipo,
                metodologia de cálculo) é de propriedade da MudAção e protegido
                pela Lei de Direitos Autorais (Lei 9.610/1998).
              </p>
              <p>
                Você pode compartilhar livremente o <strong>resultado da sua
                simulação</strong> (incluindo o PDF gerado) e o link público do
                serviço. É vedado o uso comercial não autorizado da
                metodologia, do nome, do logotipo ou do código-fonte.
              </p>
            </Section>

            <Section title="5. Limitação de responsabilidade">
              <p>
                O serviço é fornecido "como está", sem garantias expressas ou
                implícitas de disponibilidade contínua, ausência de erros ou
                adequação a um propósito específico.
              </p>
              <p>
                A MudAção não se responsabiliza por:
              </p>
              <ul className="list-disc pl-6">
                <li>
                  Decisões empresariais tomadas com base exclusiva no
                  simulador;
                </li>
                <li>
                  Interrupções temporárias do serviço (manutenção,
                  indisponibilidade de terceiros);
                </li>
                <li>
                  Mudanças regulatórias posteriores que tornem os cálculos
                  desatualizados.
                </li>
              </ul>
            </Section>

            <Section title="6. Planos pagos (futuros)">
              <p>
                Os planos pagos (Starter, Pro, Enterprise) listados em{" "}
                <Link href="/precos" className="text-mudacao-700 underline">
                  /precos
                </Link>{" "}
                ainda não estão ativos. A inscrição na lista de espera ("Avise-
                me no lançamento") não cria obrigação de fornecimento futuro
                nem reserva de preço.
              </p>
            </Section>

            <Section title="7. Modificações">
              <p>
                Podemos atualizar estes Termos a qualquer momento. A versão
                vigente sempre estará disponível nesta página, com a data de
                atualização atualizada no topo.
              </p>
            </Section>

            <Section title="8. Lei aplicável e foro">
              <p>
                Estes Termos regem-se pelas leis da República Federativa do
                Brasil. Fica eleito o foro da comarca de Porto Alegre/RS para
                dirimir eventuais controvérsias.
              </p>
            </Section>

            <Section title="9. Contato">
              <p>
                Dúvidas sobre estes Termos ou sobre o serviço?
              </p>
              <ul className="list-disc pl-6">
                <li>
                  Email:{" "}
                  <a
                    href="mailto:felipe@mudacao.com.br"
                    className="text-mudacao-700 underline"
                  >
                    felipe@mudacao.com.br
                  </a>
                </li>
                <li>
                  WhatsApp:{" "}
                  <a
                    href="https://wa.me/5511996325174"
                    className="text-mudacao-700 underline"
                  >
                    (11) 99632-5174
                  </a>
                </li>
              </ul>
            </Section>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mt-8 text-xl font-bold text-mudacao-950">{title}</h2>
      <div className="mt-3 space-y-3 leading-relaxed">{children}</div>
    </section>
  );
}
