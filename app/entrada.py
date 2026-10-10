"""Entrada HTTP: ruta comodín, autorización y traducción del catálogo.

El cuerpo de `POST /msg` se lee con `request.body` y `json.loads`. FastAPI no
declara modelos, así que no responde 422 de validación por el contrato.
"""

import hmac
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import Response

from app.catalogo import CATALOGO, CodigoError, responder
from app.configuracion import ORDEN_HTTP, Configuracion, configuracion_desde_entorno
from app.errores import ErrorDominio, ValorCampo
from app.estado import estado_proceso, reset
from app.pipeline import procesar
from app.registro import (
    RegistroSolicitud,
    configurar_registro,
    registrar_excepcion,
    registrar_solicitud,
    truncar,
)

_METODOS: tuple[str, ...] = ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD")
_RUTAS: Mapping[tuple[str, str], str] = {
    ("POST", "/msg"): "msg",
    ("GET", "/health"): "health",
    ("POST", "/__reset"): "reset",
}


@dataclass
class _Marca:
    status: int = 500
    codigo: str | None = None
    paso: str | None = None


_marca: ContextVar[_Marca | None] = ContextVar("marca_solicitud", default=None)
_datos: ContextVar[object | None] = ContextVar("datos_json", default=None)


def crear_app(configuracion: Configuracion) -> FastAPI:
    """Crea la aplicación con el token y el nivel de log indicados.

    Args:
        configuracion: Token de `Authorization` y nivel de log.

    Returns:
        Aplicación ASGI. Si el token está vacío, el ciclo de vida impide servir.
    """

    @asynccontextmanager
    async def ciclo(_aplicacion: FastAPI) -> AsyncIterator[None]:
        if not configuracion.token:
            raise RuntimeError("APP_AUTH_TOKEN es obligatoria")
        configurar_registro(configuracion)
        yield

    aplicacion = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
        lifespan=ciclo,
    )
    aplicacion.state.configuracion = configuracion
    aplicacion.state.estado = estado_proceso

    @aplicacion.api_route("/", methods=list(_METODOS), response_model=None)
    async def ruta_raiz(solicitud: Request) -> Response:
        return await _atender(solicitud)

    @aplicacion.api_route("/{_ruta:path}", methods=list(_METODOS), response_model=None)
    async def ruta_comodin(solicitud: Request, _ruta: str) -> Response:
        return await _atender(solicitud)

    aplicacion.add_exception_handler(HTTPException, _manejar_http)
    aplicacion.add_exception_handler(RequestValidationError, _manejar_validacion)
    aplicacion.add_exception_handler(Exception, _manejar_excepcion)
    return aplicacion


async def _atender(solicitud: Request) -> Response:
    marca = _Marca()
    ficha = _marca.set(marca)
    inicio = perf_counter()
    try:
        return await _despachar(solicitud)
    except ErrorDominio as exc:
        return _emitir(exc.codigo, exc.paso, exc.campos)
    except HTTPException:
        _preparar(CodigoError.E404, "ruta")
        raise
    except RequestValidationError:
        _preparar(CodigoError.E500, "interno")
        raise
    except Exception:  # noqa: BLE001  # el handler global traduce cualquier fallo no previsto a 500
        registrar_excepcion("excepcion no prevista")
        return _emitir(CodigoError.E500, "interno")
    finally:
        duracion_ms = round((perf_counter() - inicio) * 1000, 2)
        cuerpo = truncar((await solicitud.body()).decode("utf-8", errors="replace"))
        registrar_solicitud(
            RegistroSolicitud(
                solicitud.method,
                solicitud.url.path,
                marca.status,
                marca.codigo,
                marca.paso,
                duracion_ms,
                cuerpo,
            )
        )
        _marca.reset(ficha)


async def _despachar(solicitud: Request) -> Response:
    """Recorre el orden HTTP configurado y despacha la ruta conocida."""
    for paso in ORDEN_HTTP:
        if paso == "ruta":
            respuesta = _paso_ruta(solicitud)
        elif paso == "auth":
            respuesta = _paso_auth(solicitud)
        elif paso == "json":
            respuesta = await _paso_json(solicitud)
        else:
            respuesta = _paso_m(solicitud)
        if respuesta is not None:
            return respuesta
    return _emitir(CodigoError.E404, "ruta")


def _paso_ruta(solicitud: Request) -> Response | None:
    if solicitud.method == "HEAD":
        _preparar(CodigoError.E404, "ruta")
        return Response(status_code=CATALOGO[CodigoError.E404].status)
    if (solicitud.method, solicitud.url.path) not in _RUTAS:
        return _emitir(CodigoError.E404, "ruta")
    return None


def _paso_auth(solicitud: Request) -> Response | None:
    configuracion = cast(Configuracion, solicitud.app.state.configuracion)
    header = solicitud.headers.get("authorization")
    if not _autorizado(header, configuracion.token):
        return _emitir(CodigoError.E001, "auth")
    return None


async def _paso_json(solicitud: Request) -> Response | None:
    if solicitud.url.path != "/msg":
        return None
    crudo = await solicitud.body()
    if not crudo:
        raise ErrorDominio(CodigoError.E100, paso="json")
    try:
        datos = json.loads(crudo)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ErrorDominio(CodigoError.E100, paso="json") from exc
    _datos.set(datos)
    return None


def _paso_m(solicitud: Request) -> Response | None:
    if solicitud.url.path != "/msg":
        clave = _RUTAS[(solicitud.method, solicitud.url.path)]
        if clave == "health":
            return _emitir(CodigoError.OK, None)
        reset()
        return _emitir(CodigoError.OK, None)
    datos = _datos.get()
    if not isinstance(datos, dict):
        raise ErrorDominio(CodigoError.E102, paso="m")
    mensaje = datos.get("m")
    if not isinstance(mensaje, str):
        raise ErrorDominio(CodigoError.E102, paso="m")
    resultado = procesar(mensaje)
    return _emitir(resultado.codigo, None, resultado.campos)


def _emitir(
    codigo: CodigoError,
    paso: str | None,
    campos: Mapping[str, ValorCampo] | None = None,
) -> Response:
    _preparar(codigo, paso)
    return responder(codigo, campos)


def _preparar(codigo: CodigoError, paso: str | None) -> None:
    marca = _marca.get()
    if marca is None:
        return
    marca.codigo = codigo.value
    marca.status = CATALOGO[codigo].status
    marca.paso = paso


def _autorizado(header: str | None, token: str) -> bool:
    if header is None:
        return False
    esperado = f"Bearer {token}".encode()
    try:
        recibido = header.encode()
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(recibido, esperado)


async def _manejar_http(_solicitud: Request, _exc: Exception) -> Response:
    """Traduce un 404 o 405 del framework a la ruta desconocida del catálogo."""
    return responder(CodigoError.E404)


async def _manejar_validacion(_solicitud: Request, _exc: Exception) -> Response:
    """Traduce un 422 del framework a error interno.

    No debería ocurrir: el cuerpo se lee sin modelos de FastAPI.
    """
    registrar_excepcion("validacion de framework no prevista")
    return responder(CodigoError.E500)


async def _manejar_excepcion(_solicitud: Request, _exc: Exception) -> Response:
    """Traduce una excepción no prevista al texto plano del contrato."""
    registrar_excepcion("excepcion no prevista")
    return responder(CodigoError.E500)


app = crear_app(configuracion_desde_entorno())
