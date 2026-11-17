"""Extra da semana 4 — escolher no .env qual LLM faz a extração: Anthropic, Gemini ou Ollama (local).

ESCREVER SEM IA: extrair_nota_gemini e extrair_nota_ollama. O resto já está pronto.
Faça depois da terça (as duas seguem o mesmo roteiro do seu extrair_nota).
Testes:  pytest semana-04/test_provedores.py -q        (sem chave e sem Ollama: clientes falsos)

Como funciona:
    - O .env diz o provedor (PROVEDOR) e o modelo de cada um. Veja o .env.example na pasta plano-ia.
    - criar_cliente() cria o cliente do provedor escolhido.
    - extrair(cliente, texto) chama a função de extração desse provedor.
    - As três funções de extração devolvem o MESMO dict: {"nota", "tokens_entrada", "tokens_saida"}.
      Por isso a rota, o custo e a tela não precisam saber quem respondeu.
    - EXTRACAO_DEMO=1 continua valendo: vira o provedor "demo", de graça.
"""

import os
import time
from decimal import Decimal
from types import SimpleNamespace

import ollama
from anthropic import Anthropic
from google import genai
from google.genai import errors as erros_gemini
from pydantic import ValidationError

import extracao                     # o import do extracao já carrega o .env (load_dotenv lá no topo)
from extracao import INSTRUCOES, ErroExtracao, ItemExtraido, NotaExtraida, extrair_nota, montar_mensagem

# Preço em dólares por MILHÃO de tokens: (entrada, saída).
PRECOS = {
    "anthropic": (Decimal("0.10"), Decimal("0.50")),   # Haiku 5.5
    "gemini": (Decimal("0"), Decimal("0")),            # dentro da cota gratuita; no plano pago, veja a tabela do Google
    "ollama": (Decimal("0"), Decimal("0")),            # roda na sua máquina
    "demo": (Decimal("0"), Decimal("0")),              # o ClienteDemo, logo abaixo
}


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


def provedor() -> str:
    """Já pronta: o provedor escolhido. Lê o ambiente a cada chamada (assim os testes podem trocar)."""
    if os.environ.get("EXTRACAO_DEMO") == "1":
        return "demo"
    nome = os.environ.get("PROVEDOR", "anthropic").strip().lower()
    if nome not in PRECOS:
        raise ValueError(f"PROVEDOR inválido: {nome!r}. Use anthropic, gemini ou ollama.")
    return nome


def modelo() -> str:
    """Já pronta: o modelo do provedor escolhido, lido do .env."""
    nome = provedor()
    if nome in ("anthropic", "demo"):
        return extracao.MODELO                         # ANTHROPIC_MODELO, ou o Haiku se não houver
    variavel = "GEMINI_MODELO" if nome == "gemini" else "OLLAMA_MODELO"
    valor = os.environ.get(variavel, "").strip()
    if not valor:
        raise ValueError(f"Defina {variavel} no .env (veja o .env.example)")
    return valor


def criar_cliente():
    """Já pronta: o cliente do provedor escolhido. Falta de configuração vira ValueError (a API responde 503)."""
    nome = provedor()
    if nome == "demo":
        return ClienteDemo()
    if nome == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("Extração indisponível: defina ANTHROPIC_API_KEY no .env (ou EXTRACAO_DEMO=1)")
        return Anthropic()                             # lê ANTHROPIC_API_KEY sozinho
    if nome == "gemini":
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            raise ValueError("Extração indisponível: defina GEMINI_API_KEY no .env")
        return genai.Client()                          # lê GEMINI_API_KEY sozinho
    return ollama.Client(host=os.environ.get("OLLAMA_URL", "http://localhost:11434"))   # sem chave: só o endereço


def extrair_nota_gemini(cliente, texto: str) -> dict:
    """A mesma extração da terça, com o Gemini (biblioteca google-genai).

    Devolve o mesmo dict do extrair_nota: {"nota": <NotaExtraida>, "tokens_entrada": int, "tokens_saida": int}

    Passo a passo:
        1. Texto vazio ou só com espaços? raise ValueError("Texto vazio").
        2. Dentro de um try:
             resposta = cliente.models.generate_content(
                 model=modelo(),
                 contents=montar_mensagem(texto),
                 config={
                     "system_instruction": INSTRUCOES,
                     "response_mime_type": "application/json",
                     "response_schema": NotaExtraida,
                 },
             )
           except erros_gemini.APIError → ErroExtracao("Falha ao chamar o modelo")
        3. O Gemini não levanta erro quando o JSON não bate com o modelo: ele deixa resposta.parsed
           como None. Se for None → ErroExtracao("O modelo devolveu dados fora do formato esperado").
        4. Devolva o dict:
             nota            = resposta.parsed
             tokens_entrada  = resposta.usage_metadata.prompt_token_count
             tokens_saida    = resposta.usage_metadata.candidates_token_count
    """
    if not texto.strip():
        raise ValueError("Texto vazio")
    try:
        resposta = cliente.models.generate_content(
            model = modelo(),
            contents = montar_mensagem(texto),
            config={
                'system_instruction': INSTRUCOES,
                'response_mime_type': 'application/json',
                'response_schema': NotaExtraida})
        saida = {"nota": resposta.parsed,
                "tokens_entrada": resposta.usage_metadata.prompt_token_count,
                "tokens_saida": resposta.usage_metadata.candidates_token_count}
        if not resposta.parsed:
            raise ErroExtracao('O modelo devolveu dados fora do formato esperado')    
        return saida
    except erros_gemini.APIError:
        raise ErroExtracao('Falha ao chamar o modelo')
    



def extrair_nota_ollama(cliente, texto: str) -> dict:
    """A mesma extração, com um modelo rodando no seu Ollama (biblioteca ollama).

    Devolve o mesmo dict do extrair_nota.

    Passo a passo:
        1. Texto vazio ou só com espaços? raise ValueError("Texto vazio").
        2. Dentro de um try:
             resposta = cliente.chat(
                 model=modelo(),
                 messages=[
                     {"role": "system", "content": INSTRUCOES},        # no Ollama, o system é uma mensagem
                     {"role": "user", "content": montar_mensagem(texto)},
                 ],
                 format=NotaExtraida.model_json_schema(),             # o formato obrigatório, como esquema JSON
                 options={"temperature": 0},                          # respostas mais estáveis
             )
             nota = NotaExtraida.model_validate_json(resposta.message.content)   # o texto JSON vira NotaExtraida
           Três erros possíveis, cada um com o seu except:
             - ollama.ResponseError  (ex.: modelo não baixado) → ErroExtracao("Falha ao chamar o modelo")
             - ConnectionError       (o Ollama não está rodando) → ErroExtracao("Falha ao chamar o modelo")
             - ValidationError       (o JSON não bate)          → ErroExtracao("O modelo devolveu dados fora do formato esperado")
           Dica: um except pode pegar dois tipos de uma vez: except (ollama.ResponseError, ConnectionError):
        3. Devolva o dict: a nota do passo 2; os tokens em resposta.prompt_eval_count (entrada)
           e resposta.eval_count (saída).
    """
    if not texto.strip():
        raise ValueError("Texto vazio")
    try:
        resposta = cliente.chat(
            model = modelo(),
            messages=[
                {'role': 'system', 'content': INSTRUCOES},
                {'role': 'user', 'content': montar_mensagem(texto)}
            ],
            format=NotaExtraida.model_json_schema(),
            options={'temperature':0}
        )
        nota = NotaExtraida.model_validate_json(resposta.message.content)
    except ollama.ResponseError:
        raise ErroExtracao('Falha ao chamar o modelo')
    except ConnectionError:
        raise ErroExtracao('Falha ao chamar o modelo')
    except ValidationError:
        raise ErroExtracao('O modelo devolveu dados fora do formato esperado')    
    saida = {"nota": nota,
            "tokens_entrada": resposta.prompt_eval_count,
            "tokens_saida": resposta.eval_count}
    return saida


def extrair(cliente, texto: str) -> dict:
    """Já pronta: chama a extração do provedor escolhido e acrescenta quem respondeu.

    Devolve o dict da extração com mais duas chaves: "provedor" e "modelo".
    """
    nome = provedor()
    if nome == "gemini":
        resultado = extrair_nota_gemini(cliente, texto)
    elif nome == "ollama":
        resultado = extrair_nota_ollama(cliente, texto)
    else:                                              # anthropic e demo: o seu extrair_nota de terça
        resultado = extrair_nota(cliente, texto)
    resultado["provedor"] = nome
    resultado["modelo"] = modelo()
    return resultado


def custo(tokens_entrada: int, tokens_saida: int) -> Decimal:
    """Já pronta: o custo da chamada com os preços do provedor escolhido, com 6 casas."""
    preco_entrada, preco_saida = PRECOS[provedor()]    # a tupla se desmonta em duas variáveis
    valor = (tokens_entrada * preco_entrada + tokens_saida * preco_saida) / Decimal("1000000")
    return valor.quantize(Decimal("0.000001"))
