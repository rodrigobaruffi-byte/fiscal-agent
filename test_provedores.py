"""Testes do extra (provedores.py). Sem chave, sem internet e sem Ollama: tudo com clientes falsos.

Cada teste escolhe o provedor com monkeypatch.setenv, que troca uma variável de ambiente só durante
o teste. Assim, o que estiver no seu .env não interfere.
"""

from decimal import Decimal
from types import SimpleNamespace

import ollama
import pytest
from google.genai import errors as erros_gemini

import provedores
from extracao import INSTRUCOES, MODELO, ErroExtracao, ItemExtraido, NotaExtraida, montar_mensagem
from provedores import criar_cliente, custo, extrair, extrair_nota_gemini, extrair_nota_ollama, modelo, provedor

NOTA = NotaExtraida(
    numero=123,
    cnpj_emitente="11.222.333/0001-81",
    uf_origem="PR",
    uf_destino="SP",
    valor_total="2116.00",
    emitida_em="2026-11-03",
    itens=[ItemExtraido(descricao="Cabo", cfop="6102", quantidade="10", valor_unitario="211.60")],
)


class ClienteGeminiFalso:
    """No lugar do genai.Client(): cliente.models.generate_content(...) cai aqui."""

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.recebido = resposta, erro, None
        self.models = self

    def generate_content(self, **argumentos):
        self.recebido = argumentos
        if self.erro:
            raise self.erro
        return self.resposta


class ClienteOllamaFalso:
    """No lugar do ollama.Client(): cliente.chat(...) cai aqui."""

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.recebido = resposta, erro, None

    def chat(self, **argumentos):
        self.recebido = argumentos
        if self.erro:
            raise self.erro
        return self.resposta


def resposta_gemini(parsed):
    return SimpleNamespace(parsed=parsed, usage_metadata=SimpleNamespace(prompt_token_count=900, candidates_token_count=200))


def resposta_ollama(conteudo):
    return SimpleNamespace(message=SimpleNamespace(content=conteudo), prompt_eval_count=700, eval_count=150)


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    """Antes de cada teste: sem modo demonstração, e um modelo definido para Gemini e Ollama."""
    monkeypatch.delenv("EXTRACAO_DEMO", raising=False)
    monkeypatch.setenv("GEMINI_MODELO", "gemini-teste")
    monkeypatch.setenv("OLLAMA_MODELO", "ollama-teste")


# ─── Já prontas (passam desde o início) ──────────────────────────────────────


def test_provedor_padrao_e_anthropic(monkeypatch):
    monkeypatch.delenv("PROVEDOR", raising=False)
    assert provedor() == "anthropic"


def test_provedor_aceita_maiusculas_e_espacos(monkeypatch):
    monkeypatch.setenv("PROVEDOR", " Ollama ")
    assert provedor() == "ollama"


def test_provedor_invalido(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "chatgpt")
    with pytest.raises(ValueError, match="PROVEDOR inválido"):
        provedor()


def test_modelo_sem_configurar(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    monkeypatch.delenv("GEMINI_MODELO")
    with pytest.raises(ValueError, match="GEMINI_MODELO"):
        modelo()


def test_custo_por_provedor(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "anthropic")
    assert custo(1200, 300) == Decimal("0.000270")
    monkeypatch.setenv("PROVEDOR", "ollama")
    assert custo(1200, 300) == Decimal("0.000000")


def test_anthropic_sem_chave(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        criar_cliente()


def test_ollama_e_demo_nao_precisam_de_chave(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    assert isinstance(criar_cliente(), ollama.Client)
    monkeypatch.setenv("EXTRACAO_DEMO", "1")
    assert isinstance(criar_cliente(), provedores.ClienteDemo)


# ─── Gemini (você escreve) ───────────────────────────────────────────────────


def test_gemini_devolve_nota_e_tokens(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    cliente = ClienteGeminiFalso(resposta_gemini(NOTA))
    assert extrair_nota_gemini(cliente, "NF 123 ...") == {"nota": NOTA, "tokens_entrada": 900, "tokens_saida": 200}


def test_gemini_chama_com_o_formato_certo(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    cliente = ClienteGeminiFalso(resposta_gemini(NOTA))
    extrair_nota_gemini(cliente, "NF 123 ...")
    assert cliente.recebido["model"] == "gemini-teste"
    assert cliente.recebido["contents"] == montar_mensagem("NF 123 ...")
    assert cliente.recebido["config"] == {
        "system_instruction": INSTRUCOES,
        "response_mime_type": "application/json",
        "response_schema": NotaExtraida,
    }


def test_gemini_formato_errado(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    cliente = ClienteGeminiFalso(resposta_gemini(None))
    with pytest.raises(ErroExtracao, match="fora do formato esperado"):
        extrair_nota_gemini(cliente, "NF 123 ...")


def test_gemini_falha_na_api(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    cliente = ClienteGeminiFalso(erro=erros_gemini.APIError(503, {"error": {"message": "fora do ar", "status": "UNAVAILABLE"}}))
    with pytest.raises(ErroExtracao, match="Falha ao chamar o modelo"):
        extrair_nota_gemini(cliente, "NF 123 ...")


# ─── Ollama (você escreve) ───────────────────────────────────────────────────


def test_ollama_devolve_nota_e_tokens(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    cliente = ClienteOllamaFalso(resposta_ollama(NOTA.model_dump_json()))
    assert extrair_nota_ollama(cliente, "NF 123 ...") == {"nota": NOTA, "tokens_entrada": 700, "tokens_saida": 150}


def test_ollama_chama_com_o_formato_certo(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    cliente = ClienteOllamaFalso(resposta_ollama(NOTA.model_dump_json()))
    extrair_nota_ollama(cliente, "NF 123 ...")
    assert cliente.recebido["model"] == "ollama-teste"
    assert cliente.recebido["messages"] == [
        {"role": "system", "content": INSTRUCOES},
        {"role": "user", "content": montar_mensagem("NF 123 ...")},
    ]
    assert cliente.recebido["format"] == NotaExtraida.model_json_schema()


def test_ollama_json_que_nao_bate(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    cliente = ClienteOllamaFalso(resposta_ollama('{"numero": "abc"}'))
    with pytest.raises(ErroExtracao, match="fora do formato esperado"):
        extrair_nota_ollama(cliente, "NF 123 ...")


def test_ollama_fora_do_ar(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    cliente = ClienteOllamaFalso(erro=ConnectionError("Failed to connect to Ollama"))
    with pytest.raises(ErroExtracao, match="Falha ao chamar o modelo"):
        extrair_nota_ollama(cliente, "NF 123 ...")


def test_ollama_modelo_nao_baixado(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    cliente = ClienteOllamaFalso(erro=ollama.ResponseError("model 'ollama-teste' not found", 404))
    with pytest.raises(ErroExtracao, match="Falha ao chamar o modelo"):
        extrair_nota_ollama(cliente, "NF 123 ...")


def test_texto_vazio_nem_chama(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "gemini")
    gemini = ClienteGeminiFalso(resposta_gemini(NOTA))
    ollama_falso = ClienteOllamaFalso(resposta_ollama(NOTA.model_dump_json()))
    with pytest.raises(ValueError, match="Texto vazio"):
        extrair_nota_gemini(gemini, "  ")
    with pytest.raises(ValueError, match="Texto vazio"):
        extrair_nota_ollama(ollama_falso, "  ")
    assert gemini.recebido is None and ollama_falso.recebido is None


# ─── extrair: escolhe pelo PROVEDOR ──────────────────────────────────────────


def test_extrair_com_ollama(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "ollama")
    resultado = extrair(ClienteOllamaFalso(resposta_ollama(NOTA.model_dump_json())), "NF 123 ...")
    assert resultado["nota"] == NOTA
    assert resultado["provedor"] == "ollama"
    assert resultado["modelo"] == "ollama-teste"


def test_extrair_com_anthropic_usa_o_seu_extrair_nota(monkeypatch):
    monkeypatch.setenv("PROVEDOR", "anthropic")

    class ClienteAnthropicFalso:
        def __init__(self):
            self.messages = self

        def parse(self, **argumentos):
            return SimpleNamespace(parsed_output=NOTA, usage=SimpleNamespace(input_tokens=1200, output_tokens=300))

    resultado = extrair(ClienteAnthropicFalso(), "NF 123 ...")
    assert resultado["tokens_entrada"] == 1200
    assert resultado["provedor"] == "anthropic"
    assert resultado["modelo"] == MODELO
