"""Pipeline del mensaje: se detiene en el primer `ErrorDominio`.

`PING` omite el formato y el valor del control, y no omite el segmento vacío
(`docs/standards/openapi.yml`).
"""

from dataclasses import dataclass

from app.catalogo import CodigoError
from app.configuracion import (
    ARIDAD,
    COMANDOS,
    COMANDOS_CON_MONTO,
    COMANDOS_EXENTOS_CONTROL,
    DIGITOS_MONTO_MAX,
    ORDEN_MENSAJE,
)
from app.control import coincide, formato_valido
from app.errores import ErrorDominio
from app.estado import Estado, estado_proceso
from app.motor import (
    Resultado,
    validar_bloqueo,
    validar_cuentas,
    validar_halt_u_operacion,
    validar_limite,
    validar_saldo,
)
from app.motor import ejecutar as ejecutar_comando

_DISTANCIA_MAXIMA = 2


_MINIMO_SEGMENTOS = 2


@dataclass(slots=True)
class _Ctx:
    mensaje: str
    estado: Estado
    comando: str = ""
    args: list[str] | None = None
    control: str = ""
    prefijo: str = ""
    monto: int = 0
    resultado: Resultado | None = None

    def argumentos(self) -> list[str]:
        """Devuelve los argumentos ya partidos, o una lista vacía."""
        if self.args is None:
            return []
        return self.args


def procesar(mensaje: str, estado: Estado | None = None) -> Resultado:
    """Valida `m` en el orden configurado y ejecuta el comando.

    Args:
        mensaje: Valor string de `m`, que puede ser vacío.
        estado: Estado a usar. Por defecto, el del proceso.

    Returns:
        Resultado de éxito del motor.

    Raises:
        ErrorDominio: Primer fallo del pipeline.
    """
    ctx = _Ctx(mensaje, estado_proceso if estado is None else estado)
    for nombre in ORDEN_MENSAJE:
        _PASOS[nombre](ctx)
        if ctx.resultado is not None:
            return ctx.resultado
    raise RuntimeError("el pipeline no produjo resultado")


def _paso_segmentos(ctx: _Ctx) -> None:
    # Sin trim: los espacios son parte del segmento (openapi.yml).
    segmentos = ctx.mensaje.split(";")
    if len(segmentos) < _MINIMO_SEGMENTOS:
        raise ErrorDominio(CodigoError.E103, paso="segmentos")
    if any(segmento == "" for segmento in segmentos):
        raise ErrorDominio(CodigoError.E104, paso="segmentos")
    ctx.comando = segmentos[0].upper()
    ctx.args = segmentos[1:-1]
    ctx.control = segmentos[-1]
    ctx.prefijo = ";".join(segmentos[:-1])


def _paso_control(ctx: _Ctx) -> None:
    if ctx.comando in COMANDOS_EXENTOS_CONTROL:
        return
    if not formato_valido(ctx.control):
        raise ErrorDominio(CodigoError.E201, paso="control")
    if not coincide(ctx.control, ctx.prefijo):
        raise ErrorDominio(CodigoError.E202, paso="control")


def _paso_comando(ctx: _Ctx) -> None:
    if ctx.comando in COMANDOS:
        return
    sugerencia = _sugerencia(ctx.comando)
    if sugerencia is None:
        raise ErrorDominio(CodigoError.E301, paso="comando")
    raise ErrorDominio(
        CodigoError.E301_SUGERENCIA,
        paso="comando",
        campos={"sugerencia": sugerencia},
    )


def _paso_aridad(ctx: _Ctx) -> None:
    if len(ctx.argumentos()) != ARIDAD[ctx.comando]:
        raise ErrorDominio(CodigoError.E302, paso="aridad")


def _paso_monto(ctx: _Ctx) -> None:
    if ctx.comando not in COMANDOS_CON_MONTO:
        return
    texto = ctx.argumentos()[-1]
    if not _monto_valido(texto):
        raise ErrorDominio(CodigoError.E303, paso="monto")
    ctx.monto = int(texto)


def _paso_origen_destino(ctx: _Ctx) -> None:
    args = ctx.argumentos()
    if ctx.comando == "TRANSFER" and args[0] == args[1]:
        raise ErrorDominio(CodigoError.E304, paso="origen_destino")


def _paso_cuentas(ctx: _Ctx) -> None:
    validar_cuentas(ctx.estado, ctx.comando, ctx.argumentos())


def _paso_halt_u_operacion(ctx: _Ctx) -> None:
    validar_halt_u_operacion(ctx.estado, ctx.comando, ctx.argumentos())


def _paso_bloqueo(ctx: _Ctx) -> None:
    validar_bloqueo(ctx.estado, ctx.comando, ctx.argumentos())


def _paso_limite(ctx: _Ctx) -> None:
    validar_limite(ctx.estado, ctx.comando, ctx.argumentos(), ctx.monto)


def _paso_saldo(ctx: _Ctx) -> None:
    validar_saldo(ctx.estado, ctx.comando, ctx.argumentos(), ctx.monto)


def _paso_ejecutar(ctx: _Ctx) -> None:
    ctx.resultado = ejecutar_comando(ctx.estado, ctx.comando, ctx.argumentos(), ctx.monto)


def _monto_valido(texto: str) -> bool:
    if not texto or len(texto) > DIGITOS_MONTO_MAX:
        return False
    if not all("0" <= caracter <= "9" for caracter in texto):
        return False
    return texto[0] != "0"


def _sugerencia(comando: str) -> str | None:
    mejor: str | None = None
    mejor_distancia = _DISTANCIA_MAXIMA + 1
    for real in COMANDOS:
        distancia = _levenshtein(comando, real)
        if distancia > _DISTANCIA_MAXIMA:
            continue
        if (
            mejor is None
            or distancia < mejor_distancia
            or (distancia == mejor_distancia and real < mejor)
        ):
            mejor = real
            mejor_distancia = distancia
    return mejor


def _levenshtein(origen: str, destino: str) -> int:
    if origen == destino:
        return 0
    if not origen:
        return len(destino)
    if not destino:
        return len(origen)
    previa = list(range(len(destino) + 1))
    for indice, caracter in enumerate(origen, start=1):
        fila = [indice]
        for columna, otro in enumerate(destino, start=1):
            sustituir = previa[columna - 1] + (caracter != otro)
            fila.append(min(fila[columna - 1] + 1, previa[columna] + 1, sustituir))
        previa = fila
    return previa[-1]


_PASOS = {
    "segmentos": _paso_segmentos,
    "control": _paso_control,
    "comando": _paso_comando,
    "aridad": _paso_aridad,
    "monto": _paso_monto,
    "origen_destino": _paso_origen_destino,
    "cuentas": _paso_cuentas,
    "halt_u_operacion": _paso_halt_u_operacion,
    "bloqueo": _paso_bloqueo,
    "limite": _paso_limite,
    "saldo": _paso_saldo,
    "ejecutar": _paso_ejecutar,
}
