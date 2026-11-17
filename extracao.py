"""Semana 4 — Extração de dados de nota fiscal com um LLM (a API da Anthropic).

ESCREVER SEM IA. Consulte o dia1_conceito.md (segunda) e o dia2_conceito.md (terça).
Testes:  pytest semana-04/test_extracao.py -q
(Os testes NÃO chamam a API de verdade nem precisam de chave: usam um cliente falso.)

Segunda: texto_da_resposta, custo_usd e perguntar.
Terça:   montar_mensagem e extrair_nota.

Regra de sempre aqui: a função RECEBE o cliente como parâmetro (como o conn do banco), em vez de criar
um Anthropic() lá dentro. É isso que deixa o teste trocar o cliente de verdade por um falso.
"""

import os
from decimal import Decimal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()                      # lê o .env da pasta plano-ia ANTES de qualquer os.environ.get
MODELO = os.environ.get("ANTHROPIC_MODELO") or "claude-haiku-5-5"   # do .env; vazio ou sem ele, o Haiku

# Preço em dólares por MILHÃO de tokens (Haiku 5.5, conferido em nov/2026 na página de preços).
PRECO_ENTRADA = Decimal("0.10")    # o que você manda (pergunta, instruções, documento)
PRECO_SAIDA = Decimal("0.50")      # o que o modelo escreve na resposta


class ErroExtracao(Exception):
    """Já pronta: o erro da NOSSA extração. A API (quarta) transforma este erro em resposta 502."""


# ─── Segunda ─────────────────────────────────────────────────────────────────


def texto_da_resposta(resposta) -> str:
    """Junta o texto da resposta do modelo.

    Recebe:
        resposta: o objeto que cliente.messages.create(...) devolve. O que interessa nele é
        resposta.content, uma LISTA de blocos. Cada bloco tem .type ("text", "thinking"...) e,
        se for de texto, .text. São objetos: leia com PONTO (bloco.type), não com colchetes.
    Devolve:
        os .text dos blocos com .type == "text", na ordem, separados por "\\n".
        Nenhum bloco de texto → "" (texto vazio).

    Dica: monte uma lista com os textos e use "\\n".join(lista) (o join da semana 1).
    """
    resultado = []
    for bloco in resposta.content:
        if bloco.type == 'text':
            resultado.append(bloco.text)
    return '\n'.join(resultado)


def custo_usd(tokens_entrada: int, tokens_saida: int) -> Decimal:
    """Quanto custou uma chamada, em dólares.

    Conta: tokens_entrada × PRECO_ENTRADA / 1.000.000  +  tokens_saida × PRECO_SAIDA / 1.000.000
    Devolve um Decimal com 6 casas: .quantize(Decimal("0.000001")).
        custo_usd(1200, 300)  →  Decimal("0.000270")
    """
    
    custo = ((tokens_entrada * PRECO_ENTRADA)/1000000) + ((tokens_saida*PRECO_SAIDA)/1000000)
    return custo.quantize(Decimal('0.000001'))


def perguntar(cliente, pergunta: str) -> dict:
    """Faz uma pergunta ao modelo e devolve a resposta com os tokens gastos.

    Passo a passo:
        1. resposta = cliente.messages.create(...) com três argumentos nomeados:
             model=MODELO
             max_tokens=1000
             messages=[{"role": "user", "content": pergunta}]
        2. Devolva um dict:
             {"texto": texto_da_resposta(resposta),
              "tokens_entrada": resposta.usage.input_tokens,
              "tokens_saida": resposta.usage.output_tokens}
    """

    resposta = cliente.messages.create(model = MODELO,
                                       max_tokens = 1000,
                                       messages=[{"role": "user", 
                                                  "content": pergunta }])
    saida = {"texto": texto_da_resposta(resposta),
             "tokens_entrada": resposta.usage.input_tokens,
             "tokens_saida": resposta.usage.output_tokens}
    return saida


# ─── Terça ───────────────────────────────────────────────────────────────────


class ItemExtraido(BaseModel):
    """Já pronto: um item, como o modelo deve devolver. Tudo em texto: quem converte é a API (quarta).

    O description de cada campo vai junto para o modelo: é uma instrução, campo a campo.
    """

    descricao: str = Field(description="descrição do produto, como está no documento")
    cfop: str = Field(description="CFOP com 4 dígitos, só números, ex.: 6102")
    quantidade: str = Field(description="quantidade com ponto decimal, sem milhar, ex.: 10 ou 2.5")
    valor_unitario: str = Field(description="valor unitário com ponto decimal, sem milhar, ex.: 189.90")


class NotaExtraida(BaseModel):
    """Já pronto: a nota inteira que o modelo deve devolver, com a lista de itens dentro."""

    numero: int = Field(description="número da nota, sem zeros à esquerda; 0 se não houver")
    cnpj_emitente: str = Field(description="CNPJ do emitente, como aparece no documento")
    uf_origem: str = Field(description="UF do emitente, 2 letras maiúsculas, ex.: PR")
    uf_destino: str = Field(description="UF do destinatário, 2 letras maiúsculas, ex.: SP")
    valor_total: str = Field(description="valor total da nota com ponto decimal, sem milhar, ex.: 2116.00")
    emitida_em: str = Field(description="data de emissão no formato AAAA-MM-DD")
    itens: list[ItemExtraido]


# Já pronto: as instruções gerais (o "system"). Valem para a conversa toda, antes da mensagem.
INSTRUCOES = """Você extrai dados de notas fiscais brasileiras (NF-e) a partir do texto de um documento.
Regras:
- Use só o que está no documento. Não invente nem calcule valores que não aparecem.
- Valores e quantidades com ponto decimal e sem separador de milhar: 1899.00, 10, 2.5.
- Datas no formato AAAA-MM-DD.
- UF com 2 letras maiúsculas.
- Se um campo de texto não estiver no documento, devolva "" (texto vazio)."""


def montar_mensagem(texto: str) -> str:
    """Monta a mensagem do usuário: um pedido curto e o documento entre tags.

    Devolve exatamente este formato (o texto sem os espaços e quebras de linha das pontas):

        Extraia os dados da nota fiscal abaixo.

        <documento>
        ...o texto aqui...
        </documento>

    Ou seja: "Extraia os dados da nota fiscal abaixo.\\n\\n<documento>\\n" + texto + "\\n</documento>".
    Dica: uma f-string com \\n resolve; texto.strip() tira os espaços das pontas.
    """
    return f"Extraia os dados da nota fiscal abaixo.\n\n<documento>\n{texto.strip()}\n</documento>"


def extrair_nota(cliente, texto: str) -> dict:
    """Pede ao modelo os dados da nota, já no formato NotaExtraida (saída estruturada).

    Devolve:
        {"nota": <NotaExtraida>, "tokens_entrada": int, "tokens_saida": int}

    Passo a passo:
        1. Texto vazio ou só com espaços? raise ValueError("Texto vazio"), ANTES de chamar o modelo
           (não se paga por uma chamada inútil).
        2. Dentro de um try, chame:
             resposta = cliente.messages.parse(
                 model=MODELO,
                 max_tokens=2000,
                 system=INSTRUCOES,
                 messages=[{"role": "user", "content": montar_mensagem(texto)}],
                 output_format=NotaExtraida,
             )
        3. Trate dois erros, cada um com o seu except, levantando ErroExtracao com estes textos:
             - ValidationError     → "O modelo devolveu dados fora do formato esperado"
             - anthropic.APIError  → "Falha ao chamar o modelo"
        4. Devolva o dict, com resposta.parsed_output e os tokens de resposta.usage
           (input_tokens e output_tokens, como no perguntar).
    """
    if not texto.strip():
        raise ValueError("Texto vazio")
    try:
            resposta = cliente.messages.parse(
                model = MODELO,
                max_tokens = 2000,
                system = INSTRUCOES,
                messages = [{'role': 'user', 'content':montar_mensagem(texto)}],
                output_format=NotaExtraida
            )
            saida = {"nota": resposta.parsed_output,
                "tokens_entrada": resposta.usage.input_tokens,
                "tokens_saida": resposta.usage.output_tokens}
            return saida
    except ValidationError:
        raise ErroExtracao('O modelo devolveu dados fora do formato esperado')
    except anthropic.APIError:
        raise ErroExtracao('Falha ao chamar o modelo')
