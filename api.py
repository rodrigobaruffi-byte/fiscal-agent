"""Quarta — A API completa da fase 1: nota com itens, validação fiscal e listagem com filtros.

ESCREVER SEM IA. Consulte o dia3_conceito.md.
Antes: dados.py (segunda) e regras.py (terça) prontos, e `docker compose up -d`.
Testes:            pytest semana-03/test_api.py -q
Ver funcionando:   fastapi dev semana-03/api.py   e abra http://127.0.0.1:8000/docs

Já pronto: os modelos, a conexão e as rotas GET /notas/{id} e DELETE (iguais às da semana 2).
Você escreve: o corpo do POST /notas e o corpo do GET /notas.
"""

from datetime import date
from decimal import Decimal

import time
import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError


from types import SimpleNamespace
from dados import buscar_nota, conectar, excluir_nota, inserir_nota, listar_notas
from regras import validar_nota
from extracao import ErroExtracao, ItemExtraido, NotaExtraida
from provedores import criar_cliente, custo, extrair, provedor



app = FastAPI(title="Notas fiscais — Agente Fiscal")


class ItemEntrada(BaseModel):
    """Já pronto: um item da nota, como vem no JSON."""

    descricao: str = Field(min_length=1, max_length=120)
    cfop: str = Field(pattern=r"^\d{4}$")          # exatamente 4 dígitos
    quantidade: Decimal = Field(gt=0)              # maior que zero
    valor_unitario: Decimal = Field(ge=0)          # maior ou igual a zero (ge = greater or equal)


class NotaEntrada(BaseModel):
    """Já pronto: a nota com a lista de itens dentro (um modelo dentro do outro)."""

    numero: int
    cnpj_emitente: str
    uf_origem: str = Field(min_length=2, max_length=2)
    uf_destino: str = Field(min_length=2, max_length=2)
    valor_total: Decimal = Field(gt=0, decimal_places=2)
    emitida_em: date
    itens: list[ItemEntrada]                       # lista de itens, cada um conferido pelo ItemEntrada


def obter_conexao():
    """Já pronta: a mesma da semana 2 (abre, entrega, faz commit se deu certo, fecha)."""
    conn = conectar()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@app.post("/notas", status_code=201)
def criar_nota(entrada: NotaEntrada, conn: psycopg.Connection = Depends(obter_conexao)) -> dict:
    """POST /notas — valida as regras fiscais e grava a nota com os itens.

    Devolve:
        {"id": 7}
    Erros:
        - regras fiscais com problema (validar_nota devolveu erros) → 422, com a LISTA de erros:
          raise HTTPException(status_code=422, detail=erros)
        - nota repetida (mesmo CNPJ e número) → 409 "Nota já cadastrada para este emitente"

    Passo a passo:
        1. nota = entrada.model_dump()   (os itens também viram dicts, dentro de nota["itens"])
        2. UFs em maiúsculas, como na semana 2.
        3. erros = validar_nota(nota); se a lista não estiver vazia, responda 422 com ela.
        4. Grave com inserir_nota dentro de um try, tratando o UniqueViolation (409).
        5. Devolva {"id": novo_id}.
    """
    nota = entrada.model_dump()
    
    nota = {'numero':nota['numero'],
            'cnpj_emitente': nota['cnpj_emitente'],
            'uf_origem': nota['uf_origem'].upper(),
            'uf_destino': nota['uf_destino'].upper(),
            'valor_total': nota['valor_total'],
            'emitida_em': nota['emitida_em'],
            'itens':nota['itens']
            }
    erros = validar_nota(nota)
    if erros:
        raise HTTPException(status_code=422, detail=erros)
    try:
        novanota = {'id': inserir_nota(conn,nota)}
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail='Nota já cadastrada para este emitente')    
    return novanota


@app.get("/notas")
def listar(
    cnpj: str | None = None,
    uf_destino: str | None = None,
    limite: int = Query(default=20, ge=1, le=100),   # Query: parâmetro da URL com regras (entre 1 e 100)
    pagina: int = Query(default=1, ge=1),            # a partir de 1
    conn: psycopg.Connection = Depends(obter_conexao),
) -> list[dict]:
    """GET /notas?uf_destino=SP&limite=10&pagina=2 — lista com filtros opcionais.

    Todos os parâmetros são opcionais. Repasse todos para listar_notas (quarta, no dados.py)
    e devolva o que ela devolver. É uma linha.
    """
    return listar_notas(conn,cnpj,uf_destino,limite, pagina)


@app.get("/notas/{nota_id}")
def detalhar(nota_id: int, conn: psycopg.Connection = Depends(obter_conexao)) -> dict:
    """Já pronta: GET /notas/7 — a nota com os itens; 404 se não existir."""
    nota = buscar_nota(conn, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return nota


@app.delete("/notas/{nota_id}", status_code=204)
def apagar(nota_id: int, conn: psycopg.Connection = Depends(obter_conexao)) -> None:
    """Já pronta: DELETE /notas/7 — apaga a nota (e os itens, pelo CASCADE); 404 se não existir."""
    if not excluir_nota(conn, nota_id):
        raise HTTPException(status_code=404, detail="Nota não encontrada")

class PedidoExtracao(BaseModel):
    """Já pronto: o corpo do POST /extracoes."""

    texto: str = Field(min_length=1, max_length=20000)    # o texto do documento (até ~20 mil caracteres)


class ClienteDemo:
    """Já pronto: finge ser o Anthropic() quando EXTRACAO_DEMO=1. Ignora o texto e devolve sempre a
    mesma nota, que tem um problema de propósito (CFOP 5102 numa venda PR → SP). Não custa nada."""

    def __init__(self):
        self.messages = self

    def parse(self, **argumentos):
        time.sleep(1.5)                                    # demora um pouco, para a tela mostrar "carregando"
        nota = NotaExtraida(
            numero=123,
            cnpj_emitente="11.222.333/0001-81",
            uf_origem="PR",
            uf_destino="SP",
            valor_total="2116.00",
            emitida_em="2026-11-03",
            itens=[
                ItemExtraido(descricao="Cabo flexível 2,5 mm (rolo 100 m)", cfop="6102", quantidade="10", valor_unitario="189.90"),
                ItemExtraido(descricao="Disjuntor bipolar 32 A", cfop="5102", quantidade="4", valor_unitario="54.25"),
            ],
        )
        return SimpleNamespace(parsed_output=nota, usage=SimpleNamespace(input_tokens=850, output_tokens=210))


def obter_cliente():
    """Já pronta: entrega o cliente do modelo para a rota (como o obter_conexao entrega o conn).

    - EXTRACAO_DEMO=1           → o ClienteDemo (de graça, sem chave).
    - senão, o PROVEDOR do .env → criar_cliente() do provedores.py (Anthropic, Gemini ou Ollama).
    - falta configuração        → 503, com a mensagem do que falta.
    Nos testes, esta função é trocada por um cliente falso (dependency_overrides).
    """
    try:
        if provedor() == "demo":
            return ClienteDemo()
        return criar_cliente()
    except ValueError as erro:
        raise HTTPException(status_code=503, detail=str(erro))


def mensagens_de_validacao(erro: ValidationError) -> list[str]:
    """Já pronta: transforma um ValidationError do Pydantic numa lista de textos legíveis.

    Ex.: ["valor_total: Input should be a valid decimal", "itens.0.cfop: String should match pattern ..."]
    """
    mensagens = []
    for problema in erro.errors():                                  # um dict por campo com problema
        campo = ".".join(str(parte) for parte in problema["loc"])   # ("itens", 0, "cfop") → "itens.0.cfop"
        mensagens.append(f"{campo}: {problema['msg']}")
    return mensagens


@app.post("/extracoes")
def criar_extracao(pedido: PedidoExtracao, cliente=Depends(obter_cliente)) -> dict:
    """POST /extracoes — extrai os dados da nota do texto e confere com as regras fiscais. Não grava nada.

    Devolve (200):
        {"nota": {...os campos como o modelo devolveu, em texto...},
         "problemas": [...],              # vazio = nota válida
         "provedor": "anthropic", "modelo": "claude-haiku-5-5",    # quem respondeu
         "tokens_entrada": 1200, "tokens_saida": 300,
         "custo_usd": "0.000270",         # TEXTO: str(custo(...)), como o valor_total da semana 3
         "latencia_ms": 812}              # quanto a chamada ao modelo demorou, em milissegundos
    Erros:
        - texto vazio (ValueError do extrair_nota)  → 422, detail = a mensagem do erro ("Texto vazio")
        - falha na extração (ErroExtracao)          → 502, detail = a mensagem do erro

    Passo a passo:
        1. inicio = time.perf_counter()   (um cronômetro: segundos, com casas decimais)
        2. resultado = extrair(cliente, pedido.texto), dentro de um try com dois except.
           (extrair, do provedores.py, chama o seu extrair_nota ou o do provedor do .env.)
             ErroExtracao → HTTPException 502;  ValueError → HTTPException 422.  detail=str(erro).
        3. latencia_ms = round((time.perf_counter() - inicio) * 1000)
        4. dados = resultado["nota"].model_dump()   (o objeto NotaExtraida vira dict)
        5. Conferir, dentro de um try:
             nota = NotaEntrada.model_validate(dados).model_dump()   (textos viram Decimal e date)
             UFs de nota em maiúsculas (como no POST /notas)
             problemas = validar_nota(nota)
           except ValidationError as erro:  problemas = mensagens_de_validacao(erro)
        6. Devolva o dict do topo. Em resultado estão "tokens_entrada", "tokens_saida", "provedor" e
           "modelo". O custo é str(custo(tokens_entrada, tokens_saida)), com os preços do provedor.
    """
    inicio = time.perf_counter()
    try:
        resultado = extrair(cliente, pedido.texto)
    except ErroExtracao as erro: 
        raise HTTPException(status_code=502, detail=str(erro))
    except ValueError as erro: 
        raise HTTPException(status_code=422, detail=str(erro))
    latencia = round((time.perf_counter()-inicio)*1000)
    dados = resultado['nota'].model_dump()
    try:
        nota = NotaEntrada.model_validate(dados).model_dump()
        nota['uf_origem'] = nota['uf_origem'].upper()    
        nota['uf_destino'] = nota['uf_destino'].upper()    
        problemas = validar_nota(nota)
    except ValidationError as erro:
        problemas = mensagens_de_validacao(erro)
    result = {
        'nota': dados,
        'problemas': problemas,
        'provedor': resultado['provedor'], 'modelo': resultado['modelo'],
        'tokens_entrada': resultado['tokens_entrada'], 'tokens_saida': resultado['tokens_saida'],
        'custo_usd': str(custo(resultado['tokens_entrada'],resultado['tokens_saida'])),
        'latencia_ms': latencia
    }

    return result