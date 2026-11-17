/**
 * Quinta — tipos e funções de apoio da tela de extração (sem React: dados entram, dados saem).
 *
 * ESCREVER SEM IA. Consulte o dia4_conceito.md.
 * Testes (na pasta semana-04/front):  npm test        (roda o Vitest uma vez)
 * Checar tipos:                       npx tsc
 *
 * Já pronto: os tipos, EXEMPLO e mensagensDeErro.
 * Você escreve: formatarLatencia, formatarCusto e resumo.
 */

/** Um item como a API devolve: tudo em texto, do jeito que o modelo extraiu. */
export type ItemExtraido = {
  descricao: string;
  cfop: string;
  quantidade: string;
  valor_unitario: string;
};

/** A nota como a API devolve em "nota". */
export type NotaExtraida = {
  numero: number;
  cnpj_emitente: string;
  uf_origem: string;
  uf_destino: string;
  valor_total: string;
  emitida_em: string;
  itens: ItemExtraido[];
};

/** A resposta inteira do POST /extracoes (o mesmo formato da docstring da rota, na quarta). */
export type RespostaExtracao = {
  nota: NotaExtraida;
  problemas: string[];
  provedor: string;           // quem respondeu: "anthropic", "gemini", "ollama" ou "demo"
  modelo: string;             // o modelo, como "claude-haiku-5-5"
  tokens_entrada: number;
  tokens_saida: number;
  custo_usd: string;          // texto, como "0.000270"
  latencia_ms: number;
};

/** Já pronto: um texto de nota para o botão "Usar exemplo" (o mesmo do experimentar.py). */
export const EXEMPLO = `DANFE - Documento Auxiliar da Nota Fiscal Eletrônica
NF-e nº 000.123   Série 1
Emitente: Eletro Sul Materiais Elétricos Ltda - CNPJ 11.222.333/0001-81 - Curitiba/PR
Destinatário: Construtora Horizonte S.A. - São Paulo/SP
Data de emissão: 03/11/2026
Produtos:
1. Cabo flexível 2,5 mm (rolo 100 m) - CFOP 6102 - Qtde 10 - Vl. unit. R$ 189,90 - Total R$ 1.899,00
2. Disjuntor bipolar 32 A - CFOP 6102 - Qtde 4 - Vl. unit. R$ 54,25 - Total R$ 217,00
Valor total da nota: R$ 2.116,00`;

/** Já pronta: a mesma da semana 3 (o "detail" de um erro da API vira uma lista de mensagens). */
export function mensagensDeErro(detail: unknown): string[] {
  if (typeof detail === "string") return [detail];
  if (!Array.isArray(detail)) return ["Erro inesperado da API"];
  return detail.map((d) => (typeof d === "string" ? d : `${d.loc.slice(1).join(".")}: ${d.msg}`));
}

/**
 * O tempo da chamada, para mostrar na tela.
 *   - menos de 1000 ms → "850 ms"
 *   - 1000 ms ou mais  → em segundos, com UMA casa e vírgula: 1500 → "1,5 s"; 12345 → "12,3 s"
 *
 * Dica: (ms / 1000).toFixed(1) dá o texto "1.5"; troque o ponto pela vírgula com .replace(".", ",").
 */
export function formatarLatencia(ms: number): string {
  if (ms >= 1000) {
    return (ms/1000).toFixed(1).replace('.',',')+' s';
  } else {
    return `${ms} ms`;
  }
  
}

/**
 * O custo em dólares, com 6 casas e vírgula: "0.000270" → "US$ 0,000270".
 * Use Number() para converter o texto, e o mesmo toFixed / replace da função de cima.
 */
export function formatarCusto(usd: string): string {
    
  return 'US$ '+ Number(usd).toFixed(6).replace('.',',');
}

/**
 * Uma linha de resumo da extração, no singular ou no plural:
 *   1 item e nenhum problema      → "1 item, nenhum problema"
 *   2 itens e 1 problema          → "2 itens, 1 problema"
 *   3 itens e 2 problemas         → "3 itens, 2 problemas"
 *   0 itens e 1 problema          → "0 itens, 1 problema"
 *
 * Os números vêm de r.nota.itens.length e r.problemas.length.
 * Dica: o "operador ternário" escolhe entre dois textos: n === 1 ? "item" : "itens".
 */
export function resumo(r: RespostaExtracao): string {
  const it = r.nota.itens.length;
  const txit = `${it} ${it === 1 ? 'item': 'itens'}`;
  const pb = r.problemas.length;
  let txpb = '';
  if (pb === 0) {
    txpb = 'nenhum problema';
  } else {
    txpb = `${pb} ${pb === 1 ? 'problema': 'problemas'}`; 
  }
  return `${txit}, ${txpb}`;  
}
