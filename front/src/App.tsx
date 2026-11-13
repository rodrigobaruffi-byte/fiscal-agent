/**
 * Quinta — a tela principal. JÁ PRONTA: leia para entender, o exercício é o FormNota.tsx.
 *
 * Mostra o formulário (FormNota) e, abaixo, as notas cadastradas. Quando o formulário salva
 * uma nota, ele avisa o App (pela função aoSalvar), e o App recarrega a lista.
 */
import { useEffect, useState } from "react";
import { FormNota } from "./FormNota.tsx";
import { formatarMoeda, type NotaResumo } from "./notas.ts";

export function App() {
  const [notas, setNotas] = useState<NotaResumo[]>([]);   // as notas vindas da API
  const [erro, setErro] = useState("");                   // mensagem de erro da listagem

  async function carregar() {                             // busca a lista na API (usada no início e após salvar)
    try {
      const resposta = await fetch("/api/notas");         // GET /notas (a API da quarta, com banco)
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      setNotas(await resposta.json());                    // a lista de notas vira o novo estado
      setErro("");                                        // deu certo: apaga um erro antigo, se houver
    } catch {
      setErro("Não foi possível carregar as notas. A API está no ar?");
    }
  }

  useEffect(() => {                                       // roda uma vez, quando a tela aparece
    carregar();
  }, []);

  return (
    <main>
      <h1>Notas fiscais</h1>

      {/* O formulário recebe a função carregar com o nome aoSalvar (uma "prop"). */}
      <FormNota aoSalvar={carregar} />

      <h2>Notas cadastradas</h2>
      {erro && <p className="erro">{erro}</p>}
      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>CNPJ</th>
            <th>Origem</th>
            <th>Destino</th>
            <th>Emissão</th>
            <th>Valor</th>
          </tr>
        </thead>
        <tbody>
          {notas.map((n) => (
            <tr key={n.id}>
              <td>{n.numero}</td>
              <td>{n.cnpj_emitente}</td>
              <td>{n.uf_origem}</td>
              <td>{n.uf_destino}</td>
              <td>{n.emitida_em}</td>
              {/* o valor chega como texto ("150.00"): Number converte antes de formatar */}
              <td>{formatarMoeda(Number(n.valor_total))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
