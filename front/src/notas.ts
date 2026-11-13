/**
 * Quinta — tipos e funções de apoio do formulário (sem React: dados entram, dados saem).
 *
 * ESCREVER SEM IA. Consulte o dia4_conceito.md.
 * Testes (na pasta semana-03/front):  node --test src/notas.test.ts
 * Checar tipos:                       npx tsc
 *
 * Já pronto: os tipos, formatarMoeda, notaVazia, itemVazio e mensagensDeErro.
 * Você escreve: totalDoFormulario, alterarItem e montarEnvio.
 */

/** Uma nota como o GET /notas devolve. Valores em dinheiro chegam como TEXTO ("150.00"). */
export type NotaResumo = {
  id: number;
  numero: number;
  cnpj_emitente: string;
  uf_origem: string;
  uf_destino: string;
  valor_total: string;
  emitida_em: string;
};

/** Os campos da nota no formulário. Tudo é texto, porque é o que um <input> guarda. */
export type NotaForm = {
  numero: string;
  cnpj_emitente: string;
  uf_origem: string;
  uf_destino: string;
  valor_total: string;
  emitida_em: string;
};

/** Um item no formulário, também só com texto. */
export type ItemForm = {
  descricao: string;
  cfop: string;
  quantidade: string;
  valor_unitario: string;
};

/** O JSON que o POST /notas espera: o número como número; o resto pode ir como texto. */
export type NotaEnvio = {
  numero: number;
  cnpj_emitente: string;
  uf_origem: string;
  uf_destino: string;
  valor_total: string;
  emitida_em: string;
  itens: ItemForm[];
};

/** Já pronta: 1234.5 -> "R$ 1.234,50" */
export function formatarMoeda(valor: number): string {
  return "R$ " + valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Já pronta: um formulário de nota em branco. */
export function notaVazia(): NotaForm {
  return { numero: "", cnpj_emitente: "", uf_origem: "", uf_destino: "", valor_total: "", emitida_em: "" };
}

/** Já pronta: uma linha de item em branco. */
export function itemVazio(): ItemForm {
  return { descricao: "", cfop: "", quantidade: "", valor_unitario: "" };
}

/**
 * Já pronta: transforma o "detail" de um erro da API numa lista de mensagens para a tela.
 * O detail pode vir em três formatos:
 *   - texto:              "Nota já cadastrada para este emitente"        (o 409)
 *   - lista de textos:    ["Item 1: CFOP 5102 ...", "Valor total ..."]   (o 422 das regras, o seu)
 *   - lista de objetos:   [{"loc": [...], "msg": "Field required"}, ...] (o 422 do Pydantic)
 */
export function mensagensDeErro(detail: unknown): string[] {
  if (typeof detail === "string") return [detail];
  if (!Array.isArray(detail)) return ["Erro inesperado da API"];
  return detail.map((d) => (typeof d === "string" ? d : `${d.loc.slice(1).join(".")}: ${d.msg}`));
}

/**
 * Soma quantidade x valor unitário dos itens do formulário, arredondado a 2 casas.
 * Os campos são texto: converta com Number(). Campo vazio ou inválido conta como 0.
 * [{quantidade: "10", valor_unitario: "4.5"}, {quantidade: "", ...}] -> 45
 *
 * Dica: Number("") dá 0; Number("abc") dá NaN. A expressão Number(texto) || 0 troca NaN por 0.
 */
export function totalDoFormulario(itens: ItemForm[]): number {
  let total = 0;
  for (const item of itens){
    total += (Number(item.quantidade) || 0) * (Number(item.valor_unitario) || 0);
  }
  return Math.round(total*100)/100;
  
}

/**
 * Devolve uma lista NOVA de itens, com um campo de um item trocado. A lista recebida não muda.
 * alterarItem(itens, 1, "cfop", "6102") -> igual a itens, mas o item da posição 1 com cfop "6102".
 *
 * Por que uma lista nova: o React só redesenha a tela quando o estado recebe um valor NOVO
 * (seção 3 do conceito). Alterar a lista antiga no lugar não avisa ninguém.
 *
 * Passo a passo: itens.map((item, i) => (i === indice ? { ...item, [campo]: valor } : item))
 */
export function alterarItem(itens: ItemForm[], indice: number, campo: keyof ItemForm, valor: string): ItemForm[] {
  const novalista = itens.map((item,i) => (i===indice ? {...item,[campo]:valor}:item));
    
  return novalista;
}

/**
 * Monta o JSON do POST a partir do formulário.
 *   - numero vira número (Number);
 *   - UFs em maiúsculas (a API também converte, mas é bom mandar certo);
 *   - os demais campos da nota vão como estão;
 *   - itens: só os que têm descrição preenchida (linhas em branco ficam de fora).
 */
export function montarEnvio(nota: NotaForm, itens: ItemForm[]): NotaEnvio {
  const envio : NotaEnvio = {
    numero: Number(nota.numero),
    cnpj_emitente: nota.cnpj_emitente,
    uf_origem: nota.uf_origem.toUpperCase(),
    uf_destino: nota.uf_destino.toUpperCase(),
    valor_total: nota.valor_total,
    emitida_em: nota.emitida_em,
    itens: itens.filter((x) => x.descricao !== '')
  };
  return envio;
}



