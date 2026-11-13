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

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from dados import buscar_nota, conectar, excluir_nota, inserir_nota, listar_notas
from regras import validar_nota

app = FastAPI(title="Notas fiscais — semana 3")


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
