"""Pruebas del estado en memoria."""

from app.estado import Estado, estado_proceso, reset


def test_estado_reset_vuelve_correlativos_a_0001() -> None:
    estado = Estado()
    estado.crear_cuenta()
    estado.depositar("AC-0001", 10)

    estado.reset()

    assert estado.crear_cuenta() == "AC-0001"
    assert estado.depositar("AC-0001", 1) == "OP-0001"
    estado_proceso.crear_cuenta()
    reset()
    assert estado_proceso.crear_cuenta() == "AC-0001"


def test_estado_deposito_suma_y_transferencia_mueve_los_dos_saldos() -> None:
    estado = Estado()
    origen = estado.crear_cuenta()
    destino = estado.crear_cuenta()

    estado.depositar(origen, 40)
    estado.depositar(origen, 2)
    estado.transferir(origen, destino, 15)

    assert estado.saldo_de(origen) == 27
    assert estado.saldo_de(destino) == 15


def test_estado_anular_deposito_gastado_deja_saldo_negativo() -> None:
    estado = Estado()
    origen = estado.crear_cuenta()
    destino = estado.crear_cuenta()
    deposito = estado.depositar(origen, 1000)
    estado.transferir(origen, destino, 1000)

    assert estado.anular(deposito) is True

    assert estado.saldo_de(origen) == -1000


def test_estado_anular_transferencia_revierte_ambos_lados() -> None:
    estado = Estado()
    origen = estado.crear_cuenta()
    destino = estado.crear_cuenta()
    estado.depositar(origen, 500)
    transferencia = estado.transferir(origen, destino, 200)

    assert estado.anular(transferencia) is True

    assert estado.saldo_de(origen) == 500
    assert estado.saldo_de(destino) == 0


def test_estado_anula_no_consume_correlativo_op() -> None:
    estado = Estado()
    cuenta = estado.crear_cuenta()
    primera = estado.depositar(cuenta, 10)

    estado.anular(primera)
    segunda = estado.depositar(cuenta, 5)

    assert primera == "OP-0001"
    assert segunda == "OP-0002"


def test_estado_segunda_anulacion_no_mueve_saldos() -> None:
    estado = Estado()
    origen = estado.crear_cuenta()
    destino = estado.crear_cuenta()
    estado.depositar(origen, 80)
    transferencia = estado.transferir(origen, destino, 30)

    assert estado.anular(transferencia) is True
    assert estado.anular(transferencia) is False

    assert estado.saldo_de(origen) == 80
    assert estado.saldo_de(destino) == 0


def test_estado_strikes_suben_y_el_deposito_los_reinicia() -> None:
    estado = Estado()
    origen = estado.crear_cuenta()
    estado.sumar_strike(origen)
    estado.sumar_strike(origen)
    assert estado.strikes_de(origen) == 2

    operacion = estado.depositar(origen, 50)
    assert estado.strikes_de(origen) == 0
    estado.sumar_strike(origen)
    estado.anular(operacion)

    assert estado.strikes_de(origen) == 1
    assert estado.saldo_de(origen) == 0
