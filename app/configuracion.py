"""Token, nivel de log y orden de validación del servicio.

El orden es el de `docs/standards/openapi.yml`: gana el primer fallo.
`ruta`, `auth`, `json` y `m` los resuelve la entrada HTTP; el resto, el pipeline.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

ORDEN_HTTP: Final[tuple[str, ...]] = ("ruta", "auth", "json", "m")
ORDEN_MENSAJE: Final[tuple[str, ...]] = (
    "segmentos",
    "control",
    "comando",
    "aridad",
    "monto",
    "origen_destino",
    "cuentas",
    "halt_u_operacion",
    "bloqueo",
    "limite",
    "saldo",
    "ejecutar",
)
ORDEN_VALIDACION: Final[tuple[str, ...]] = ORDEN_HTTP + ORDEN_MENSAJE

# PING omite formato y valor del control, no el segmento vacío (openapi.yml).
COMANDOS_EXENTOS_CONTROL: Final[frozenset[str]] = frozenset({"PING"})

COMANDOS: Final[tuple[str, ...]] = (
    "PING",
    "ALTA",
    "CONSULTA",
    "DEPOSITO",
    "TRANSFER",
    "ANULA",
    "HALT",
)

ARIDAD: Final[Mapping[str, int]] = MappingProxyType(
    {
        "PING": 0,
        "ALTA": 1,
        "CONSULTA": 1,
        "DEPOSITO": 2,
        "TRANSFER": 3,
        "ANULA": 1,
        "HALT": 1,
    }
)

COMANDOS_CON_MONTO: Final[frozenset[str]] = frozenset({"DEPOSITO", "TRANSFER"})

# ISO 7064 MOD 97-10: control = 98 - (N * 100) % 97 (openapi.yml).
MODULO_CONTROL: Final[int] = 97
CONSTANTE_CONTROL: Final[int] = 98
FACTOR_CONTROL: Final[int] = 100

DIGITOS_MONTO_MAX: Final[int] = 10
LIMITE_TRANSFER: Final[int] = 100_000
STRIKES_PARA_BLOQUEO: Final[int] = 3
ANCHO_CORRELATIVO: Final[int] = 4
LIMITE_CUERPO_LOG: Final[int] = 500
NIVEL_LOG_DEFECTO: Final[str] = "INFO"


@dataclass(frozen=True, slots=True)
class Configuracion:
    """Parámetros de arranque inyectables en la aplicación.

    Args:
        token: Valor secreto comparado con `Authorization: Bearer <token>`.
        nivel_log: Nombre de nivel de `logging` (`INFO` si no se reconoce).
    """

    token: str
    nivel_log: str = NIVEL_LOG_DEFECTO


def configuracion_desde_entorno() -> Configuracion:
    """Lee token y nivel de log de las variables de entorno.

    Returns:
        Configuración de producción. El token vacío se rechaza al arrancar.
    """
    return Configuracion(
        token=os.environ.get("APP_AUTH_TOKEN", ""),
        nivel_log=os.environ.get("APP_LOG_LEVEL", NIVEL_LOG_DEFECTO),
    )
