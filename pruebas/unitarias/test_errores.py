"""Pruebas de la excepción de dominio."""

from app.catalogo import CodigoError
from app.errores import ErrorDominio


def test_errores_dominio_expone_codigo_y_paso() -> None:
    error = ErrorDominio(CodigoError.E104, paso="segmentos", campos={"sugerencia": "PING"})

    assert error.codigo is CodigoError.E104
    assert error.paso == "segmentos"
    assert error.campos["sugerencia"] == "PING"
    assert str(error) == "E104"


def test_errores_sin_campos_queda_vacio() -> None:
    error = ErrorDominio(CodigoError.E103)

    assert error.campos == {}
    assert error.paso is None
