"""Fixtures compartidas de las pruebas."""

from collections.abc import Iterator

import pytest
from app.configuracion import Configuracion
from app.entrada import crear_app
from app.estado import reset
from fastapi import FastAPI
from fastapi.testclient import TestClient

TOKEN_PRUEBA = "token-prueba-fijo"  # noqa: S105  # token falso fijo de las fixtures


@pytest.fixture
def token_prueba() -> str:
    """Token falso fijo. No es un secreto de producción."""
    return TOKEN_PRUEBA


@pytest.fixture
def app(token_prueba: str) -> FastAPI:
    """Aplicación con el token de prueba inyectado."""
    return crear_app(Configuracion(token=token_prueba))


@pytest.fixture
def client(app: FastAPI, token_prueba: str) -> Iterator[TestClient]:
    """Cliente HTTP con `Authorization: Bearer <token de prueba>`."""
    with TestClient(app) as cliente:
        cliente.headers["Authorization"] = f"Bearer {token_prueba}"
        yield cliente


@pytest.fixture(autouse=True)
def estado_limpio() -> Iterator[None]:
    """Reinicia el estado en memoria antes y después de cada prueba."""
    reset()
    yield
    reset()
