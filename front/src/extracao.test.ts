// Testes do extracao.ts com o Vitest. Rodar (na pasta semana-04/front): npm test
import { describe, expect, it } from "vitest";
import { formatarCusto, formatarLatencia, resumo, type ItemExtraido, type RespostaExtracao } from "./extracao.ts";

const item: ItemExtraido = { descricao: "Cabo", cfop: "6102", quantidade: "10", valor_unitario: "189.90" };

function resposta(quantosItens: number, problemas: string[]): RespostaExtracao {
  return {
    nota: {
      numero: 123,
      cnpj_emitente: "11.222.333/0001-81",
      uf_origem: "PR",
      uf_destino: "SP",
      valor_total: "1899.00",
      emitida_em: "2026-11-03",
      itens: Array(quantosItens).fill(item),       // uma lista com o mesmo item repetido N vezes
    },
    problemas,
    provedor: "anthropic",
    modelo: "claude-haiku-5-5",
    tokens_entrada: 1200,
    tokens_saida: 300,
    custo_usd: "0.000270",
    latencia_ms: 812,
  };
}

describe("formatarLatencia", () => {
  it("abaixo de 1 segundo, em milissegundos", () => {
    expect(formatarLatencia(850)).toBe("850 ms");
    expect(formatarLatencia(0)).toBe("0 ms");
  });

  it("a partir de 1 segundo, em segundos com uma casa e vírgula", () => {
    expect(formatarLatencia(1000)).toBe("1,0 s");
    expect(formatarLatencia(1500)).toBe("1,5 s");
    expect(formatarLatencia(12345)).toBe("12,3 s");
  });
});

describe("formatarCusto", () => {
  it("dólares com 6 casas e vírgula", () => {
    expect(formatarCusto("0.000270")).toBe("US$ 0,000270");
    expect(formatarCusto("0.1")).toBe("US$ 0,100000");
  });
});

describe("resumo", () => {
  it("singular", () => {
    expect(resumo(resposta(1, ["Valor total não confere com os itens"]))).toBe("1 item, 1 problema");
  });

  it("plural", () => {
    expect(resumo(resposta(3, ["a", "b"]))).toBe("3 itens, 2 problemas");
  });

  it("nenhum problema e zero itens", () => {
    expect(resumo(resposta(1, []))).toBe("1 item, nenhum problema");
    expect(resumo(resposta(0, ["Nota sem itens"]))).toBe("0 itens, 1 problema");
  });
});
