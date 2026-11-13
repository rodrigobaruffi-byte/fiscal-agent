from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import app, obter_conexao
from dados import conectar

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def cliente():
    """Cliente HTTP ligado a uma conexão de teste: tudo é desfeito no fim."""
    try:
        conexao = conectar()
    except psycopg.OperationalError:
        pytest.skip("Banco não está no ar: rode `docker compose up -d` na pasta plano-ia")
    conexao.execute(SCHEMA)
    conexao.execute("DELETE FROM notas")
    app.dependency_overrides[obter_conexao] = lambda: conexao
    yield TestClient(app)
    app.dependency_overrides.clear()
    conexao.rollback()
    conexao.close()


def item(cfop="6102", quantidade="10", valor_unitario="4.50"):
    return {"descricao": "Cabo", "cfop": cfop, "quantidade": quantidade, "valor_unitario": valor_unitario}


def nota(numero=1, cnpj="11.222.333/0001-81", uf_destino="sp", valor_total="45.00", itens=None):
    return {
        "numero": numero,
        "cnpj_emitente": cnpj,
        "uf_origem": "pr",
        "uf_destino": uf_destino,
        "valor_total": valor_total,
        "emitida_em": "2026-11-04",
        "itens": itens if itens is not None else [item()],
    }


# ─── POST /notas ─────────────────────────────────────────────────────────────


def test_criar_nota(cliente):
    resposta = cliente.post("/notas", json=nota())
    assert resposta.status_code == 201
    assert isinstance(resposta.json()["id"], int)


def test_criar_nota_com_erro_de_regra(cliente):
    resposta = cliente.post("/notas", json=nota(valor_total="99.00", itens=[item(cfop="5102")]))
    assert resposta.status_code == 422
    assert resposta.json() == {"detail": [
        "Item 1: CFOP 5102 é de operação estadual, mas as UFs são diferentes",
        "Valor total não confere com os itens",
    ]}


def test_criar_nota_sem_itens(cliente):
    resposta = cliente.post("/notas", json=nota(itens=[]))
    assert resposta.status_code == 422
    assert resposta.json() == {"detail": ["Nota sem itens"]}


def test_ufs_em_minusculas_viram_maiusculas(cliente):
    # "pr" → "sp" com CFOP 6102 é interestadual: só passa se as UFs forem comparadas em maiúsculas
    novo_id = cliente.post("/notas", json=nota()).json()["id"]
    detalhe = cliente.get(f"/notas/{novo_id}").json()
    assert (detalhe["uf_origem"], detalhe["uf_destino"]) == ("PR", "SP")


def test_criar_nota_duplicada(cliente):
    assert cliente.post("/notas", json=nota(numero=5)).status_code == 201
    resposta = cliente.post("/notas", json=nota(numero=5))
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Nota já cadastrada para este emitente"}


def test_item_com_cfop_mal_formado(cliente):
    # Recusado pelo modelo ItemEntrada (4 dígitos), antes de chegar à sua função
    assert cliente.post("/notas", json=nota(itens=[item(cfop="61A2")])).status_code == 422


# ─── GET /notas/{id} (já pronta) ─────────────────────────────────────────────


def test_detalhar_traz_itens(cliente):
    novo_id = cliente.post("/notas", json=nota()).json()["id"]
    detalhe = cliente.get(f"/notas/{novo_id}").json()
    assert detalhe["valor_total"] == "45.00"
    assert [i["cfop"] for i in detalhe["itens"]] == ["6102"]
    assert detalhe["itens"][0]["quantidade"] == "10.000"   # NUMERIC(12,3) no banco: 3 casas


def test_detalhar_inexistente(cliente):
    assert cliente.get("/notas/999999").status_code == 404


# ─── GET /notas ──────────────────────────────────────────────────────────────


def cadastrar_varias(cliente):
    cliente.post("/notas", json=nota(1, uf_destino="SP"))
    cliente.post("/notas", json=nota(2, uf_destino="BA"))
    cliente.post("/notas", json=nota(3, uf_destino="SP"))


def test_listar_todas(cliente):
    cadastrar_varias(cliente)
    resposta = cliente.get("/notas")
    assert resposta.status_code == 200
    assert [n["numero"] for n in resposta.json()] == [1, 2, 3]


def test_listar_filtrando_uf(cliente):
    cadastrar_varias(cliente)
    resposta = cliente.get("/notas", params={"uf_destino": "sp"})
    assert [n["numero"] for n in resposta.json()] == [1, 3]


def test_listar_paginando(cliente):
    cadastrar_varias(cliente)
    resposta = cliente.get("/notas", params={"limite": 2, "pagina": 2})
    assert [n["numero"] for n in resposta.json()] == [3]


def test_listar_com_limite_invalido(cliente):
    # Recusado pelo Query(ge=1, le=100), antes de chegar à sua função
    assert cliente.get("/notas", params={"limite": 0}).status_code == 422
    assert cliente.get("/notas", params={"limite": 500}).status_code == 422
