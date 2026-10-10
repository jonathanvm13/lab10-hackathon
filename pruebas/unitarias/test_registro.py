"""Pruebas del log JSON y de la redacción del token."""

import json
import logging

import pytest
from app.configuracion import Configuracion
from app.registro import configurar_registro, truncar
from fastapi.testclient import TestClient


def test_registro_no_incluye_el_token(
    client: TestClient,
    token_prueba: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client.get("/health")
    client.get("/health", headers={"Authorization": "Bearer invalido"})
    client.post("/msg", json={"m": token_prueba})

    salida = capsys.readouterr().out

    assert token_prueba not in salida
    assert "Authorization" not in salida
    assert "Bearer ***" in salida


def test_registro_traceback_sin_token(
    client: TestClient,
    token_prueba: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(mensaje: str, estado: object = None) -> object:
        raise RuntimeError(token_prueba)

    monkeypatch.setattr("app.entrada.procesar", boom)

    respuesta = client.post("/msg", json={"m": "PING;64"})
    salida = capsys.readouterr().out

    assert respuesta.status_code == 500
    assert token_prueba not in salida
    assert "Authorization" not in salida
    assert "traceback" in salida


def test_registro_trunca_el_cuerpo(
    client: TestClient,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client.post("/msg", json={"m": "A" * 600})

    lineas = [linea for linea in capsys.readouterr().out.splitlines() if linea.startswith("{")]
    registro = json.loads(lineas[-1])

    assert len(registro["cuerpo"]) == 500


def test_registro_truncar_corto_no_cambia() -> None:
    assert truncar("hola") == "hola"


def test_registro_nivel_desconocido_usa_info() -> None:
    configurar_registro(Configuracion(token="abc", nivel_log="NO_EXISTE"))  # noqa: S106

    assert logging.getLogger("app").level == logging.INFO
