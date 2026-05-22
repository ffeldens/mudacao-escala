import { ChevronDown } from "lucide-react";

export const faqItems = [
  {
    q: "O que é a PEC 8/2025?",
    a: "É a Proposta de Emenda à Constituição que reduz a jornada de trabalho semanal de 44 horas (escala 6x1) para 40 horas (escala 5x2). Afeta diretamente varejo, food service e qualquer setor com operação 6 ou 7 dias por semana.",
  },
  {
    q: "Quando a PEC 8/2025 entra em vigor?",
    a: "Ainda está em tramitação no Congresso. A previsão de transição é gradual, com prazos para adaptação das empresas. Recomendamos simular o impacto agora para ter tempo de planejar antes da entrada em vigor obrigatória.",
  },
  {
    q: "Quanto custa migrar para a escala 5x2?",
    a: "Em média, redes de varejo gastam entre 8% e 14% a mais com folha de pagamento (estudo Fitch). O valor exato depende do porte da loja, horário de funcionamento, headcount atual e salário médio. Use nosso simulador grátis para ter o número da sua rede.",
  },
  {
    q: "É possível reduzir o impacto financeiro?",
    a: "Sim. Workforce Management (WFM) baseado em IA pode reduzir 4 a 7% da folha através de alocação mais precisa de pessoas vs. demanda. Outras estratégias: mix com horistas regulamentados, multifunção e renegociação coletiva.",
  },
  {
    q: "O simulador é realmente gratuito?",
    a: "Sim. A simulação de 1 loja com 3 cenários (pessimista, neutro, otimista) e extrapolação para rede é 100% gratuita e sem cadastro inicial. Você só fornece email e WhatsApp se quiser receber o PDF com o relatório completo.",
  },
  {
    q: "Meus dados são seguros?",
    a: "Sim. Nenhum dado de funcionário identificado é coletado — apenas números agregados (quantos FTEs, salário médio). Os dados ficam criptografados em banco seguro e não compartilhamos seu contato com terceiros.",
  },
  {
    q: "Em quanto tempo recebo o resultado?",
    a: "Instantâneo. O cálculo roda em menos de 1 segundo. O PDF chega no seu email em até 30 segundos após o gate de captura.",
  },
  {
    q: "Funciona para food service e restaurantes?",
    a: "Sim. As fórmulas são as mesmas para qualquer operação CLT em escala 6x1 com jornada de 44h/semana. Bares, restaurantes e franquias de alimentação são casos de uso comuns.",
  },
];

export function FAQ() {
  return (
    <section id="faq" className="px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-center text-3xl font-bold text-mudacao-950 sm:text-4xl">
          Perguntas frequentes
        </h2>
        <p className="mt-4 text-center text-lg text-slate-600">
          Tudo o que você precisa saber sobre a PEC 8/2025 e o simulador.
        </p>

        <div className="mt-12 space-y-3">
          {faqItems.map((item) => (
            <details
              key={item.q}
              className="group rounded-xl border border-slate-200 bg-white p-5 open:shadow-sm"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-mudacao-950">
                <span>{item.q}</span>
                <ChevronDown className="h-5 w-5 flex-shrink-0 text-mudacao-700 transition group-open:rotate-180" />
              </summary>
              <p className="mt-4 leading-relaxed text-slate-700">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
