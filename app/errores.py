"""Excepción de dominio que el catálogo traduce a una respuesta HTTP."""

from collections.abc import Mapping

from app.catalogo import CodigoError

type ValorCampo = str | int | bool


class ErrorDominio(Exception):  # noqa: N818  # el diseño nombra esta excepción ErrorDominio
    """Fallo de negocio identificado por un código del catálogo.

    Args:
        codigo: Entrada del catálogo que debe responderse.
        paso: Nombre del paso del pipeline que falló, si aplica.
        campos: Valores que sustituyen campos del cuerpo de ejemplo.
    """

    def __init__(
        self,
        codigo: CodigoError,
        paso: str | None = None,
        campos: Mapping[str, ValorCampo] | None = None,
    ) -> None:
        """Guarda el código, el paso y los campos de la respuesta."""
        self.codigo = codigo
        self.paso = paso
        self.campos: Mapping[str, ValorCampo] = {} if campos is None else campos
        super().__init__(codigo.value)
