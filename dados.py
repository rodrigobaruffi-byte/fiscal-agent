"""Acesso ao banco da semana 3: a nota com os seus itens (tabela pai e tabela filha).

ESCREVER SEM IA. Consulte o dia1_conceito.md.
Antes: na pasta plano-ia, `docker compose up -d` para subir o banco.
Testes:  pytest semana-03/test_dados.py -q
(Sem banco no ar, os testes aparecem como "skipped".)

Segunda: inserir_nota, buscar_nota e excluir_nota.
Quarta:  listar_notas (filtros e paginação).

Regras de sempre: parâmetros com %s e tupla (nunca f-string com valores); sem commit aqui dentro.
"""

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

URL_PADRAO = "postgresql://estudos:estudos@localhost:5433/estudos"


def conectar() -> psycopg.Connection:
    """Já pronta: abre a conexão. Cada linha lida volta como dict."""
    return psycopg.connect(os.environ.get("DATABASE_URL", URL_PADRAO), row_factory=dict_row)


def somente_digitos(texto: str) -> str:
    """Já pronta: a mesma de sempre."""
    return "".join(c for c in texto if c.isdigit())


# ─── Segunda ─────────────────────────────────────────────────────────────────


def inserir_nota(conn: psycopg.Connection, nota: dict) -> int:
    """Grava a nota e todos os itens dela. Devolve o id da nota.

    Recebe:
        nota: dict com as 6 colunas da nota e mais a chave "itens", uma lista de dicts:
            {"numero": 1, "cnpj_emitente": "11.222.333/0001-81", "uf_origem": "PR",
             "uf_destino": "SP", "valor_total": Decimal("230.00"), "emitida_em": date(2026, 11, 2),
             "itens": [{"descricao": "Cabo", "cfop": "6102",
                        "quantidade": Decimal("10"), "valor_unitario": Decimal("4.50")}, ...]}
    Devolve:
        o id (int) da nota criada.

    Passo a passo:
        1. INSERT da nota (igual à semana 2, CNPJ só com dígitos) com RETURNING id.
        2. Para cada item de nota["itens"]: INSERT em itens, com o nota_id do passo 1.
        3. Devolva o id da nota.
    Sem commit: se um item falhar, quem chamou faz rollback e nem a nota fica gravada.
    """
    idnota = conn.execute('Insert into notas ( numero, cnpj_emitente, uf_origem, uf_destino, valor_total, emitida_em )' \
    'values (%s, %s, %s, %s, %s, %s) returning id',
    (nota['numero'], somente_digitos(nota['cnpj_emitente']), nota['uf_origem'], nota['uf_destino'], nota['valor_total'], nota['emitida_em'])).fetchone()
    nota_id = idnota['id']
    for item in nota['itens']:
        conn.execute('insert into itens ( nota_id, descricao, cfop, quantidade, valor_unitario )' \
        'values (%s, %s, %s, %s, %s)', 
        (nota_id, item['descricao'], item['cfop'], item['quantidade'], item['valor_unitario'] )
                       )
    return nota_id


def buscar_nota(conn: psycopg.Connection, nota_id: int) -> dict | None:
    """Devolve a nota com os itens dentro, ou None se o id não existir.

    Devolve:
        o dict da nota (todas as colunas) com uma chave a mais, "itens":
            {"id": 7, "numero": 1, ..., "itens": [{"id": 3, "nota_id": 7, "descricao": "Cabo", ...}, ...]}
        Os itens vêm em ordem de id. Nota inexistente → None.

    Passo a passo:
        1. SELECT da nota pelo id com .fetchone(). Veio None? Devolva None.
        2. SELECT dos itens dessa nota (WHERE nota_id = ...) ORDER BY id, com .fetchall().
        3. Guarde a lista na chave "itens" do dict da nota e devolva a nota.
    """
    nota = conn.execute('select * from notas where id = %s',(nota_id,)).fetchone();
    if nota is None: 
        return None
    nota['itens'] = conn.execute('select * from itens where nota_id = %s',(nota_id,)).fetchall()

    return nota


def excluir_nota(conn: psycopg.Connection, nota_id: int) -> bool:
    """Apaga a nota. Os itens vão junto, sozinhos (ON DELETE CASCADE no schema.sql).

    Devolve:
        True se apagou; False se o id não existia. Igual à semana 2.
    """
    deleted =  conn.execute('delete from notas where id = %s',(nota_id,)).rowcount == 1
    return deleted


# ─── Quarta ──────────────────────────────────────────────────────────────────


def listar_notas(
    conn: psycopg.Connection,
    cnpj: str | None = None,
    uf_destino: str | None = None,
    limite: int = 20,
    pagina: int = 1,
) -> list[dict]:
    """Lista notas (sem os itens), com filtros opcionais e paginação, em ordem de id.

    Recebe:
        cnpj:       se vier, só as notas desse emitente (aceite pontuado).
        uf_destino: se vier, só as notas com esse destino (aceite minúsculas).
        limite:     quantas notas por página.
        pagina:     qual página (1 = as primeiras "limite" notas).
    Devolve:
        lista de dicts, uma por nota, só com as colunas da tabela notas. Nada encontrado → [].

    Passo a passo (montar o SQL aos pedaços, sempre com %s):
        1. condicoes = [] e valores = [].
        2. Se cnpj veio: condicoes.append("cnpj_emitente = %s") e valores.append(...).
           O mesmo para uf_destino.
        3. sql = "SELECT * FROM notas"; se houver condições, some " WHERE " + " AND ".join(condicoes).
        4. Some " ORDER BY id LIMIT %s OFFSET %s" e acrescente limite e (pagina - 1) * limite aos valores.
        5. conn.execute(sql, valores).fetchall()
    """
    condicoes=[]
    valores=[]
    if cnpj is not None:
        condicoes.append(' cnpj_emitente = %s ')
        valores.append(somente_digitos(cnpj))
    if uf_destino is not None:
        condicoes.append(' uf_destino = %s ')
        valores.append(uf_destino.upper())
    
    sql = 'select * from notas '
    if condicoes:
        sql += ' where '+' and '.join(condicoes)
    sql += 'order by id Limit %s offset %s'
    valores.append(limite)
    valores.append((pagina-1)*limite)
    return conn.execute(sql,valores).fetchall()
