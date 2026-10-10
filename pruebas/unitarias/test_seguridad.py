"""Pruebas de autorización y de ausencia de clientes de red."""

import ast
import asyncio
import re
import tomllib
from collections.abc import MutableMapping
from pathlib import Path

import pytest
from app.configuracion import Configuracion
from app.entrada import crear_app
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.security

_PROHIBIDOS = ("httpx", "requests", "urllib.request", "http.client", "socket", "aiohttp")
_URL = re.compile(r"https?://")
_RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")],
)
@pytest.mark.parametrize(
    "header",
    [
        None,
        "Bearer otro-token",
        "token-prueba-fijo",
        "Bearer",
        "bearer token-prueba-fijo",
    ],
    ids=["sin-header", "token-distinto", "sin-prefijo", "bearer-sin-token", "bearer-minuscula"],
)
def test_seguridad_header_invalido_responde_401(
    app: FastAPI,
    metodo: str,
    ruta: str,
    header: str | None,
) -> None:
    with TestClient(app) as cliente:
        headers = {} if header is None else {"Authorization": header}
        respuesta = cliente.request(metodo, ruta, headers=headers, json={"m": "PING;64"})

    assert respuesta.status_code == 401
    assert respuesta.json()["error"] == "E001"


def test_seguridad_ruta_desconocida_gana_a_la_auth(app: FastAPI) -> None:
    with TestClient(app) as cliente:
        respuesta = cliente.get("/msg")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "E404"


def test_seguridad_token_no_ascii_responde_401_y_no_500(token_prueba: str) -> None:
    # httpx rechaza headers no ASCII; el servicio los recibe por ASGI en latin-1.
    status, cuerpo = _pedir(crear_app(Configuracion(token=token_prueba)), "Bearer cañón")

    assert status == 401
    assert b"E001" in cuerpo
    assert b"Internal Server Error" not in cuerpo


def test_seguridad_token_configurado_no_ascii_no_responde_500() -> None:
    aplicacion = crear_app(Configuracion(token="cañón"))  # noqa: S106

    distinto, _ = _pedir(aplicacion, "Bearer canion")
    exacto, cuerpo = _pedir(aplicacion, "Bearer cañón")

    assert distinto == 401
    assert exacto == 200
    assert b"Internal Server Error" not in cuerpo


def test_seguridad_paquete_sin_clientes_de_red() -> None:
    for archivo in (_RAIZ / "app").rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        assert _URL.search(texto) is None
        for nodo in ast.walk(ast.parse(texto)):
            if isinstance(nodo, ast.Import):
                nombres = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""]
            else:
                continue
            for nombre in nombres:
                assert not _prohibido(nombre), archivo.name


def test_seguridad_dependencias_runtime_sin_clientes_http() -> None:
    proyecto = tomllib.loads((_RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    dependencias = proyecto["project"]["dependencies"]
    assert isinstance(dependencias, list)
    nombres = {str(dep).split("==", 1)[0].lower() for dep in dependencias}

    assert nombres.isdisjoint({"httpx", "requests", "aiohttp", "urllib3"})


def _prohibido(nombre: str) -> bool:
    return any(nombre == modulo or nombre.startswith(f"{modulo}.") for modulo in _PROHIBIDOS)


def _pedir(aplicacion: FastAPI, autorizacion: str) -> tuple[int, bytes]:
    return asyncio.run(_pedir_asgi(aplicacion, autorizacion))


async def _pedir_asgi(aplicacion: FastAPI, autorizacion: str) -> tuple[int, bytes]:
    cuerpo = bytearray()
    status = 0

    async def recibir() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(mensaje: MutableMapping[str, object]) -> None:
        nonlocal status
        if mensaje["type"] == "http.response.start":
            codigo = mensaje["status"]
            if isinstance(codigo, int):
                status = codigo
        elif mensaje["type"] == "http.response.body":
            parte = mensaje.get("body", b"")
            if isinstance(parte, bytes):
                cuerpo.extend(parte)

    alcance: dict[str, object] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [(b"authorization", autorizacion.encode("latin-1"))],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    await aplicacion(alcance, recibir, enviar)
    return status, bytes(cuerpo)
