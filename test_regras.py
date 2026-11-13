from datetime import date
from decimal import Decimal

from regras import total_dos_itens, validar_nota


def item(cfop="6102", quantidade="10", valor_unitario="4.50"):
    return {"descricao": "Item", "cfop": cfop,
            "quantidade": Decimal(quantidade), "valor_unitario": Decimal(valor_unitario)}


def nota(uf_origem="PR", uf_destino="SP", valor_total="150.00", itens=None):
    return {
        "numero": 1,
        "cnpj_emitente": "11222333000181",
        "uf_origem": uf_origem,
        "uf_destino": uf_destino,
        "valor_total": Decimal(valor_total),
        "emitida_em": date(2026, 11, 3),
        "itens": itens if itens is not None else [item(), item(valor_unitario="10.50")],
    }


def test_total_dos_itens():
    assert total_dos_itens([item(), item(valor_unitario="10.50")]) == Decimal("150.00")


def test_total_dos_itens_arredonda():
    # 3 x 0,333 = 0,999 → 1,00
    assert total_dos_itens([item(quantidade="3", valor_unitario="0.333")]) == Decimal("1.00")


def test_total_dos_itens_vazio():
    assert total_dos_itens([]) == Decimal("0.00")


def test_total_dos_itens_e_decimal():
    assert isinstance(total_dos_itens([item()]), Decimal)


def test_nota_valida():
    assert validar_nota(nota()) == []


def test_nota_valida_estadual():
    assert validar_nota(nota(uf_destino="PR", itens=[item(cfop="5102"), item(cfop="5405", valor_unitario="10.50")])) == []


def test_nota_sem_itens():
    assert validar_nota(nota(itens=[])) == ["Nota sem itens"]


def test_cfop_estadual_com_ufs_diferentes():
    erros = validar_nota(nota(itens=[item(cfop="5102"), item(valor_unitario="10.50")]))
    assert erros == ["Item 1: CFOP 5102 é de operação estadual, mas as UFs são diferentes"]


def test_cfop_interestadual_com_ufs_iguais():
    erros = validar_nota(nota(uf_destino="PR"))
    assert erros == [
        "Item 1: CFOP 6102 é de operação interestadual, mas as UFs são iguais",
        "Item 2: CFOP 6102 é de operação interestadual, mas as UFs são iguais",
    ]


def test_cfop_que_nao_e_de_saida():
    erros = validar_nota(nota(itens=[item(), item(cfop="1102", valor_unitario="10.50")]))
    assert erros == ["Item 2: CFOP 1102 não é de saída"]


def test_total_nao_confere():
    assert validar_nota(nota(valor_total="149.00")) == ["Valor total não confere com os itens"]


def test_total_com_um_centavo_de_diferenca_passa():
    assert validar_nota(nota(valor_total="150.01")) == []


def test_varios_erros_na_ordem():
    erros = validar_nota(nota(valor_total="1.00", itens=[item(cfop="5102"), item(cfop="2102")]))
    assert erros == [
        "Item 1: CFOP 5102 é de operação estadual, mas as UFs são diferentes",
        "Item 2: CFOP 2102 não é de saída",
        "Valor total não confere com os itens",
    ]
