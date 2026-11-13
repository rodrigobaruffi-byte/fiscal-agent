import { test } from "node:test";
import assert from "node:assert/strict";

import { alterarItem, itemVazio, montarEnvio, notaVazia, totalDoFormulario, type ItemForm } from "./notas.ts";

function item(descricao: string, quantidade: string, valor_unitario: string): ItemForm {
  return { descricao, cfop: "6102", quantidade, valor_unitario };
}

test("totalDoFormulario soma e arredonda", () => {
  assert.equal(totalDoFormulario([item("Cabo", "10", "4.5"), item("Tomada", "3", "0.333")]), 46);
});

test("totalDoFormulario: campos vazios ou inválidos contam como zero", () => {
  assert.equal(totalDoFormulario([item("Cabo", "10", "4.5"), itemVazio(), item("X", "abc", "2")]), 45);
  assert.equal(totalDoFormulario([]), 0);
});

test("alterarItem troca só o campo pedido, no item pedido", () => {
  const itens = [item("Cabo", "10", "4.5"), item("Tomada", "3", "1")];
  const novos = alterarItem(itens, 1, "cfop", "5102");
  assert.equal(novos[1].cfop, "5102");
  assert.equal(novos[1].descricao, "Tomada");
  assert.deepEqual(novos[0], itens[0]);
});

test("alterarItem não altera a lista recebida", () => {
  const itens = [item("Cabo", "10", "4.5")];
  const antes = structuredClone(itens);
  const novos = alterarItem(itens, 0, "descricao", "Fio");
  assert.deepEqual(itens, antes);
  assert.notEqual(novos, itens); // é outra lista, não a mesma
});

test("montarEnvio converte e limpa", () => {
  const nota = { ...notaVazia(), numero: "15", cnpj_emitente: "11.222.333/0001-81", uf_origem: "pr",
                 uf_destino: "sp", valor_total: "45.00", emitida_em: "2026-11-05" };
  const envio = montarEnvio(nota, [item("Cabo", "10", "4.5"), itemVazio()]);
  assert.deepEqual(envio, {
    numero: 15,
    cnpj_emitente: "11.222.333/0001-81",
    uf_origem: "PR",
    uf_destino: "SP",
    valor_total: "45.00",
    emitida_em: "2026-11-05",
    itens: [item("Cabo", "10", "4.5")],
  });
});
