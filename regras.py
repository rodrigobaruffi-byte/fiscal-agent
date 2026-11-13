"""Terça — Regras fiscais da nota, em Python puro (sem banco, sem API).

ESCREVER SEM IA. Consulte o dia2_conceito.md.
Testes:  pytest semana-03/test_regras.py -q

Por que separado: regras sem banco e sem HTTP são as mais fáceis de testar, e a mesma
função vai servir à API (quarta) e, mais adiante, ao agente fiscal.
"""

from decimal import Decimal


def total_dos_itens(itens: list[dict]) -> Decimal:
    """Soma quantidade * valor_unitario de todos os itens, arredondado a 2 casas.

    Recebe:
        itens: [{"descricao": "Cabo", "cfop": "6102",
                 "quantidade": Decimal("10"), "valor_unitario": Decimal("4.50")}, ...]
    Devolve:
        Decimal("45.00") para o exemplo acima. Lista vazia → Decimal("0.00").

    Dica: arredondar Decimal a 2 casas é .quantize(Decimal("0.01")) (seção 2 do conceito).
    """
    total = Decimal('0.00')
    for i in itens:
        total = total + Decimal(i['quantidade'])*Decimal(i['valor_unitario'])
    return total.quantize(Decimal('0.01'))


def validar_nota(nota: dict) -> list[str]:
    """Confere as regras e devolve a lista de erros. Lista vazia = nota válida.

    Recebe:
        nota: o mesmo dict de segunda (6 campos + "itens"). As UFs já chegam em maiúsculas.
    Devolve:
        uma lista de mensagens, nesta ordem e exatamente com estes textos:

        1. Sem itens → ["Nota sem itens"] e mais nada (sem itens, as outras regras não fazem sentido).
        2. Para cada item, na ordem, numerando a partir de 1 (Item 1, Item 2...):
           - CFOP começando com 5 (saída estadual), mas UFs diferentes:
             "Item 1: CFOP 5102 é de operação estadual, mas as UFs são diferentes"
           - CFOP começando com 6 (saída interestadual), mas UFs iguais:
             "Item 2: CFOP 6102 é de operação interestadual, mas as UFs são iguais"
           - CFOP começando com outro dígito:
             "Item 3: CFOP 1102 não é de saída"
        3. Depois dos itens: se a diferença entre valor_total e total_dos_itens for maior que 0,01:
           "Valor total não confere com os itens"

    Passo a passo:
        1. erros = []
        2. Sem itens? return ["Nota sem itens"]
        3. for numero, item in enumerate(nota["itens"], start=1): ... (seção 3 do conceito)
        4. Compare os totais com abs(...) > Decimal("0.01").
        5. return erros
    """
    erros = []
    if ( (not nota['itens'])):
        erros.append("Nota sem itens")
        return erros
    for numero, i in enumerate(nota['itens'],start=1):
        cfop = i['cfop']
        if ((cfop[0] == '5' ) ) and (nota['uf_origem'] != nota['uf_destino']):
            erros.append(f'Item {numero}: CFOP {cfop} é de operação estadual, mas as UFs são diferentes')
        elif ((cfop[0] == '6' ) ) and (nota['uf_origem'] == nota['uf_destino']):
            erros.append(f'Item {numero}: CFOP {cfop} é de operação interestadual, mas as UFs são iguais')
        elif ((cfop[0] in '123') ): 
            erros.append(f'Item {numero}: CFOP {cfop} não é de saída')
    if abs(Decimal(nota['valor_total']) - total_dos_itens(nota['itens'])) > Decimal('0.01'):
        erros.append('Valor total não confere com os itens')

    return erros
