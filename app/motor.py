"""Ejecución de PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA y HALT.

`HALT` responde el error del contrato y no detiene el proceso ni toca el estado.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.catalogo import CodigoError
from app.configuracion import LIMITE_TRANSFER, STRIKES_PARA_BLOQUEO
from app.errores import ErrorDominio, ValorCampo
from app.estado import Estado


@dataclass(frozen=True, slots=True)
class Resultado:
    """Comando aceptado, con los campos que completan el ejemplo del catálogo."""

    codigo: CodigoError
    campos: Mapping[str, ValorCampo]


def validar_cuentas(estado: Estado, comando: str, args: list[str]) -> None:
    """Rechaza cuentas citadas que no existen.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado a mayúsculas.
        args: Argumentos sin el control.

    Raises:
        ErrorDominio: `E401` si falta la cuenta de consulta, depósito o transferencia.
    """
    if comando in {"CONSULTA", "DEPOSITO"} and not estado.existe_cuenta(args[0]):
        raise ErrorDominio(CodigoError.E401, paso="cuentas")
    if comando == "TRANSFER" and (
        not estado.existe_cuenta(args[0]) or not estado.existe_cuenta(args[1])
    ):
        raise ErrorDominio(CodigoError.E401, paso="cuentas")


def validar_halt_u_operacion(estado: Estado, comando: str, args: list[str]) -> None:
    """Resuelve `HALT` y la existencia de la operación a anular.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado.
        args: Argumentos sin el control.

    Raises:
        ErrorDominio: `E520` en `HALT`, o `E402` si la operación no existe.
    """
    if comando == "HALT":
        # No altera cuentas, saldos, operaciones ni strikes (spec HALT).
        raise ErrorDominio(CodigoError.E520, paso="halt_u_operacion")
    if comando == "ANULA" and estado.obtener_operacion(args[0]) is None:
        raise ErrorDominio(CodigoError.E402, paso="halt_u_operacion")


def validar_bloqueo(estado: Estado, comando: str, args: list[str]) -> None:
    """Bloquea la transferencia cuando el origen ya acumuló tres strikes.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado.
        args: Argumentos sin el control.

    Raises:
        ErrorDominio: `E510` sin ejecutar la transferencia ni sumar otro strike.
    """
    if comando == "TRANSFER" and estado.strikes_de(args[0]) >= STRIKES_PARA_BLOQUEO:
        raise ErrorDominio(CodigoError.E510, paso="bloqueo")


def validar_limite(estado: Estado, comando: str, args: list[str], monto: int) -> None:
    """Rechaza una transferencia por encima de 100000 y suma un strike.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado.
        args: Argumentos sin el control.
        monto: Monto ya validado.

    Raises:
        ErrorDominio: `E506` si el monto supera el límite inclusive.
    """
    if comando == "TRANSFER" and monto > LIMITE_TRANSFER:
        estado.sumar_strike(args[0])
        raise ErrorDominio(CodigoError.E506, paso="limite")


def validar_saldo(estado: Estado, comando: str, args: list[str], monto: int) -> None:
    """Rechaza una transferencia sin saldo y suma un strike.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado.
        args: Argumentos sin el control.
        monto: Monto ya validado.

    Raises:
        ErrorDominio: `E507` si el origen no cubre el monto.
    """
    if comando == "TRANSFER" and estado.saldo_de(args[0]) < monto:
        estado.sumar_strike(args[0])
        raise ErrorDominio(CodigoError.E507, paso="saldo")


def ejecutar(estado: Estado, comando: str, args: list[str], monto: int) -> Resultado:
    """Aplica un comando que ya pasó el pipeline.

    Args:
        estado: Estado del proceso.
        comando: Comando ya normalizado.
        args: Argumentos sin el control.
        monto: Monto validado, o 0 si el comando no lo usa.

    Returns:
        Código de éxito y los campos dinámicos del cuerpo.
    """
    if comando == "ANULA":
        return _anular(estado, args[0])
    return _EXITOS[comando](estado, args, monto)


def _anular(estado: Estado, operacion: str) -> Resultado:
    if estado.anular(operacion):
        return Resultado(CodigoError.OK_ANULA, {"anulada": operacion})
    return Resultado(CodigoError.OK_ANULA_YA_ANULADA, {})


def _ping(_estado: Estado, _args: list[str], _monto: int) -> Resultado:
    return Resultado(CodigoError.OK_PING, {})


def _alta(estado: Estado, _args: list[str], _monto: int) -> Resultado:
    return Resultado(CodigoError.OK_ALTA, {"cuentaId": estado.crear_cuenta()})


def _consulta(estado: Estado, args: list[str], _monto: int) -> Resultado:
    cuenta = args[0]
    return Resultado(
        CodigoError.OK_CONSULTA,
        {"cuenta_id": cuenta, "saldo": estado.saldo_de(cuenta)},
    )


def _deposito(estado: Estado, args: list[str], monto: int) -> Resultado:
    return Resultado(
        CodigoError.OK_DEPOSITO,
        {"operacionId": estado.depositar(args[0], monto)},
    )


def _transferir(estado: Estado, args: list[str], monto: int) -> Resultado:
    return Resultado(
        CodigoError.OK_TRANSFER,
        {"operacionId": estado.transferir(args[0], args[1], monto)},
    )


_EXITOS = {
    "PING": _ping,
    "ALTA": _alta,
    "CONSULTA": _consulta,
    "DEPOSITO": _deposito,
    "TRANSFER": _transferir,
}
