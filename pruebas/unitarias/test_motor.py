"""Pruebas del motor de comandos."""

import pytest
from app.catalogo import CodigoError
from app.errores import ErrorDominio
from app.estado import estado_proceso
from app.pipeline import procesar
from pruebas.apoyo import firmar


def test_motor_alta_deja_saldo_0() -> None:
    alta = procesar(firmar("ALTA;Lucia"))

    assert alta.codigo is CodigoError.OK_ALTA
    assert alta.campos["cuentaId"] == "AC-0001"
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == "0.00"


def test_motor_deposito_suma_saldo() -> None:
    procesar(firmar("ALTA;Lucia"))

    deposito = procesar(firmar("DEPOSITO;AC-0001;250"))

    assert deposito.codigo is CodigoError.OK_DEPOSITO
    assert deposito.campos["operacionId"] == "OP-0001"
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == "2.50"


def test_motor_transfer_en_limite_100000_responde_e506() -> None:
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;100000"))

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;100000"))

    assert exc.value.codigo is CodigoError.E506


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
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == "0.00"


def test_motor_halt_sin_argumentos_responde_e302() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("HALT"))

    assert exc.value.codigo is CodigoError.E302


# Cada id cita docs/architecture/INCIDENT.md, salvo "-0.01": fórmula entero/100 del delta.
@pytest.mark.parametrize(
    ("pasos", "esperado"),
    [
        (["ALTA;A"], "0.00"),
        (["ALTA;A", "DEPOSITO;AC-0001;12345"], "123.45"),
        (["ALTA;A", "DEPOSITO;AC-0001;5"], "0.05"),
        (["ALTA;A", "DEPOSITO;AC-0001;123456789"], "1234567.89"),
        (
            [
                "ALTA;A",
                "ALTA;B",
                "DEPOSITO;AC-0001;500",
                "TRANSFER;AC-0001;AC-0002;500",
                "ANULA;OP-0001",
            ],
            "-5.00",
        ),
        (["ALTA;A", "DEPOSITO;AC-0001;9999999999"], "99999999.99"),
        (
            [
                "ALTA;A",
                "ALTA;B",
                "DEPOSITO;AC-0001;1",
                "TRANSFER;AC-0001;AC-0002;1",
                "ANULA;OP-0001",
            ],
            "-0.01",
        ),
    ],
    ids=[
        "inc 116",
        "inc 163",
        "inc 166",
        "inc 169",
        "inc 174",
        "inc 254",
        "formula del delta",
    ],
)
def test_motor_consulta_formatea_saldo_string(pasos: list[str], esperado: str) -> None:
    for paso in pasos:
        procesar(firmar(paso))

    consulta = procesar(firmar("CONSULTA;AC-0001"))

    assert consulta.campos["saldo"] == esperado


def test_motor_limite_transfer_50000_acepta() -> None:
    # inc 212 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;50000"))

    transferencia = procesar(firmar("TRANSFER;AC-0001;AC-0002;50000"))

    assert transferencia.codigo is CodigoError.OK_TRANSFER


def test_motor_limite_transfer_50001_responde_e506_y_suma_strike() -> None:
    # inc 213 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;50001"))

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;50001"))

    assert exc.value.codigo is CodigoError.E506
    assert estado_proceso.strikes_de("AC-0001") == 1


@pytest.mark.parametrize(
    "monto",
    [100000, 99999],
    ids=["inc 118 y 149", "inc 120"],
)
def test_motor_limite_transfer_monto_de_la_manana_responde_e506(monto: int) -> None:
    _dos_cuentas()
    procesar(firmar(f"DEPOSITO;AC-0001;{monto}"))

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar(f"TRANSFER;AC-0001;AC-0002;{monto}"))

    assert exc.value.codigo is CodigoError.E506


@pytest.mark.parametrize(
    "monto",
    [100001, 123456789],
    ids=["inc 179", "inc 168"],
)
def test_motor_limite_transfer_deposito_sobre_tope_acepta(monto: int) -> None:
    procesar(firmar("ALTA;A"))

    deposito = procesar(firmar(f"DEPOSITO;AC-0001;{monto}"))

    assert deposito.codigo is CodigoError.OK_DEPOSITO


def test_motor_limite_transfer_rechazado_no_crea_op_0002() -> None:
    # inc 124, 125, 127 y 128 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;500000"))

    with pytest.raises(ErrorDominio) as primero:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;100000"))
    with pytest.raises(ErrorDominio) as segundo:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;99999"))

    assert primero.value.codigo is CodigoError.E506
    assert segundo.value.codigo is CodigoError.E506
    with pytest.raises(ErrorDominio) as anula_primera:
        procesar(firmar("ANULA;OP-0002"))
    with pytest.raises(ErrorDominio) as anula_segunda:
        procesar(firmar("ANULA;OP-0002"))
    assert anula_primera.value.codigo is CodigoError.E402
    assert anula_segunda.value.codigo is CodigoError.E402
    assert procesar(firmar("CONSULTA;AC-0001")).campos["saldo"] == "5000.00"
    assert procesar(firmar("CONSULTA;AC-0002")).campos["saldo"] == "0.00"


def test_motor_e510_intentos_suben_1_2_y_3() -> None:
    # inc 225-227 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    _tres_rechazos(120000, CodigoError.E506)

    for esperado in (1, 2, 3):
        with pytest.raises(ErrorDominio) as exc:
            procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
        assert exc.value.codigo is CodigoError.E510
        assert exc.value.campos["intentos"] == esperado


def test_motor_deposito_propio_reinicia_intentos() -> None:
    # inc 235 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    _tres_rechazos(120000, CodigoError.E506)
    with pytest.raises(ErrorDominio):
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
    procesar(firmar("DEPOSITO;AC-0001;50"))
    _tres_rechazos(120000, CodigoError.E506)

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))

    assert exc.value.codigo is CodigoError.E510
    assert exc.value.campos["intentos"] == 1


def test_motor_tres_e507_cuarto_transfer_responde_e510_intentos() -> None:
    # inc 243-246 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    _tres_rechazos(1, CodigoError.E507)

    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))

    assert exc.value.codigo is CodigoError.E510
    assert exc.value.campos["intentos"] == 1


def test_motor_anula_no_desbloquea_siguiente_intentos() -> None:
    # inc 247-248 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;100"))
    _tres_rechazos(120000, CodigoError.E506)
    with pytest.raises(ErrorDominio) as primero:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
    assert primero.value.codigo is CodigoError.E510
    assert primero.value.campos["intentos"] == 1

    anula = procesar(firmar("ANULA;OP-0001"))

    assert anula.codigo is CodigoError.OK_ANULA
    with pytest.raises(ErrorDominio) as segundo:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
    assert segundo.value.codigo is CodigoError.E510
    assert segundo.value.campos["intentos"] == 2


def test_motor_consulta_y_transfer_inverso_no_responden_e510() -> None:
    # inc 228 y 229 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0002;10"))
    _tres_rechazos(120000, CodigoError.E506)
    with pytest.raises(ErrorDominio) as bloqueo:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
    assert bloqueo.value.codigo is CodigoError.E510

    consulta = procesar(firmar("CONSULTA;AC-0001"))
    inverso = procesar(firmar("TRANSFER;AC-0002;AC-0001;10"))

    assert consulta.codigo is CodigoError.OK_CONSULTA
    assert inverso.codigo is CodigoError.OK_TRANSFER


def test_motor_dos_strikes_transfer_40000_acepta_y_reinicia_intentos() -> None:
    # inc 221-225 (docs/architecture/INCIDENT.md).
    _dos_cuentas()
    procesar(firmar("DEPOSITO;AC-0001;40000"))
    _rechazos(2, 120000, CodigoError.E506)

    aceptada = procesar(firmar("TRANSFER;AC-0001;AC-0002;40000"))

    assert aceptada.codigo is CodigoError.OK_TRANSFER
    assert estado_proceso.strikes_de("AC-0001") == 0
    _tres_rechazos(120000, CodigoError.E506)
    with pytest.raises(ErrorDominio) as bloqueo:
        procesar(firmar("TRANSFER;AC-0001;AC-0002;1"))
    assert bloqueo.value.codigo is CodigoError.E510
    assert bloqueo.value.campos["intentos"] == 1


def _dos_cuentas() -> None:
    procesar(firmar("ALTA;A"))
    procesar(firmar("ALTA;B"))


def _tres_rechazos(monto: int, codigo: CodigoError) -> None:
    _rechazos(3, monto, codigo)


def _rechazos(veces: int, monto: int, codigo: CodigoError) -> None:
    for _ in range(veces):
        with pytest.raises(ErrorDominio) as exc:
            procesar(firmar(f"TRANSFER;AC-0001;AC-0002;{monto}"))
        assert exc.value.codigo is codigo
