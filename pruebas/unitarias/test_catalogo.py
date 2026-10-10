"""Pruebas del catálogo contra los ejemplos del contrato."""

from collections.abc import Mapping
from pathlib import Path

import yaml
from app.catalogo import CATALOGO, CodigoError


def _ejemplos() -> dict[str, object]:
    ruta = Path("docs/standards/openapi.yml")
    spec = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    ejemplos = spec["components"]["examples"]
    return {clave: ejemplos[clave]["value"] for clave in ejemplos}


def test_catalogo_cubre_todo_el_enum_pasa() -> None:
    assert set(CATALOGO) == set(CodigoError)


def test_catalogo_cuerpos_igual_examples_coinciden() -> None:
    ejemplos = _ejemplos()
    for codigo, respuesta in CATALOGO.items():
        assert respuesta.cuerpo == ejemplos[codigo.value]


def test_catalogo_e510_status_423_termina_en_intentos() -> None:
    respuesta = CATALOGO[CodigoError.E510]
    cuerpo = respuesta.cuerpo

    assert respuesta.status == 423
    assert isinstance(cuerpo, Mapping)
    assert list(cuerpo.items())[-1] == ("intentos", 1)
