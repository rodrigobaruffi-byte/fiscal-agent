"""Testes da rota POST /extracoes (api.py). Sem chave e sem banco: o cliente do modelo é trocado por um falso."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from api import app, obter_cliente
from extracao import MODELO, ItemExtraido, NotaExtraida

TEXTO = "DANFE ... NF-e nº 123 ... (o texto do documento)"


class ClienteFalso:
    """No lugar do Anthropic(): cliente.messages.parse(...) devolve a resposta pronta (ou levanta o erro)."""

    def __init__(self, nota=None, erro=None):
        self.nota = nota
        self.erro = erro
        self.messages = self

    def parse(self, **argumentos):
        if self.erro:
            raise self.erro
        return SimpleNamespace(parsed_output=self.nota, usage=SimpleNamespace(input_tokens=1200, output_tokens=300))


def nota(uf_origem="PR", uf_destino="SP", cfop="6102", valor_total="2116.00"):
    return NotaExtraida(
        numero=123,
        cnpj_emitente="11.222.333/0001-81",
        uf_origem=uf_origem,
        uf_destino=uf_destino,
        valor_total=valor_total,
        emitida_em="2026-11-03",
        itens=[
            ItemExtraido(descricao="Cabo", cfop=cfop, quantidade="10", valor_unitario="189.90"),
            ItemExtraido(descricao="Disjuntor", cfop="6102", quantidade="4", valor_unitario="54.25"),
        ],
    )


@pytest.fixture
def usar(monkeypatch):
    """usar(cliente) troca o obter_cliente pelo cliente falso e devolve o TestClient. Desfaz no fim.

    O provedor fica fixo em anthropic (o formato do ClienteFalso), seja qual for o do seu .env.
    """
    monkeypatch.setenv("PROVEDOR", "anthropic")
    monkeypatch.delenv("EXTRACAO_DEMO", raising=False)

    def trocar(cliente):
        app.dependency_overrides[obter_cliente] = lambda: cliente
        return TestClient(app)

    yield trocar
    app.dependency_overrides.clear()


def test_nota_valida(usar):
    resposta = usar(ClienteFalso(nota())).post("/extracoes", json={"texto": TEXTO})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["problemas"] == []
    assert corpo["nota"]["numero"] == 123
    assert corpo["nota"]["itens"][0]["cfop"] == "6102"


def test_tokens_custo_e_latencia(usar):
    corpo = usar(ClienteFalso(nota())).post("/extracoes", json={"texto": TEXTO}).json()
    assert corpo["tokens_entrada"] == 1200
    assert corpo["tokens_saida"] == 300
    assert corpo["custo_usd"] == "0.000270"
    assert corpo["provedor"] == "anthropic"
    assert corpo["modelo"] == MODELO
    assert isinstance(corpo["latencia_ms"], int)
    assert corpo["latencia_ms"] >= 0


def test_problema_fiscal(usar):
    corpo = usar(ClienteFalso(nota(cfop="5102"))).post("/extracoes", json={"texto": TEXTO}).json()
    assert corpo["problemas"] == ["Item 1: CFOP 5102 é de operação estadual, mas as UFs são diferentes"]


def test_ufs_em_minusculas_sao_conferidas_em_maiusculas(usar):
    corpo = usar(ClienteFalso(nota(uf_origem="pr", uf_destino="PR", cfop="5102"))).post("/extracoes", json={"texto": TEXTO}).json()
    assert corpo["problemas"] == ["Item 2: CFOP 6102 é de operação interestadual, mas as UFs são iguais"]


def test_campo_que_nao_veio_vira_problema(usar):
    corpo = usar(ClienteFalso(nota(valor_total=""))).post("/extracoes", json={"texto": TEXTO}).json()
    assert len(corpo["problemas"]) == 1
    assert corpo["problemas"][0].startswith("valor_total: ")
    assert corpo["nota"]["valor_total"] == ""


def test_falha_no_modelo_responde_502(usar):
    falha = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    resposta = usar(ClienteFalso(erro=falha)).post("/extracoes", json={"texto": TEXTO})
    assert resposta.status_code == 502
    assert resposta.json()["detail"] == "Falha ao chamar o modelo"


def test_texto_so_com_espacos_responde_422(usar):
    resposta = usar(ClienteFalso(nota())).post("/extracoes", json={"texto": "   "})
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Texto vazio"


def test_sem_texto_responde_422(usar):
    resposta = usar(ClienteFalso(nota())).post("/extracoes", json={})
    assert resposta.status_code == 422


def test_sem_chave_responde_503(monkeypatch):
    # Este usa o obter_cliente de verdade: sem chave e sem modo demonstração, a rota avisa com 503.
    monkeypatch.setenv("PROVEDOR", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("EXTRACAO_DEMO", raising=False)
    resposta = TestClient(app).post("/extracoes", json={"texto": TEXTO})
    assert resposta.status_code == 503
