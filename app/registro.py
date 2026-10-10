"""Log JSON a stdout y redacción del token."""

import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TextIO

from app.configuracion import LIMITE_CUERPO_LOG, Configuracion

_LOGGER = logging.getLogger("app")
_BEARER = re.compile(r"Bearer \S+")
_SUSTITUTO = "Bearer ***"
_CAMPOS_TEXTO = ("cuerpo", "metodo", "ruta", "codigo", "paso")


class FiltroRedaccion(logging.Filter):
    """Sustituye el token y cualquier `Bearer <valor>` antes de emitir el log."""

    def __init__(self, token: str) -> None:
        """Guarda el token que el filtro debe redactar."""
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        """Redacta el mensaje y los campos de texto del registro.

        Args:
            record: Registro que está por emitirse.

        Returns:
            Siempre `True`; el filtro no descarta registros.
        """
        record.msg = _redactar(str(record.msg), self._token)
        for campo in _CAMPOS_TEXTO:
            valor = getattr(record, campo, None)
            if isinstance(valor, str):
                setattr(record, campo, _redactar(valor, self._token))
        return True


class FormateadorJson(logging.Formatter):
    """Una línea JSON por registro, con traceback redactado si lo hay."""

    def __init__(self, token: str) -> None:
        """Guarda el token que el formateador debe redactar."""
        super().__init__()
        self._token = token

    def format(self, record: logging.LogRecord) -> str:
        """Serializa el registro a una línea JSON.

        Args:
            record: Registro ya filtrado.

        Returns:
            Objeto JSON compacto, sin el token.
        """
        payload: dict[str, object] = {
            "ts": _marca_tiempo(),
            "nivel": record.levelname,
            "metodo": getattr(record, "metodo", None),
            "ruta": getattr(record, "ruta", None),
            "status": getattr(record, "status", None),
            "codigo": getattr(record, "codigo", None),
            "paso": getattr(record, "paso", None),
            "duracion_ms": getattr(record, "duracion_ms", None),
            "cuerpo": getattr(record, "cuerpo", None),
        }
        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["traceback"] = record.exc_text
        return _redactar(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            self._token,
        )


def configurar_registro(configuracion: Configuracion) -> None:
    """Deja el logger `app` escribiendo JSON redactado a stdout.

    Args:
        configuracion: Token a redactar y nivel de log.
    """
    _LOGGER.handlers.clear()
    _LOGGER.setLevel(_nivel(configuracion.nivel_log))
    _LOGGER.propagate = False
    manejador = _ManejadorStdout()
    manejador.setFormatter(FormateadorJson(configuracion.token))
    manejador.addFilter(FiltroRedaccion(configuracion.token))
    _LOGGER.addHandler(manejador)


@dataclass(frozen=True, slots=True)
class RegistroSolicitud:
    """Datos de una request que se escriben en el log."""

    metodo: str
    ruta: str
    status: int
    codigo: str | None
    paso: str | None
    duracion_ms: float
    cuerpo: str


def registrar_solicitud(registro: RegistroSolicitud) -> None:
    """Emite el registro INFO de una request.

    Args:
        registro: Método, ruta, status, código, paso, duración y cuerpo.
    """
    _LOGGER.info(
        "solicitud",
        extra={
            "metodo": registro.metodo,
            "ruta": registro.ruta,
            "status": registro.status,
            "codigo": registro.codigo,
            "paso": registro.paso,
            "duracion_ms": registro.duracion_ms,
            "cuerpo": registro.cuerpo,
        },
    )


def registrar_excepcion(mensaje: str) -> None:
    """Emite un ERROR con el traceback de la excepción activa.

    Args:
        mensaje: Texto fijo del registro, sin datos de la request.
    """
    _LOGGER.exception(mensaje)


def truncar(texto: str, limite: int = LIMITE_CUERPO_LOG) -> str:
    """Trunca un texto al máximo de caracteres del log.

    Cuenta caracteres Unicode, no bytes.

    Args:
        texto: Texto a truncar, por ejemplo el cuerpo de la request.
        limite: Máximo de caracteres a conservar.

    Returns:
        El texto completo o sus primeros `limite` caracteres.
    """
    if len(texto) <= limite:
        return texto
    return texto[:limite]


def _redactar(texto: str, token: str) -> str:
    redactado = _BEARER.sub(_SUSTITUTO, texto)
    if token:
        return redactado.replace(token, _SUSTITUTO)
    return redactado


def _marca_tiempo() -> str:
    ahora = datetime.now(UTC)
    return ahora.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ahora.microsecond // 1000:03d}Z"


class _ManejadorStdout(logging.StreamHandler[TextIO]):
    """Escribe en el stdout vigente, para que las pruebas capturen el log."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        """Emite el registro hacia el stdout actual.

        Args:
            record: Registro ya filtrado y formateado por el handler.
        """
        self.stream = sys.stdout
        super().emit(record)


def _nivel(nombre: str) -> int:
    return logging.getLevelNamesMapping().get(nombre.upper(), logging.INFO)
