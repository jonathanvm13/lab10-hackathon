"""Catálogo de status y cuerpos copiados de `docs/standards/openapi.yml`.

El paquete no lee el YAML en runtime. Los textos, incluido el espacio final de
E301 y la grafía `recieved`, son los del contrato.
"""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from starlette.responses import JSONResponse, PlainTextResponse, Response

type ValorCampo = str | int | bool
type Cuerpo = Mapping[str, ValorCampo] | str


class CodigoError(StrEnum):
    """Clave de una respuesta del contrato, de éxito o de error."""

    OK = "OK"
    OK_PING = "OK_PING"
    OK_ALTA = "OK_ALTA"
    OK_CONSULTA = "OK_CONSULTA"
    OK_DEPOSITO = "OK_DEPOSITO"
    OK_TRANSFER = "OK_TRANSFER"
    OK_ANULA = "OK_ANULA"
    OK_ANULA_YA_ANULADA = "OK_ANULA_YA_ANULADA"
    E001 = "E001"
    E404 = "E404"
    E100 = "E100"
    E102 = "E102"
    E103 = "E103"
    E104 = "E104"
    E201 = "E201"
    E202 = "E202"
    E301 = "E301"
    E301_SUGERENCIA = "E301_SUGERENCIA"
    E302 = "E302"
    E303 = "E303"
    E304 = "E304"
    E401 = "E401"
    E402 = "E402"
    E520 = "E520"
    E510 = "E510"
    E506 = "E506"
    E507 = "E507"
    E500 = "E500"


class Respuesta:
    """Status HTTP y cuerpo exacto de una clave del catálogo."""

    __slots__ = ("cuerpo", "status")

    def __init__(self, status: int, cuerpo: Cuerpo) -> None:
        """Guarda el status y el cuerpo de la entrada."""
        self.status = status
        self.cuerpo = cuerpo


def _json(status: int, cuerpo: dict[str, ValorCampo]) -> Respuesta:
    return Respuesta(status, MappingProxyType(cuerpo))


# Texto literal del contrato; no corregir el espacio final (openapi.yml E301).
_COMANDO_DESCONOCIDO = "comando desconocido "

CATALOGO: Mapping[CodigoError, Respuesta] = MappingProxyType(
    {
        CodigoError.OK: _json(200, {"ok": True}),
        CodigoError.OK_PING: _json(200, {"pong": True}),
        CodigoError.OK_ALTA: _json(201, {"cuentaId": "AC-0001"}),
        CodigoError.OK_CONSULTA: _json(200, {"cuenta_id": "AC-0001", "saldo": "0.00"}),
        # Texto literal del contrato; no corregir (openapi.yml OperacionRecibida).
        CodigoError.OK_DEPOSITO: _json(
            200,
            {"status": "recieved", "operacionId": "OP-0001"},
        ),
        CodigoError.OK_TRANSFER: _json(
            200,
            {"status": "recieved", "operacionId": "OP-0002"},
        ),
        CodigoError.OK_ANULA: _json(200, {"ok": True, "anulada": "OP-0003"}),
        CodigoError.OK_ANULA_YA_ANULADA: _json(200, {"ok": False, "motivo": "ya anulada"}),
        CodigoError.E001: _json(401, {"error": "E001", "mensaje": "no autorizado"}),
        CodigoError.E404: _json(404, {"error": "E404", "mensaje": "ruta desconocida"}),
        CodigoError.E100: _json(400, {"error": "E100", "mensaje": "json inválido"}),
        CodigoError.E102: _json(400, {"error": "E102", "mensaje": "falta m"}),
        CodigoError.E103: _json(400, {"error": "E103", "mensaje": "falta control"}),
        CodigoError.E104: _json(400, {"error": "E104", "mensaje": "segmento vacío"}),
        CodigoError.E201: _json(400, {"error": "E201", "mensaje": "control mal formado"}),
        CodigoError.E202: _json(400, {"error": "E202", "mensaje": "control inválido"}),
        CodigoError.E301: _json(400, {"error": "E301", "mensaje": _COMANDO_DESCONOCIDO}),
        CodigoError.E301_SUGERENCIA: _json(
            400,
            {"error": "E301", "mensaje": _COMANDO_DESCONOCIDO, "sugerencia": "PING"},
        ),
        CodigoError.E302: _json(400, {"error": "E302", "mensaje": "aridad inválida"}),
        CodigoError.E303: _json(400, {"error": "E303", "mensaje": "monto inválido"}),
        CodigoError.E304: _json(400, {"error": "E304", "mensaje": "origen y destino iguales"}),
        CodigoError.E401: _json(404, {"error": "E401", "mensaje": "cuenta inexistente"}),
        CodigoError.E402: _json(404, {"error": "E402", "mensaje": "operación inexistente"}),
        CodigoError.E520: _json(
            409,
            {
                "error": "E520",
                "mensaje": ("operación destructiva: detiene el servicio; reenvía con confirmación"),
            },
        ),
        CodigoError.E510: _json(
            423,
            {"error": "E510", "mensaje": "cuenta bloqueada", "intentos": 1},
        ),
        CodigoError.E506: _json(422, {"error": "E506", "mensaje": "límite excedido"}),
        CodigoError.E507: _json(422, {"error": "E507", "mensaje": "saldo insuficiente"}),
        CodigoError.E500: Respuesta(500, "Internal Server Error"),
    }
)


def responder(
    codigo: CodigoError,
    campos: Mapping[str, ValorCampo] | None = None,
) -> Response:
    """Arma la respuesta HTTP de una clave del catálogo.

    Args:
        codigo: Clave del catálogo.
        campos: Sustituciones sobre el cuerpo de ejemplo. Solo aplica a JSON.

    Returns:
        `JSONResponse` compacta, o texto plano si el cuerpo del catálogo es texto.
    """
    respuesta = CATALOGO[codigo]
    if isinstance(respuesta.cuerpo, str):
        return PlainTextResponse(respuesta.cuerpo, status_code=respuesta.status)
    cuerpo = dict(respuesta.cuerpo)
    if campos:
        cuerpo.update(campos)
    return JSONResponse(cuerpo, status_code=respuesta.status)
