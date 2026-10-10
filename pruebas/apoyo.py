"""Ayudas de las pruebas. No forman parte del paquete desplegable."""

from app.control import calcular_control


def firmar(base: str) -> str:
    """Agrega el control textual calculado para `base`."""
    return f"{base};{calcular_control(base)}"
