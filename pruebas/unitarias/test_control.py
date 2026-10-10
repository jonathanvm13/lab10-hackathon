"""Pruebas del dígito de control ISO 7064 MOD 97-10."""

from app.control import calcular_control, coincide, formato_valido


def test_control_letra_ascii_alta_lucia_es_82() -> None:
    assert calcular_control("ALTA;Lucia") == "82"
    assert calcular_control("alta;lucia") == calcular_control("ALTA;LUCIA")


def test_control_no_ascii_se_ignora() -> None:
    assert calcular_control("ñ") == calcular_control("")
    assert calcular_control("ALTA;Jose_2") == calcular_control("ALTA;Jose2")
    assert calcular_control("ALTA;Jose_2") == "25"
    assert calcular_control("ALTA;Ana Maria") == "44"


def test_control_cadena_vacia_es_98() -> None:
    assert calcular_control("") == "98"


def test_control_02_distinto_de_2() -> None:
    base = _base_con_control("2")

    assert coincide("2", base)
    assert not coincide("02", base)
    assert formato_valido("02")
    assert not formato_valido("5X")
    assert not formato_valido("100")


def _base_con_control(esperado: str) -> str:
    for indice in range(500):
        base = f"ALTA;n{indice}"
        if calcular_control(base) == esperado:
            return base
    raise AssertionError(esperado)
