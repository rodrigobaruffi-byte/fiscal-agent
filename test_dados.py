from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from dados import buscar_nota, conectar, excluir_nota, inserir_nota, listar_notas

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def conn():
    try:
        conexao = conectar()
    except psycopg.OperationalError:
        pytest.skip("Banco não está no ar: rode `docker compose up -d` na pasta plano-ia")
    conexao.execute(SCHEMA)
    conexao.execute("DELETE FROM notas")  # os itens vão junto (ON DELETE CASCADE)
    yield conexao
    conexao.rollback()  # desfaz tudo que o teste gravou
    conexao.close()


def item(descricao="Cabo", cfop="6102", quantidade="10", valor_unitario="4.50"):
    return {
        "descricao": descricao,
        "cfop": cfop,
        "quantidade": Decimal(quantidade),
        "valor_unitario": Decimal(valor_unitario),
    }


def nota(numero=1, cnpj="11.222.333/0001-81", uf_destino="SP", itens=None):
    return {
        "numero": numero,
        "cnpj_emitente": cnpj,
        "uf_origem": "PR",
        "uf_destino": uf_destino,
        "valor_total": Decimal("150.00"),
        "emitida_em": date(2026, 11, 2),
        "itens": itens if itens is not None else [item(), item("Tomada", valor_unitario="10.50")],
    }


def contar(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]  # tabela vem do teste, não do usuário


# ─── Segunda ─────────────────────────────────────────────────────────────────


def test_inserir_devolve_id_e_grava_itens(conn):
    nota_id = inserir_nota(conn, nota())
    assert isinstance(nota_id, int)
    assert contar(conn, "notas") == 1
    assert contar(conn, "itens") == 2


def test_itens_ficam_ligados_a_nota(conn):
    nota_id = inserir_nota(conn, nota())
    ids = conn.execute("SELECT DISTINCT nota_id FROM itens").fetchall()
    assert ids == [{"nota_id": nota_id}]


def test_inserir_grava_cnpj_so_com_digitos(conn):
    nota_id = inserir_nota(conn, nota())
    linha = conn.execute("SELECT cnpj_emitente FROM notas WHERE id = %s", (nota_id,)).fetchone()
    assert linha["cnpj_emitente"] == "11222333000181"


def test_item_invalido_nao_deixa_nada_gravado(conn):
    # O CFOP "61A2" é recusado pelo CHECK da tabela itens. A nota já tinha sido inserida,
    # mas o rollback desfaz a transação inteira: nem a nota fica.
    with pytest.raises(psycopg.errors.CheckViolation):
        inserir_nota(conn, nota(numero=987654, itens=[item(), item(cfop="61A2")]))
    conn.rollback()
    conn.execute(SCHEMA)
    sobrou = conn.execute("SELECT COUNT(*) AS n FROM notas WHERE numero = 987654").fetchone()["n"]
    assert sobrou == 0


def test_buscar_nota_com_itens(conn):
    nota_id = inserir_nota(conn, nota())
    encontrada = buscar_nota(conn, nota_id)
    assert encontrada["numero"] == 1
    assert encontrada["valor_total"] == Decimal("150.00")
    assert [i["descricao"] for i in encontrada["itens"]] == ["Cabo", "Tomada"]
    assert encontrada["itens"][0]["quantidade"] == Decimal("10")


def test_buscar_nota_sem_itens(conn):
    nota_id = inserir_nota(conn, nota(itens=[]))
    assert buscar_nota(conn, nota_id)["itens"] == []


def test_buscar_nota_inexistente(conn):
    assert buscar_nota(conn, 999999) is None


def test_excluir_nota_leva_os_itens(conn):
    nota_id = inserir_nota(conn, nota())
    assert excluir_nota(conn, nota_id) is True
    assert contar(conn, "itens") == 0
    assert excluir_nota(conn, nota_id) is False


# ─── Quarta ──────────────────────────────────────────────────────────────────


def cadastrar_varias(conn):
    inserir_nota(conn, nota(1, uf_destino="SP"))
    inserir_nota(conn, nota(2, uf_destino="BA"))
    inserir_nota(conn, nota(3, uf_destino="SP"))
    inserir_nota(conn, nota(4, cnpj="11444777000161", uf_destino="SP"))


def test_listar_todas(conn):
    cadastrar_varias(conn)
    assert [n["numero"] for n in listar_notas(conn)] == [1, 2, 3, 4]


def test_listar_nao_traz_itens(conn):
    cadastrar_varias(conn)
    assert "itens" not in listar_notas(conn)[0]


def test_listar_por_cnpj(conn):
    cadastrar_varias(conn)
    resultado = listar_notas(conn, cnpj="11.444.777/0001-61")
    assert [n["numero"] for n in resultado] == [4]


def test_listar_por_uf(conn):
    cadastrar_varias(conn)
    assert [n["numero"] for n in listar_notas(conn, uf_destino="sp")] == [1, 3, 4]


def test_listar_com_os_dois_filtros(conn):
    cadastrar_varias(conn)
    resultado = listar_notas(conn, cnpj="11222333000181", uf_destino="SP")
    assert [n["numero"] for n in resultado] == [1, 3]


def test_listar_paginando(conn):
    cadastrar_varias(conn)
    assert [n["numero"] for n in listar_notas(conn, limite=3, pagina=1)] == [1, 2, 3]
    assert [n["numero"] for n in listar_notas(conn, limite=3, pagina=2)] == [4]
    assert listar_notas(conn, limite=3, pagina=3) == []


def test_listar_nao_aceita_sql_no_filtro(conn):
    cadastrar_varias(conn)
    assert listar_notas(conn, uf_destino="SP' OR '1'='1") == []
