/**
 * Quinta — a tela de extração: texto entra, dados da nota e problemas saem. Você completa os trechos FAÇA.
 *
 * ESCREVER SEM IA. Consulte o dia4_conceito.md (as seções estão indicadas em cada FAÇA).
 * Ver funcionando: veja o passo a passo da quinta no LEIAME da semana.
 * Checar tipos:    npx tsc   (na pasta semana-04/front)
 */
import { useState, type SubmitEvent } from "react";
import { EXEMPLO, formatarCusto, formatarLatencia, mensagensDeErro, resumo, type RespostaExtracao } from "./extracao.ts";

export function Extracao() {
  const [texto, setTexto] = useState("");                                    // o que está na caixa de texto
  const [carregando, setCarregando] = useState(false);                       // true enquanto espera a API
  const [erros, setErros] = useState<string[]>([]);                          // erros da API (502, 503, 422...)
  const [resultado, setResultado] = useState<RespostaExtracao | null>(null); // null = ainda não há resultado

  async function extrair(evento: SubmitEvent) {
    evento.preventDefault();          // impede o navegador de recarregar a página
    // FAÇA 1 (seções 1 e 2 do conceito), nesta ordem:
    //   - antes de chamar: setCarregando(true), setErros([]) e setResultado(null);
    //   - try:
    //       POST em "/api/extracoes" com o corpo JSON.stringify({ texto }) e o cabeçalho de JSON;
    //       resposta.ok? setResultado(await resposta.json());
    //       senão: const corpo = await resposta.json(); setErros(mensagensDeErro(corpo.detail));
    //   - catch: setErros(["Não foi possível falar com a API. Ela está no ar?"]);
    //   - finally: setCarregando(false)  (roda tanto se deu certo quanto se deu erro).
    setCarregando(true);  
    setErros([]);
    setResultado(null);
    try {
      const resposta = await fetch('/api/extracoes',{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({texto})
      });
      if (resposta.ok) {
        setResultado(await resposta.json());
      } else {
        const corpo = await resposta.json();
        setErros(mensagensDeErro(corpo.detail));
      }
    } catch {
      setErros(['Não foi possível falar com a API. Ela está no ar?']);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <form onSubmit={extrair}>
      <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={12} placeholder="Cole aqui o texto da nota" />

      {/* Já pronto: preenche a caixa com o texto de exemplo. type="button" para NÃO enviar o formulário. */}
      <button type="button" onClick={() => setTexto(EXEMPLO)}>
        Usar exemplo
      </button>

      {/* FAÇA 2 (seção 3): o botão de envio.
            - desabilitado (disabled) enquanto carrega OU com a caixa vazia: carregando || texto.trim() === ""
            - o texto do botão: "Extraindo..." enquanto carrega; "Extrair" no resto do tempo. */}
      <button type="submit" disabled={carregando || texto.trim() === ''}>{carregando ? 'Extraindo...' : 'Extrair' } </button>

      {/* FAÇA 3 (seção 4): se houver erros, um <ul className="erro"> com um <li> por erro
            (o mesmo do FormNota da semana 3). */}

      {erros.length > 0 && (                // só desenha se houver erros
        <ul className="erro">
          {erros.map((erro) => (            // um <li> por erro
            <li key={erro}>{erro}</li>      // o próprio texto serve de key
          ))}
        </ul>
      )}

      {/* Já pronto: o resultado só aparece quando existe (resultado não é null). */}
      {resultado && (
        <section>
          <h2>Dados extraídos</h2>
          <p className="uso">
            {resumo(resultado)} · {resultado.modelo} · {resultado.tokens_entrada + resultado.tokens_saida} tokens ·{" "}
            {formatarCusto(resultado.custo_usd)} · {formatarLatencia(resultado.latencia_ms)}
          </p>

          <table>
            <tbody>
              <tr><th>Número</th><td>{resultado.nota.numero}</td></tr>
              <tr><th>CNPJ do emitente</th><td>{resultado.nota.cnpj_emitente}</td></tr>
              <tr><th>UF origem → destino</th><td>{resultado.nota.uf_origem} → {resultado.nota.uf_destino}</td></tr>
              <tr><th>Emissão</th><td>{resultado.nota.emitida_em}</td></tr>
              <tr><th>Valor total</th><td>{resultado.nota.valor_total}</td></tr>
            </tbody>
          </table>

          {/* FAÇA 4 (seção 5): a tabela de itens. Cabeçalho: Descrição, CFOP, Quantidade, Valor unitário.
                Uma linha <tr> por item de resultado.nota.itens (map, com key={indice}). */}
          <table>
            <thead>
              <tr>
                <th>Descrição</th>
                <th>CFOP</th>
                <th>Quantidade</th>
                <th>Valor Unitário</th>
              </tr> 
            </thead>
            <tbody>
              {resultado.nota.itens.map((item, indice) => (
                <tr key={indice}>
                  <td>{item.descricao}</td>
                  <td>{item.cfop}</td>
                  <td>{item.quantidade}</td>
                  <td>{item.valor_unitario}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Conferência fiscal</h3>
          {/* FAÇA 5 (seção 5): se resultado.problemas estiver vazio, <p className="ok">Nenhum problema encontrado.</p>;
                senão, <ul className="erro"> com um <li> por problema. Use o ternário: condição ? (...) : (...) */}
          {resultado.problemas.length === 0 ? (
            <p className="ok">Nenhum problema encontrado.</p>
          ) : (
            <ul className="erro">
              {resultado.problemas.map((erro) => (
                <li key={erro}>{erro}</li>
              ))}
            </ul>
          )}

        </section>
      )}
    </form>
  );
}
