"""Pruebas del motor de comandos."""

import pytest
from app.catalogo import CodigoError
from app.errores import ErrorDominio
from app.pipeline import procesar
from pruebas.apoyo import firmar


def test_motor_alta_deja_saldo_0() -> None:
    alta = procesar(firmar("ALTA;Lucia"))

    assert alta.codigo is CodigoError.OK_ALTA
    assert alta.campos["cuentaId"] == "AC-0001"
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == 0


def test_motor_deposito_suma_saldo() -> None:
    procesar(firmar("ALTA;Lucia"))

    deposito = procesar(firmar("DEPOSITO;AC-0001;250"))

    assert deposito.codigo is CodigoError.OK_DEPOSITO
    assert deposito.campos["operacionId"] == "OP-0001"
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == 250


def test_motor_transfer_en_limite_100000_acepta() -> None:
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;100000"))

    transferencia = procesar(firmar("TRANSFER;AC-0001;AC-0002;100000"))

    assert transferencia.codigo is CodigoError.OK_TRANSFER
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == 0
    assert procesar(firmar("CONSULTA;AC-0002")).campos["saldo"] == 100000


def test_motor_monto_120000_responde_e506() -> None:
    _dos_cuentas()

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;120000"))

    assert exc.value.codigo is CodigoError.E506


def test_motor_saldo_insuficiente_responde_e507() -> None:
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;100"))

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;500"))

    assert exc.value.codigo is CodigoError.E507


def test_motor_cuarto_intento_responde_e510() -> None:
    _dos_cuentas()
    for _ in range(3):
        with pytest.raises(ErrorDominio) as exc:
            procesar(firmar("TRANSFER;AC-0001;AC-0002;120000"))
        assert exc.value.codigo is CodigoError.E506

    with pytest.raises(ErrorDominio) as bloqueo:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))

    assert bloqueo.value.codigo is CodigoError.E510


def test_motor_deposito_propio_desbloquea() -> None:
    _dos_cuentas()
    for _ in range(3):
        with pytest.raises(ErrorDominio):
            procesar(firmar("TRANSFER;AC-0001;AC-0002;120000"))
    procesar(firmar("DEPOSITO;AC-0001;50"))

    transferencia = procesar(firmar("TRANSFER;AC-0001;AC-0002;50"))

    assert transferencia.codigo is CodigoError.OK_TRANSFER


def test_motor_halt_con_argumento_no_cambia_estado() -> None:
    alta = procesar(firmar("ALTA;A"))

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("HALT;X"))

    assert exc.value.codigo is CodigoError.E520
    assert alta.campos["cuentaId"] == "AC-0001"
    assert procesar(firmar("ALTA;B")).campos["cuentaId"] == "AC-0002"
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == 0


def test_motor_halt_sin_argumentos_responde_e302() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("HALT"))

    assert exc.value.codigo is CodigoError.E302


def _dos_cuentas() -> None:
    procesar(firmar("ALTA;A"))
    procesar(firmar("ALTA;B"))
