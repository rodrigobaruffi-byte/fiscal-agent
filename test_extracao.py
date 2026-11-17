"""Testes da semana 4 (extracao.py). Não chamam a API de verdade nem precisam de chave.

O ClienteFalso faz o papel do Anthropic(): guarda o que recebeu e devolve uma resposta pronta.
Os objetos de resposta são SimpleNamespace: um objeto qualquer com os atributos que a gente quiser,
lidos com ponto (resposta.usage.input_tokens), igual aos objetos de verdade da biblioteca.
"""

from decimal import Decimal
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from pydantic import ValidationError

from extracao import (
    INSTRUCOES,
    MODELO,
    ErroExtracao,
    ItemExtraido,
    NotaExtraida,
    custo_usd,
    extrair_nota,
    montar_mensagem,
    perguntar,
    texto_da_resposta,
)


class ClienteFalso:
    """No lugar do Anthropic(): cliente.messages.create(...) e cliente.messages.parse(...) caem aqui."""

    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta    # o que devolver
        self.erro = erro            # ou o erro a levantar
        self.recebido = None        # os argumentos da última chamada (para conferir)
        self.messages = self        # cliente.messages é o próprio objeto

    def create(self, **argumentos):
        self.recebido = argumentos
        if self.erro:
            raise self.erro
        return self.resposta

    parse = create                  # parse faz o mesmo que create


def uso(entrada, saida):
    return SimpleNamespace(input_tokens=entrada, output_tokens=saida)


def resposta_de_texto(*textos, entrada=10, saida=5):
    blocos = [SimpleNamespace(type="text", text=t) for t in textos]
    return SimpleNamespace(content=blocos, usage=uso(entrada, saida))


NOTA = NotaExtraida(
    numero=123,
    cnpj_emitente="11.222.333/0001-81",
    uf_origem="PR",
    uf_destino="SP",
    valor_total="2116.00",
    emitida_em="2026-11-03",
    itens=[ItemExtraido(descricao="Cabo", cfop="6102", quantidade="10", valor_unitario="211.60")],
)


# ─── Segunda ─────────────────────────────────────────────────────────────────


def test_texto_da_resposta_um_bloco():
    assert texto_da_resposta(resposta_de_texto("Olá")) == "Olá"


def test_texto_da_resposta_junta_os_blocos():
    assert texto_da_resposta(resposta_de_texto("Primeira parte", "Segunda parte")) == "Primeira parte\nSegunda parte"


def test_texto_da_resposta_ignora_o_que_nao_e_texto():
    resposta = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking="pensando..."), SimpleNamespace(type="text", text="Pronto")],
        usage=uso(1, 1),
    )
    assert texto_da_resposta(resposta) == "Pronto"


def test_texto_da_resposta_sem_texto():
    assert texto_da_resposta(SimpleNamespace(content=[], usage=uso(1, 0))) == ""


def test_custo_usd():
    assert custo_usd(1_000_000, 0) == Decimal("0.100000")
    assert custo_usd(0, 1_000_000) == Decimal("0.500000")
    assert custo_usd(1200, 300) == Decimal("0.000270")


def test_custo_usd_e_decimal_com_6_casas():
    custo = custo_usd(1, 1)
    assert isinstance(custo, Decimal)
    assert str(custo) == "0.000001"


def test_perguntar_devolve_texto_e_tokens():
    cliente = ClienteFalso(resposta_de_texto("Brasília", entrada=12, saida=3))
    assert perguntar(cliente, "Qual a capital do Brasil?") == {"texto": "Brasília", "tokens_entrada": 12, "tokens_saida": 3}


def test_perguntar_manda_modelo_limite_e_mensagem():
    cliente = ClienteFalso(resposta_de_texto("Brasília"))
    perguntar(cliente, "Qual a capital do Brasil?")
    assert cliente.recebido["model"] == MODELO
    assert cliente.recebido["max_tokens"] == 1000
    assert cliente.recebido["messages"] == [{"role": "user", "content": "Qual a capital do Brasil?"}]


# ─── Terça ───────────────────────────────────────────────────────────────────


def test_montar_mensagem():
    assert montar_mensagem("NF 123") == "Extraia os dados da nota fiscal abaixo.\n\n<documento>\nNF 123\n</documento>"


def test_montar_mensagem_tira_espacos_das_pontas():
    assert montar_mensagem("  \nNF 123\n  ").endswith("<documento>\nNF 123\n</documento>")


def test_extrair_nota_devolve_nota_e_tokens():
    cliente = ClienteFalso(SimpleNamespace(parsed_output=NOTA, usage=uso(1200, 300)))
    resultado = extrair_nota(cliente, "NF 123 ...")
    assert resultado == {"nota": NOTA, "tokens_entrada": 1200, "tokens_saida": 300}


def test_extrair_nota_chama_o_parse_certo():
    cliente = ClienteFalso(SimpleNamespace(parsed_output=NOTA, usage=uso(1, 1)))
    extrair_nota(cliente, "NF 123 ...")
    assert cliente.recebido["model"] == MODELO
    assert cliente.recebido["max_tokens"] == 2000
    assert cliente.recebido["system"] == INSTRUCOES
    assert cliente.recebido["output_format"] is NotaExtraida
    assert cliente.recebido["messages"] == [{"role": "user", "content": montar_mensagem("NF 123 ...")}]


def test_extrair_nota_texto_vazio_nem_chama_o_modelo():
    cliente = ClienteFalso(SimpleNamespace(parsed_output=NOTA, usage=uso(1, 1)))
    with pytest.raises(ValueError, match="Texto vazio"):
        extrair_nota(cliente, "   \n ")
    assert cliente.recebido is None


def test_extrair_nota_formato_errado_vira_erro_de_extracao():
    try:
        NotaExtraida.model_validate({"numero": "abc"})      # só para obter um ValidationError de verdade
    except ValidationError as erro:
        erro_de_formato = erro
    cliente = ClienteFalso(erro=erro_de_formato)
    with pytest.raises(ErroExtracao, match="O modelo devolveu dados fora do formato esperado"):
        extrair_nota(cliente, "NF 123 ...")


def test_extrair_nota_falha_na_api_vira_erro_de_extracao():
    falha = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    cliente = ClienteFalso(erro=falha)
    with pytest.raises(ErroExtracao, match="Falha ao chamar o modelo"):
        extrair_nota(cliente, "NF 123 ...")
