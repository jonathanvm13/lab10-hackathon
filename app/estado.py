"""Cuentas, saldos, operaciones, strikes y correlativos del proceso.

Un solo objeto por proceso. `reset` lo devuelve al estado inicial.
"""

from dataclasses import dataclass

from app.configuracion import ANCHO_CORRELATIVO


@dataclass(slots=True)
class Cuenta:
    """Cuenta en memoria, con saldo y strikes de transferencia."""

    identificador: str
    saldo: int
    strikes: int = 0


@dataclass(slots=True)
class Operacion:
    """Depósito o transferencia que `ANULA` puede revertir.

    `destino` es `None` en un depósito. Anular no crea otra operación.
    """

    identificador: str
    tipo: str
    monto: int
    origen: str
    destino: str | None
    anulada: bool = False


class Estado:
    """Estado mutable del mini banco dentro de este proceso."""

    def __init__(self) -> None:
        """Deja cuentas y operaciones vacías, con los correlativos en 1."""
        self.cuentas: dict[str, Cuenta] = {}
        self.operaciones: dict[str, Operacion] = {}
        self.siguiente_cuenta = 1
        self.siguiente_operacion = 1

    def reset(self) -> None:
        """Borra cuentas, operaciones y strikes, y reinicia los correlativos."""
        self.cuentas = {}
        self.operaciones = {}
        self.siguiente_cuenta = 1
        self.siguiente_operacion = 1

    def existe_cuenta(self, identificador: str) -> bool:
        """Indica si la cuenta fue dada de alta en este estado.

        Args:
            identificador: Id tal cual, con mayúsculas significativas.

        Returns:
            `True` si la cuenta existe.
        """
        return identificador in self.cuentas

    def saldo_de(self, identificador: str) -> int:
        """Devuelve el saldo actual de una cuenta existente.

        Args:
            identificador: Id de la cuenta.

        Returns:
            Saldo, que puede ser negativo tras una anulación.
        """
        return self.cuentas[identificador].saldo

    def strikes_de(self, identificador: str) -> int:
        """Devuelve los strikes acumulados de una cuenta origen.

        Args:
            identificador: Id de la cuenta origen.

        Returns:
            Cantidad de `E506` o `E507` desde el último reinicio.
        """
        return self.cuentas[identificador].strikes

    def sumar_strike(self, identificador: str) -> None:
        """Suma un strike a la cuenta origen.

        Args:
            identificador: Id de la cuenta que originó la transferencia.
        """
        self.cuentas[identificador].strikes += 1

    def crear_cuenta(self) -> str:
        """Crea la siguiente cuenta con saldo 0.

        Returns:
            Id `AC-NNNN` recién asignado.
        """
        identificador = f"AC-{self.siguiente_cuenta:0{ANCHO_CORRELATIVO}d}"
        self.siguiente_cuenta += 1
        self.cuentas[identificador] = Cuenta(identificador, 0)
        return identificador

    def depositar(self, identificador: str, monto: int) -> str:
        """Suma un depósito y reinicia los strikes de esa cuenta.

        Args:
            identificador: Cuenta que recibe el depósito.
            monto: Monto ya validado.

        Returns:
            Id `OP-NNNN` de la operación.
        """
        self.cuentas[identificador].saldo += monto
        self.cuentas[identificador].strikes = 0
        return self._registrar("DEPOSITO", monto, identificador, None)

    def transferir(self, origen: str, destino: str, monto: int) -> str:
        """Mueve un monto y reinicia los strikes del origen.

        Args:
            origen: Cuenta que entrega el monto.
            destino: Cuenta que lo recibe.
            monto: Monto ya validado.

        Returns:
            Id `OP-NNNN` de la operación.
        """
        self.cuentas[origen].saldo -= monto
        self.cuentas[destino].saldo += monto
        self.cuentas[origen].strikes = 0
        return self._registrar("TRANSFER", monto, origen, destino)

    def obtener_operacion(self, identificador: str) -> Operacion | None:
        """Busca una operación emitida.

        Args:
            identificador: Id `OP-NNNN` u otro texto citado por `ANULA`.

        Returns:
            La operación, o `None` si nunca se emitió.
        """
        return self.operaciones.get(identificador)

    def anular(self, identificador: str) -> bool:
        """Revierte una operación si todavía no estaba anulada.

        Anular un depósito resta el monto aunque el saldo quede negativo.
        Anular una transferencia devuelve el monto al origen y lo quita del
        destino. No consume un correlativo `OP`.

        Args:
            identificador: Id de una operación existente.

        Returns:
            `True` si esta llamada anuló la operación. `False` si ya lo estaba.
        """
        operacion = self.operaciones[identificador]
        if operacion.anulada:
            return False
        if operacion.tipo == "DEPOSITO":
            self.cuentas[operacion.origen].saldo -= operacion.monto
        else:
            self.cuentas[operacion.origen].saldo += operacion.monto
            destino = operacion.destino
            if destino is None:
                raise RuntimeError("transferencia sin destino")
            self.cuentas[destino].saldo -= operacion.monto
        operacion.anulada = True
        return True

    def _registrar(
        self,
        tipo: str,
        monto: int,
        origen: str,
        destino: str | None,
    ) -> str:
        identificador = f"OP-{self.siguiente_operacion:0{ANCHO_CORRELATIVO}d}"
        self.siguiente_operacion += 1
        self.operaciones[identificador] = Operacion(
            identificador,
            tipo,
            monto,
            origen,
            destino,
        )
        return identificador


estado_proceso = Estado()


def reset() -> None:
    """Reinicia el estado único del proceso."""
    estado_proceso.reset()
