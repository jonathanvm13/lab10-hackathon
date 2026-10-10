#!/usr/bin/env python3
"""Recorre los pasos del contrato contra el servicio desplegado.

Uso:
  APP_AUTH_TOKEN=... python3 herramientas/pasos.py

La URL por defecto es la del servicio en Railway. APP_BASE_URL la reemplaza.
El token no se imprime. El script llama a POST /__reset y deja el estado en cero.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional, Tuple

BASE = os.environ.get(
    "APP_BASE_URL",
    "https://lab10-hackathon-production.up.railway.app",
).rstrip("/")

_FALLOS = 0


def _control(mensaje: str) -> str:
    piezas = []
    for caracter in mensaje:
        if "a" <= caracter <= "z" or "A" <= caracter <= "Z":
            piezas.append(str(ord(caracter.upper()) - 64))
        elif "0" <= caracter <= "9":
            piezas.append(caracter)
    numero = int("".join(piezas) or "0")
    return str(98 - (numero * 100) % 97)


def _firmar(base: str) -> str:
    return f"{base};{_control(base)}"


def _token() -> str:
    token = os.environ.get("APP_AUTH_TOKEN", "").strip()
    if not token:
        print("Falta APP_AUTH_TOKEN", file=sys.stderr)
        raise SystemExit(2)
    return token


def _enviar(
    metodo: str, ruta: str, cuerpo: Optional[bytes], token: Optional[str]
) -> Tuple[int, str]:
    headers = {}
    if cuerpo is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    solicitud = urllib.request.Request(
        BASE + ruta,
        data=cuerpo,
        method=metodo,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=15) as respuesta:
            return respuesta.getcode(), respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _json(valor: object) -> bytes:
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _esperar(paso: str, status: int, texto: str, esperado_status: int, esperado: object) -> None:
    global _FALLOS
    try:
        recibido = json.loads(texto) if texto else ""
    except json.JSONDecodeError:
        recibido = texto
    if status == esperado_status and recibido == esperado:
        print(f"ok    {paso}")
        return
    _FALLOS += 1
    print(f"fallo {paso}")
    print(f"      esperaba {esperado_status} {esperado}")
    print(f"      recibio  {status} {recibido}")


def _http(
    paso: str,
    metodo: str,
    ruta: str,
    cuerpo: Optional[bytes],
    token: Optional[str],
    status: int,
    esperado: object,
) -> None:
    real_status, texto = _enviar(metodo, ruta, cuerpo, token)
    _esperar(paso, real_status, texto, status, esperado)


def _msg(paso: str, mensaje: str, token: str, status: int, esperado: object, *, firmar: bool = True) -> None:
    if firmar:
        mensaje = _firmar(mensaje)
    _http(paso, "POST", "/msg", _json({"m": mensaje}), token, status, esperado)


def main() -> int:
    token = _token()
    print(BASE)

    _http("ruta", "GET", "/", None, None, 404, {"error": "E404", "mensaje": "ruta desconocida"})
    _http("auth", "GET", "/health", None, None, 401, {"error": "E001", "mensaje": "no autorizado"})
    _http("json", "POST", "/msg", b"no-es-json", token, 400, {"error": "E100", "mensaje": "json inválido"})
    _http("m", "POST", "/msg", _json({}), token, 400, {"error": "E102", "mensaje": "falta m"})
    _msg("segmentos", "PING", token, 400, {"error": "E103", "mensaje": "falta control"}, firmar=False)
    _msg("segmentos", "PING;", token, 400, {"error": "E104", "mensaje": "segmento vacío"}, firmar=False)
    _msg("control", "ALTA;Lucia;xx", token, 400, {"error": "E201", "mensaje": "control mal formado"}, firmar=False)
    malo = "2" if _control("ALTA;Lucia") != "2" else "3"
    _msg("control", f"ALTA;Lucia;{malo}", token, 400, {"error": "E202", "mensaje": "control inválido"}, firmar=False)
    _msg("comando", "ZZZZ", token, 400, {"error": "E301", "mensaje": "comando desconocido "})
    _msg(
        "comando",
        "PONG",
        token,
        400,
        {"error": "E301", "mensaje": "comando desconocido ", "sugerencia": "PING"},
    )
    _msg("aridad", "ALTA", token, 400, {"error": "E302", "mensaje": "aridad inválida"})
    _msg("monto", "DEPOSITO;AC-0001;abc", token, 400, {"error": "E303", "mensaje": "monto inválido"})
    _msg(
        "origen_destino",
        "TRANSFER;AC-0001;AC-0001;10",
        token,
        400,
        {"error": "E304", "mensaje": "origen y destino iguales"},
    )

    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})
    _msg("cuentas", "CONSULTA;AC-0001", token, 404, {"error": "E401", "mensaje": "cuenta inexistente"})
    _msg(
        "halt_u_operacion",
        "HALT;X",
        token,
        409,
        {
            "error": "E520",
            "mensaje": "operación destructiva: detiene el servicio; reenvía con confirmación",
        },
    )
    _msg(
        "halt_u_operacion",
        "ANULA;OP-0001",
        token,
        404,
        {"error": "E402", "mensaje": "operación inexistente"},
    )

    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})
    _msg("ejecutar", "ALTA;A", token, 201, {"cuentaId": "AC-0001"})
    _msg("ejecutar", "ALTA;B", token, 201, {"cuentaId": "AC-0002"})
    _msg("limite", "TRANSFER;AC-0001;AC-0002;120000", token, 422, {"error": "E506", "mensaje": "límite excedido"})

    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})
    _msg("ejecutar", "ALTA;A", token, 201, {"cuentaId": "AC-0001"})
    _msg("ejecutar", "ALTA;B", token, 201, {"cuentaId": "AC-0002"})
    _msg("ejecutar", "DEPOSITO;AC-0001;100", token, 200, {"status": "recieved", "operacionId": "OP-0001"})
    _msg("saldo", "TRANSFER;AC-0001;AC-0002;500", token, 422, {"error": "E507", "mensaje": "saldo insuficiente"})

    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})
    _msg("ejecutar", "ALTA;A", token, 201, {"cuentaId": "AC-0001"})
    _msg("ejecutar", "ALTA;B", token, 201, {"cuentaId": "AC-0002"})
    for _ in range(3):
        _msg(
            "limite",
            "TRANSFER;AC-0001;AC-0002;120000",
            token,
            422,
            {"error": "E506", "mensaje": "límite excedido"},
        )
    _msg(
        "bloqueo",
        "TRANSFER;AC-0001;AC-0002;1",
        token,
        423,
        {"error": "E510", "mensaje": "cuenta bloqueada", "intentos": 1},
    )

    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})
    _msg("ejecutar", "PING;0", token, 200, {"pong": True}, firmar=False)
    _msg("ejecutar", "ALTA;A", token, 201, {"cuentaId": "AC-0001"})
    _msg("ejecutar", "CONSULTA;AC-0001", token, 200, {"cuenta_id": "AC-0001", "saldo": "0.00"})
    _msg("ejecutar", "DEPOSITO;AC-0001;250", token, 200, {"status": "recieved", "operacionId": "OP-0001"})
    _msg("ejecutar", "ALTA;B", token, 201, {"cuentaId": "AC-0002"})
    _msg(
        "ejecutar",
        "TRANSFER;AC-0001;AC-0002;100",
        token,
        200,
        {"status": "recieved", "operacionId": "OP-0002"},
    )
    _msg("ejecutar", "ANULA;OP-0001", token, 200, {"ok": True, "anulada": "OP-0001"})
    _msg("ejecutar", "ANULA;OP-0001", token, 200, {"ok": False, "motivo": "ya anulada"})
    _http("reset", "POST", "/__reset", None, token, 200, {"ok": True})

    if _FALLOS:
        print(f"{_FALLOS} fallo(s)")
        return 1
    print("todos los pasos pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
