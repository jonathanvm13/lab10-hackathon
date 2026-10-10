"""Pruebas del orden del pipeline."""

import pytest
from app.catalogo import CodigoError
from app.errores import ErrorDominio
from app.pipeline import procesar
from pruebas.apoyo import firmar


def test_pipeline_e303_gana_antes_de_e304() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-0001;AC-0001;abc"))

    assert exc.value.codigo is CodigoError.E303


def test_pipeline_e304_gana_antes_de_e401() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar(firmar("TRANSFER;AC-9999;AC-9999;100"))

    assert exc.value.codigo is CodigoError.E304


def test_pipeline_e201_gana_antes_del_comando() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar("ZZZQ;100")

    assert exc.value.codigo is CodigoError.E201


@pytest.mark.parametrize("mensaje", ["PING;", "PING;X;"], ids=["PING;", "PING;X;"])
def test_pipeline_ping_segmento_vacio_responde_e104(mensaje: str) -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar(mensaje)

    assert exc.value.codigo is CodigoError.E104


def test_pipeline_ping_segundo_segmento_no_vacio_no_aplica_e202() -> None:
    resultado = procesar("PING;XX")

    assert resultado.codigo is CodigoError.OK_PING


def test_pipeline_m_vacio_responde_e103() -> None:
    with pytest.raises(ErrorDominio) as exc:
        procesar("")

    assert exc.value.codigo is CodigoError.E103
