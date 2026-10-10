#!/usr/bin/env python3
"""Reejecuta los ids 93-346 de incidente-experimentos.jsonl contra una URL.

Es el mismo oráculo que pruebas/contrato/test_replay.py, pero por HTTP.
Antes de cada secuencia hace POST /__reset para dejar el estado limpio,
igual que el harness en proceso. Al terminar vuelve a resetear.

Uso:
  APP_AUTH_TOKEN=... APP_BASE_URL=http://127.0.0.1:8000 uv run python herramientas/replay_tarde.py

La URL por defecto es http://127.0.0.1:8000. El token no se imprime.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from time import perf_counter

_RAIZ = Path(__file__).resolve().parents[1]
_LOG = _RAIZ / "docs" / "architecture" / "incidente-experimentos.jsonl"
_ID_DESDE = 93
_ID_HASTA = 346
_LIMITE_SEGUNDOS = 5.0
_PREFIJO = re.compile(r"^\[([A-Z]+) (\S+)(.*?)]")
_HEADER_EXTRA = re.compile(r"\+ header\s+([^:]+):\s*(.+)$")

BASE = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _token() -> str:
    token = os.environ.get("APP_AUTH_TOKEN", "").strip()
    if not token:
        print("Falta APP_AUTH_TOKEN", file=sys.stderr)
        raise SystemExit(2)
    return token


def _secuencias() -> list[tuple[str, list[dict[str, object]]]]:
    grupos: dict[str, list[dict[str, object]]] = {}
    orden: list[str] = []
    for texto in _LOG.read_text(encoding="utf-8").splitlines():
        if not texto:
            continue
        valor = json.loads(texto)
        if not isinstance(valor, dict):
            continue
        identificador = valor.get("id")
        seq = valor.get("seq")
        if (
            not isinstance(identificador, int)
            or identificador < _ID_DESDE
            or identificador > _ID_HASTA
            or not isinstance(seq, str)
        ):
            continue
        if seq not in grupos:
            grupos[seq] = []
            orden.append(seq)
        grupos[seq].append(valor)
    return [(seq, grupos[seq]) for seq in orden]


def _destino(hipotesis: str, token: str) -> tuple[str, str, dict[str, str]]:
    coincidencia = _PREFIJO.match(hipotesis)
    if coincidencia is None:
        metodo, ruta, resto = "POST", "/msg", ""
    else:
        metodo = coincidencia.group(1)
        ruta = coincidencia.group(2)
        resto = coincidencia.group(3)
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
    return metodo, ruta, headers


def _enviar(metodo: str, ruta: str, headers: dict[str, str], cuerpo: object) -> tuple[int, str]:
    data = None
    if cuerpo != "-":
        if isinstance(cuerpo, str):
            data = cuerpo.encode("utf-8")
        else:
            data = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json"}
    solicitud = urllib.request.Request(BASE + ruta, data=data, method=metodo, headers=headers)
    try:
        with urllib.request.urlopen(solicitud, timeout=15) as respuesta:
            return respuesta.getcode(), respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _reset(token: str) -> None:
    status, texto = _enviar(
        "POST",
        "/__reset",
        {"Authorization": f"Bearer {token}"},
        "-",
    )
    if status != 200:
        print(f"no se pudo resetear: {status} {texto}", file=sys.stderr)
        raise SystemExit(2)


def _cuerpo_recibido(texto: str, esperado: object) -> object:
    if isinstance(esperado, str):
        return texto
    if not texto:
        return ""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


def main() -> int:
    token = _token()
    secuencias = _secuencias()
    total = sum(len(pasos) for _, pasos in secuencias)
    fallos = 0
    print(f"{BASE}  {total} pasos en {len(secuencias)} secuencias")

    for secuencia, pasos in secuencias:
        _reset(token)
        for paso in pasos:
            inicio = perf_counter()
            hipotesis = paso["hipotesis"]
            if not isinstance(hipotesis, str):
                print(f"fallo {paso.get('id')} hipotesis no es texto")
                fallos += 1
                continue
            metodo, ruta, headers = _destino(hipotesis, token)
            status, texto = _enviar(metodo, ruta, headers, paso["request"])
            duracion = perf_counter() - inicio
            identificador = paso["id"]
            esperado_status = paso["status"]
            esperado = paso["response"]
            recibido = _cuerpo_recibido(texto, esperado)
            if (
                isinstance(esperado_status, int)
                and status == esperado_status
                and recibido == esperado
                and duracion < _LIMITE_SEGUNDOS
            ):
                continue
            fallos += 1
            print(f"fallo {identificador} {secuencia} ({duracion:.2f}s)")
            print(f"      esperaba {esperado_status} {esperado}")
            print(f"      recibio  {status} {recibido}")

    _reset(token)
    if fallos:
        print(f"{total - fallos}/{total} ok, {fallos} fallo(s)")
        return 1
    print(f"{total}/{total} ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
