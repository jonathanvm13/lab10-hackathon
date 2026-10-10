"""Pruebas de contrato del OpenAPI y del catálogo."""

import tomllib
from pathlib import Path

import yaml
from app.catalogo import CATALOGO
from openapi_spec_validator import validate

_RAIZ = Path(__file__).resolve().parents[2]
_OPENAPI = _RAIZ / "docs" / "standards" / "openapi.yml"


def _spec() -> dict[str, object]:
    cargado = yaml.safe_load(_OPENAPI.read_text(encoding="utf-8"))
    assert isinstance(cargado, dict)
    return cargado


def test_openapi_estructura_valida_pasa() -> None:
    validate(_spec())


def test_openapi_version_igual_proyecto_coincide() -> None:
    spec = _spec()
    info = spec["info"]
    proyecto = tomllib.loads((_RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    seccion = proyecto["project"]

    assert isinstance(info, dict)
    assert isinstance(seccion, dict)
    assert info["version"] == seccion["version"]


def test_catalogo_cuerpos_igual_examples_coinciden() -> None:
    spec = _spec()
    componentes = spec["components"]
    assert isinstance(componentes, dict)
    ejemplos = componentes["examples"]
    assert isinstance(ejemplos, dict)
    for codigo, respuesta in CATALOGO.items():
        ejemplo = ejemplos[codigo.value]
        assert isinstance(ejemplo, dict)
        assert respuesta.cuerpo == ejemplo["value"]


def test_catalogo_status_igual_openapi_coincide() -> None:
    spec = _spec()
    estatus = _estatus_por_ejemplo(spec)
    for codigo, respuesta in CATALOGO.items():
        assert respuesta.status == estatus[codigo.value]


def test_openapi_sin_ejemplos_huerfanos_pasa() -> None:
    spec = _spec()
    componentes = spec["components"]
    assert isinstance(componentes, dict)
    ejemplos = componentes["examples"]
    assert isinstance(ejemplos, dict)
    assert set(ejemplos) == {codigo.value for codigo in CATALOGO}


def _estatus_por_ejemplo(spec: dict[str, object]) -> dict[str, int]:
    paths = spec["paths"]
    assert isinstance(paths, dict)
    hallados: dict[str, int] = {}
    for item in paths.values():
        if not isinstance(item, dict):
            continue
        for operacion in item.values():
            if not isinstance(operacion, dict) or "responses" not in operacion:
                continue
            respuestas = operacion["responses"]
            if not isinstance(respuestas, dict):
                continue
            for status, respuesta in respuestas.items():
                for clave in _ejemplos_en(respuesta, spec):
                    hallados[clave] = int(status)
    return hallados


def _ejemplos_en(nodo: object, spec: dict[str, object], profundidad: int = 0) -> set[str]:
    if profundidad > 8 or not isinstance(nodo, dict):
        return set()
    ref = nodo.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/examples/"):
        return {ref.rsplit("/", 1)[-1]}
    if isinstance(ref, str) and ref.startswith("#/components/responses/"):
        return _ejemplos_en(_resolver(spec, ref), spec, profundidad + 1)
    hallados: set[str] = set()
    for valor in nodo.values():
        if isinstance(valor, dict):
            hallados |= _ejemplos_en(valor, spec, profundidad + 1)
        elif isinstance(valor, list):
            for item in valor:
                hallados |= _ejemplos_en(item, spec, profundidad + 1)
    return hallados


def _resolver(spec: dict[str, object], ref: str) -> object:
    nodo: object = spec
    for parte in ref.removeprefix("#/").split("/"):
        assert isinstance(nodo, dict)
        assert parte in nodo
        nodo = nodo[parte]
    return nodo
