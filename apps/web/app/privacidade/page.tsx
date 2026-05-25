import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Política de Privacidade — MudAção Escala",
  description:
    "Como o MudAção Escala coleta, usa e protege seus dados pessoais. Conforme LGPD (Lei 13.709/2018).",
  robots: { index: true, follow: true },
};

export default function PrivacidadePage() {
  return (
    <>
      <Header />

      <main className="bg-white px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <span className="text-sm font-bold uppercase tracking-widest text-mudacao-700">
            Privacidade
          </span>
          <h1 className="mt-2 text-4xl font-bold text-mudacao-950">
            Política de Privacidade
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            Última atualização: 25 de maio de 2026
          </p>

          <div className="mt-6 rounded-lg bg-mudacao-50 p-4 text-sm text-mudacao-900">
            <p>
              <strong>Resumo em 1 linha:</strong> coletamos apenas o que você
              voluntariamente fornece no formulário (nome, email, WhatsApp e
              dados agregados da sua loja), usamos pra te entregar o relatório
              e melhorar o serviço, e não compartilhamos com terceiros para fins
              comerciais.
            </p>
          </div>

          <div className="mt-10 space-y-6 text-slate-700">
            <Section title="1. Quem somos (Controlador dos dados)">
              <p>
                <strong>MudAção</strong> — consultoria de cultura, estratégia
                e liderança, representada por Felipe Feldens
                (felipe@mudacao.com.br).
              </p>
              <p>
                Esta política aplica-se ao serviço <strong>MudAção
                Escala</strong> (simulaescala.mudacao.com.br).
              </p>
            </Section>

            <Section title="2. Quais dados coletamos">
              <p>
                <strong>Dados que você fornece voluntariamente</strong> ao
                preencher o formulário do simulador:
              </p>
              <ul className="list-disc pl-6">
                <li>Nome completo</li>
                <li>Email</li>
                <li>WhatsApp / telefone</li>
                <li>Empresa (opcional)</li>
                <li>
                  Dados agregados da sua operação: setor, porte, número de FTEs,
                  salário médio, faturamento mensal (opcional), horários de
                  funcionamento, número de lojas
                </li>
              </ul>
              <p>
                <strong>Dados coletados automaticamente</strong>:
              </p>
              <ul className="list-disc pl-6">
                <li>
                  IP, navegador, sistema operacional, páginas visitadas,
                  origem do tráfego (referenciador, UTM)
                </li>
                <li>
                  Cookies essenciais e cookies de análise (Google Analytics 4)
                </li>
              </ul>
              <p>
                <strong>Não coletamos</strong> dados de funcionários
                identificáveis, CPF, RG, dados financeiros pessoais ou
                informações sensíveis.
              </p>
            </Section>

            <Section title="3. Para que usamos seus dados (Finalidade)">
              <ul className="list-disc pl-6">
                <li>
                  Processar a simulação solicitada e entregar o relatório PDF
                  por email;
                </li>
                <li>
                  Comunicação direta sobre o resultado e eventual follow-up
                  comercial caso você se interesse em planos pagos;
                </li>
                <li>
                  Análise agregada e anônima de uso pra melhorar o produto;
                </li>
                <li>
                  Cumprimento de obrigações legais e regulatórias.
                </li>
              </ul>
            </Section>

            <Section title="4. Base legal (LGPD Art. 7)">
              <ul className="list-disc pl-6">
                <li>
                  <strong>Consentimento</strong> (Art. 7º, I): você marca a
                  caixa de aceite antes de submeter o formulário;
                </li>
                <li>
                  <strong>Legítimo interesse</strong> (Art. 7º, IX): análise
                  agregada e melhoria do serviço;
                </li>
                <li>
                  <strong>Execução de contrato</strong> (Art. 7º, V):
                  entregar a simulação que você solicitou.
                </li>
              </ul>
            </Section>

            <Section title="5. Compartilhamento com terceiros">
              <p>
                Não vendemos nem compartilhamos seus dados para fins comerciais.
                Utilizamos operadores tecnológicos com seus próprios termos de
                proteção de dados:
              </p>
              <ul className="list-disc pl-6">
                <li>
                  <strong>Supabase</strong> (PostgreSQL gerenciado) — armazena
                  o banco de dados;
                </li>
                <li>
                  <strong>Resend</strong> — envio de email transacional com o
                  PDF do resultado;
                </li>
                <li>
                  <strong>Google Analytics 4</strong> — análise agregada de
                  uso. Você pode optar por desativar no seu navegador via{" "}
                  <a
                    href="https://tools.google.com/dlpage/gaoptout"
                    target="_blank"
                    rel="noreferrer"
                    className="text-mudacao-700 underline"
                  >
                    add-on oficial do Google
                  </a>
                  ;
                </li>
                <li>
                  <strong>Hostinger</strong> — infraestrutura de servidor.
                </li>
              </ul>
              <p>
                Todos os operadores acima possuem políticas de proteção de
                dados próprias e adotam medidas técnicas para garantir a
                segurança das informações.
              </p>
            </Section>

            <Section title="6. Segurança">
              <p>
                Adotamos medidas técnicas e administrativas para proteger seus
                dados, incluindo:
              </p>
              <ul className="list-disc pl-6">
                <li>Conexões cifradas (HTTPS / TLS) em todas as páginas;</li>
                <li>Armazenamento em banco de dados criptografado;</li>
                <li>
                  Acesso restrito por autenticação e princípio do menor
                  privilégio;
                </li>
                <li>Logs de auditoria para acesso a dados pessoais.</li>
              </ul>
              <p>
                Apesar disso, nenhum sistema é 100% imune. Em caso de
                incidente que possa expor seus dados, você será notificado
                conforme prazos da LGPD.
              </p>
            </Section>

            <Section title="7. Retenção">
              <p>
                Mantemos seus dados pelo tempo necessário às finalidades
                descritas, observando as seguintes orientações:
              </p>
              <ul className="list-disc pl-6">
                <li>
                  <strong>Leads sem conversão</strong>: até 24 meses, depois
                  anonimizados ou excluídos automaticamente;
                </li>
                <li>
                  <strong>Dados de simulação</strong>: agregados e anonimizados
                  após 12 meses;
                </li>
                <li>
                  <strong>Solicitação de exclusão</strong>: atendida em até
                  15 dias úteis a partir do recebimento (LGPD Art. 19, §3º).
                </li>
              </ul>
            </Section>

            <Section title="8. Seus direitos (LGPD Art. 18)">
              <p>Você tem direito a, a qualquer momento, solicitar:</p>
              <ul className="list-disc pl-6">
                <li>Confirmação da existência de tratamento dos seus dados;</li>
                <li>Acesso aos dados;</li>
                <li>Correção de dados incompletos, inexatos ou desatualizados;</li>
                <li>
                  Anonimização, bloqueio ou eliminação de dados desnecessários
                  ou excessivos;
                </li>
                <li>
                  Portabilidade dos dados a outro fornecedor de serviço;
                </li>
                <li>
                  Eliminação dos dados tratados com seu consentimento;
                </li>
                <li>
                  Informação sobre entidades com as quais compartilhamos seus
                  dados;
                </li>
                <li>Revogação do consentimento, a qualquer momento.</li>
              </ul>
              <p>
                Para exercer qualquer destes direitos, envie um email para{" "}
                <a
                  href="mailto:felipe@mudacao.com.br"
                  className="text-mudacao-700 underline"
                >
                  felipe@mudacao.com.br
                </a>{" "}
                com o assunto "LGPD — solicitação de dados".
              </p>
            </Section>

            <Section title="9. Cookies">
              <p>Usamos os seguintes tipos de cookies:</p>
              <ul className="list-disc pl-6">
                <li>
                  <strong>Essenciais</strong>: necessários ao funcionamento do
                  site (sessionStorage do navegador para preservar dados do
                  formulário);
                </li>
                <li>
                  <strong>Análise</strong>: Google Analytics 4 para entender
                  padrões de uso de forma agregada. Você pode desativá-los nas
                  configurações do seu navegador a qualquer momento.
                </li>
              </ul>
            </Section>

            <Section title="10. Encarregado de Dados (DPO)">
              <p>
                O encarregado de proteção de dados (DPO) é{" "}
                <strong>Felipe Feldens</strong>, contatável em{" "}
                <a
                  href="mailto:felipe@mudacao.com.br"
                  className="text-mudacao-700 underline"
                >
                  felipe@mudacao.com.br
                </a>
                .
              </p>
            </Section>

            <Section title="11. Alterações nesta política">
              <p>
                Podemos atualizar esta política periodicamente. Quando
                houver mudança material, comunicaremos por email os usuários
                ativos. A versão vigente sempre estará disponível nesta página
                com a data de atualização no topo.
              </p>
            </Section>

            <Section title="12. Autoridade Nacional de Proteção de Dados (ANPD)">
              <p>
                Caso você acredite que seus direitos não foram respeitados,
                pode também apresentar reclamação à{" "}
                <a
                  href="https://www.gov.br/anpd/pt-br"
                  target="_blank"
                  rel="noreferrer"
                  className="text-mudacao-700 underline"
                >
                  ANPD
                </a>
                .
              </p>
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
