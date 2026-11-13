/**
 * Quinta — o formulário de cadastro de nota, com itens. Você completa os trechos FAÇA.
 *
 * ESCREVER SEM IA. Consulte o dia4_conceito.md (as seções estão indicadas em cada FAÇA).
 * Ver funcionando: veja o passo a passo da quinta no LEIAME da semana.
 * Checar tipos:    npx tsc   (na pasta semana-03/front)
 */
import { useState, type SubmitEvent } from "react";
import {
  alterarItem,
  formatarMoeda,
  itemVazio,
  mensagensDeErro,
  montarEnvio,
  notaVazia,
  totalDoFormulario,
  type ItemForm,
  type NotaForm,
} from "./notas.ts";

// Props: o que o componente recebe de quem o usa. Aqui, a função a chamar depois de salvar.
type Props = { aoSalvar: () => void };

export function FormNota({ aoSalvar }: Props) {
  const [nota, setNota] = useState<NotaForm>(notaVazia());            // os 6 campos da nota
  const [itens, setItens] = useState<ItemForm[]>([itemVazio()]);      // as linhas de itens (começa com 1)
  const [erros, setErros] = useState<string[]>([]);                   // erros devolvidos pela API

  // Já pronta: troca um campo da nota, guardando um objeto NOVO no estado.
  function alterarCampo(campo: keyof NotaForm, valor: string) {
    setNota({ ...nota, [campo]: valor });
  }

  // Chamada quando o formulário é enviado (botão Salvar ou Enter).
  async function enviar(evento: SubmitEvent) {
    evento.preventDefault();          // impede o navegador de recarregar a página (comportamento padrão do form)
    // FAÇA 3 (seção 5 do conceito):
    //   - POST em "/api/notas" com o corpo JSON.stringify(montarEnvio(nota, itens))
    //     e o cabeçalho "Content-Type": "application/json";
    //   - deu certo (resposta.ok)? limpe o formulário (notaVazia, [itemVazio()], erros []) e chame aoSalvar();
    //   - não deu? leia o corpo (await resposta.json()) e mostre setErros(mensagensDeErro(corpo.detail)).

    const resposta = await fetch("/api/notas", {             // o segundo argumento configura o pedido
      method: "POST",                                          // o método (o padrão do fetch é GET)
      headers: { "Content-Type": "application/json" },         // avisa a API que o corpo é JSON
      body: JSON.stringify(montarEnvio(nota,itens))                            // o objeto vira texto JSON
    });
    if (resposta.ok) {                                         // 200 a 299: deu certo (o 201 entra aqui)
      aoSalvar();             
      setNota(notaVazia());
      setItens([itemVazio()]);
      setErros([]);                                 // avisa quem usa o formulário
    } else {                                                   // 409, 422...
      const corpo = await resposta.json();                     // {"detail": ...}
      setErros(mensagensDeErro(corpo.detail));                 // já pronta: transforma em lista de textos
    }    

  }

  return (
    <form onSubmit={enviar}>
      <h2>Nova nota</h2>

      {/* Exemplo pronto de campo controlado: o value vem do estado; o onChange grava no estado. */}
      <label>
        Número{" "}
        <input value={nota.numero} onChange={(e) => alterarCampo("numero", e.target.value)} size={6} />
      </label>
      <label>
        Cnpj{" "}
        <input value={nota.cnpj_emitente} onChange={(e) => alterarCampo("cnpj_emitente", e.target.value)} size={17} />
      </label>
      <label>
        Uf de Origem{" "}
        <input 
          value={nota.uf_origem} 
          onChange={(e) => alterarCampo("uf_origem", e.target.value.toUpperCase())} 
          size={2}
          maxLength={2} />
      </label>
      <label>
        Uf de Destino{" "}
        <input value={nota.uf_destino} onChange={(e) => alterarCampo("uf_destino", e.target.value.toUpperCase())} 
          size={2} maxLength={2} />
      </label>
      <label>
        Data de Emissão{" "}
        <input value={nota.emitida_em} onChange={(e) => alterarCampo("emitida_em", e.target.value)} 
          size={2} type={"date"} />
      </label>
      <label>
        Valor Total{" "}
        <input value={nota.valor_total} onChange={(e) => alterarCampo("valor_total", e.target.value)} 
          size={10}  />
      </label>


      <table>
        <thead>
          <tr>
            <th>Descrição</th>
            <th>CFOP</th>
            <th>Quantidade</th>
            <th>Valor unitário</th>
          </tr>
        </thead>
        <tbody>
          {itens.map((item, indice) => (
            <tr key={indice}>
              {/* Exemplo pronto: a coluna Descrição. A lista inteira é trocada por uma nova (alterarItem). */}
              <td>
                <input
                  value={item.descricao}
                  onChange={(e) => setItens(alterarItem(itens, indice, "descricao", e.target.value))}
                />
              </td>
              <td>
                <input
                  value={item.cfop} onChange={(e) => setItens(alterarItem(itens, indice, "cfop", e.target.value)) } 
                />
              </td>
              <td>
                <input
                  value={item.quantidade} onChange={(e) => setItens(alterarItem(itens, indice, "quantidade", e.target.value)) } size={7}
                />
              </td>
              <td>
                <input
                  value={item.valor_unitario} onChange={(e) => setItens(alterarItem(itens, indice, "valor_unitario", e.target.value)) } size={9}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Já pronto: acrescenta uma linha em branco, guardando uma lista NOVA ([...antiga, nova]). */}
      <button type="button" onClick={() => setItens([...itens, itemVazio()])}>
        + Item
      </button>

      <p>Total dos itens: {formatarMoeda(totalDoFormulario(itens))}</p>

      {/* FAÇA 4 (seção 6 do conceito): se houver erros, um <ul className="erro"> com um <li> por erro. */}
      {erros.length > 0 && (                // só desenha o que vem depois do && se houver avisos
        <ul className="erro">
        {erros.map((a) => (               // um <li> por aviso
        <li key={a}>{a}</li>             // o próprio texto serve de key
        ))}
        </ul>
      )}
      <button type="submit">Salvar</button>
    </form>
  );
}
