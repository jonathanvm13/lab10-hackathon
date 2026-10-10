"""Replay en proceso de `docs/architecture/experimentos.jsonl`."""

import json
import re
from pathlib import Path
from time import perf_counter
from typing import cast

import httpx
from app.estado import reset
from fastapi import FastAPI
from fastapi.testclient import TestClient

_LOG = Path("docs/architecture/experimentos.jsonl")
_PREFIJO = re.compile(r"^\[([A-Z]+) (\S+)(.*?)]")
_HEADER_EXTRA = re.compile(r"\+ header\s+([^:]+):\s*(.+)$")
_LIMITE_SEGUNDOS = 5.0
_EXCLUIDA = "c2"


def test_replay_log_coincide_status_y_cuerpo(app: FastAPI, token_prueba: str) -> None:
    with TestClient(app) as client:
        for secuencia, pasos in _secuencias():
            reset()
            for paso in pasos:
                inicio = perf_counter()
                respuesta = _enviar(client, paso, token_prueba)
                duracion = perf_counter() - inicio
                identificador = paso["id"]
                status = paso["status"]
                assert isinstance(status, int)

                assert duracion < _LIMITE_SEGUNDOS, identificador
                assert respuesta.status_code == status, (secuencia, identificador)
                esperado = paso["response"]
                if isinstance(esperado, str):
                    assert respuesta.text == esperado, (secuencia, identificador)
                else:
                    assert respuesta.json() == esperado, (secuencia, identificador)


def test_replay_incluye_secuencia_sin_reset() -> None:
    nombres = [nombre for nombre, _ in _secuencias()]

    assert "adv-a5" in nombres
    assert "c2" not in nombres
    assert "c2b" in nombres


def _secuencias() -> list[tuple[str, list[dict[str, object]]]]:
    grupos: dict[str, list[dict[str, object]]] = {}
    orden: list[str] = []
    for texto in _LOG.read_text(encoding="utf-8").splitlines():
        if not texto:
            continue
        valor = json.loads(texto)
        if not isinstance(valor, dict):
            continue
        seq = valor["seq"]
        if not isinstance(seq, str) or seq == _EXCLUIDA:
            continue
        if seq not in grupos:
            grupos[seq] = []
            orden.append(seq)
        grupos[seq].append(valor)
    return [(seq, grupos[seq]) for seq in orden]


def _enviar(
    client: TestClient,
    paso: dict[str, object],
    token: str,
) -> httpx.Response:
    hipotesis = paso["hipotesis"]
    assert isinstance(hipotesis, str)
    metodo, ruta, headers = _destino(hipotesis, token)
    cuerpo = paso["request"]
    if cuerpo == "-":
        return cast(httpx.Response, client.request(metodo, ruta, headers=headers))
    if isinstance(cuerpo, str):
        return cast(
            httpx.Response,
            client.request(metodo, ruta, headers=headers, content=cuerpo.encode("utf-8")),
        )
    return cast(httpx.Response, client.request(metodo, ruta, headers=headers, json=cuerpo))


def _destino(hipotesis: str, token: str) -> tuple[str, str, dict[str, str]]:
    coincidencia = _PREFIJO.match(hipotesis)
    if coincidencia is None:
        metodo, ruta, resto = "POST", "/msg", ""
    else:
        metodo = coincidencia.group(1)
        ruta = coincidencia.group(2)
        resto = coincidencia.group(3)
    return metodo, ruta, _headers(resto, token)


def _headers(resto: str, token: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if "'Bearer' sin token" in resto:
        headers["Authorization"] = "Bearer"
    elif "sin prefijo Bearer" in resto:
        headers["Authorization"] = token
    elif "bearer" in resto:
        headers["Authorization"] = f"bearer {token}"
    elif "sin token" in resto:
        pass
    elif "token inválido" in resto or "token ajeno" in resto:
        headers["Authorization"] = "Bearer token-ajeno"
    else:
        headers["Authorization"] = f"Bearer {token}"
    extra = _HEADER_EXTRA.search(resto)
    if extra is not None:
        headers[extra.group(1).strip()] = extra.group(2).strip()
    return headers
